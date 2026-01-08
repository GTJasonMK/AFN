"""
Coding项目管理API路由

处理Coding项目的CRUD操作。
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_default_user
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....schemas.coding import (
    CodingProjectCreate,
    CodingProjectUpdate,
    CodingProjectResponse,
    CodingProjectSummary,
)
from ....services.coding import CodingProjectService

router = APIRouter()


@router.get("/coding", response_model=List[CodingProjectSummary])
async def list_coding_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """获取用户的Coding项目列表"""
    service = CodingProjectService(session)
    summaries, total = await service.list_projects_for_user(
        user.id, page, page_size
    )
    return summaries


@router.post("/coding", response_model=CodingProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_coding_project(
    data: CodingProjectCreate,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """创建新的Coding项目"""
    service = CodingProjectService(session)
    project = await service.create_project(
        user_id=user.id,
        title=data.title,
        initial_prompt=data.initial_prompt or "",
    )
    await session.commit()

    return await service.get_project_schema(project.id)


@router.get("/coding/{project_id}", response_model=CodingProjectResponse)
async def get_coding_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """获取Coding项目详情"""
    service = CodingProjectService(session)
    return await service.get_project_schema(project_id, user.id)


@router.patch("/coding/{project_id}", response_model=CodingProjectResponse)
async def update_coding_project(
    project_id: str,
    data: CodingProjectUpdate,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """更新Coding项目"""
    service = CodingProjectService(session)
    await service.update_project(
        project_id=project_id,
        user_id=user.id,
        title=data.title,
    )
    await session.commit()

    return await service.get_project_schema(project_id, user.id)


@router.delete("/coding/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coding_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """删除Coding项目"""
    service = CodingProjectService(session)
    await service.delete_project(project_id, user.id)
    await session.commit()


@router.post("/coding/batch-delete", status_code=status.HTTP_204_NO_CONTENT)
async def batch_delete_coding_projects(
    project_ids: List[str],
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """批量删除Coding项目"""
    service = CodingProjectService(session)
    await service.delete_projects(project_ids, user.id)
    await session.commit()
