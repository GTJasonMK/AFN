"""
Coding 文件相关路由：版本管理 API

拆分自 `backend/app/api/routers/coding/files.py`。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_default_user
from ....db.session import get_session
from ....schemas.coding_files import FileVersionListResponse, SelectFileVersionRequest
from ....schemas.user import UserInDB
from ....services.coding_files import FilePromptService
from .files_dependencies import get_file_prompt_service

router = APIRouter()


@router.get("/coding/{project_id}/files/{file_id}/versions")
async def get_file_versions(
    project_id: str,
    file_id: int,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> FileVersionListResponse:
    """获取文件的所有版本"""
    versions = await file_service.get_versions(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
    )

    # 获取当前选中的版本ID
    file = await file_service.file_repo.get_by_id(file_id)
    selected_version_id = file.selected_version_id if file else None

    return FileVersionListResponse(
        versions=versions,
        selected_version_id=selected_version_id,
    )


@router.post("/coding/{project_id}/files/{file_id}/select-version")
async def select_file_version(
    project_id: str,
    file_id: int,
    request: SelectFileVersionRequest,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """选择文件版本"""
    file = await file_service.select_version(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        version_id=request.version_id,
    )
    await session.commit()

    return {
        "success": True,
        "selected_version_id": file.selected_version_id,
    }


__all__ = ["router"]

