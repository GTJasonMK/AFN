"""
编程项目层级路由：依赖关系管理

拆分自 `backend/app/api/routers/coding/hierarchy.py`。
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_coding_project_service, get_default_user
from ....db.session import get_session
from ....exceptions import ResourceNotFoundError
from ....repositories.coding_repository import CodingModuleRepository
from ....schemas.user import UserInDB
from ....services.coding import CodingProjectService

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateDependencyRequest(BaseModel):
    """创建依赖关系请求"""

    from_module: str = Field(..., description="源模块名称")
    to_module: str = Field(..., description="目标模块名称")
    description: str = Field(default="", description="依赖描述")


class DependencyResponse(BaseModel):
    """依赖关系响应"""

    id: int
    from_module: str
    to_module: str
    description: str
    position: int


@router.get("/coding/{project_id}/dependencies")
async def list_dependencies(
    project_id: str,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[DependencyResponse]:
    """获取模块依赖关系列表

    从各模块的dependencies字段提取依赖关系。
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)
    modules = await module_repo.get_by_project_ordered(project_id)

    # 遍历所有模块，提取依赖关系
    dependencies = []
    position = 0

    for module in modules:
        module_deps = module.dependencies or []
        for dep_name in module_deps:
            position += 1
            dependencies.append(
                DependencyResponse(
                    id=position,  # 使用位置作为伪ID
                    from_module=module.name,
                    to_module=dep_name,
                    description=f"{module.name} 依赖 {dep_name}",
                    position=position,
                )
            )

    return dependencies


@router.post("/coding/{project_id}/dependencies")
async def create_dependency(
    project_id: str,
    request: CreateDependencyRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> DependencyResponse:
    """创建模块依赖关系

    将依赖添加到源模块的dependencies字段中。
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)
    modules = await module_repo.get_by_project_ordered(project_id)

    # 查找源模块
    source_module = None
    target_exists = False
    for m in modules:
        if m.name == request.from_module:
            source_module = m
        if m.name == request.to_module:
            target_exists = True

    if not source_module:
        raise ResourceNotFoundError("module", request.from_module, "源模块不存在")
    if not target_exists:
        raise ResourceNotFoundError("module", request.to_module, "目标模块不存在")

    # 添加依赖到源模块
    current_deps = source_module.dependencies or []
    if request.to_module not in current_deps:
        current_deps.append(request.to_module)
        source_module.dependencies = current_deps
        await session.commit()

    logger.info("项目 %s 创建依赖: %s -> %s", project_id, request.from_module, request.to_module)

    # 计算position
    position = len(current_deps)

    return DependencyResponse(
        id=position,
        from_module=request.from_module,
        to_module=request.to_module,
        description=request.description or f"{request.from_module} 依赖 {request.to_module}",
        position=position,
    )


@router.delete("/coding/{project_id}/dependencies/{dependency_id}")
async def delete_dependency(
    project_id: str,
    dependency_id: int,
    from_module: str = Query(..., description="源模块名称"),
    to_module: str = Query(..., description="目标模块名称"),
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除模块依赖关系

    从源模块的dependencies字段中移除指定依赖。
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)
    modules = await module_repo.get_by_project_ordered(project_id)

    # 查找源模块
    source_module = None
    for m in modules:
        if m.name == from_module:
            source_module = m
            break

    if not source_module:
        raise ResourceNotFoundError("module", from_module, "源模块不存在")

    # 从源模块移除依赖
    current_deps = source_module.dependencies or []
    if to_module in current_deps:
        current_deps.remove(to_module)
        source_module.dependencies = current_deps
        await session.commit()
        logger.info("项目 %s 删除依赖: %s -> %s", project_id, from_module, to_module)
        return {"success": True, "deleted_dependency": {"from": from_module, "to": to_module}}

    raise ResourceNotFoundError("dependency", f"{from_module}->{to_module}", "依赖关系不存在")


@router.post("/coding/{project_id}/dependencies/sync")
async def sync_dependencies(
    project_id: str,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """同步依赖关系统计

    返回当前所有模块的依赖关系统计信息。
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)
    modules = await module_repo.get_by_project_ordered(project_id)

    # 构建模块名称集合
    module_names = {m.name for m in modules}

    # 遍历模块，提取依赖关系
    all_dependencies = []
    valid_dependencies = []
    invalid_dependencies = []

    for module in modules:
        module_deps = module.dependencies or []
        for dep_name in module_deps:
            dep_info = {"from": module.name, "to": dep_name}
            all_dependencies.append(dep_info)
            if dep_name in module_names:
                valid_dependencies.append(dep_info)
            else:
                invalid_dependencies.append(dep_info)

    logger.info(
        "项目 %s 依赖关系统计: 总计 %d 条, 有效 %d 条, 无效 %d 条",
        project_id,
        len(all_dependencies),
        len(valid_dependencies),
        len(invalid_dependencies),
    )

    return {
        "success": True,
        "synced_count": len(valid_dependencies),  # 向后兼容
        "total_count": len(all_dependencies),
        "valid_count": len(valid_dependencies),
        "invalid_count": len(invalid_dependencies),
        "dependencies": valid_dependencies,
        "invalid_dependencies": invalid_dependencies,
    }


__all__ = [
    "router",
    "CreateDependencyRequest",
    "DependencyResponse",
]

