"""
编程项目三层结构管理路由

处理系统(System)、模块(Module)、功能(Feature)的CRUD和生成操作。

数据库存储映射：
- Systems -> part_outlines 表
- Modules -> characters 表
- Features -> chapter_outlines 表
"""

import json
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_novel_service,
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
from ....models.part_outline import PartOutline
from ....models.novel import BlueprintCharacter, ChapterOutline, BlueprintRelationship
from ....repositories.part_outline_repository import PartOutlineRepository
from ....repositories.blueprint_repository import BlueprintCharacterRepository
from ....repositories.chapter_repository import ChapterOutlineRepository
from ....services.llm_service import LLMService
from ....services.novel_service import NovelService
from ....services.prompt_service import PromptService
from ....serializers.novel_serializer import NovelSerializer
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


class GenerateModulesRequest(BaseModel):
    """生成模块请求"""
    system_number: int = Field(..., description="目标系统编号")
    min_modules: int = Field(default=3, description="最少模块数")
    max_modules: int = Field(default=8, description="最多模块数")


class GenerateFeaturesRequest(BaseModel):
    """生成功能请求"""
    system_number: int = Field(..., description="所属系统编号")
    module_number: int = Field(..., description="目标模块编号")
    min_features: int = Field(default=2, description="最少功能数")
    max_features: int = Field(default=6, description="最多功能数")


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

def _validate_coding_project(project) -> None:
    """验证是否为编程项目"""
    if project.project_type != 'coding':
        raise InvalidParameterError("此API仅支持编程项目", parameter="project_type")


async def _get_architecture_context(project) -> dict:
    """获取项目架构上下文信息"""
    blueprint = NovelSerializer.build_coding_blueprint_schema(project)
    return blueprint.model_dump() if blueprint else {}


def _serialize_system(part: PartOutline) -> CodingSystem:
    """将PartOutline序列化为CodingSystem"""
    responsibilities = []
    if part.theme:
        try:
            responsibilities = json.loads(part.theme) if part.theme.startswith('[') else [part.theme]
        except (json.JSONDecodeError, TypeError):
            responsibilities = [part.theme] if part.theme else []

    tech_requirements = ""
    if part.key_events:
        if isinstance(part.key_events, list):
            tech_requirements = "\n".join(str(e) for e in part.key_events)
        else:
            tech_requirements = str(part.key_events)

    try:
        gen_status = CodingSystemStatus(part.generation_status) if part.generation_status else CodingSystemStatus.PENDING
    except ValueError:
        gen_status = CodingSystemStatus.PENDING

    return CodingSystem(
        system_number=part.part_number,
        name=part.title or f"系统{part.part_number}",
        description=part.summary or "",
        responsibilities=responsibilities,
        tech_requirements=tech_requirements,
        module_count=part.end_chapter - part.start_chapter + 1 if part.start_chapter and part.end_chapter else 0,
        feature_count=0,
        generation_status=gen_status,
        progress=part.progress or 0,
    )


def _serialize_module(character: BlueprintCharacter) -> CodingModule:
    """将BlueprintCharacter序列化为CodingModule"""
    extra = character.extra or {}

    dependencies = []
    if character.abilities:
        try:
            dependencies = json.loads(character.abilities) if character.abilities.startswith('[') else [d.strip() for d in character.abilities.split(',') if d.strip()]
        except (json.JSONDecodeError, TypeError):
            dependencies = [character.abilities] if character.abilities else []

    try:
        gen_status = CodingSystemStatus(extra.get("generation_status", "pending"))
    except ValueError:
        gen_status = CodingSystemStatus.PENDING

    return CodingModule(
        module_number=extra.get("module_number", character.position),
        system_number=extra.get("system_number", 1),
        name=character.name,
        type=character.identity or "",
        description=character.personality or "",
        interface=character.goals or "",
        dependencies=dependencies,
        feature_count=extra.get("feature_count", 0),
        generation_status=gen_status,
    )


def _serialize_feature(outline: ChapterOutline) -> CodingFeature:
    """将ChapterOutline序列化为CodingFeature"""
    feature_data = {"description": outline.summary or ""}
    if outline.summary:
        try:
            parsed = json.loads(outline.summary)
            if isinstance(parsed, dict):
                feature_data = parsed
        except (json.JSONDecodeError, TypeError):
            pass

    return CodingFeature(
        feature_number=outline.chapter_number,
        module_number=feature_data.get("module_number", 1),
        system_number=feature_data.get("system_number", 1),
        name=outline.title or f"功能{outline.chapter_number}",
        description=feature_data.get("description", outline.summary or ""),
        inputs=feature_data.get("inputs", ""),
        outputs=feature_data.get("outputs", ""),
        implementation_notes=feature_data.get("implementation_notes", ""),
        priority=feature_data.get("priority", "medium"),
    )


# ==================== 系统(System) CRUD ====================

@router.get("/coding/{project_id}/systems")
async def list_systems(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[CodingSystem]:
    """获取编程项目的系统列表"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    part_repo = PartOutlineRepository(session)
    parts = await part_repo.get_by_project_id(project_id)

    return [_serialize_system(part) for part in sorted(parts, key=lambda p: p.part_number)]


@router.get("/coding/{project_id}/systems/{system_number}")
async def get_system(
    project_id: str,
    system_number: int,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingSystem:
    """获取指定系统详情"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    part_repo = PartOutlineRepository(session)
    part = await part_repo.get_by_part_number(project_id, system_number)

    if not part:
        raise ResourceNotFoundError("system", str(system_number), "系统不存在")

    return _serialize_system(part)


@router.post("/coding/{project_id}/systems")
async def create_system(
    project_id: str,
    request: CreateSystemRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingSystem:
    """手动创建系统"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    part_repo = PartOutlineRepository(session)

    # 计算新的系统编号
    existing_parts = await part_repo.get_by_project_id(project_id)
    new_number = max([p.part_number for p in existing_parts], default=0) + 1

    # 创建PartOutline记录
    new_part = PartOutline(
        id=str(uuid.uuid4()),
        project_id=project_id,
        part_number=new_number,
        title=request.name,
        summary=request.description,
        theme=json.dumps(request.responsibilities, ensure_ascii=False) if request.responsibilities else "",
        key_events=[request.tech_requirements] if request.tech_requirements else [],
        start_chapter=0,
        end_chapter=0,
        generation_status=CodingSystemStatus.PENDING.value,
        progress=0,
    )
    session.add(new_part)
    await session.commit()

    logger.info("项目 %s 创建系统 %d: %s", project_id, new_number, request.name)
    return _serialize_system(new_part)


@router.put("/coding/{project_id}/systems/{system_number}")
async def update_system(
    project_id: str,
    system_number: int,
    request: UpdateSystemRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingSystem:
    """更新系统信息"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    part_repo = PartOutlineRepository(session)
    part = await part_repo.get_by_part_number(project_id, system_number)

    if not part:
        raise ResourceNotFoundError("system", str(system_number), "系统不存在")

    # 更新字段
    if request.name is not None:
        part.title = request.name
    if request.description is not None:
        part.summary = request.description
    if request.responsibilities is not None:
        part.theme = json.dumps(request.responsibilities, ensure_ascii=False)
    if request.tech_requirements is not None:
        part.key_events = [request.tech_requirements]

    await session.commit()
    logger.info("项目 %s 更新系统 %d", project_id, system_number)

    return _serialize_system(part)


@router.delete("/coding/{project_id}/systems/{system_number}")
async def delete_system(
    project_id: str,
    system_number: int,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除系统（同时删除关联的模块和功能）"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    part_repo = PartOutlineRepository(session)
    part = await part_repo.get_by_part_number(project_id, system_number)

    if not part:
        raise ResourceNotFoundError("system", str(system_number), "系统不存在")

    # 删除关联的模块（characters表中system_number匹配的记录）
    character_repo = BlueprintCharacterRepository(session)
    from sqlalchemy import delete
    await session.execute(
        delete(BlueprintCharacter).where(
            BlueprintCharacter.project_id == project_id,
            BlueprintCharacter.extra["system_number"].as_integer() == system_number
        )
    )

    # 删除关联的功能（chapter_outlines表中system_number匹配的记录）
    # 功能的system_number存储在summary的JSON中，需要特殊处理
    outline_repo = ChapterOutlineRepository(session)
    outlines = await outline_repo.get_by_project(project_id)
    deleted_chapter_numbers = set()
    for outline in outlines:
        try:
            data = json.loads(outline.summary or "{}")
            if data.get("system_number") == system_number:
                deleted_chapter_numbers.add(outline.chapter_number)
                await session.delete(outline)
        except (json.JSONDecodeError, TypeError):
            pass

    # 同时删除对应的功能内容（chapters表）
    # ChapterVersion会因外键级联删除而自动清理
    if deleted_chapter_numbers:
        from sqlalchemy import delete as sql_delete
        from ....models.novel import Chapter
        await session.execute(
            sql_delete(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number.in_(deleted_chapter_numbers)
            )
        )

    # 删除系统本身
    await session.delete(part)
    await session.commit()

    logger.info("项目 %s 删除系统 %d 及关联数据", project_id, system_number)
    return {"success": True, "deleted_system_number": system_number}


# ==================== 模块(Module) CRUD ====================

@router.get("/coding/{project_id}/modules")
async def list_modules(
    project_id: str,
    system_number: Optional[int] = Query(None, description="按系统编号过滤"),
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[CodingModule]:
    """获取模块列表"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    modules = [_serialize_module(c) for c in sorted(project.characters, key=lambda c: c.position)]

    # 按系统编号过滤
    if system_number is not None:
        modules = [m for m in modules if m.system_number == system_number]

    return modules


@router.get("/coding/{project_id}/modules/{module_number}")
async def get_module(
    project_id: str,
    module_number: int,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingModule:
    """获取指定模块详情"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    for character in project.characters:
        extra = character.extra or {}
        if extra.get("module_number") == module_number:
            return _serialize_module(character)

    raise ResourceNotFoundError("module", str(module_number), "模块不存在")


@router.post("/coding/{project_id}/modules")
async def create_module(
    project_id: str,
    request: CreateModuleRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingModule:
    """手动创建模块"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    # 计算新的模块编号
    existing_modules = [c.extra.get("module_number", c.position) for c in project.characters if c.extra]
    new_number = max(existing_modules, default=0) + 1

    # 计算position
    max_position = max([c.position for c in project.characters], default=0)

    # 创建BlueprintCharacter记录
    new_character = BlueprintCharacter(
        project_id=project_id,
        name=request.name,
        identity=request.type,
        personality=request.description,
        goals=request.interface,
        abilities=json.dumps(request.dependencies, ensure_ascii=False) if request.dependencies else "",
        position=max_position + 1,
        extra={
            "module_number": new_number,
            "system_number": request.system_number,
            "feature_count": 0,
            "generation_status": CodingSystemStatus.PENDING.value,
        },
    )
    session.add(new_character)
    await session.commit()

    logger.info("项目 %s 创建模块 %d: %s (系统 %d)", project_id, new_number, request.name, request.system_number)
    return _serialize_module(new_character)


@router.put("/coding/{project_id}/modules/{module_number}")
async def update_module(
    project_id: str,
    module_number: int,
    request: UpdateModuleRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingModule:
    """更新模块信息"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    target_character = None
    for character in project.characters:
        extra = character.extra or {}
        if extra.get("module_number") == module_number:
            target_character = character
            break

    if not target_character:
        raise ResourceNotFoundError("module", str(module_number), "模块不存在")

    # 更新字段
    if request.name is not None:
        target_character.name = request.name
    if request.type is not None:
        target_character.identity = request.type
    if request.description is not None:
        target_character.personality = request.description
    if request.interface is not None:
        target_character.goals = request.interface
    if request.dependencies is not None:
        target_character.abilities = json.dumps(request.dependencies, ensure_ascii=False)

    await session.commit()
    logger.info("项目 %s 更新模块 %d", project_id, module_number)

    return _serialize_module(target_character)


@router.delete("/coding/{project_id}/modules/{module_number}")
async def delete_module(
    project_id: str,
    module_number: int,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除模块（同时删除关联的功能）"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    target_character = None
    for character in project.characters:
        extra = character.extra or {}
        if extra.get("module_number") == module_number:
            target_character = character
            break

    if not target_character:
        raise ResourceNotFoundError("module", str(module_number), "模块不存在")

    # 删除关联的功能
    outline_repo = ChapterOutlineRepository(session)
    outlines = await outline_repo.get_by_project(project_id)
    deleted_chapter_numbers = set()
    for outline in outlines:
        try:
            data = json.loads(outline.summary or "{}")
            if data.get("module_number") == module_number:
                deleted_chapter_numbers.add(outline.chapter_number)
                await session.delete(outline)
        except (json.JSONDecodeError, TypeError):
            pass

    # 同时删除对应的功能内容（chapters表）
    # ChapterVersion会因外键级联删除而自动清理
    if deleted_chapter_numbers:
        from sqlalchemy import delete as sql_delete
        from ....models.novel import Chapter
        await session.execute(
            sql_delete(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number.in_(deleted_chapter_numbers)
            )
        )

    # 删除模块本身
    await session.delete(target_character)
    await session.commit()

    logger.info("项目 %s 删除模块 %d 及关联功能", project_id, module_number)
    return {"success": True, "deleted_module_number": module_number}


# ==================== 功能(Feature) CRUD ====================

@router.get("/coding/{project_id}/features/outlines")
async def list_feature_outlines(
    project_id: str,
    system_number: Optional[int] = Query(None, description="按系统编号过滤"),
    module_number: Optional[int] = Query(None, description="按模块编号过滤"),
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[CodingFeature]:
    """获取功能大纲列表"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    features = [_serialize_feature(o) for o in sorted(project.outlines, key=lambda o: o.chapter_number)]

    # 按系统/模块过滤
    if system_number is not None:
        features = [f for f in features if f.system_number == system_number]
    if module_number is not None:
        features = [f for f in features if f.module_number == module_number]

    return features


@router.get("/coding/{project_id}/features/outlines/{feature_number}")
async def get_feature_outline(
    project_id: str,
    feature_number: int,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingFeature:
    """获取指定功能大纲详情"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    for outline in project.outlines:
        if outline.chapter_number == feature_number:
            return _serialize_feature(outline)

    raise ResourceNotFoundError("feature", str(feature_number), "功能不存在")


@router.post("/coding/{project_id}/features/outlines")
async def create_feature_outline(
    project_id: str,
    request: CreateFeatureRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingFeature:
    """手动创建功能大纲"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    outline_repo = ChapterOutlineRepository(session)

    # 计算新的功能编号
    existing_numbers = [o.chapter_number for o in project.outlines]
    new_number = max(existing_numbers, default=0) + 1

    # 构建存储数据
    feature_data = {
        "system_number": request.system_number,
        "module_number": request.module_number,
        "description": request.description,
        "inputs": request.inputs,
        "outputs": request.outputs,
        "implementation_notes": request.implementation_notes,
        "priority": request.priority,
    }

    # 创建ChapterOutline记录
    new_outline = ChapterOutline(
        project_id=project_id,
        chapter_number=new_number,
        title=request.name,
        summary=json.dumps(feature_data, ensure_ascii=False),
    )
    session.add(new_outline)
    await session.commit()

    logger.info(
        "项目 %s 创建功能 %d: %s (系统 %d, 模块 %d)",
        project_id, new_number, request.name, request.system_number, request.module_number
    )
    return _serialize_feature(new_outline)


@router.put("/coding/{project_id}/features/outlines/{feature_number}")
async def update_feature_outline(
    project_id: str,
    feature_number: int,
    request: UpdateFeatureRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CodingFeature:
    """更新功能大纲"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    target_outline = None
    for outline in project.outlines:
        if outline.chapter_number == feature_number:
            target_outline = outline
            break

    if not target_outline:
        raise ResourceNotFoundError("feature", str(feature_number), "功能不存在")

    # 解析现有数据
    feature_data = {}
    try:
        feature_data = json.loads(target_outline.summary or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    # 更新字段
    if request.name is not None:
        target_outline.title = request.name
    if request.description is not None:
        feature_data["description"] = request.description
    if request.inputs is not None:
        feature_data["inputs"] = request.inputs
    if request.outputs is not None:
        feature_data["outputs"] = request.outputs
    if request.implementation_notes is not None:
        feature_data["implementation_notes"] = request.implementation_notes
    if request.priority is not None:
        feature_data["priority"] = request.priority

    target_outline.summary = json.dumps(feature_data, ensure_ascii=False)
    await session.commit()

    logger.info("项目 %s 更新功能 %d", project_id, feature_number)
    return _serialize_feature(target_outline)


@router.delete("/coding/{project_id}/features/outlines/{feature_number}")
async def delete_feature_outline(
    project_id: str,
    feature_number: int,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除功能大纲"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    target_outline = None
    for outline in project.outlines:
        if outline.chapter_number == feature_number:
            target_outline = outline
            break

    if not target_outline:
        raise ResourceNotFoundError("feature", str(feature_number), "功能不存在")

    # 删除功能大纲
    await session.delete(target_outline)

    # 同时删除对应的功能内容（chapters表）
    # ChapterVersion会因外键级联删除而自动清理
    from sqlalchemy import delete as sql_delete
    from ....models.novel import Chapter
    await session.execute(
        sql_delete(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.chapter_number == feature_number
        )
    )

    await session.commit()

    logger.info("项目 %s 删除功能 %d", project_id, feature_number)
    return {"success": True, "deleted_feature_number": feature_number}


# ==================== 生成接口 ====================

@router.post("/coding/{project_id}/systems/generate")
async def generate_systems(
    project_id: str,
    request: GenerateSystemsRequest = Body(default_factory=GenerateSystemsRequest),
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
) -> List[CodingSystem]:
    """根据架构设计自动生成系统划分"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

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

请生成系统划分的JSON。"""

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
    part_repo = PartOutlineRepository(session)
    await part_repo.delete_by_project_id(project_id)  # 清除旧数据

    systems = result.get("systems", [])
    created_systems = []

    for sys_data in systems:
        new_part = PartOutline(
            id=str(uuid.uuid4()),
            project_id=project_id,
            part_number=sys_data.get("system_number", len(created_systems) + 1),
            title=sys_data.get("name", ""),
            summary=sys_data.get("description", ""),
            theme=json.dumps(sys_data.get("responsibilities", []), ensure_ascii=False),
            key_events=[sys_data.get("tech_requirements", "")],
            start_chapter=0,
            end_chapter=sys_data.get("estimated_module_count", 0),
            generation_status=CodingSystemStatus.PENDING.value,
            progress=0,
        )
        session.add(new_part)
        await session.flush()
        created_systems.append(_serialize_system(new_part))

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
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
) -> List[CodingModule]:
    """为指定系统生成模块列表"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    # 获取目标系统
    part_repo = PartOutlineRepository(session)
    target_system = await part_repo.get_by_part_number(project_id, request.system_number)
    if not target_system:
        raise ResourceNotFoundError("system", str(request.system_number), "系统不存在")

    # 获取架构上下文
    architecture = await _get_architecture_context(project)

    # 计算起始模块编号
    existing_modules = [c.extra.get("module_number", c.position) for c in project.characters if c.extra]
    start_module_number = max(existing_modules, default=0) + 1

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
- 系统编号: {target_system.part_number}
- 系统名称: {target_system.title}
- 系统描述: {target_system.summary}

## 生成配置
- 起始模块编号 (start_module_number): {start_module_number}
- 最少模块数: {request.min_modules}
- 最多模块数: {request.max_modules}

请生成该系统的模块列表JSON。"""

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
    # 先删除该系统下的旧模块
    from sqlalchemy import delete
    # 注意：SQLite的JSON操作有限，这里使用Python过滤
    for character in list(project.characters):
        extra = character.extra or {}
        if extra.get("system_number") == request.system_number:
            await session.delete(character)
    await session.flush()

    modules = result.get("modules", [])
    created_modules = []
    max_position = max([c.position for c in project.characters], default=0)

    for mod_data in modules:
        new_character = BlueprintCharacter(
            project_id=project_id,
            name=mod_data.get("name", ""),
            identity=mod_data.get("type", "service"),
            personality=mod_data.get("description", ""),
            goals=mod_data.get("interface", ""),
            abilities=json.dumps(mod_data.get("dependencies", []), ensure_ascii=False),
            position=max_position + len(created_modules) + 1,
            extra={
                "module_number": mod_data.get("module_number", start_module_number + len(created_modules)),
                "system_number": request.system_number,
                "feature_count": mod_data.get("estimated_feature_count", 0),
                "generation_status": CodingSystemStatus.PENDING.value,
            },
        )
        session.add(new_character)
        await session.flush()
        created_modules.append(_serialize_module(new_character))

    # 更新系统的模块数量
    target_system.end_chapter = target_system.start_chapter + len(created_modules)
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
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
) -> List[CodingFeature]:
    """为指定模块生成功能大纲"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    # 获取目标模块
    target_module = None
    for character in project.characters:
        extra = character.extra or {}
        if extra.get("module_number") == request.module_number:
            target_module = character
            break

    if not target_module:
        raise ResourceNotFoundError("module", str(request.module_number), "模块不存在")

    # 获取架构上下文
    architecture = await _get_architecture_context(project)

    # 先删除该模块下的旧功能（在计算起始编号之前处理！）
    # 关键：使用已加载的 project.outlines，不做任何新的数据库查询，避免会话状态冲突

    # 1. 从已加载的 project.outlines 中收集需要删除的功能
    outlines_to_delete = []
    deleted_chapter_numbers = set()
    for outline in project.outlines:
        try:
            data = json.loads(outline.summary or "{}")
            if data.get("module_number") == request.module_number:
                outlines_to_delete.append(outline)
                deleted_chapter_numbers.add(outline.chapter_number)
        except (json.JSONDecodeError, TypeError):
            pass

    # 2. 计算起始功能编号（基于不会被删除的 outlines，完全在内存中计算）
    remaining_numbers = [o.chapter_number for o in project.outlines if o.chapter_number not in deleted_chapter_numbers]
    start_feature_number = max(remaining_numbers, default=0) + 1

    # 3. 批量删除旧功能（使用SQL语句，不触碰ORM对象状态）
    if outlines_to_delete:
        ids_to_delete = [o.id for o in outlines_to_delete]
        from sqlalchemy import delete as sql_delete
        from ....models.novel import Chapter

        # 删除功能大纲
        stmt = sql_delete(ChapterOutline).where(ChapterOutline.id.in_(ids_to_delete))
        await session.execute(stmt)

        # 同时删除对应的功能内容（chapters表，通过project_id + chapter_number关联）
        # ChapterVersion会因外键级联删除而自动清理
        if deleted_chapter_numbers:
            stmt_chapters = sql_delete(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number.in_(deleted_chapter_numbers)
            )
            await session.execute(stmt_chapters)

        await session.flush()

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

请生成该模块的功能大纲列表JSON。"""

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

    # 保存到数据库（旧功能已在前面删除）
    features = result.get("features", [])
    created_features = []

    for feat_data in features:
        feature_json = {
            "system_number": request.system_number,
            "module_number": request.module_number,
            "description": feat_data.get("description", ""),
            "inputs": feat_data.get("inputs", ""),
            "outputs": feat_data.get("outputs", ""),
            "implementation_notes": feat_data.get("implementation_notes", ""),
            "priority": feat_data.get("priority", "medium"),
        }

        new_outline = ChapterOutline(
            project_id=project_id,
            chapter_number=feat_data.get("feature_number", start_feature_number + len(created_features)),
            title=feat_data.get("name", ""),
            summary=json.dumps(feature_json, ensure_ascii=False),
        )
        session.add(new_outline)
        await session.flush()
        created_features.append(_serialize_feature(new_outline))

    # 更新模块的功能数量
    extra = target_module.extra or {}
    extra["feature_count"] = len(created_features)
    target_module.extra = extra

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
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[DependencyResponse]:
    """获取模块依赖关系列表"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    return [
        DependencyResponse(
            id=rel.id,
            from_module=rel.character_from,
            to_module=rel.character_to,
            description=rel.description or "",
            position=rel.position or 0,
        )
        for rel in sorted(project.relationships_, key=lambda r: r.position)
    ]


@router.post("/coding/{project_id}/dependencies")
async def create_dependency(
    project_id: str,
    request: CreateDependencyRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> DependencyResponse:
    """创建模块依赖关系"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    # 计算position
    max_position = max([r.position for r in project.relationships_], default=0)

    new_rel = BlueprintRelationship(
        project_id=project_id,
        character_from=request.from_module,
        character_to=request.to_module,
        description=request.description,
        position=max_position + 1,
    )
    session.add(new_rel)
    await session.commit()

    logger.info("项目 %s 创建依赖: %s -> %s", project_id, request.from_module, request.to_module)

    return DependencyResponse(
        id=new_rel.id,
        from_module=new_rel.character_from,
        to_module=new_rel.character_to,
        description=new_rel.description or "",
        position=new_rel.position,
    )


@router.delete("/coding/{project_id}/dependencies/{dependency_id}")
async def delete_dependency(
    project_id: str,
    dependency_id: int,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除模块依赖关系"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    target_rel = None
    for rel in project.relationships_:
        if rel.id == dependency_id:
            target_rel = rel
            break

    if not target_rel:
        raise ResourceNotFoundError("dependency", str(dependency_id), "依赖关系不存在")

    await session.delete(target_rel)
    await session.commit()

    logger.info("项目 %s 删除依赖 %d", project_id, dependency_id)
    return {"success": True, "deleted_dependency_id": dependency_id}


@router.post("/coding/{project_id}/dependencies/sync")
async def sync_dependencies(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """根据模块的dependencies字段同步依赖关系表

    遍历所有模块，将其dependencies字段中声明的依赖同步到relationships_表。
    这是一个幂等操作，会清除旧的依赖关系并重新创建。
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    _validate_coding_project(project)

    # 清除旧的依赖关系
    from sqlalchemy import delete
    await session.execute(
        delete(BlueprintRelationship).where(BlueprintRelationship.project_id == project_id)
    )

    # 构建模块名称映射
    module_names = {c.name for c in project.characters if c.extra and c.extra.get("module_number")}

    # 遍历模块，提取依赖关系
    new_dependencies = []
    position = 0

    for character in project.characters:
        extra = character.extra or {}
        if not extra.get("module_number"):
            continue

        # 解析dependencies字段
        dependencies = []
        if character.abilities:
            try:
                deps = json.loads(character.abilities) if character.abilities.startswith('[') else [d.strip() for d in character.abilities.split(',') if d.strip()]
                dependencies = deps
            except (json.JSONDecodeError, TypeError):
                if character.abilities:
                    dependencies = [character.abilities]

        # 为每个依赖创建关系记录
        for dep_name in dependencies:
            # 验证目标模块存在
            if dep_name in module_names:
                position += 1
                new_rel = BlueprintRelationship(
                    project_id=project_id,
                    character_from=character.name,
                    character_to=dep_name,
                    description=f"{character.name} 依赖 {dep_name}",
                    position=position,
                )
                session.add(new_rel)
                new_dependencies.append({
                    "from": character.name,
                    "to": dep_name,
                })

    await session.commit()

    logger.info("项目 %s 同步依赖关系: 创建 %d 条", project_id, len(new_dependencies))

    return {
        "success": True,
        "synced_count": len(new_dependencies),
        "dependencies": new_dependencies,
    }
