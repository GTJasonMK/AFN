"""
Coding 文件相关路由：目录 CRUD API

拆分自 `backend/app/api/routers/coding/files.py`。
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_default_user
from ....db.session import get_session
from ....schemas.coding_files import DirectoryNodeCreate, DirectoryNodeUpdate, DirectoryNodeResponse
from ....schemas.user import UserInDB
from ....services.coding_files import DirectoryStructureService
from .files_dependencies import get_directory_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_flat_directory_node_response(node) -> DirectoryNodeResponse:
    """将目录节点序列化为“扁平响应”（不包含 files/children 递归展开）"""
    from ....serializers.coding_files_serializer import build_directory_node_response

    return build_directory_node_response(
        node,
        file_count=0,
        files=[],
        children=[],
    )


@router.post("/coding/{project_id}/directories")
async def create_directory(
    project_id: str,
    request: DirectoryNodeCreate,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> DirectoryNodeResponse:
    """
    手动创建目录

    在指定父目录下创建新目录，parent_id为空则创建根目录。
    """
    node = await directory_service.create_directory(
        project_id=project_id,
        user_id=desktop_user.id,
        name=request.name,
        parent_id=request.parent_id,
        node_type=request.node_type.value,
        description=request.description,
    )
    await session.commit()

    return _to_flat_directory_node_response(node)


@router.patch("/coding/{project_id}/directories/{node_id}")
async def update_directory(
    project_id: str,
    node_id: int,
    request: DirectoryNodeUpdate,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> DirectoryNodeResponse:
    """
    更新目录

    修改目录名称、描述或排序顺序。
    """
    node = await directory_service.update_directory(
        project_id=project_id,
        user_id=desktop_user.id,
        node_id=node_id,
        name=request.name,
        description=request.description,
        sort_order=request.sort_order,
    )
    await session.commit()

    return _to_flat_directory_node_response(node)


@router.delete("/coding/{project_id}/directories/{node_id}")
async def delete_directory(
    project_id: str,
    node_id: int,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    删除目录

    级联删除所有子目录和文件。
    """
    await directory_service.delete_directory(
        project_id=project_id,
        user_id=desktop_user.id,
        node_id=node_id,
    )
    await session.commit()

    return {"success": True, "message": "目录已删除"}


class RepairDirectoriesResponse(BaseModel):
    """修复目录关系响应"""

    success: bool
    total_directories: int = Field(description="总目录数")
    fixed_directories: int = Field(description="修复的目录数")
    created_parents: int = Field(description="创建的缺失父目录数")
    message: str


@router.post("/coding/{project_id}/directories/repair")
async def repair_directory_relationships(
    project_id: str,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> RepairDirectoriesResponse:
    """
    修复目录的parent_id关系

    遍历项目所有目录，根据路径重建正确的父子关系。
    用于修复之前由于bug导致的parent_id全为NULL的问题。
    """
    logger.info("收到目录关系修复请求: project_id=%s", project_id)

    stats = await directory_service.repair_parent_relationships(
        project_id=project_id,
        user_id=desktop_user.id,
    )
    await session.commit()

    message = f"修复完成：检查了{stats['total_directories']}个目录，修复了{stats['fixed_directories']}个关系"
    if stats["created_parents"] > 0:
        message += f"，创建了{stats['created_parents']}个缺失的父目录"

    logger.info(
        "目录关系修复完成: project_id=%s total=%d fixed=%d created=%d",
        project_id,
        stats["total_directories"],
        stats["fixed_directories"],
        stats["created_parents"],
    )

    return RepairDirectoriesResponse(
        success=True,
        total_directories=stats["total_directories"],
        fixed_directories=stats["fixed_directories"],
        created_parents=stats["created_parents"],
        message=message,
    )


__all__ = ["router"]

