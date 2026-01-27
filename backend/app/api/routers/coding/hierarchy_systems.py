"""
编程项目层级路由：System 管理（CRUD）

拆分自 `backend/app/api/routers/coding/hierarchy.py`。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_coding_project_service, get_default_user
from ....db.session import get_session
from ....exceptions import ResourceNotFoundError
from ....models.coding import CodingModule as CodingModuleModel
from ....models.coding import CodingSystem as CodingSystemModel
from ....repositories.coding_repository import CodingSystemRepository
from ....schemas.coding import CodingSystem, CodingSystemStatus
from ....schemas.user import UserInDB
from ....serializers.coding_serializer import CodingSerializer
from ....services.coding import CodingProjectService

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateSystemRequest(BaseModel):
    """创建系统请求"""

    name: str = Field(..., description="系统名称")
    description: str = Field(default="", description="系统描述")
    responsibilities: List[str] = Field(default_factory=list, description="系统职责")
    tech_requirements: str = Field(default="", description="技术要求")


class UpdateSystemRequest(BaseModel):
    """更新系统请求"""

    name: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    tech_requirements: Optional[str] = None


@router.get("/coding/{project_id}/systems")
async def list_systems(
    project_id: str,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[CodingSystem]:
    """获取编程项目的系统列表"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    system_repo = CodingSystemRepository(session)
    systems = await system_repo.get_by_project_ordered(project_id)

    return [CodingSerializer.build_system_schema(sys) for sys in systems]


@router.get("/coding/{project_id}/systems/{system_number}")
async def get_system(
    project_id: str,
    system_number: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingSystem:
    """获取指定系统详情"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    system_repo = CodingSystemRepository(session)
    system = await system_repo.get_by_project_and_number(project_id, system_number)

    if not system:
        raise ResourceNotFoundError("system", str(system_number), "系统不存在")

    return CodingSerializer.build_system_schema(system)


@router.post("/coding/{project_id}/systems")
async def create_system(
    project_id: str,
    request: CreateSystemRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingSystem:
    """手动创建系统"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    system_repo = CodingSystemRepository(session)

    # 计算新的系统编号
    new_number = await system_repo.get_max_number(project_id) + 1

    # 创建CodingSystem记录
    new_system = CodingSystemModel(
        project_id=project_id,
        system_number=new_number,
        name=request.name,
        description=request.description or "",
        responsibilities=request.responsibilities or [],
        tech_requirements=request.tech_requirements or "",
        generation_status=CodingSystemStatus.PENDING.value,
        progress=0,
    )
    session.add(new_system)
    await session.commit()

    logger.info("项目 %s 创建系统 %d: %s", project_id, new_number, request.name)
    return CodingSerializer.build_system_schema(new_system)


@router.put("/coding/{project_id}/systems/{system_number}")
async def update_system(
    project_id: str,
    system_number: int,
    request: UpdateSystemRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingSystem:
    """更新系统信息"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    system_repo = CodingSystemRepository(session)
    system = await system_repo.get_by_project_and_number(project_id, system_number)

    if not system:
        raise ResourceNotFoundError("system", str(system_number), "系统不存在")

    # 更新字段
    if request.name is not None:
        system.name = request.name
    if request.description is not None:
        system.description = request.description
    if request.responsibilities is not None:
        system.responsibilities = request.responsibilities
    if request.tech_requirements is not None:
        system.tech_requirements = request.tech_requirements

    await session.commit()
    logger.info("项目 %s 更新系统 %d", project_id, system_number)

    return CodingSerializer.build_system_schema(system)


@router.delete("/coding/{project_id}/systems/{system_number}")
async def delete_system(
    project_id: str,
    system_number: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除系统（同时删除关联的模块）"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    system_repo = CodingSystemRepository(session)
    system = await system_repo.get_by_project_and_number(project_id, system_number)

    if not system:
        raise ResourceNotFoundError("system", str(system_number), "系统不存在")

    # 删除关联的模块
    from sqlalchemy import delete

    await session.execute(
        delete(CodingModuleModel).where(
            CodingModuleModel.project_id == project_id,
            CodingModuleModel.system_number == system_number,
        )
    )

    # 删除系统本身
    await session.delete(system)
    await session.commit()

    logger.info("项目 %s 删除系统 %d 及关联数据", project_id, system_number)
    return {"success": True, "deleted_system_number": system_number}


__all__ = [
    "router",
    "CreateSystemRequest",
    "UpdateSystemRequest",
]

