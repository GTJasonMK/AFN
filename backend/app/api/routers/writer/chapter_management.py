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
    chapter = await chapter_repo.get_chapter(project_id, request.chapter_number)
    
    if not chapter:
        # 创建新章节
        chapter = Chapter(
            project_id=project_id,
            chapter_number=request.chapter_number,
            title=request.title,
        )
        session.add(chapter)
        await session.commit()  # 提交以获取ID
    
    # 3. 创建新的版本并设为选中
    from ....models.novel import ChapterVersion  # 延迟导入避免循环
    
    # 确定新版本号
    new_version_number = 1
    if chapter.versions:
        new_version_number = max(v.version_number for v in chapter.versions) + 1
        
    new_version = ChapterVersion(
        chapter_id=chapter.id,
        version_number=new_version_number,
        content=request.content,
        llm_model="imported",  # 标记为导入
        prompt="imported"
    )
    session.add(new_version)
    await session.commit()
    
    # 更新章节选中版本和字数
    chapter.selected_version_id = new_version.id
    chapter.word_count = len(request.content)
    session.add(chapter)
    await session.commit()

    logger.info(
        "用户 %s 导入项目 %s 第 %s 章内容 (版本 %d)", 
        desktop_user.id, 
        project_id, 
        request.chapter_number,
        new_version_number
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

    # 5. 向量入库
    vector_store: Optional[VectorStoreService]
    if not settings.vector_store_enabled:
        vector_store = None
    else:
        try:
            vector_store = VectorStoreService()
        except RuntimeError as exc:
            logger.warning("向量库初始化失败，跳过章节向量更新: %s", exc)
            vector_store = None

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
        except Exception as exc:
            logger.error(
                "项目 %s 第 %s 章分析失败，但版本选择已保存: %s",
                project_id,
                request.chapter_number,
                exc,
            )
            # 分析失败不影响版本选择结果，继续处理

        # 选定版本后同步向量库，确保后续章节可检索到最新内容
        vector_store: Optional[VectorStoreService]
        if not settings.vector_store_enabled:
            vector_store = None
        else:
            try:
                vector_store = VectorStoreService()
            except RuntimeError as exc:
                logger.warning("向量库初始化失败，跳过章节向量同步: %s", exc)
                vector_store = None

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
) -> NovelProjectSchema:

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
    # print("blueprint_dict:",blueprint_dict)
    evaluator_payload = {
        "novel_blueprint": blueprint_dict,
        "content_to_evaluate": {
            "chapter_number": chapter.chapter_number,
            "versions": versions_to_evaluate,
        },
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

    # 删除章节时同步清理向量库，避免过时内容被检索
    vector_store: Optional[VectorStoreService]
    if not settings.vector_store_enabled:
        vector_store = None
    else:
        try:
            vector_store = VectorStoreService()
        except RuntimeError as exc:
            logger.warning("向量库初始化失败，跳过章节向量删除: %s", exc)
            vector_store = None

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

    vector_store: Optional[VectorStoreService]
    if not settings.vector_store_enabled:
        vector_store = None
    else:
        try:
            vector_store = VectorStoreService()
        except RuntimeError as exc:
            logger.warning("向量库初始化失败，跳过章节向量更新: %s", exc)
            vector_store = None

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


