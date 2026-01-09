"""
Coding项目管理API路由

处理Coding项目的CRUD操作。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_llm_service,
    get_prompt_service,
)
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....schemas.coding import (
    CodingProjectCreate,
    CodingProjectUpdate,
    CodingProjectResponse,
    CodingProjectSummary,
)
from ....services.coding import CodingProjectService
from ....services.conversation_service import ConversationService
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from ....utils.json_utils import parse_llm_json_or_fail

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/coding", response_model=List[CodingProjectSummary])
async def list_coding_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """获取用户的Coding项目列表"""
    service = CodingProjectService(session)
    summaries, total = await service.list_projects_for_user(
        user.id, page, page_size
    )
    return summaries


@router.post("/coding", response_model=CodingProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_coding_project(
    data: CodingProjectCreate,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """创建新的Coding项目"""
    service = CodingProjectService(session)
    project = await service.create_project(
        user_id=user.id,
        title=data.title,
        initial_prompt=data.initial_prompt or "",
        skip_conversation=data.skip_conversation,
    )
    await session.commit()

    return await service.get_project_schema(project.id)


@router.get("/coding/{project_id}", response_model=CodingProjectResponse)
async def get_coding_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """获取Coding项目详情"""
    service = CodingProjectService(session)
    return await service.get_project_schema(project_id, user.id)


@router.patch("/coding/{project_id}", response_model=CodingProjectResponse)
async def update_coding_project(
    project_id: str,
    data: CodingProjectUpdate,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """更新Coding项目"""
    service = CodingProjectService(session)
    await service.update_project(
        project_id=project_id,
        user_id=user.id,
        title=data.title,
    )
    await session.commit()

    return await service.get_project_schema(project_id, user.id)


@router.delete("/coding/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coding_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """删除Coding项目"""
    service = CodingProjectService(session)
    await service.delete_project(project_id, user.id)
    await session.commit()


@router.post("/coding/batch-delete", status_code=status.HTTP_204_NO_CONTENT)
async def batch_delete_coding_projects(
    project_ids: List[str],
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """批量删除Coding项目"""
    service = CodingProjectService(session)
    await service.delete_projects(project_ids, user.id)
    await session.commit()


@router.post("/coding/{project_id}/blueprint/generate")
async def generate_coding_blueprint(
    project_id: str,
    allow_incomplete: bool = False,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
) -> Dict[str, Any]:
    """
    根据需求分析对话生成项目架构设计蓝图

    Args:
        project_id: 项目ID
        allow_incomplete: 是否允许在需求分析对话未完成时生成（自动补全模式）

    Returns:
        生成结果，包含蓝图数据
    """
    project_service = CodingProjectService(session)
    conversation_service = ConversationService(session, project_type="coding")

    # 验证项目权限
    project = await project_service.ensure_project_owner(project_id, user.id)

    # 获取对话历史
    history_records = await conversation_service.list_conversations(project_id)

    # 构建对话历史文本
    if history_records:
        conversation_text = "\n\n".join([
            f"{'用户' if r.role == 'user' else 'AI'}: {r.content}"
            for r in history_records
        ])
    else:
        # 没有对话历史
        if not allow_incomplete:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="请先进行需求分析对话"
            )
        # 自动补全模式：使用项目的initial_prompt或默认提示
        conversation_text = project.initial_prompt or "用户希望构建一个软件系统，请根据最佳实践设计一个通用的项目架构。"
        logger.info("项目 %s 使用自动补全模式（allow_incomplete=True）", project_id)

    # 获取架构设计提示词
    system_prompt = await prompt_service.get_prompt("architecture_design")
    if not system_prompt:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail="无法获取架构设计提示词"
        )

    # 如果是自动补全模式，在提示词中添加说明
    user_prompt = f"以下是需求分析对话历史，请基于此生成项目架构设计：\n\n{conversation_text}"
    if allow_incomplete and not history_records:
        user_prompt = (
            "用户提供的需求信息较少，请根据提供的信息和软件开发最佳实践，"
            "自动补全缺失的需求细节并生成完整的项目架构设计。\n\n"
            f"用户需求：\n{conversation_text}"
        )

    # 调用LLM生成架构设计
    logger.info("项目 %s 开始生成架构设计蓝图", project_id)

    # 构建对话历史（将用户提示作为一条消息）
    conversation_history = [{"role": "user", "content": user_prompt}]

    from ....core.config import settings
    from ....core.constants import LLMConstants

    llm_response = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=conversation_history,
        temperature=LLMConstants.BLUEPRINT_TEMPERATURE,
        user_id=user.id,
        timeout=LLMConstants.BLUEPRINT_GENERATION_TIMEOUT,
        max_tokens=settings.llm_max_tokens_coding_blueprint,
    )

    # 解析LLM响应
    blueprint_data = parse_llm_json_or_fail(llm_response, "架构设计生成失败")

    # 更新蓝图数据
    from ....repositories.coding_repository import CodingBlueprintRepository
    blueprint_repo = CodingBlueprintRepository(session)
    blueprint = await blueprint_repo.get_by_project(project_id)

    if blueprint:
        # 更新蓝图字段
        blueprint.title = blueprint_data.get("title", project.title)
        blueprint.architecture_synopsis = blueprint_data.get("architecture_synopsis", "")
        blueprint.target_audience = blueprint_data.get("target_audience", "")
        blueprint.project_type_desc = blueprint_data.get("project_type_desc", "")
        blueprint.tech_style = blueprint_data.get("tech_style", "")
        blueprint.project_tone = blueprint_data.get("project_tone", "")
        blueprint.one_sentence_summary = blueprint_data.get("one_sentence_summary", "")

        # 同步更新项目标题（如果蓝图中有title）
        if "title" in blueprint_data and blueprint_data["title"]:
            project.title = blueprint_data["title"]

        # 更新复杂字段（JSON）
        if "tech_stack" in blueprint_data:
            blueprint.tech_stack = blueprint_data["tech_stack"]
        if "system_suggestions" in blueprint_data:
            blueprint.system_suggestions = blueprint_data["system_suggestions"]
        if "core_requirements" in blueprint_data:
            blueprint.core_requirements = blueprint_data["core_requirements"]
        if "technical_challenges" in blueprint_data:
            blueprint.technical_challenges = blueprint_data["technical_challenges"]
        if "non_functional_requirements" in blueprint_data:
            blueprint.non_functional_requirements = blueprint_data["non_functional_requirements"]
        if "risks" in blueprint_data:
            blueprint.risks = blueprint_data["risks"]
        if "milestones" in blueprint_data:
            blueprint.milestones = blueprint_data["milestones"]

        blueprint.needs_phased_design = blueprint_data.get("needs_phased_design", False)
        blueprint.total_modules = blueprint_data.get("total_modules", 0)
        blueprint.total_systems = blueprint_data.get("total_systems", 0)

    # 更新项目状态为 BLUEPRINT_READY
    from ....core.state_machine import ProjectStatus
    project.status = ProjectStatus.BLUEPRINT_READY.value

    await session.commit()

    logger.info("项目 %s 架构设计蓝图生成成功", project_id)

    return {
        "success": True,
        "blueprint": blueprint_data,
        "project_id": project_id,
    }
