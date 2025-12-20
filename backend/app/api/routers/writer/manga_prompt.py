"""
漫画提示词API路由

提供章节内容转漫画提示词的API端点。
支持断点续传：如果生成过程中断，可以从上次完成的步骤继续。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_llm_service,
    get_prompt_service,
)
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....services.manga_prompt import (
    MangaPromptService,
    MangaPromptRequest,
    MangaPromptResult,
    MangaScene,
)
from ....services.manga_prompt.schemas import SceneUpdateRequest
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerationStatusResponse(BaseModel):
    """生成状态响应"""
    status: str  # pending, scene_extracted, layout_generated, completed, failed
    has_checkpoint: bool  # 是否有可恢复的检查点
    failed_step: Optional[str] = None  # 失败的步骤（如果有）
    error_message: Optional[str] = None  # 错误信息（如果有）
    progress_info: Optional[dict] = None  # 进度详情


@router.get("/novels/{project_id}/chapters/{chapter_number}/manga-prompts/status")
async def get_generation_status(
    project_id: str,
    chapter_number: int,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> GenerationStatusResponse:
    """
    获取漫画提示词生成状态

    用于检查是否有未完成的生成任务可以继续。

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        生成状态信息
    """
    from ....repositories.chapter_repository import ChapterRepository

    chapter_repo = ChapterRepository(session)
    chapter = await chapter_repo.get_by_project_and_number(project_id, chapter_number)

    if not chapter:
        raise HTTPException(status_code=404, detail=f"章节 {chapter_number} 不存在")

    manga_prompt = chapter.manga_prompt

    if not manga_prompt:
        return GenerationStatusResponse(
            status="none",
            has_checkpoint=False,
        )

    status = manga_prompt.generation_status or "completed"
    progress = manga_prompt.generation_progress or {}

    # 检查是否有可恢复的检查点
    has_checkpoint = status in ("scene_extracted", "layout_generated", "failed")

    # 提取错误信息（如果有）
    failed_step = progress.get("failed_step") if status == "failed" else None
    error_message = progress.get("error") if status == "failed" else None

    # 构建进度详情
    progress_info = None
    if status != "completed" and status != "none":
        progress_info = {
            "scene_count": len(progress.get("scene_summaries", [])),
            "has_layout": "layout_result" in progress,
        }

    return GenerationStatusResponse(
        status=status,
        has_checkpoint=has_checkpoint,
        failed_step=failed_step,
        error_message=error_message,
        progress_info=progress_info,
    )


@router.post("/novels/{project_id}/chapters/{chapter_number}/manga-prompts")
async def generate_manga_prompts(
    project_id: str,
    chapter_number: int,
    request: MangaPromptRequest,
    continue_from_checkpoint: bool = Query(False, description="是否从检查点继续生成"),
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> MangaPromptResult:
    """
    生成章节的漫画提示词

    将章节内容智能分割为多个关键画面，并为每个画面生成文生图提示词。
    支持断点续传：如果 continue_from_checkpoint=True，会从上次中断的步骤继续。

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        request: 生成请求
            - style: 漫画风格 (manga/anime/comic/webtoon)
            - scene_count: 目标场景数量 (5-20)
        continue_from_checkpoint: 是否从检查点继续（默认False，重新生成）

    Returns:
        漫画提示词结果，包含：
        - character_profiles: 角色外观描述字典
        - scenes: 场景列表，每个场景包含英文提示词、中文说明等
        - style_guide: 整体风格指南
    """
    logger.info(
        "用户 %s 请求生成项目 %s 第 %s 章的漫画提示词 (continue=%s)",
        desktop_user.id,
        project_id,
        chapter_number,
        continue_from_checkpoint,
    )

    service = MangaPromptService(
        session=session,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )

    try:
        result = await service.generate_manga_prompts(
            project_id=project_id,
            chapter_number=chapter_number,
            request=request,
            user_id=desktop_user.id,
            continue_from_checkpoint=continue_from_checkpoint,
        )
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/novels/{project_id}/chapters/{chapter_number}/manga-prompts")
async def get_manga_prompts(
    project_id: str,
    chapter_number: int,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> MangaPromptResult:
    """
    获取已保存的漫画提示词

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        已保存的漫画提示词结果
    """
    service = MangaPromptService(
        session=session,
        llm_service=llm_service,
    )

    result = await service.get_manga_prompts(
        project_id=project_id,
        chapter_number=chapter_number,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"章节 {chapter_number} 尚未生成漫画提示词"
        )

    return result


@router.put("/novels/{project_id}/chapters/{chapter_number}/manga-prompts/scenes/{scene_id}")
async def update_manga_scene(
    project_id: str,
    chapter_number: int,
    scene_id: int,
    request: SceneUpdateRequest,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> MangaScene:
    """
    更新单个场景的提示词

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        scene_id: 场景ID
        request: 更新请求

    Returns:
        更新后的场景
    """
    logger.info(
        "用户 %s 更新项目 %s 第 %s 章场景 %s",
        desktop_user.id,
        project_id,
        chapter_number,
        scene_id,
    )

    service = MangaPromptService(
        session=session,
        llm_service=llm_service,
    )

    try:
        result = await service.update_scene(
            project_id=project_id,
            chapter_number=chapter_number,
            scene_id=scene_id,
            update=request,
        )
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/novels/{project_id}/chapters/{chapter_number}/manga-prompts")
async def delete_manga_prompts(
    project_id: str,
    chapter_number: int,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    删除章节的漫画提示词

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        删除结果
    """
    logger.info(
        "用户 %s 删除项目 %s 第 %s 章的漫画提示词",
        desktop_user.id,
        project_id,
        chapter_number,
    )

    service = MangaPromptService(
        session=session,
        llm_service=llm_service,
    )

    success = await service.delete_manga_prompts(
        project_id=project_id,
        chapter_number=chapter_number,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"章节 {chapter_number} 没有漫画提示词"
        )

    await session.commit()
    return {"success": True, "message": "漫画提示词已删除"}
