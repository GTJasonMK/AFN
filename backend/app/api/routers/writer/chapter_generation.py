"""
章节生成路由

处理章节内容的生成和重试操作。
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

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
    PromptTemplateNotFoundError,
    ResourceNotFoundError,
)
from ....models.novel import Chapter, ChapterOutline
from ....schemas.novel import (
    GenerateChapterRequest,
    NovelProject as NovelProjectSchema,
    RetryVersionRequest,
)
from ....schemas.user import UserInDB
from ....repositories.chapter_repository import ChapterOutlineRepository
from ....services.chapter_context_service import ChapterContextService
from ....services.chapter_ingest_service import ChapterIngestionService
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
from ....utils.writer_helpers import extract_tail_excerpt
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

    # 4. 获取写作提示词并执行RAG检索
    writer_prompt = ensure_prompt(await prompt_service.get_prompt("writing"), "writing")

    context_service = ChapterContextService(llm_service=llm_service, vector_store=vector_store)
    outline_title = outline.title or f"第{outline.chapter_number}章"
    outline_summary = outline.summary or "暂无摘要"
    query_parts = [outline_title, outline_summary]
    if request.writing_notes:
        query_parts.append(request.writing_notes)
    rag_query = "\n".join(part for part in query_parts if part)
    rag_context = await context_service.retrieve_for_generation(
        project_id=project_id,
        query_text=rag_query or outline.title or outline.summary or "",
        user_id=desktop_user.id,
    )

    chunk_count = len(rag_context.chunks) if rag_context and rag_context.chunks else 0
    summary_count = len(rag_context.summaries) if rag_context and rag_context.summaries else 0
    logger.info("项目 %s 第 %s 章检索到 %s 个剧情片段和 %s 条摘要", project_id, request.chapter_number, chunk_count, summary_count)

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

    # 构建生成上下文（复用generate_chapter的逻辑）
    outline = await novel_service.get_outline(project_id, request.chapter_number)
    if not outline:
        raise ResourceNotFoundError("章节大纲", f"项目 {project_id} 第 {request.chapter_number} 章")

    outlines_map = {item.chapter_number: item for item in project.outlines}
    previous_summary_text = ""
    previous_tail_excerpt = ""
    latest_prev_number = -1

    for existing in project.chapters:
        if existing.chapter_number >= request.chapter_number:
            continue
        if existing.selected_version is None or not existing.selected_version.content:
            continue
        if existing.chapter_number > latest_prev_number:
            latest_prev_number = existing.chapter_number
            previous_summary_text = existing.real_summary or ""
            previous_tail_excerpt = extract_tail_excerpt(existing.selected_version.content)

    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint_dict = project_schema.blueprint.model_dump()
    blueprint_dict = chapter_gen_service.prepare_blueprint_for_generation(blueprint_dict)

    writer_prompt = ensure_prompt(await prompt_service.get_prompt("writing"), "writing")

    # 使用依赖注入的向量检索服务
    context_service = ChapterContextService(llm_service=llm_service, vector_store=vector_store)
    outline_title = outline.title or f"第{outline.chapter_number}章"
    outline_summary = outline.summary or "暂无摘要"
    query_parts = [outline_title, outline_summary]
    if request.custom_prompt:
        query_parts.append(request.custom_prompt)
    rag_query = "\n".join(query_parts)
    rag_context = await context_service.retrieve_for_generation(
        project_id=project_id,
        query_text=rag_query,
        user_id=desktop_user.id,
    )

    blueprint_text = json.dumps(blueprint_dict, ensure_ascii=False, indent=2)
    previous_summary_text = previous_summary_text or "暂无可用摘要"
    previous_tail_excerpt = previous_tail_excerpt or "暂无上一章结尾内容"
    rag_chunks_text = "\n\n".join(rag_context.chunk_texts()) if rag_context.chunks else "未检索到章节片段"
    rag_summaries_text = "\n".join(rag_context.summary_lines()) if rag_context.summaries else "未检索到章节摘要"

    # 如果用户提供了自定义提示词，添加到写作要求中
    writing_notes = request.custom_prompt or "无额外写作指令"

    prompt_sections = [
        ("[世界蓝图](JSON)", blueprint_text),
        ("[上一章摘要]", previous_summary_text),
        ("[上一章结尾]", previous_tail_excerpt),
        ("[检索到的剧情上下文](Markdown)", rag_chunks_text),
        ("[检索到的章节摘要]", rag_summaries_text),
        ("[当前章节目标]", f"标题：{outline_title}\n摘要：{outline_summary}\n写作要求：{writing_notes}"),
    ]
    prompt_input = "\n\n".join(f"{title}\n{content}" for title, content in prompt_sections if content)

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
        # JSON解析成功，直接使用
        raw_result = result
    else:
        # JSON解析失败，包装为标准格式
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


