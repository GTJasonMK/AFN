"""
角色立绘路由

处理角色立绘的生成、管理和查询。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_default_user, get_novel_service
from ...db.session import get_session
from ...exceptions import ResourceNotFoundError
from ...schemas.character_portrait import (
    GeneratePortraitRequest,
    RegeneratePortraitRequest,
    CharacterPortraitResponse,
    CharacterPortraitListResponse,
    GeneratePortraitResponse,
    PORTRAIT_STYLES,
    PortraitStyleInfo,
)
from ...schemas.user import UserInDB
from ...services.character_portrait_service import CharacterPortraitService
from ...services.novel_service import NovelService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["character-portraits"])


async def get_portrait_service(
    session: AsyncSession = Depends(get_session),
) -> CharacterPortraitService:
    """获取角色立绘服务实例"""
    return CharacterPortraitService(session)


@router.get("/novels/{project_id}/character-portraits", response_model=CharacterPortraitListResponse)
async def get_project_portraits(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    portrait_service: CharacterPortraitService = Depends(get_portrait_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CharacterPortraitListResponse:
    """获取项目的所有角色立绘"""
    # 验证项目权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    portraits = await portrait_service.get_project_portraits(project_id)

    return CharacterPortraitListResponse(
        portraits=[
            CharacterPortraitResponse.from_orm_with_url(p)
            for p in portraits
        ],
        total=len(portraits),
    )


@router.get("/novels/{project_id}/character-portraits/active", response_model=CharacterPortraitListResponse)
async def get_active_portraits(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    portrait_service: CharacterPortraitService = Depends(get_portrait_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CharacterPortraitListResponse:
    """获取项目所有角色的激活立绘"""
    # 验证项目权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    portraits = await portrait_service.repo.get_all_active_by_project(project_id)

    return CharacterPortraitListResponse(
        portraits=[
            CharacterPortraitResponse.from_orm_with_url(p)
            for p in portraits
        ],
        total=len(portraits),
    )


@router.get("/novels/{project_id}/character-portraits/{character_name}", response_model=CharacterPortraitListResponse)
async def get_character_portraits(
    project_id: str,
    character_name: str,
    novel_service: NovelService = Depends(get_novel_service),
    portrait_service: CharacterPortraitService = Depends(get_portrait_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CharacterPortraitListResponse:
    """获取指定角色的所有立绘"""
    # 验证项目权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    portraits = await portrait_service.get_character_portraits(project_id, character_name)

    return CharacterPortraitListResponse(
        portraits=[
            CharacterPortraitResponse.from_orm_with_url(p)
            for p in portraits
        ],
        total=len(portraits),
    )


@router.post("/novels/{project_id}/character-portraits/generate", response_model=GeneratePortraitResponse)
async def generate_portrait(
    project_id: str,
    request: GeneratePortraitRequest,
    novel_service: NovelService = Depends(get_novel_service),
    portrait_service: CharacterPortraitService = Depends(get_portrait_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> GeneratePortraitResponse:
    """生成角色立绘"""
    # 验证项目权限
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 如果没有提供角色描述，尝试从蓝图中获取
    if not request.character_description and project.characters:
        for char in project.characters:
            if char.name == request.character_name:
                # 组合角色描述
                description_parts = []
                if char.identity:
                    description_parts.append(char.identity)
                if char.personality:
                    description_parts.append(char.personality)
                if description_parts:
                    request.character_description = ", ".join(description_parts)
                break

    try:
        portrait = await portrait_service.generate_portrait(
            user_id=desktop_user.id,
            project_id=project_id,
            request=request,
        )
        await session.commit()

        return GeneratePortraitResponse(
            success=True,
            portrait=CharacterPortraitResponse.from_orm_with_url(portrait),
        )
    except Exception as e:
        logger.error("生成立绘失败: %s", e)
        return GeneratePortraitResponse(
            success=False,
            error_message=str(e),
        )


@router.post("/novels/{project_id}/character-portraits/{portrait_id}/regenerate", response_model=GeneratePortraitResponse)
async def regenerate_portrait(
    project_id: str,
    portrait_id: str,
    request: Optional[RegeneratePortraitRequest] = None,
    novel_service: NovelService = Depends(get_novel_service),
    portrait_service: CharacterPortraitService = Depends(get_portrait_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> GeneratePortraitResponse:
    """重新生成立绘"""
    # 验证项目权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    try:
        portrait = await portrait_service.regenerate_portrait(
            user_id=desktop_user.id,
            portrait_id=portrait_id,
            request=request,
        )
        await session.commit()

        return GeneratePortraitResponse(
            success=True,
            portrait=CharacterPortraitResponse.from_orm_with_url(portrait),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("重新生成立绘失败: %s", e)
        return GeneratePortraitResponse(
            success=False,
            error_message=str(e),
        )


@router.post("/novels/{project_id}/character-portraits/{portrait_id}/set-active", response_model=CharacterPortraitResponse)
async def set_active_portrait(
    project_id: str,
    portrait_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    portrait_service: CharacterPortraitService = Depends(get_portrait_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CharacterPortraitResponse:
    """设置立绘为激活状态"""
    # 验证项目权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    portrait = await portrait_service.set_active_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=404, detail="立绘不存在")

    await session.commit()

    return CharacterPortraitResponse.from_orm_with_url(portrait)


@router.delete("/novels/{project_id}/character-portraits/{portrait_id}")
async def delete_portrait(
    project_id: str,
    portrait_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    portrait_service: CharacterPortraitService = Depends(get_portrait_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除立绘"""
    # 验证项目权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    success = await portrait_service.delete_portrait(portrait_id)
    if not success:
        raise HTTPException(status_code=404, detail="立绘不存在")

    await session.commit()

    return {"success": True, "message": "立绘已删除"}


@router.get("/character-portrait-styles", response_model=List[PortraitStyleInfo])
async def get_portrait_styles() -> List[PortraitStyleInfo]:
    """获取可用的立绘风格列表"""
    return PORTRAIT_STYLES
