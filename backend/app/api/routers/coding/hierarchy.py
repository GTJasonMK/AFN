"""
编程项目三层结构管理路由

处理系统(System)、模块(Module)、功能(Feature)的CRUD和生成操作。

数据库存储映射：
- Systems -> coding_systems 表
- Modules -> coding_modules 表
- Features -> coding_features 表
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_coding_project_service,
    get_default_user,
    get_llm_service,
    get_prompt_service,
    get_vector_store,
)
from ....core.config import settings
from ....db.session import get_session
from ....exceptions import (
    InvalidParameterError,
    ResourceNotFoundError,
    JSONParseError,
)
from ....schemas.user import UserInDB
from ....schemas.coding import (
    CodingSystem,
    CodingSystemStatus,
    CodingModule,
    CodingFeature,
)
from ....models.coding import (
    CodingSystem as CodingSystemModel,
    CodingModule as CodingModuleModel,
    CodingFeature as CodingFeatureModel,
)
from ....repositories.coding_repository import (
    CodingSystemRepository,
    CodingModuleRepository,
    CodingFeatureRepository,
)
from ....services.llm_service import LLMService
from ....services.coding import CodingProjectService
from ....services.prompt_service import PromptService
from ....utils.json_utils import parse_llm_json_or_fail
from ....utils.prompt_helpers import ensure_prompt
from ....utils.sse_helpers import sse_event, create_sse_response

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 请求/响应模型 ====================

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


class CreateFeatureRequest(BaseModel):
    """创建功能请求"""
    system_number: int = Field(..., description="所属系统编号")
    module_number: int = Field(..., description="所属模块编号")
    name: str = Field(..., description="功能名称")
    description: str = Field(default="", description="功能描述")
    inputs: str = Field(default="", description="输入说明")
    outputs: str = Field(default="", description="输出说明")
    implementation_notes: str = Field(default="", description="实现要点")
    priority: str = Field(default="medium", description="优先级")


class UpdateFeatureRequest(BaseModel):
    """更新功能请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    implementation_notes: Optional[str] = None
    priority: Optional[str] = None


class GenerateSystemsRequest(BaseModel):
    """生成系统请求"""
    min_systems: int = Field(default=3, description="最少系统数")
    max_systems: int = Field(default=8, description="最多系统数")
    preference: Optional[str] = Field(default=None, description="重新生成时的偏好指导")


class GenerateModulesRequest(BaseModel):
    """生成模块请求"""
    system_number: int = Field(..., description="目标系统编号")
    min_modules: int = Field(default=3, description="最少模块数")
    max_modules: int = Field(default=8, description="最多模块数")
    preference: Optional[str] = Field(default=None, description="重新生成时的偏好指导")


class GenerateFeaturesRequest(BaseModel):
    """生成功能请求"""
    system_number: int = Field(..., description="所属系统编号")
    module_number: int = Field(..., description="目标模块编号")
    min_features: int = Field(default=2, description="最少功能数")
    max_features: int = Field(default=6, description="最多功能数")
    preference: Optional[str] = Field(default=None, description="重新生成时的偏好指导")


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


# ==================== 辅助函数 ====================

async def _get_architecture_context(project) -> dict:
    """获取项目架构上下文信息"""
    from ....serializers.coding_serializer import CodingSerializer
    blueprint = CodingSerializer.build_blueprint_schema(project)
    return blueprint.model_dump() if blueprint else {}


def _serialize_system(system: CodingSystemModel) -> CodingSystem:
    """将CodingSystemModel序列化为CodingSystem Schema"""
    try:
        gen_status = CodingSystemStatus(system.generation_status) if system.generation_status else CodingSystemStatus.PENDING
    except ValueError:
        gen_status = CodingSystemStatus.PENDING

    return CodingSystem(
        system_number=system.system_number,
        name=system.name or f"系统{system.system_number}",
        description=system.description or "",
        responsibilities=system.responsibilities or [],
        tech_requirements=system.tech_requirements or "",
        module_count=system.module_count or 0,
        feature_count=system.feature_count or 0,
        generation_status=gen_status,
        progress=system.progress or 0,
    )


def _serialize_module(module: CodingModuleModel) -> CodingModule:
    """将CodingModuleModel序列化为CodingModule Schema"""
    try:
        gen_status = CodingSystemStatus(module.generation_status) if module.generation_status else CodingSystemStatus.PENDING
    except ValueError:
        gen_status = CodingSystemStatus.PENDING

    return CodingModule(
        module_number=module.module_number,
        system_number=module.system_number,
        name=module.name,
        type=module.module_type or "",
        description=module.description or "",
        interface=module.interface or "",
        dependencies=module.dependencies or [],
        feature_count=module.feature_count or 0,
        generation_status=gen_status,
    )


def _serialize_feature(feature: CodingFeatureModel) -> CodingFeature:
    """将CodingFeatureModel序列化为CodingFeature Schema"""
    return CodingFeature(
        feature_number=feature.feature_number,
        module_number=feature.module_number,
        system_number=feature.system_number,
        name=feature.name or f"功能{feature.feature_number}",
        description=feature.description or "",
        inputs=feature.inputs or "",
        outputs=feature.outputs or "",
        implementation_notes=feature.implementation_notes or "",
        priority=feature.priority or "medium",
    )


# ==================== 系统(System) CRUD ====================

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

    return [_serialize_system(sys) for sys in systems]


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

    return _serialize_system(system)


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
    return _serialize_system(new_system)


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

    return _serialize_system(system)


@router.delete("/coding/{project_id}/systems/{system_number}")
async def delete_system(
    project_id: str,
    system_number: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除系统（同时删除关联的模块和功能）"""
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
            CodingModuleModel.system_number == system_number
        )
    )

    # 删除关联的功能
    await session.execute(
        delete(CodingFeatureModel).where(
            CodingFeatureModel.project_id == project_id,
            CodingFeatureModel.system_number == system_number
        )
    )

    # 删除系统本身
    await session.delete(system)
    await session.commit()

    logger.info("项目 %s 删除系统 %d 及关联数据", project_id, system_number)
    return {"success": True, "deleted_system_number": system_number}


# ==================== 模块(Module) CRUD ====================

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

    return [_serialize_module(m) for m in modules]


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

    return _serialize_module(module)



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
    return _serialize_module(new_module)


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

    return _serialize_module(module)


@router.delete("/coding/{project_id}/modules/{module_number}")
async def delete_module(
    project_id: str,
    module_number: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除模块（同时删除关联的功能）"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    module_repo = CodingModuleRepository(session)
    module = await module_repo.get_by_project_and_number(project_id, module_number)

    if not module:
        raise ResourceNotFoundError("module", str(module_number), "模块不存在")

    # 删除关联的功能
    from sqlalchemy import delete as sql_delete
    await session.execute(
        sql_delete(CodingFeatureModel).where(
            CodingFeatureModel.project_id == project_id,
            CodingFeatureModel.module_number == module_number
        )
    )

    # 删除模块本身
    await session.delete(module)
    await session.commit()

    logger.info("项目 %s 删除模块 %d 及关联功能", project_id, module_number)
    return {"success": True, "deleted_module_number": module_number}


# ==================== 功能(Feature) CRUD ====================

@router.get("/coding/{project_id}/features/outlines")
async def list_feature_outlines(
    project_id: str,
    system_number: Optional[int] = Query(None, description="按系统编号过滤"),
    module_number: Optional[int] = Query(None, description="按模块编号过滤"),
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[CodingFeature]:
    """获取功能大纲列表"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    feature_repo = CodingFeatureRepository(session)

    if module_number is not None:
        features = await feature_repo.get_by_module(project_id, module_number)
    elif system_number is not None:
        features = await feature_repo.get_by_system(project_id, system_number)
    else:
        features = await feature_repo.get_by_project_ordered(project_id)

    return [_serialize_feature(f) for f in features]


@router.get("/coding/{project_id}/features/outlines/{feature_number}")
async def get_feature_outline(
    project_id: str,
    feature_number: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingFeature:
    """获取指定功能大纲详情"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    feature_repo = CodingFeatureRepository(session)
    feature = await feature_repo.get_by_project_and_number(project_id, feature_number)

    if not feature:
        raise ResourceNotFoundError("feature", str(feature_number), "功能不存在")

    return _serialize_feature(feature)


@router.post("/coding/{project_id}/features/outlines")
async def create_feature_outline(
    project_id: str,
    request: CreateFeatureRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingFeature:
    """手动创建功能大纲"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    feature_repo = CodingFeatureRepository(session)

    # 计算新的功能编号
    new_number = await feature_repo.get_max_number(project_id) + 1

    # 创建CodingFeature记录
    new_feature = CodingFeatureModel(
        project_id=project_id,
        feature_number=new_number,
        system_number=request.system_number,
        module_number=request.module_number,
        name=request.name,
        description=request.description or "",
        inputs=request.inputs or "",
        outputs=request.outputs or "",
        implementation_notes=request.implementation_notes or "",
        priority=request.priority or "medium",
    )
    session.add(new_feature)
    await session.commit()

    logger.info(
        "项目 %s 创建功能 %d: %s (系统 %d, 模块 %d)",
        project_id, new_number, request.name, request.system_number, request.module_number
    )
    return _serialize_feature(new_feature)


@router.put("/coding/{project_id}/features/outlines/{feature_number}")
async def update_feature_outline(
    project_id: str,
    feature_number: int,
    request: UpdateFeatureRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingFeature:
    """更新功能大纲"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    feature_repo = CodingFeatureRepository(session)
    feature = await feature_repo.get_by_project_and_number(project_id, feature_number)

    if not feature:
        raise ResourceNotFoundError("feature", str(feature_number), "功能不存在")

    # 更新字段
    if request.name is not None:
        feature.name = request.name
    if request.description is not None:
        feature.description = request.description
    if request.inputs is not None:
        feature.inputs = request.inputs
    if request.outputs is not None:
        feature.outputs = request.outputs
    if request.implementation_notes is not None:
        feature.implementation_notes = request.implementation_notes
    if request.priority is not None:
        feature.priority = request.priority

    await session.commit()

    logger.info("项目 %s 更新功能 %d", project_id, feature_number)
    return _serialize_feature(feature)


@router.delete("/coding/{project_id}/features/outlines/{feature_number}")
async def delete_feature_outline(
    project_id: str,
    feature_number: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除功能大纲"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    feature_repo = CodingFeatureRepository(session)
    feature = await feature_repo.get_by_project_and_number(project_id, feature_number)

    if not feature:
        raise ResourceNotFoundError("feature", str(feature_number), "功能不存在")

    # 删除功能
    await session.delete(feature)
    await session.commit()

    logger.info("项目 %s 删除功能 %d", project_id, feature_number)
    return {"success": True, "deleted_feature_number": feature_number}


# ==================== 生成接口 ====================

@router.post("/coding/{project_id}/systems/generate")
async def generate_systems(
    project_id: str,
    request: GenerateSystemsRequest = Body(default_factory=GenerateSystemsRequest),
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
) -> List[CodingSystem]:
    """根据架构设计自动生成系统划分"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    if not project.blueprint:
        raise InvalidParameterError("请先生成项目架构设计", parameter="blueprint")

    # 获取架构上下文
    architecture = await _get_architecture_context(project)

    # 获取提示词
    system_prompt = ensure_prompt(
        await prompt_service.get_prompt("system_design"),
        "system_design"
    )

    # 构建用户消息
    user_message = f"""请根据以下项目架构设计，将项目划分为多个独立的子系统。

## 项目架构设计
{json.dumps(architecture, ensure_ascii=False, indent=2)}

## 生成配置
- 最少系统数: {request.min_systems}
- 最多系统数: {request.max_systems}
- 项目规模: 根据架构描述自动判断
"""

    # 如果有偏好指导，添加到用户消息中
    if request.preference:
        user_message += f"""
## 用户偏好指导
请特别注意以下偏好要求：
{request.preference}
"""
        logger.info("项目 %s 使用偏好指导重新生成系统划分", project_id)

    user_message += "\n请生成系统划分的JSON。"

    # 调用LLM（系统划分需要足够的token来生成完整JSON）
    response = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=[{"role": "user", "content": user_message}],
        user_id=desktop_user.id,
        temperature=settings.llm_temp_outline,
        max_tokens=settings.llm_max_tokens_coding_system,
        timeout=180,
    )

    # 解析结果
    result = parse_llm_json_or_fail(response, "系统划分生成失败")

    # 保存到数据库
    system_repo = CodingSystemRepository(session)
    # 清除旧数据（级联删除：先删功能、再删模块、最后删系统）
    from sqlalchemy import delete
    # 删除所有功能大纲
    await session.execute(
        delete(CodingFeatureModel).where(CodingFeatureModel.project_id == project_id)
    )
    # 删除所有模块
    await session.execute(
        delete(CodingModuleModel).where(CodingModuleModel.project_id == project_id)
    )
    # 删除所有系统
    await session.execute(
        delete(CodingSystemModel).where(CodingSystemModel.project_id == project_id)
    )
    await session.flush()
    logger.info("项目 %s 重新生成系统划分，已级联删除旧的系统/模块/功能数据", project_id)

    systems = result.get("systems", [])
    created_systems = []

    for sys_data in systems:
        new_system = CodingSystemModel(
            project_id=project_id,
            system_number=sys_data.get("system_number", len(created_systems) + 1),
            name=sys_data.get("name", ""),
            description=sys_data.get("description", ""),
            responsibilities=sys_data.get("responsibilities", []),
            tech_requirements=sys_data.get("tech_requirements", ""),
            module_count=sys_data.get("estimated_module_count", 0),
            generation_status=CodingSystemStatus.PENDING.value,
            progress=0,
        )
        session.add(new_system)
        await session.flush()
        created_systems.append(_serialize_system(new_system))

    await session.commit()
    logger.info("项目 %s 生成 %d 个系统", project_id, len(created_systems))

    # 自动入库：系统划分数据
    if vector_store and created_systems:
        try:
            from ....services.coding_rag import schedule_ingestion, CodingDataType
            schedule_ingestion(
                project_id=project_id,
                user_id=desktop_user.id,
                data_type=CodingDataType.SYSTEM,
                vector_store=vector_store,
                llm_service=llm_service,
            )
            logger.info("项目 %s 系统划分已调度RAG入库", project_id)
        except Exception as rag_exc:
            logger.warning("项目 %s 系统划分RAG入库调度失败: %s", project_id, str(rag_exc))

    return created_systems


@router.post("/coding/{project_id}/modules/generate")
async def generate_modules(
    project_id: str,
    request: GenerateModulesRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
) -> List[CodingModule]:
    """为指定系统生成模块列表"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    # 获取目标系统
    system_repo = CodingSystemRepository(session)
    target_system = await system_repo.get_by_project_and_number(project_id, request.system_number)
    if not target_system:
        raise ResourceNotFoundError("system", str(request.system_number), "系统不存在")

    # 获取架构上下文
    architecture = await _get_architecture_context(project)

    # 计算起始模块编号
    module_repo = CodingModuleRepository(session)
    start_module_number = await module_repo.get_max_number(project_id) + 1

    # 获取提示词
    system_prompt = ensure_prompt(
        await prompt_service.get_prompt("modules_batch_design"),
        "modules_batch_design"
    )

    # 构建用户消息
    user_message = f"""请为以下系统设计模块列表。

## 项目架构设计
{json.dumps(architecture, ensure_ascii=False, indent=2)}

## 当前系统信息
- 系统编号: {target_system.system_number}
- 系统名称: {target_system.name}
- 系统描述: {target_system.description}

## 生成配置
- 起始模块编号 (start_module_number): {start_module_number}
- 最少模块数: {request.min_modules}
- 最多模块数: {request.max_modules}
"""

    # 如果有偏好指导，添加到用户消息中
    if request.preference:
        user_message += f"""
## 用户偏好指导
请特别注意以下偏好要求：
{request.preference}
"""
        logger.info("项目 %s 系统 %d 使用偏好指导重新生成模块", project_id, request.system_number)

    user_message += "\n请生成该系统的模块列表JSON。"

    # 调用LLM（模块设计需要足够的token）
    response = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=[{"role": "user", "content": user_message}],
        user_id=desktop_user.id,
        temperature=settings.llm_temp_outline,
        max_tokens=settings.llm_max_tokens_coding_module,
        timeout=180,
    )

    # 解析结果
    result = parse_llm_json_or_fail(response, "模块生成失败")

    # 保存到数据库
    # 先删除该系统下的旧功能和旧模块（级联删除）
    from sqlalchemy import delete
    # 删除该系统下的所有功能大纲
    await session.execute(
        delete(CodingFeatureModel).where(
            CodingFeatureModel.project_id == project_id,
            CodingFeatureModel.system_number == request.system_number
        )
    )
    # 删除该系统下的所有模块
    await session.execute(
        delete(CodingModuleModel).where(
            CodingModuleModel.project_id == project_id,
            CodingModuleModel.system_number == request.system_number
        )
    )
    await session.flush()
    logger.info("项目 %s 系统 %d 重新生成模块，已级联删除旧的模块/功能数据", project_id, request.system_number)

    modules = result.get("modules", [])
    created_modules = []

    for mod_data in modules:
        new_module = CodingModuleModel(
            project_id=project_id,
            module_number=mod_data.get("module_number", start_module_number + len(created_modules)),
            system_number=request.system_number,
            name=mod_data.get("name", ""),
            module_type=mod_data.get("type", "service"),
            description=mod_data.get("description", ""),
            interface=mod_data.get("interface", ""),
            dependencies=mod_data.get("dependencies", []),
            feature_count=mod_data.get("estimated_feature_count", 0),
            generation_status=CodingSystemStatus.PENDING.value,
        )
        session.add(new_module)
        await session.flush()
        created_modules.append(_serialize_module(new_module))

    # 更新系统的模块数量
    target_system.module_count = len(created_modules)
    await session.commit()

    logger.info("项目 %s 系统 %d 生成 %d 个模块", project_id, request.system_number, len(created_modules))

    # 自动入库：模块定义和依赖关系
    if vector_store and created_modules:
        try:
            from ....services.coding_rag import schedule_ingestion, CodingDataType
            # 入库模块定义
            schedule_ingestion(
                project_id=project_id,
                user_id=desktop_user.id,
                data_type=CodingDataType.MODULE,
                vector_store=vector_store,
                llm_service=llm_service,
            )
            # 入库依赖关系
            schedule_ingestion(
                project_id=project_id,
                user_id=desktop_user.id,
                data_type=CodingDataType.DEPENDENCY,
                vector_store=vector_store,
                llm_service=llm_service,
            )
            logger.info("项目 %s 模块定义已调度RAG入库", project_id)
        except Exception as rag_exc:
            logger.warning("项目 %s 模块定义RAG入库调度失败: %s", project_id, str(rag_exc))

    return created_modules


@router.post("/coding/{project_id}/features/generate")
async def generate_features(
    project_id: str,
    request: GenerateFeaturesRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
) -> List[CodingFeature]:
    """为指定模块生成功能大纲"""
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    # 获取目标模块
    module_repo = CodingModuleRepository(session)
    target_module = await module_repo.get_by_project_and_number(project_id, request.module_number)

    if not target_module:
        raise ResourceNotFoundError("module", str(request.module_number), "模块不存在")

    # 获取架构上下文
    architecture = await _get_architecture_context(project)

    # 先删除该模块下的旧功能
    feature_repo = CodingFeatureRepository(session)
    from sqlalchemy import delete as sql_delete
    await session.execute(
        sql_delete(CodingFeatureModel).where(
            CodingFeatureModel.project_id == project_id,
            CodingFeatureModel.module_number == request.module_number
        )
    )
    await session.flush()

    # 计算起始功能编号
    start_feature_number = await feature_repo.get_max_number(project_id) + 1

    # 获取提示词
    system_prompt = ensure_prompt(
        await prompt_service.get_prompt("features_batch_outline"),
        "features_batch_outline"
    )

    # 构建模块信息
    module_info = _serialize_module(target_module).model_dump()

    # 构建用户消息
    user_message = f"""请为以下模块生成功能大纲列表。

## 项目架构设计
{json.dumps(architecture, ensure_ascii=False, indent=2)}

## 系统信息
- 系统编号: {request.system_number}

## 模块信息
{json.dumps(module_info, ensure_ascii=False, indent=2)}

## 生成配置
- 起始功能编号 (start_feature_number): {start_feature_number}
- 最少功能数: {request.min_features}
- 最多功能数: {request.max_features}
"""

    # 如果有偏好指导，添加到用户消息中
    if request.preference:
        user_message += f"""
## 用户偏好指导
请特别注意以下偏好要求：
{request.preference}
"""
        logger.info("项目 %s 模块 %d 使用偏好指导重新生成功能大纲", project_id, request.module_number)

    user_message += "\n请生成该模块的功能大纲列表JSON。"

    # 调用LLM（功能大纲需要足够的token）
    response = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=[{"role": "user", "content": user_message}],
        user_id=desktop_user.id,
        temperature=settings.llm_temp_outline,
        max_tokens=settings.llm_max_tokens_coding_feature,
        timeout=180,
    )

    # 解析结果
    result = parse_llm_json_or_fail(response, "功能大纲生成失败")

    # 保存到数据库
    features = result.get("features", [])
    created_features = []

    for feat_data in features:
        new_feature = CodingFeatureModel(
            project_id=project_id,
            feature_number=feat_data.get("feature_number", start_feature_number + len(created_features)),
            system_number=request.system_number,
            module_number=request.module_number,
            name=feat_data.get("name", ""),
            description=feat_data.get("description", ""),
            inputs=feat_data.get("inputs", ""),
            outputs=feat_data.get("outputs", ""),
            implementation_notes=feat_data.get("implementation_notes", ""),
            priority=feat_data.get("priority", "medium"),
        )
        session.add(new_feature)
        await session.flush()
        created_features.append(_serialize_feature(new_feature))

    # 更新模块的功能数量
    target_module.feature_count = len(created_features)

    await session.commit()

    logger.info(
        "项目 %s 模块 %d 生成 %d 个功能大纲",
        project_id, request.module_number, len(created_features)
    )

    # 自动入库：功能大纲
    if vector_store and created_features:
        try:
            from ....services.coding_rag import schedule_ingestion, CodingDataType
            schedule_ingestion(
                project_id=project_id,
                user_id=desktop_user.id,
                data_type=CodingDataType.FEATURE_OUTLINE,
                vector_store=vector_store,
                llm_service=llm_service,
            )
            logger.info("项目 %s 功能大纲已调度RAG入库", project_id)
        except Exception as rag_exc:
            logger.warning("项目 %s 功能大纲RAG入库调度失败: %s", project_id, str(rag_exc))

    return created_features


# ==================== 依赖关系管理 ====================

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

    # 构建模块名称到编号的映射
    module_name_map = {m.name: m.module_number for m in modules}

    # 遍历所有模块，提取依赖关系
    dependencies = []
    position = 0

    for module in modules:
        module_deps = module.dependencies or []
        for dep_name in module_deps:
            position += 1
            dependencies.append(DependencyResponse(
                id=position,  # 使用位置作为伪ID
                from_module=module.name,
                to_module=dep_name,
                description=f"{module.name} 依赖 {dep_name}",
                position=position,
            ))

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
    else:
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

    logger.info("项目 %s 依赖关系统计: 总计 %d 条, 有效 %d 条, 无效 %d 条",
                project_id, len(all_dependencies), len(valid_dependencies), len(invalid_dependencies))

    return {
        "success": True,
        "synced_count": len(valid_dependencies),  # 向后兼容
        "total_count": len(all_dependencies),
        "valid_count": len(valid_dependencies),
        "invalid_count": len(invalid_dependencies),
        "dependencies": valid_dependencies,
        "invalid_dependencies": invalid_dependencies,
    }
