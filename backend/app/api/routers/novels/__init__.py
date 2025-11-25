"""
小说项目路由模块

拆分后的路由结构：
- __init__.py (本文件): 项目CRUD操作（直接定义，避免路由嵌套问题）
- inspiration.py: 灵感对话
- blueprints.py: 蓝图管理
- outlines.py: 章节大纲生成
- export.py: 导出功能
"""

import logging
from typing import Dict, List

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_default_user, get_novel_service
from ....db.session import get_session
from ....schemas.novel import (
    Chapter as ChapterSchema,
    NovelProject as NovelProjectSchema,
    NovelProjectSummary,
    NovelSectionResponse,
    NovelSectionType,
    ProjectUpdateRequest,
)
from ....schemas.user import UserInDB
from ....services.novel_service import NovelService

from .inspiration import router as inspiration_router
from .blueprints import router as blueprints_router
from .outlines import router as outlines_router
from .export import router as export_router

logger = logging.getLogger(__name__)

# 创建novels总路由器（prefix在主路由器中设置）
router = APIRouter(tags=["Novels"])


# ==================== 项目CRUD操作 ====================

@router.post("", response_model=NovelProjectSchema, status_code=status.HTTP_201_CREATED)
async def create_novel(
    title: str = Body(...),
    initial_prompt: str = Body(...),
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelProjectSchema:
    """为当前用户创建一个新的小说项目"""
    project = await novel_service.create_project(desktop_user.id, title, initial_prompt)
    await session.commit()  # 提交项目创建事务
    logger.info("用户 %s 创建项目 %s", desktop_user.id, project.id)
    return await novel_service.get_project_schema(project.id, desktop_user.id)


@router.get("", response_model=List[NovelProjectSummary])
async def list_novels(
    novel_service: NovelService = Depends(get_novel_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[NovelProjectSummary]:
    """列出用户的全部小说项目摘要信息"""
    projects = await novel_service.list_projects_for_user(desktop_user.id)
    logger.info("用户 %s 获取项目列表，共 %s 个", desktop_user.id, len(projects))
    return projects


@router.get("/{project_id}", response_model=NovelProjectSchema)
async def get_novel(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelProjectSchema:
    """获取指定项目的完整信息"""
    logger.info("用户 %s 查询项目 %s", desktop_user.id, project_id)
    return await novel_service.get_project_schema(project_id, desktop_user.id)


@router.get("/{project_id}/sections/{section}", response_model=NovelSectionResponse)
async def get_novel_section(
    project_id: str,
    section: NovelSectionType,
    novel_service: NovelService = Depends(get_novel_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelSectionResponse:
    """获取项目的指定区段数据（概览、世界设定、角色等）"""
    logger.info("用户 %s 获取项目 %s 的 %s 区段", desktop_user.id, project_id, section)
    return await novel_service.get_section_data(project_id, section, desktop_user.id)


@router.get("/{project_id}/chapters/{chapter_number}", response_model=ChapterSchema)
async def get_chapter(
    project_id: str,
    chapter_number: int,
    novel_service: NovelService = Depends(get_novel_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ChapterSchema:
    """获取指定章节的详细信息"""
    logger.info("用户 %s 获取项目 %s 第 %s 章", desktop_user.id, project_id, chapter_number)
    return await novel_service.get_chapter_schema(project_id, chapter_number, desktop_user.id)


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_novels(
    project_ids: List[str],  # 直接使用类型提示,不需要Body(...)
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, str]:
    """批量删除项目

    请求体格式: ["project_id_1", "project_id_2"]
    """
    await novel_service.delete_projects(project_ids, desktop_user.id)
    await session.commit()  # 提交删除事务
    logger.info("用户 %s 删除项目 %s", desktop_user.id, project_ids)
    return {"status": "success", "message": f"成功删除 {len(project_ids)} 个项目"}


@router.patch("/{project_id}", response_model=NovelProjectSchema)
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelProjectSchema:
    """更新项目基本信息（标题、描述等）"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)

    update_data = payload.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(project, key, value)
        await session.commit()
        logger.info("项目 %s 更新基本信息：%s", project_id, list(update_data.keys()))

    return await novel_service.get_project_schema(project_id, desktop_user.id)


# ==================== 挂载子路由 ====================

# 挂载所有子路由
router.include_router(inspiration_router)
router.include_router(blueprints_router)
router.include_router(outlines_router)
router.include_router(export_router)

__all__ = ["router"]
