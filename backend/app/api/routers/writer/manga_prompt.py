"""
漫画提示词API路由

提供章节内容转漫画提示词的API端点。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
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


@router.post("/novels/{project_id}/chapters/{chapter_number}/manga-prompts")
async def generate_manga_prompts(
    project_id: str,
    chapter_number: int,
    request: MangaPromptRequest,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> MangaPromptResult:
    """
    生成章节的漫画提示词

    将章节内容智能分割为多个关键画面，并为每个画面生成文生图提示词。

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        request: 生成请求
            - style: 漫画风格 (manga/anime/comic/webtoon)
            - scene_count: 目标场景数量 (5-20)

    Returns:
        漫画提示词结果，包含：
        - character_profiles: 角色外观描述字典
        - scenes: 场景列表，每个场景包含英文提示词、中文说明等
        - style_guide: 整体风格指南
    """
    logger.info(
        "用户 %s 请求生成项目 %s 第 %s 章的漫画提示词",
        desktop_user.id,
        project_id,
        chapter_number,
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
        )
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("生成漫画提示词失败: %s", str(e))
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


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
