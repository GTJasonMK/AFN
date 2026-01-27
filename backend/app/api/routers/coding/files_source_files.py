"""
Coding 文件相关路由：源文件 API

拆分自 `backend/app/api/routers/coding/files.py`。
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_default_user
from ....db.session import get_session
from ....schemas.coding_files import (
    SourceFileCreate,
    SourceFileDetail,
    SourceFileListResponse,
    SourceFileResponse,
    SourceFileUpdate,
)
from ....schemas.user import UserInDB
from ....services.coding_files import FilePromptService
from .files_dependencies import get_file_prompt_service

router = APIRouter()


@router.get("/coding/{project_id}/files")
async def list_files(
    project_id: str,
    module_number: Optional[int] = None,
    directory_id: Optional[int] = None,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> SourceFileListResponse:
    """
    获取源文件列表

    可按模块或目录筛选。
    """
    files = await file_service.list_files(
        project_id=project_id,
        user_id=desktop_user.id,
        module_number=module_number,
        directory_id=directory_id,
    )

    return SourceFileListResponse(files=files, total=len(files))


@router.get("/coding/{project_id}/files/{file_id}")
async def get_file(
    project_id: str,
    file_id: int,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> SourceFileDetail:
    """
    获取源文件详情

    包含文件信息和当前选中版本的内容。
    """
    return await file_service.get_file(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
    )


@router.post("/coding/{project_id}/files")
async def create_file(
    project_id: str,
    request: SourceFileCreate,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> SourceFileResponse:
    """手动创建源文件"""
    file = await file_service.create_file(
        project_id=project_id,
        user_id=desktop_user.id,
        directory_id=request.directory_id,
        filename=request.filename,
        file_type=request.file_type.value,
        language=request.language,
        description=request.description,
        purpose=request.purpose,
        priority=request.priority.value,
    )
    await session.commit()

    return await file_service._serialize_file(file)


@router.patch("/coding/{project_id}/files/{file_id}")
async def update_file(
    project_id: str,
    file_id: int,
    request: SourceFileUpdate,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> SourceFileResponse:
    """更新源文件信息"""
    file = await file_service.update_file(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        filename=request.filename,
        description=request.description,
        purpose=request.purpose,
        priority=request.priority.value if request.priority else None,
        sort_order=request.sort_order,
    )
    await session.commit()

    return await file_service._serialize_file(file)


@router.delete("/coding/{project_id}/files/{file_id}")
async def delete_file(
    project_id: str,
    file_id: int,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除源文件"""
    await file_service.delete_file(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
    )
    await session.commit()

    return {"success": True, "message": "文件已删除"}


__all__ = ["router"]

