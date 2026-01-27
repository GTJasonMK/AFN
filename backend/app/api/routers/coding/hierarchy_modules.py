"""
编程项目层级路由：Module 管理（CRUD）

拆分自 `backend/app/api/routers/coding/hierarchy.py`。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_coding_project_service, get_default_user
from ....db.session import get_session
from ....exceptions import ResourceNotFoundError
from ....models.coding import CodingModule as CodingModuleModel
from ....repositories.coding_repository import CodingModuleRepository
from ....schemas.coding import CodingModule, CodingSystemStatus
from ....schemas.user import UserInDB
from ....serializers.coding_serializer import CodingSerializer
from ....services.coding import CodingProjectService

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateModuleRequest(BaseModel):
    """创建模块请求"""

    system_number: int = Field(..., description="所属系统编号")
    name: str = Field(..., description="模块名称")
    type: str = Field(default="service", description="模块类型")
    description: str = Field(default="", description="模块描述")
    interface: str = Field(default="", description="接口说明")
    dependencies: List[str] = Field(default_factory=list, description="依赖模块")


class UpdateModuleRequest(BaseModel):
    """更新模块请求"""

    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    interface: Optional[str] = None
    dependencies: Optional[List[str]] = None


@router.get("/coding/{project_id}/modules")
async def list_modules(
    project_id: str,
    system_number: Optional[int] = Query(None, description="按系统编号过滤"),
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[CodingModule]:
    """获取模块列表"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)

    if system_number is not None:
        modules = await module_repo.get_by_system(project_id, system_number)
    else:
        modules = await module_repo.get_by_project_ordered(project_id)

    return [CodingSerializer.build_module_schema(m) for m in modules]


@router.get("/coding/{project_id}/modules/{module_number}")
async def get_module(
    project_id: str,
    module_number: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingModule:
    """获取指定模块详情"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)
    module = await module_repo.get_by_project_and_number(project_id, module_number)

    if not module:
        raise ResourceNotFoundError("module", str(module_number), "模块不存在")

    return CodingSerializer.build_module_schema(module)


@router.post("/coding/{project_id}/modules")
async def create_module(
    project_id: str,
    request: CreateModuleRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingModule:
    """手动创建模块"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)

    # 计算新的模块编号
    new_number = await module_repo.get_max_number(project_id) + 1

    # 创建CodingModule记录
    new_module = CodingModuleModel(
        project_id=project_id,
        module_number=new_number,
        system_number=request.system_number,
        name=request.name,
        module_type=request.type or "",
        description=request.description or "",
        interface=request.interface or "",
        dependencies=request.dependencies or [],
        generation_status=CodingSystemStatus.PENDING.value,
    )
    session.add(new_module)
    await session.commit()

    logger.info("项目 %s 创建模块 %d: %s (系统 %d)", project_id, new_number, request.name, request.system_number)
    return CodingSerializer.build_module_schema(new_module)


@router.put("/coding/{project_id}/modules/{module_number}")
async def update_module(
    project_id: str,
    module_number: int,
    request: UpdateModuleRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingModule:
    """更新模块信息"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)
    module = await module_repo.get_by_project_and_number(project_id, module_number)

    if not module:
        raise ResourceNotFoundError("module", str(module_number), "模块不存在")

    # 更新字段
    if request.name is not None:
        module.name = request.name
    if request.type is not None:
        module.module_type = request.type
    if request.description is not None:
        module.description = request.description
    if request.interface is not None:
        module.interface = request.interface
    if request.dependencies is not None:
        module.dependencies = request.dependencies

    await session.commit()
    logger.info("项目 %s 更新模块 %d", project_id, module_number)

    return CodingSerializer.build_module_schema(module)


@router.delete("/coding/{project_id}/modules/{module_number}")
async def delete_module(
    project_id: str,
    module_number: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除模块"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)
    module = await module_repo.get_by_project_and_number(project_id, module_number)

    if not module:
        raise ResourceNotFoundError("module", str(module_number), "模块不存在")

    # 删除模块本身
    await session.delete(module)
    await session.commit()

    logger.info("项目 %s 删除模块 %d", project_id, module_number)
    return {"success": True, "deleted_module_number": module_number}


__all__ = [
    "router",
    "CreateModuleRequest",
    "UpdateModuleRequest",
]

