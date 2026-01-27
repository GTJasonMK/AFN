"""
编程项目层级路由：生成接口（systems/modules/dependencies）

拆分自 `backend/app/api/routers/coding/hierarchy.py`。
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.dependencies import (
    get_coding_project_service,
    get_default_user,
    get_llm_service,
    get_prompt_service,
    get_vector_store,
)
from ....db.session import get_session
from ....exceptions import InvalidParameterError, ResourceNotFoundError
from ....models.coding import CodingModule as CodingModuleModel
from ....models.coding import CodingSystem as CodingSystemModel
from ....repositories.coding_repository import CodingModuleRepository, CodingSystemRepository
from ....schemas.coding import CodingModule, CodingSystem, CodingSystemStatus
from ....schemas.user import UserInDB
from ....serializers.coding_serializer import CodingSerializer
from ....services.coding import CodingProjectService
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from ....utils.json_utils import parse_llm_json_or_fail
from ....utils.prompt_helpers import ensure_prompt
from ....utils.sse_helpers import create_sse_response, sse_event

logger = logging.getLogger(__name__)
router = APIRouter()


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


class GenerateAllModulesRequest(BaseModel):
    """批量生成所有系统模块请求"""

    min_modules: int = Field(default=3, description="每个系统最少模块数")
    max_modules: int = Field(default=8, description="每个系统最多模块数")
    preference: Optional[str] = Field(default=None, description="生成偏好指导")


async def _get_architecture_context(project) -> dict:
    """获取项目架构上下文信息"""
    blueprint = CodingSerializer.build_blueprint_schema(project)
    return blueprint.model_dump() if blueprint else {}


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
    system_prompt = ensure_prompt(await prompt_service.get_prompt("system_design"), "system_design")

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

    # 清除旧数据（级联删除：先删模块、再删系统）
    from sqlalchemy import delete

    await session.execute(delete(CodingModuleModel).where(CodingModuleModel.project_id == project_id))
    await session.execute(delete(CodingSystemModel).where(CodingSystemModel.project_id == project_id))
    await session.flush()
    logger.info("项目 %s 重新生成系统划分，已级联删除旧的系统/模块数据", project_id)

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
        created_systems.append(CodingSerializer.build_system_schema(new_system))

    await session.commit()
    logger.info("项目 %s 生成 %d 个系统", project_id, len(created_systems))

    # 自动入库：系统划分数据
    if vector_store and created_systems:
        try:
            from ....services.coding_rag import CodingDataType, schedule_ingestion

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
    system_prompt = ensure_prompt(await prompt_service.get_prompt("modules_batch_design"), "modules_batch_design")

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

    # 保存到数据库：先删除该系统下的旧模块
    from sqlalchemy import delete

    await session.execute(
        delete(CodingModuleModel).where(
            CodingModuleModel.project_id == project_id,
            CodingModuleModel.system_number == request.system_number,
        )
    )
    await session.flush()
    logger.info("项目 %s 系统 %d 重新生成模块，已删除旧的模块数据", project_id, request.system_number)

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
            generation_status=CodingSystemStatus.PENDING.value,
        )
        session.add(new_module)
        await session.flush()
        created_modules.append(CodingSerializer.build_module_schema(new_module))

    # 更新系统的模块数量
    target_system.module_count = len(created_modules)
    await session.commit()
    logger.info("项目 %s 系统 %d 生成 %d 个模块", project_id, request.system_number, len(created_modules))

    # 自动入库RAG
    if vector_store and created_modules:
        try:
            from ....services.coding_rag import CodingDataType, schedule_ingestion

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


@router.post("/coding/{project_id}/modules/generate-all")
async def generate_all_modules_stream(
    project_id: str,
    request: Optional[GenerateAllModulesRequest] = None,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
):
    """
    为所有系统批量生成模块（SSE流式）

    逐个系统生成模块，通过LLM队列控制并发，实时返回进度。

    事件类型:
    - start: 开始批量生成 {"total_systems": N}
    - system_start: 开始处理某个系统 {"system_number": N, "system_name": "xxx", "index": N}
    - system_complete: 完成某个系统 {"system_number": N, "modules_created": N}
    - system_error: 某个系统生成失败 {"system_number": N, "error": "xxx"}
    - complete: 全部完成 {"total_modules": N, "systems_processed": N}
    - error: 整体错误 {"message": "xxx"}
    """
    logger.info("收到批量生成模块请求: project_id=%s", project_id)

    # 验证项目所有权
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    # 获取所有系统
    system_repo = CodingSystemRepository(session)
    systems = await system_repo.get_by_project_ordered(project_id)

    if not systems:
        async def no_systems_generator():
            yield sse_event("error", {"message": "项目没有系统划分，请先生成系统"})

        return create_sse_response(no_systems_generator())

    # 获取请求参数
    min_modules = request.min_modules if request else 3
    max_modules = request.max_modules if request else 8
    preference = request.preference if request else None

    # 获取架构上下文
    architecture = await _get_architecture_context(project)

    # 获取提示词
    system_prompt = ensure_prompt(await prompt_service.get_prompt("modules_batch_design"), "modules_batch_design")

    # 获取LLM队列
    from ....services.queue import LLMRequestQueue

    llm_queue = LLMRequestQueue.get_instance()

    async def event_generator():
        total_modules_created = 0
        systems_processed = 0
        module_repo = CodingModuleRepository(session)

        # 发送开始事件
        yield sse_event(
            "start",
            {
                "total_systems": len(systems),
                "project_name": project.title,
            },
        )

        for idx, target_system in enumerate(systems):
            system_number = target_system.system_number
            system_name = target_system.name

            # 发送系统开始事件
            yield sse_event(
                "system_start",
                {
                    "system_number": system_number,
                    "system_name": system_name,
                    "index": idx + 1,
                    "total": len(systems),
                },
            )

            try:
                # 通过LLM队列控制并发
                async with llm_queue.request_slot():
                    # 计算起始模块编号
                    start_module_number = await module_repo.get_max_number(project_id) + 1

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
- 最少模块数: {min_modules}
- 最多模块数: {max_modules}
"""
                    if preference:
                        user_message += f"""
## 用户偏好指导
请特别注意以下偏好要求：
{preference}
"""
                    user_message += "\n请生成该系统的模块列表JSON。"

                    # 调用LLM
                    response = await llm_service.get_llm_response(
                        system_prompt=system_prompt,
                        conversation_history=[{"role": "user", "content": user_message}],
                        user_id=desktop_user.id,
                        temperature=settings.llm_temp_outline,
                        max_tokens=settings.llm_max_tokens_coding_module,
                        timeout=180,
                    )

                    # 解析结果
                    result = parse_llm_json_or_fail(response, f"系统{system_name}模块生成失败")

                    # 删除该系统下的旧模块
                    from sqlalchemy import delete

                    await session.execute(
                        delete(CodingModuleModel).where(
                            CodingModuleModel.project_id == project_id,
                            CodingModuleModel.system_number == system_number,
                        )
                    )
                    await session.flush()

                    # 保存模块
                    modules = result.get("modules", [])
                    modules_created = 0

                    for mod_data in modules:
                        new_module = CodingModuleModel(
                            project_id=project_id,
                            module_number=mod_data.get("module_number", start_module_number + modules_created),
                            system_number=system_number,
                            name=mod_data.get("name", ""),
                            module_type=mod_data.get("type", "service"),
                            description=mod_data.get("description", ""),
                            interface=mod_data.get("interface", ""),
                            dependencies=mod_data.get("dependencies", []),
                            generation_status=CodingSystemStatus.PENDING.value,
                        )
                        session.add(new_module)
                        modules_created += 1

                    # 更新系统的模块数量
                    target_system.module_count = modules_created
                    await session.commit()

                    total_modules_created += modules_created
                    systems_processed += 1

                    logger.info("系统 %s 模块生成完成: %d 个模块", system_name, modules_created)

                    # 发送系统完成事件
                    yield sse_event(
                        "system_complete",
                        {
                            "system_number": system_number,
                            "system_name": system_name,
                            "modules_created": modules_created,
                            "index": idx + 1,
                        },
                    )

            except Exception as e:
                logger.error("系统 %s 模块生成失败: %s", system_name, str(e))
                yield sse_event(
                    "system_error",
                    {
                        "system_number": system_number,
                        "system_name": system_name,
                        "error": str(e),
                        "index": idx + 1,
                    },
                )
                # 继续处理下一个系统
                continue

        # 发送完成事件
        yield sse_event(
            "complete",
            {
                "total_modules": total_modules_created,
                "systems_processed": systems_processed,
                "total_systems": len(systems),
            },
        )

        # 自动入库RAG
        if vector_store and total_modules_created > 0:
            try:
                from ....services.coding_rag import CodingDataType, schedule_ingestion

                schedule_ingestion(
                    project_id=project_id,
                    user_id=desktop_user.id,
                    data_type=CodingDataType.MODULE,
                    vector_store=vector_store,
                    llm_service=llm_service,
                )
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

    return create_sse_response(event_generator())


__all__ = [
    "router",
    "GenerateSystemsRequest",
    "GenerateModulesRequest",
    "GenerateAllModulesRequest",
]

