"""
章节生成路由

处理章节内容的生成和重试操作。
"""

import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.constants import LLMConstants
from ....core.state_validators import (
    validate_project_status,
    CHAPTER_GENERATION_STATES,
)
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
from ....services.chapter_generation import (
    ChapterGenerationService,
    ChapterGenerationWorkflow,
)
from ....services.llm_service import LLMService
from ....services.novel_service import NovelService
from ....services.prompt_service import PromptService
from ....services.vector_store_service import VectorStoreService
from ....utils.json_utils import extract_llm_content
from ....utils.prompt_helpers import ensure_prompt
from ....utils.sse_helpers import sse_event, create_sse_response

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

    使用ChapterGenerationWorkflow封装业务逻辑，保持Router层简洁。
    """
    logger.info(
        "收到章节生成请求: project_id=%s chapter_number=%s user_id=%s",
        project_id, request.chapter_number, desktop_user.id
    )

    # 状态校验：确保项目处于可生成章节的状态
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    validate_project_status(project.status, CHAPTER_GENERATION_STATES, "生成章节内容")

    # 顺序校验：第2章及以后的章节必须确保前一章已有选定的正文版本
    chapter_number = request.chapter_number
    if chapter_number > 1:
        prev_chapter = next(
            (ch for ch in project.chapters if ch.chapter_number == chapter_number - 1),
            None
        )
        # 检查前一章是否存在、是否有选定版本、选定版本是否有内容
        if not prev_chapter or not prev_chapter.selected_version_id:
            raise InvalidParameterError(
                f"请先完成第{chapter_number - 1}章的生成并选择一个版本后，再生成第{chapter_number}章",
                parameter="chapter_number"
            )
        # 验证选定版本是否有实际内容
        selected_version = prev_chapter.selected_version
        if not selected_version or not selected_version.content or not selected_version.content.strip():
            raise InvalidParameterError(
                f"第{chapter_number - 1}章尚无正文内容，请先生成正文后再生成第{chapter_number}章",
                parameter="chapter_number"
            )
        logger.debug(
            "章节顺序校验通过: 第%d章已有选定版本(id=%d, 字数=%d)",
            chapter_number - 1, selected_version.id, len(selected_version.content or "")
        )

    # 创建工作流并执行
    workflow = ChapterGenerationWorkflow(
        session=session,
        llm_service=llm_service,
        novel_service=novel_service,
        prompt_service=prompt_service,
        project_id=project_id,
        chapter_number=request.chapter_number,
        user_id=desktop_user.id,
        writing_notes=request.writing_notes,
        vector_store=vector_store,
    )

    result = await workflow.execute()
    logger.info(
        "项目 %s 第 %s 章生成完成，共 %s 个版本",
        project_id, request.chapter_number, result.version_count
    )

    # 返回最新项目数据
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

    # 状态校验：确保项目处于可生成章节的状态
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    validate_project_status(project.status, CHAPTER_GENERATION_STATES, "重新生成章节版本")

    # 初始化章节生成服务
    chapter_gen_service = ChapterGenerationService(session, llm_service)

    chapter = next((ch for ch in project.chapters if ch.chapter_number == request.chapter_number), None)
    if not chapter or not chapter.versions:
        raise ChapterNotGeneratedError(project_id, request.chapter_number)

    versions = sorted(chapter.versions, key=lambda item: item.created_at)
    if request.version_index < 0 or request.version_index >= len(versions):
        raise InvalidParameterError("版本索引无效")

    # 获取大纲
    outline = await novel_service.get_outline_or_raise(project_id, request.chapter_number)

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
        rag_context=gen_context.rag_context,
        writing_notes=request.custom_prompt,
    )

    # 生成单个版本
    response = await llm_service.get_llm_response(
        system_prompt=writer_prompt,
        conversation_history=[{"role": "user", "content": prompt_input}],
        temperature=settings.llm_temp_writing,
        user_id=desktop_user.id,
        timeout=LLMConstants.CHAPTER_GENERATION_TIMEOUT,
        max_tokens=LLMConstants.CHAPTER_MAX_TOKENS,
        response_format=None,  # 章节内容是纯文本，不使用 JSON 模式
    )

    # 使用统一的内容提取方法
    new_content, _ = extract_llm_content(response)

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
    outline = await novel_service.get_outline_or_raise(project_id, request.chapter_number)

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
            rag_context=gen_context.rag_context,
            writing_notes=request.writing_notes,
        )
    else:
        # 首次生成模式：使用完整版提示词（包含分层前情摘要）
        prompt_input = chapter_gen_service.build_writing_prompt(
            outline=outline,
            blueprint_dict=blueprint_dict,
            previous_summary_text=previous_summary_text,
            previous_tail_excerpt=previous_tail_excerpt,
            rag_context=gen_context.rag_context,
            writing_notes=request.writing_notes,
            chapter_number=request.chapter_number,
            completed_chapters=completed_chapters,
        )

    # 6. 构建各部分内容（用于调试，与新的场景聚焦结构匹配）
    # 核心设定信息
    core_info_parts = []
    if blueprint_dict.get("genre"):
        core_info_parts.append(f"题材: {blueprint_dict['genre']}")
    if blueprint_dict.get("style"):
        core_info_parts.append(f"风格: {blueprint_dict['style']}")
    if blueprint_dict.get("tone"):
        core_info_parts.append(f"基调: {blueprint_dict['tone']}")
    if blueprint_dict.get("one_sentence_summary"):
        core_info_parts.append(f"故事: {blueprint_dict['one_sentence_summary']}")
    characters = blueprint_dict.get("characters", [])
    if characters:
        names = [c.get("name", "") for c in characters if c.get("name")]
        if names:
            core_info_parts.append(f"角色名单: {', '.join(names)}")
    core_setting_text = "\n".join(core_info_parts) if core_info_parts else "暂无核心设定"

    outline_title = outline.title or f"第{outline.chapter_number}章"
    outline_summary = outline.summary or "暂无摘要"

    rag_chunks_text = "未检索到相关段落"
    rag_summaries_text = "未检索到章节摘要"
    rag_context = gen_context.rag_context
    if rag_context:
        if rag_context.chunks:
            rag_chunks_text = "\n\n".join(rag_context.chunk_texts())
        if rag_context.summaries:
            rag_summaries_text = "\n".join(rag_context.summary_lines())

    # 根据模式构建不同的分段内容（与新的场景聚焦结构匹配）
    if request.is_retry:
        # 重新生成模式：不包含前情摘要（复用之前获取的retry变量）
        prompt_sections = {
            "核心设定": core_setting_text,
            "当前任务": f"第{outline.chapter_number}章: {outline_title}\n大纲: {outline_summary}\n写作指令: {request.writing_notes or '无'}",
            "场景状态": f"上一章结尾:\n> {retry_previous_tail or '暂无上一章结尾内容'}\n\n上一章摘要: {retry_previous_summary or '暂无可用摘要'}",
            "相关段落": rag_chunks_text,
            "章节摘要": rag_summaries_text,
        }
    else:
        # 首次生成模式：包含完整前情摘要
        from ....utils.writer_helpers import build_layered_summary
        completed_section = build_layered_summary(completed_chapters, request.chapter_number)
        prompt_sections = {
            "核心设定": core_setting_text,
            "当前任务": f"第{outline.chapter_number}章: {outline_title}\n大纲: {outline_summary}\n写作指令: {request.writing_notes or '无'}",
            "场景状态": f"上一章结尾:\n> {previous_tail_excerpt or '暂无上一章结尾内容'}\n\n上一章摘要: {previous_summary_text or '暂无可用摘要'}",
            "前情摘要": completed_section or "暂无前情摘要",
            "相关段落": rag_chunks_text,
            "章节摘要": rag_summaries_text,
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


@router.post("/novels/{project_id}/chapters/generate-stream")
async def generate_chapter_stream(
    project_id: str,
    request: GenerateChapterRequest,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
):
    """
    生成章节内容（SSE流式返回进度）

    使用ChapterGenerationWorkflow.execute_with_progress()实现流式进度推送。

    事件类型：
    - progress: 阶段进度 {"stage", "message", "current", "total"}
    - complete: 完成 {"message", "chapter_number", "version_count"}
    - error: 错误 {"message"}

    阶段（stage）说明：
    - initializing: 初始化和验证
    - collecting_context: 收集历史章节上下文
    - preparing_prompt: 准备提示词和RAG检索
    - generating: 生成版本内容
    - saving: 保存结果
    """
    logger.info(
        "收到章节生成请求（SSE模式）: project_id=%s chapter_number=%s user_id=%s",
        project_id, request.chapter_number, desktop_user.id
    )

    # 状态校验：确保项目处于可生成章节的状态
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    validate_project_status(project.status, CHAPTER_GENERATION_STATES, "生成章节内容")

    # 创建工作流
    workflow = ChapterGenerationWorkflow(
        session=session,
        llm_service=llm_service,
        novel_service=novel_service,
        prompt_service=prompt_service,
        project_id=project_id,
        chapter_number=request.chapter_number,
        user_id=desktop_user.id,
        writing_notes=request.writing_notes,
        vector_store=vector_store,
    )

    async def event_generator():
        async for progress in workflow.execute_with_progress():
            stage = progress.get("stage", "unknown")
            if stage == "complete":
                yield sse_event("complete", progress)
            elif stage == "error":
                yield sse_event("error", progress)
            elif stage == "cancelled":
                # 用户取消操作，发送取消事件后正常结束
                yield sse_event("cancelled", progress)
            else:
                yield sse_event("progress", progress)

    return create_sse_response(event_generator())