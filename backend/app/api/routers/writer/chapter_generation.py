"""
章节生成路由

处理章节内容的生成和重试操作。
"""

import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.state_machine import ProjectStatus
from ....core.dependencies import (
    get_default_user,
    get_vector_store,
    get_novel_service,
    get_llm_service,
    get_prompt_service,
)
from ....db.session import get_session
from ....exceptions import (
    ChapterNotGeneratedError,
    InvalidParameterError,
    ResourceNotFoundError,
)
from ....schemas.novel import (
    GenerateChapterRequest,
    NovelProject as NovelProjectSchema,
    RetryVersionRequest,
    PromptPreviewRequest,
    PromptPreviewResponse,
    RAGStatistics,
)
from ....schemas.user import UserInDB
from ....services.chapter_generation_service import ChapterGenerationService
from ....services.llm_service import LLMService
from ....services.novel_service import NovelService
from ....services.prompt_service import PromptService
from ....services.vector_store_service import VectorStoreService
from ....utils.json_utils import (
    remove_think_tags,
    unwrap_markdown_json,
    parse_llm_json_safe,
)
from ....utils.prompt_helpers import ensure_prompt

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/novels/{project_id}/chapters/generate", response_model=NovelProjectSchema)
async def generate_chapter(
    project_id: str,
    request: GenerateChapterRequest,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> NovelProjectSchema:
    """
    生成章节内容，支持并行生成多个版本

    重构后的简化版本，业务逻辑已迁移到ChapterGenerationService
    """
    logger.info("=" * 100)
    logger.info("!!! 收到章节生成请求 !!!")
    logger.info("project_id=%s, chapter_number=%s, user_id=%s", project_id, request.chapter_number, desktop_user.id)
    logger.info("=" * 100)

    # 初始化章节生成服务
    chapter_gen_service = ChapterGenerationService(session, llm_service)

    # 1. 初始化和验证
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    logger.info("用户 %s 开始为项目 %s 生成第 %s 章", desktop_user.id, project_id, request.chapter_number)

    if project.status == ProjectStatus.CHAPTER_OUTLINES_READY.value:
        await novel_service.transition_project_status(project, ProjectStatus.WRITING.value)
        logger.info("项目 %s 状态更新为 %s", project_id, ProjectStatus.WRITING.value)

    version_count = chapter_gen_service.resolve_version_count()
    if settings.writer_parallel_generation and version_count > 1:
        await llm_service.enforce_daily_limit(desktop_user.id)
        logger.info("项目 %s 第 %s 章（并行模式）已完成 daily limit 检查", project_id, request.chapter_number)

    outline = await novel_service.get_outline(project_id, request.chapter_number)
    if not outline:
        logger.warning("项目 %s 未找到第 %s 章纲要，生成流程终止", project_id, request.chapter_number)
        raise ResourceNotFoundError("章节大纲", f"项目 {project_id} 第 {request.chapter_number} 章")

    chapter = await novel_service.get_or_create_chapter(project_id, request.chapter_number)
    chapter.real_summary = None
    chapter.selected_version_id = None
    chapter.status = "generating"
    await session.commit()

    # 2. 收集历史章节摘要
    completed_chapters, previous_summary_text, previous_tail_excerpt = await chapter_gen_service.collect_chapter_summaries(
        project=project,
        current_chapter_number=request.chapter_number,
        user_id=desktop_user.id,
        project_id=project_id,
    )

    # 3. 准备蓝图数据
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint_dict = project_schema.blueprint.model_dump()
    blueprint_dict = chapter_gen_service.prepare_blueprint_for_generation(blueprint_dict)

    # 4. 获取写作提示词并执行增强型RAG检索
    writer_prompt = ensure_prompt(await prompt_service.get_prompt("writing"), "writing")

    # 使用统一的上下文准备方法
    gen_context = await chapter_gen_service.prepare_generation_context(
        project=project,
        outline=outline,
        blueprint_dict=blueprint_dict,
        chapter_number=request.chapter_number,
        user_id=desktop_user.id,
        writing_notes=request.writing_notes,
        vector_store=vector_store,
    )

    # 获取旧版上下文格式（用于兼容现有的build_writing_prompt）
    rag_context = gen_context.enhanced_rag_context.get_legacy_context() if gen_context.enhanced_rag_context else None

    # 5. 构建完整提示词
    prompt_input = chapter_gen_service.build_writing_prompt(
        outline=outline,
        blueprint_dict=blueprint_dict,
        completed_chapters=completed_chapters,
        previous_summary_text=previous_summary_text,
        previous_tail_excerpt=previous_tail_excerpt,
        rag_context=rag_context,
        writing_notes=request.writing_notes,
        chapter_number=request.chapter_number,
    )
    logger.debug("章节写作提示词：%s\n%s", writer_prompt, prompt_input)

    # 6. 准备并行生成配置
    skip_usage_tracking = settings.writer_parallel_generation
    llm_config: Optional[Dict[str, Optional[str]]] = None
    if skip_usage_tracking:
        llm_config = await llm_service.resolve_llm_config_cached(desktop_user.id, skip_daily_limit_check=True)
        logger.info("项目 %s 第 %s 章（并行模式）已缓存 LLM 配置", project_id, request.chapter_number)

    # 7. 生成所有版本
    raw_versions = await chapter_gen_service.generate_chapter_versions(
        version_count=version_count,
        writer_prompt=writer_prompt,
        prompt_input=prompt_input,
        llm_config=llm_config,
        skip_usage_tracking=skip_usage_tracking,
        user_id=desktop_user.id,
        project_id=project_id,
        chapter_number=request.chapter_number,
    )

    # 8. 处理生成结果并保存
    contents, metadata = chapter_gen_service.process_generated_versions(raw_versions)
    await novel_service.replace_chapter_versions(chapter, contents, metadata)
    await session.commit()
    logger.info("项目 %s 第 %s 章生成完成，已写入 %s 个版本", project_id, request.chapter_number, len(contents))

    # 9. 返回最新项目数据
    session.expire_all()
    return await novel_service.get_project_schema(project_id, desktop_user.id)




@router.post("/novels/{project_id}/chapters/retry-version", response_model=NovelProjectSchema)
async def retry_chapter_version(
    project_id: str,
    request: RetryVersionRequest,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> NovelProjectSchema:
    """重新生成指定章节的某个版本"""
    logger.info("用户 %s 请求重试项目 %s 第 %s 章的版本 %s", desktop_user.id, project_id, request.chapter_number, request.version_index)

    # 初始化章节生成服务
    chapter_gen_service = ChapterGenerationService(session, llm_service)

    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    chapter = next((ch for ch in project.chapters if ch.chapter_number == request.chapter_number), None)
    if not chapter or not chapter.versions:
        raise ChapterNotGeneratedError(project_id, request.chapter_number)

    versions = sorted(chapter.versions, key=lambda item: item.created_at)
    if request.version_index < 0 or request.version_index >= len(versions):
        raise InvalidParameterError("版本索引无效")

    # 获取大纲
    outline = await novel_service.get_outline(project_id, request.chapter_number)
    if not outline:
        raise ResourceNotFoundError("章节大纲", f"项目 {project_id} 第 {request.chapter_number} 章")

    # 准备蓝图
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint_dict = project_schema.blueprint.model_dump()
    blueprint_dict = chapter_gen_service.prepare_blueprint_for_generation(blueprint_dict)

    writer_prompt = ensure_prompt(await prompt_service.get_prompt("writing"), "writing")

    # 使用统一的上下文准备方法
    gen_context = await chapter_gen_service.prepare_generation_context(
        project=project,
        outline=outline,
        blueprint_dict=blueprint_dict,
        chapter_number=request.chapter_number,
        user_id=desktop_user.id,
        writing_notes=request.custom_prompt,
        vector_store=vector_store,
    )

    # 获取RAG上下文
    rag_context = gen_context.enhanced_rag_context.get_legacy_context() if gen_context.enhanced_rag_context else None

    # 使用统一的方法获取上一章信息
    previous_summary_text, previous_tail_excerpt = chapter_gen_service.get_previous_chapter_info(
        project, request.chapter_number
    )

    # 使用统一的方法构建提示词
    prompt_input = chapter_gen_service.build_retry_prompt(
        outline=outline,
        blueprint_dict=blueprint_dict,
        previous_summary_text=previous_summary_text,
        previous_tail_excerpt=previous_tail_excerpt,
        rag_context=rag_context,
        writing_notes=request.custom_prompt,
    )

    # 生成单个版本
    response = await llm_service.get_llm_response(
        system_prompt=writer_prompt,
        conversation_history=[{"role": "user", "content": prompt_input}],
        temperature=settings.llm_temp_writing,
        user_id=desktop_user.id,
        timeout=600.0,
    )

    # 使用和generate_chapter_versions相同的处理逻辑
    cleaned = remove_think_tags(response)
    result = parse_llm_json_safe(cleaned)
    if result:
        raw_result = result
    else:
        raw_result = {"content": unwrap_markdown_json(cleaned)}

    # 使用统一的process_generated_versions方法提取content
    contents, _ = chapter_gen_service.process_generated_versions([raw_result])
    new_content = contents[0] if contents else unwrap_markdown_json(cleaned)

    # 替换指定版本的内容
    target_version = versions[request.version_index]
    target_version.content = new_content
    await session.commit()

    logger.info("项目 %s 第 %s 章版本 %s 重试完成", project_id, request.chapter_number, request.version_index)

    session.expire_all()
    return await novel_service.get_project_schema(project_id, desktop_user.id)


@router.post("/novels/{project_id}/chapters/preview-prompt", response_model=PromptPreviewResponse)
async def preview_chapter_prompt(
    project_id: str,
    request: PromptPreviewRequest,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> PromptPreviewResponse:
    """
    预览章节生成的提示词（用于测试RAG效果）

    此端点只构建提示词，不调用LLM生成内容，适用于：
    - 测试RAG检索效果
    - 调试提示词构建逻辑
    - 预估token消耗
    """
    logger.info(
        "用户 %s 预览项目 %s 第 %s 章的生成提示词 (is_retry=%s)",
        desktop_user.id, project_id, request.chapter_number, request.is_retry
    )

    # 初始化服务
    chapter_gen_service = ChapterGenerationService(session, llm_service)

    # 1. 验证项目和大纲
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    outline = await novel_service.get_outline(project_id, request.chapter_number)
    if not outline:
        raise ResourceNotFoundError("章节大纲", f"项目 {project_id} 第 {request.chapter_number} 章")

    # 2. 收集历史章节摘要
    completed_chapters, previous_summary_text, previous_tail_excerpt = await chapter_gen_service.collect_chapter_summaries(
        project=project,
        current_chapter_number=request.chapter_number,
        user_id=desktop_user.id,
        project_id=project_id,
    )

    # 3. 准备蓝图数据
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint_dict = project_schema.blueprint.model_dump()
    blueprint_dict = chapter_gen_service.prepare_blueprint_for_generation(blueprint_dict)

    # 4. 获取写作提示词并执行增强型RAG检索
    writer_prompt = ensure_prompt(await prompt_service.get_prompt("writing"), "writing")

    gen_context = await chapter_gen_service.prepare_generation_context(
        project=project,
        outline=outline,
        blueprint_dict=blueprint_dict,
        chapter_number=request.chapter_number,
        user_id=desktop_user.id,
        writing_notes=request.writing_notes,
        vector_store=vector_store,
    )

    # 获取RAG上下文
    rag_context = gen_context.enhanced_rag_context.get_legacy_context() if gen_context.enhanced_rag_context else None

    # 5. 根据模式构建提示词
    if request.is_retry:
        # 重新生成模式：使用简化版提示词（不包含完整前情摘要）
        # 对于重试，需要单独获取上一章信息
        retry_previous_summary, retry_previous_tail = chapter_gen_service.get_previous_chapter_info(
            project, request.chapter_number
        )
        prompt_input = chapter_gen_service.build_retry_prompt(
            outline=outline,
            blueprint_dict=blueprint_dict,
            previous_summary_text=retry_previous_summary,
            previous_tail_excerpt=retry_previous_tail,
            rag_context=rag_context,
            writing_notes=request.writing_notes,
        )
    else:
        # 首次生成模式：使用完整版提示词（包含分层前情摘要）
        prompt_input = chapter_gen_service.build_writing_prompt(
            outline=outline,
            blueprint_dict=blueprint_dict,
            completed_chapters=completed_chapters,
            previous_summary_text=previous_summary_text,
            previous_tail_excerpt=previous_tail_excerpt,
            rag_context=rag_context,
            writing_notes=request.writing_notes,
            chapter_number=request.chapter_number,
        )

    # 6. 构建各部分内容（用于调试）
    import json
    blueprint_text = json.dumps(blueprint_dict, ensure_ascii=False, indent=2)

    outline_title = outline.title or f"第{outline.chapter_number}章"
    outline_summary = outline.summary or "暂无摘要"

    rag_chunks_text = "未检索到章节片段"
    rag_summaries_text = "未检索到章节摘要"
    if rag_context:
        if rag_context.chunks:
            rag_chunks_text = "\n\n".join(rag_context.chunk_texts())
        if rag_context.summaries:
            rag_summaries_text = "\n".join(rag_context.summary_lines())

    # 根据模式构建不同的分段内容
    if request.is_retry:
        # 重新生成模式：不包含前情摘要
        prompt_sections = {
            "世界蓝图": blueprint_text,
            "上一章摘要": retry_previous_summary or "暂无可用摘要",
            "上一章结尾": retry_previous_tail or "暂无上一章结尾内容",
            "检索到的剧情上下文": rag_chunks_text,
            "检索到的章节摘要": rag_summaries_text,
            "当前章节目标": f"标题：{outline_title}\n摘要：{outline_summary}\n写作要求：{request.writing_notes or '无额外写作指令'}",
        }
    else:
        # 首次生成模式：包含完整前情摘要
        from ....utils.writer_helpers import build_layered_summary
        completed_section = build_layered_summary(completed_chapters, request.chapter_number)
        prompt_sections = {
            "世界蓝图": blueprint_text,
            "前情摘要": completed_section,
            "上一章摘要": previous_summary_text or "暂无可用摘要",
            "上一章结尾": previous_tail_excerpt or "暂无上一章结尾内容",
            "检索到的剧情上下文": rag_chunks_text,
            "检索到的章节摘要": rag_summaries_text,
            "当前章节目标": f"标题：{outline_title}\n摘要：{outline_summary}\n写作要求：{request.writing_notes or '无额外写作指令'}",
        }

    # 7. 构建RAG统计信息
    rag_stats = RAGStatistics()
    if gen_context.enhanced_rag_context:
        enhanced_ctx = gen_context.enhanced_rag_context
        rag_stats.chunk_count = len(rag_context.chunks) if rag_context and rag_context.chunks else 0
        rag_stats.summary_count = len(rag_context.summaries) if rag_context and rag_context.summaries else 0
        rag_stats.context_length = len(enhanced_ctx.compressed_context)

        # 提取查询信息
        if enhanced_ctx.enhanced_query:
            query = enhanced_ctx.enhanced_query
            rag_stats.query_main = query.main_query
            rag_stats.query_characters = query.character_queries or []
            rag_stats.query_foreshadowing = query.foreshadow_queries or []

    # 8. 估算token数量（简单估算：中文约1.5字符/token）
    total_length = len(writer_prompt) + len(prompt_input)
    estimated_tokens = int(total_length / 1.5)

    logger.info(
        "项目 %s 第 %s 章提示词预览完成: 总长度=%d, 估算tokens=%d, RAG chunks=%d, summaries=%d",
        project_id, request.chapter_number, total_length, estimated_tokens,
        rag_stats.chunk_count, rag_stats.summary_count
    )

    return PromptPreviewResponse(
        system_prompt=writer_prompt,
        user_prompt=prompt_input,
        rag_statistics=rag_stats,
        prompt_sections=prompt_sections,
        total_length=total_length,
        estimated_tokens=estimated_tokens,
    )


