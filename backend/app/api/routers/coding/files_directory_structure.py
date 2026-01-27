"""
Coding 文件相关路由：目录结构 API

拆分自 `backend/app/api/routers/coding/files.py`。
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_llm_service,
    get_prompt_service,
)
from ....db.session import get_session
from ....exceptions import ResourceNotFoundError
from ....schemas.coding_files import (
    DirectoryTreeResponse,
    GenerateDirectoryStructureRequest,
    GenerateDirectoryStructureResponse,
)
from ....schemas.user import UserInDB
from ....services.coding_files import DirectoryStructureService
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from .files_dependencies import get_directory_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/coding/{project_id}/directories/tree")
async def get_directory_tree(
    project_id: str,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> DirectoryTreeResponse:
    """
    获取项目的完整目录树

    返回项目的所有目录和文件，按树形结构组织。
    """
    return await directory_service.get_directory_tree(project_id, desktop_user.id)


@router.post("/coding/{project_id}/directories/generate")
async def generate_directory_structure(
    project_id: str,
    request: GenerateDirectoryStructureRequest,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> GenerateDirectoryStructureResponse:
    """
    为指定模块生成目录结构

    根据模块信息和功能列表，使用LLM生成合理的目录结构和源文件列表。
    """
    logger.info(
        "收到目录结构生成请求: project_id=%s module_number=%d",
        project_id,
        request.module_number,
    )

    # 获取模块名称
    from ....repositories.coding_repository import CodingModuleRepository

    module_repo = CodingModuleRepository(session)
    module = await module_repo.get_by_project_and_number(project_id, request.module_number)
    if not module:
        raise ResourceNotFoundError("模块", str(request.module_number))

    dirs_created, files_created, root_path = await directory_service.generate_for_module(
        project_id=project_id,
        user_id=desktop_user.id,
        module_number=request.module_number,
        preference=request.preference,
        clear_existing=request.clear_existing,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )

    await session.commit()

    logger.info(
        "目录结构生成完成: project_id=%s module=%d dirs=%d files=%d",
        project_id,
        request.module_number,
        dirs_created,
        files_created,
    )

    return GenerateDirectoryStructureResponse(
        module_number=request.module_number,
        module_name=module.name,
        directories_created=dirs_created,
        files_created=files_created,
        root_path=root_path,
        ai_message=f"已为模块「{module.name}」生成{dirs_created}个目录和{files_created}个源文件",
    )


__all__ = ["router"]

