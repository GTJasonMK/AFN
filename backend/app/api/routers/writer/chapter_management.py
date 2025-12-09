"""
章节管理路由

处理章节的选择、评价、编辑、删除等管理操作。
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.state_machine import ProjectStatus
from ....core.dependencies import (
    get_default_user,
    get_novel_service,
    get_llm_service,
    get_prompt_service,
    get_vector_store,
)
from ....db.session import get_session
from ....exceptions import (
    ChapterNotGeneratedError,
    InvalidParameterError,
    PromptTemplateNotFoundError,
)
from ....models.novel import Chapter, ChapterOutline
from ....schemas.novel import (
    DeleteChapterRequest,
    ImportChapterRequest,
    EvaluateChapterRequest,
    NovelProject as NovelProjectSchema,
    SelectVersionRequest,
    UpdateChapterOutlineRequest,
)
from ....schemas.user import UserInDB
from ....repositories.chapter_repository import ChapterOutlineRepository, ChapterRepository
from ....services.chapter_analysis_service import ChapterAnalysisService
from ....services.chapter_ingest_service import ChapterIngestionService
from ....services.incremental_indexer import IncrementalIndexer
from ....services.llm_service import LLMService
from ....services.novel_service import NovelService
from ....services.prompt_service import PromptService
from ....services.vector_store_service import VectorStoreService
from ....utils.json_utils import remove_think_tags, unwrap_markdown_json
from ....utils.prompt_helpers import ensure_prompt

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/novels/{project_id}/chapters/import", response_model=NovelProjectSchema)
async def import_chapter(
    project_id: str,
    request: ImportChapterRequest,
    novel_service: NovelService = Depends(get_novel_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> NovelProjectSchema:
    """
    导入章节内容

    如果章节已存在，则更新内容；如果不存在，则创建章节和大纲。
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    
    # 1. 确保大纲存在或更新大纲
    chapter_outline_repo = ChapterOutlineRepository(session)
    await chapter_outline_repo.upsert_outline(
        project_id=project_id,
        chapter_number=request.chapter_number,
        title=request.title,
        summary="（导入章节，摘要待生成）",  # 默认摘要
    )
    
    # 2. 获取或创建章节记录
    chapter_repo = ChapterRepository(session)
    chapter = await chapter_repo.get_by_project_and_number(project_id, request.chapter_number)

    if not chapter:
        # 创建新章节（Chapter模型不包含title字段，title存储在ChapterOutline中）
        chapter = Chapter(
            project_id=project_id,
            chapter_number=request.chapter_number,
        )
        session.add(chapter)
        await session.flush()  # flush以获取ID，稍后统一commit

    # 3. 创建新的版本并设为选中
    from ....models.novel import ChapterVersion  # 延迟导入避免循环

    # 确定新版本标签
    new_version_label = "v1"
    if chapter.versions:
        # 基于现有版本数量生成新标签
        new_version_label = f"v{len(chapter.versions) + 1}"

    new_version = ChapterVersion(
        chapter_id=chapter.id,
        version_label=new_version_label,
        content=request.content,
        provider="imported",  # 标记为导入
    )
    session.add(new_version)
    await session.flush()  # flush以获取版本ID

    # 更新章节选中版本和字数
    chapter.selected_version_id = new_version.id
    chapter.word_count = len(request.content)
    await session.commit()

    logger.info(
        "用户 %s 导入项目 %s 第 %s 章内容 (版本 %s)",
        desktop_user.id,
        project_id,
        request.chapter_number,
        new_version_label
    )

    # 4. 尝试生成摘要（异步或同步）
    if request.content.strip():
        try:
            summary = await llm_service.get_summary(
                request.content,
                temperature=settings.llm_temp_summary,
                user_id=desktop_user.id,
                timeout=180.0,
            )
            chapter.real_summary = remove_think_tags(summary)
            
            # 同时更新大纲摘要
            await chapter_outline_repo.upsert_outline(
                project_id=project_id,
                chapter_number=request.chapter_number,
                title=request.title,
                summary=chapter.real_summary,
            )
            
        except Exception as exc:
            logger.error("项目 %s 第 %s 章导入后摘要生成失败: %s", project_id, request.chapter_number, exc)
            chapter.real_summary = "摘要生成失败，请稍后手动生成"
    
    await session.commit()

    # 5. 向量入库（使用依赖注入的vector_store）
    if vector_store:
        ingestion_service = ChapterIngestionService(llm_service=llm_service, vector_store=vector_store)
        await ingestion_service.ingest_chapter(
            project_id=project_id,
            chapter_number=request.chapter_number,
            title=request.title,
            content=request.content,
            summary=chapter.real_summary,
            user_id=desktop_user.id,
        )
        logger.info("项目 %s 第 %s 章导入内容已同步至向量库", project_id, request.chapter_number)

    # 检查完成状态
    await novel_service.check_and_update_completion_status(project_id, desktop_user.id)

    return await novel_service.get_project_schema(project_id, desktop_user.id)


@router.post("/novels/{project_id}/chapters/select", response_model=NovelProjectSchema)
async def select_chapter_version(
    project_id: str,
    request: SelectVersionRequest,
    novel_service: NovelService = Depends(get_novel_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> NovelProjectSchema:

    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    chapter = next((ch for ch in project.chapters if ch.chapter_number == request.chapter_number), None)
    if not chapter:
        logger.warning("项目 %s 未找到第 %s 章，无法选择版本", project_id, request.chapter_number)
        raise ChapterNotGeneratedError(project_id, request.chapter_number)

    selected = await novel_service.select_chapter_version(chapter, request.version_index)
    await session.commit()

    logger.info(
        "用户 %s 选择了项目 %s 第 %s 章的第 %s 个版本",
        desktop_user.id,
        project_id,
        request.chapter_number,
        request.version_index,
    )
    
    # 优化：分离版本选择和摘要生成，避免摘要失败导致整个操作失败
    if selected and selected.content:
        try:
            summary = await llm_service.get_summary(
                selected.content,
                temperature=settings.llm_temp_summary,
                user_id=desktop_user.id,
                timeout=180.0,
            )
            chapter.real_summary = remove_think_tags(summary)
            await session.commit()
        except Exception as exc:
            logger.error("项目 %s 第 %s 章摘要生成失败，但版本选择已保存: %s", project_id, request.chapter_number, exc)
            # 摘要生成失败不影响版本选择结果，继续处理

        # 执行章节深度分析，提取元数据、角色状态、伏笔等结构化信息
        outline = next((item for item in project.outlines if item.chapter_number == chapter.chapter_number), None)
        chapter_title = outline.title if outline and outline.title else f"第{chapter.chapter_number}章"
        try:
            analysis_service = ChapterAnalysisService(session)
            analysis_data = await analysis_service.analyze_chapter(
                content=selected.content,
                title=chapter_title,
                chapter_number=chapter.chapter_number,
                novel_title=project.title,
                user_id=desktop_user.id,
                timeout=300.0,
            )
            if analysis_data:
                chapter.analysis_data = analysis_data.model_dump()
                await session.commit()
                logger.info(
                    "项目 %s 第 %s 章分析数据已保存",
                    project_id,
                    request.chapter_number,
                )

                # 更新角色状态和伏笔索引
                try:
                    indexer = IncrementalIndexer(session)
                    index_stats = await indexer.index_chapter_analysis(
                        project_id=project_id,
                        chapter_number=request.chapter_number,
                        analysis_data=analysis_data,
                    )
                    await session.commit()
                    logger.info(
                        "项目 %s 第 %s 章索引更新完成: %s",
                        project_id,
                        request.chapter_number,
                        index_stats,
                    )
                except Exception as index_exc:
                    logger.error(
                        "项目 %s 第 %s 章索引更新失败: %s",
                        project_id,
                        request.chapter_number,
                        index_exc,
                    )
                    # 索引更新失败不影响主流程
        except Exception as exc:
            logger.error(
                "项目 %s 第 %s 章分析失败，但版本选择已保存: %s",
                project_id,
                request.chapter_number,
                exc,
            )
            # 分析失败不影响版本选择结果，继续处理

        # 选定版本后同步向量库，确保后续章节可检索到最新内容（使用依赖注入的vector_store）
        if vector_store:
            ingestion_service = ChapterIngestionService(llm_service=llm_service, vector_store=vector_store)
            await ingestion_service.ingest_chapter(
                project_id=project_id,
                chapter_number=chapter.chapter_number,
                title=chapter_title,
                content=selected.content,
                summary=chapter.real_summary,
                user_id=desktop_user.id,
            )
            logger.info(
                "项目 %s 第 %s 章已同步至向量库",
                project_id,
                chapter.chapter_number,
            )

    # 选择版本后检查是否所有章节都完成了
    await novel_service.check_and_update_completion_status(project_id, desktop_user.id)

    # 返回最新数据（重新从数据库加载，确保selected_version关系被正确加载）
    return await novel_service.get_project_schema(project_id, desktop_user.id)


@router.post("/novels/{project_id}/chapters/evaluate", response_model=NovelProjectSchema)
async def evaluate_chapter(
    project_id: str,
    request: EvaluateChapterRequest,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> NovelProjectSchema:
    """
    评估章节的多个版本，选出最佳版本。

    使用RAG检索增强评估：
    1. 获取前序章节摘要（结构化数据）
    2. 基于待评估内容检索相关历史片段（向量检索）
    3. 将两者结合提供给LLM进行评估
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    chapter = next((ch for ch in project.chapters if ch.chapter_number == request.chapter_number), None)
    if not chapter:
        logger.warning("项目 %s 未找到第 %s 章，无法执行评估", project_id, request.chapter_number)
        raise ChapterNotGeneratedError(project_id, request.chapter_number)
    if not chapter.versions:
        logger.warning("项目 %s 第 %s 章无可评估版本", project_id, request.chapter_number)
        raise InvalidParameterError("无可评估的章节版本")

    evaluator_prompt = ensure_prompt(await prompt_service.get_prompt("evaluation"), "evaluation")

    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint_dict = project_schema.blueprint.model_dump()

    versions_to_evaluate = [
        {"version_id": idx + 1, "content": version.content}
        for idx, version in enumerate(sorted(chapter.versions, key=lambda item: item.created_at))
    ]

    # 构建前序章节摘要列表（completed_chapters）
    # 获取当前章节之前所有已确认的章节，按章节号排序
    completed_chapters = []
    current_chapter_number = request.chapter_number

    # 从大纲和章节数据中构建前序章节信息
    outlines_map = {o.chapter_number: o for o in project.outlines}
    chapters_map = {c.chapter_number: c for c in project.chapters}

    for ch_num in sorted(outlines_map.keys()):
        if ch_num >= current_chapter_number:
            break  # 只获取当前章节之前的

        outline = outlines_map.get(ch_num)
        ch = chapters_map.get(ch_num)

        # 判断章节是否已完成（有选中版本）
        if ch and ch.selected_version_id:
            # 优先使用实际摘要，其次使用大纲摘要
            summary = ch.real_summary or (outline.summary if outline else None) or "（无摘要）"
            completed_chapters.append({
                "chapter_number": ch_num,
                "title": outline.title if outline else f"第{ch_num}章",
                "summary": summary,
            })

    # RAG检索：基于待评估内容检索相关历史片段
    relevant_chunks = []
    relevant_summaries = []

    if vector_store:
        try:
            # 构建查询文本：使用章节大纲 + 第一个版本的开头内容
            current_outline = outlines_map.get(current_chapter_number)
            outline_text = ""
            if current_outline:
                outline_text = f"{current_outline.title}: {current_outline.summary or ''}"

            # 取第一个版本的开头作为查询补充（避免太长）
            first_version_preview = versions_to_evaluate[0]["content"][:800] if versions_to_evaluate else ""
            query_text = f"{outline_text}\n{first_version_preview}".strip()

            if query_text:
                # 生成查询向量
                query_embedding = await llm_service.get_embedding(
                    query_text,
                    user_id=desktop_user.id,
                )

                if query_embedding:
                    # 检索相关历史片段（只检索当前章节之前的内容）
                    chunks = await vector_store.query_chunks(
                        project_id=project_id,
                        embedding=query_embedding,
                        top_k=5,
                    )
                    # 过滤：只保留当前章节之前的片段
                    chunks = [c for c in chunks if c.chapter_number < current_chapter_number]

                    # 检索相关摘要
                    summaries = await vector_store.query_summaries(
                        project_id=project_id,
                        embedding=query_embedding,
                        top_k=3,
                    )
                    # 过滤：只保留当前章节之前的摘要
                    summaries = [s for s in summaries if s.chapter_number < current_chapter_number]

                    # 格式化检索结果
                    for chunk in chunks:
                        relevant_chunks.append({
                            "chapter_number": chunk.chapter_number,
                            "chapter_title": chunk.chapter_title or f"第{chunk.chapter_number}章",
                            "content": chunk.content,
                            "relevance_score": round(chunk.score, 3) if chunk.score else None,
                        })

                    for summary in summaries:
                        relevant_summaries.append({
                            "chapter_number": summary.chapter_number,
                            "title": summary.title,
                            "summary": summary.summary,
                            "relevance_score": round(summary.score, 3) if summary.score else None,
                        })

                    logger.info(
                        "项目 %s 第 %s 章评估RAG检索完成: chunks=%d summaries=%d",
                        project_id,
                        request.chapter_number,
                        len(relevant_chunks),
                        len(relevant_summaries),
                    )
        except Exception as rag_exc:
            logger.warning(
                "项目 %s 第 %s 章评估RAG检索失败，将使用基础上下文: %s",
                project_id,
                request.chapter_number,
                rag_exc,
            )
            # RAG失败不影响评估，继续使用基础上下文

    logger.info(
        "项目 %s 第 %s 章评估准备: 前序章节数=%d RAG片段=%d RAG摘要=%d",
        project_id,
        request.chapter_number,
        len(completed_chapters),
        len(relevant_chunks),
        len(relevant_summaries),
    )

    # 构建评估payload，包含前序章节上下文和RAG检索结果
    evaluator_payload = {
        "novel_blueprint": blueprint_dict,
        "completed_chapters": completed_chapters,
        "content_to_evaluate": {
            "chapter_number": chapter.chapter_number,
            "versions": versions_to_evaluate,
        },
    }

    # 添加RAG检索结果（如果有）
    if relevant_chunks or relevant_summaries:
        evaluator_payload["relevant_context"] = {
            "description": "以下是通过语义检索找到的与待评估章节最相关的历史内容，可用于判断伏笔处理、人物一致性等",
            "relevant_chunks": relevant_chunks,
            "relevant_summaries": relevant_summaries,
        }

    # 优化：添加错误处理，避免评估失败导致整个操作失败
    try:
        evaluation_raw = await llm_service.get_llm_response(
            system_prompt=evaluator_prompt,
            conversation_history=[{"role": "user", "content": json.dumps(evaluator_payload, ensure_ascii=False)}],
            temperature=settings.llm_temp_evaluation,
            user_id=desktop_user.id,
            timeout=360.0,
        )
        # 先移除think标签，再提取markdown代码块中的JSON
        evaluation_clean = remove_think_tags(evaluation_raw)
        evaluation_json = unwrap_markdown_json(evaluation_clean)
        await novel_service.add_chapter_evaluation(chapter, None, evaluation_json)
        await session.commit()
        logger.info("项目 %s 第 %s 章评估完成", project_id, request.chapter_number)
    except Exception as exc:
        logger.error("项目 %s 第 %s 章评估失败: %s", project_id, request.chapter_number, exc)
        # 评估失败不影响章节数据，添加失败标记
        await novel_service.add_chapter_evaluation(
            chapter,
            None,
            json.dumps({"error": "评估失败，请稍后重试", "details": str(exc)}, ensure_ascii=False)
        )
        await session.commit()

    return await novel_service.get_project_schema(project_id, desktop_user.id)


@router.post("/novels/{project_id}/chapters/update-outline", response_model=NovelProjectSchema)
async def update_chapter_outline(
    project_id: str,
    request: UpdateChapterOutlineRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelProjectSchema:
    await novel_service.ensure_project_owner(project_id, desktop_user.id)
    logger.info(
        "用户 %s 更新项目 %s 第 %s 章大纲",
        desktop_user.id,
        project_id,
        request.chapter_number,
    )

    # 使用Repository的upsert_outline方法（更新或创建）
    chapter_outline_repo = ChapterOutlineRepository(session)
    await chapter_outline_repo.upsert_outline(
        project_id=project_id,
        chapter_number=request.chapter_number,
        title=request.title,
        summary=request.summary,
    )
    await session.commit()
    logger.info("项目 %s 第 %s 章大纲已更新", project_id, request.chapter_number)

    return await novel_service.get_project_schema(project_id, desktop_user.id)


@router.post("/novels/{project_id}/chapters/delete", response_model=NovelProjectSchema)
async def delete_chapters(
    project_id: str,
    request: DeleteChapterRequest,
    novel_service: NovelService = Depends(get_novel_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> NovelProjectSchema:
    if not request.chapter_numbers:
        logger.warning("项目 %s 未提供要删除的章节号", project_id)
        raise InvalidParameterError("请提供要删除的章节号")
    await novel_service.ensure_project_owner(project_id, desktop_user.id)
    logger.info(
        "用户 %s 删除项目 %s 的章节 %s",
        desktop_user.id,
        project_id,
        request.chapter_numbers,
    )
    await novel_service.delete_chapters(project_id, request.chapter_numbers)
    await session.commit()

    # 删除章节时同步清理向量库，避免过时内容被检索（使用依赖注入的vector_store）
    if vector_store:
        ingestion_service = ChapterIngestionService(llm_service=llm_service, vector_store=vector_store)
        await ingestion_service.delete_chapters(project_id, request.chapter_numbers)
        logger.info(
            "项目 %s 已从向量库移除章节 %s",
            project_id,
            request.chapter_numbers,
        )

    return await novel_service.get_project_schema(project_id, desktop_user.id)


@router.put("/novels/{project_id}/chapters/{chapter_number}", response_model=NovelProjectSchema)
async def update_chapter(
    project_id: str,
    chapter_number: int,
    content: str = Body(..., embed=True),
    novel_service: NovelService = Depends(get_novel_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> NovelProjectSchema:
    """
    更新章节内容（RESTful风格端点）

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        content: 新内容

    Returns:
        更新后的项目信息
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    chapter = next((ch for ch in project.chapters if ch.chapter_number == chapter_number), None)
    if not chapter or chapter.selected_version is None:
        logger.warning("项目 %s 第 %s 章尚未生成或未选择版本，无法编辑", project_id, chapter_number)
        raise ChapterNotGeneratedError(project_id, chapter_number)

    chapter.selected_version.content = content
    chapter.word_count = len(content)
    logger.info("用户 %s 更新了项目 %s 第 %s 章内容", desktop_user.id, project_id, chapter_number)

    # 优化：分离内容保存和摘要生成，避免摘要失败导致编辑失败
    if content.strip():
        try:
            summary = await llm_service.get_summary(
                content,
                temperature=settings.llm_temp_summary,
                user_id=desktop_user.id,
                timeout=180.0,
            )
            chapter.real_summary = remove_think_tags(summary)
        except Exception as exc:
            logger.error("项目 %s 第 %s 章编辑后摘要生成失败，但内容已保存: %s", project_id, chapter_number, exc)
            # 摘要生成失败不影响内容保存，继续处理
            chapter.real_summary = "摘要生成失败，请稍后手动生成"
    await session.commit()

    # 同步向量库（使用依赖注入的vector_store）
    if vector_store and chapter.selected_version and chapter.selected_version.content:
        ingestion_service = ChapterIngestionService(llm_service=llm_service, vector_store=vector_store)
        outline = next((item for item in project.outlines if item.chapter_number == chapter.chapter_number), None)
        chapter_title = outline.title if outline and outline.title else f"第{chapter.chapter_number}章"
        await ingestion_service.ingest_chapter(
            project_id=project_id,
            chapter_number=chapter.chapter_number,
            title=chapter_title,
            content=chapter.selected_version.content,
            summary=chapter.real_summary,
            user_id=desktop_user.id,
        )
        logger.info("项目 %s 第 %s 章更新内容已同步至向量库", project_id, chapter_number)

    return await novel_service.get_project_schema(project_id, desktop_user.id)


# ------------------------------------------------------------------
# 章节大纲灵活管理接口（增量生成、删除、重新生成）
# ------------------------------------------------------------------


