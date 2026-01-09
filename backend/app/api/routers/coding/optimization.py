"""
Prompt 优化路由

提供编程项目功能 Prompt 的 Agent 优化 API。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_coding_project_service,
    get_default_user,
    get_llm_service,
    get_vector_store,
)
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....services.coding import CodingProjectService
from ....services.llm_service import LLMService
from ....services.vector_store_service import VectorStoreService
from ....services.coding_prompt_optimization import (
    DEFAULT_DIMENSIONS,
    DEFAULT_REVIEW_DIMENSIONS,
    DIMENSION_DISPLAY_NAMES,
    REVIEW_DIMENSION_DISPLAY_NAMES,
    OptimizationMode,
    PromptOptimizationWorkflow,
    PromptType,
    get_default_dimensions,
)
from ....utils.sse_helpers import create_sse_response

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 请求/响应模型 ====================

class StartOptimizationRequest(BaseModel):
    """启动优化请求"""
    feature_index: int = Field(..., description="功能索引（从0开始）")
    dimensions: Optional[List[str]] = Field(
        None,
        description="检查维度列表，默认使用全部维度",
    )
    mode: str = Field(
        "auto",
        description="优化模式: auto(自动), review(逐个审核), plan(计划模式)",
    )
    prompt_type: str = Field(
        "implementation",
        description="Prompt 类型: implementation(实现), review(审查)",
    )


class ApplySuggestionRequest(BaseModel):
    """应用建议请求"""
    feature_index: int = Field(..., description="功能索引（从0开始）")
    suggestion_id: str = Field(..., description="建议 ID")
    suggested_text: str = Field(..., description="建议的新文本")
    original_text: Optional[str] = Field(None, description="原始文本（用于替换）")
    prompt_type: str = Field(
        "implementation",
        description="Prompt 类型: implementation(实现), review(审查)",
    )


class SessionControlRequest(BaseModel):
    """会话控制请求"""
    session_id: str = Field(..., description="会话 ID")


class DimensionInfo(BaseModel):
    """维度信息"""
    id: str
    name: str
    weight: float


# ==================== 路由 ====================

@router.get("/coding/{project_id}/optimization/dimensions")
async def get_optimization_dimensions(
    project_id: str,
    prompt_type: str = "implementation",
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[DimensionInfo]:
    """
    获取可用的优化检查维度

    根据 prompt_type 返回对应的检查维度及其权重。
    - implementation: 实现 Prompt 维度
    - review: 审查 Prompt 维度
    """
    # 验证项目
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    from ....services.coding_prompt_optimization import (
        DIMENSION_WEIGHTS,
        REVIEW_DIMENSION_WEIGHTS,
    )

    # 根据 prompt_type 选择维度配置
    try:
        pt = PromptType(prompt_type)
    except ValueError:
        pt = PromptType.IMPLEMENTATION

    if pt == PromptType.REVIEW:
        default_dims = DEFAULT_REVIEW_DIMENSIONS
        display_names = REVIEW_DIMENSION_DISPLAY_NAMES
        weights = REVIEW_DIMENSION_WEIGHTS
    else:
        default_dims = DEFAULT_DIMENSIONS
        display_names = DIMENSION_DISPLAY_NAMES
        weights = DIMENSION_WEIGHTS

    dimensions = []
    for dim_id in default_dims:
        dimensions.append(DimensionInfo(
            id=dim_id,
            name=display_names.get(dim_id, dim_id),
            weight=weights.get(dim_id, 0.5),
        ))

    return dimensions


@router.post("/coding/{project_id}/optimization/start")
async def start_optimization(
    project_id: str,
    request: StartOptimizationRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    启动 Prompt 优化工作流（SSE 流式返回）

    事件类型：
    - workflow_start: 工作流开始
    - thinking: Agent 思考过程
    - action: Agent 执行动作
    - observation: 动作结果观察
    - suggestion: 生成的优化建议
    - workflow_paused: 工作流暂停（review/plan 模式）
    - workflow_resumed: 工作流恢复
    - plan_ready: 计划就绪（plan 模式）
    - workflow_complete: 工作流完成
    - error: 错误
    """
    logger.info(
        "启动 Prompt 优化: project=%s feature_index=%s mode=%s prompt_type=%s",
        project_id, request.feature_index, request.mode, request.prompt_type
    )

    # 验证项目
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    # 解析优化模式
    try:
        mode = OptimizationMode(request.mode)
    except ValueError:
        mode = OptimizationMode.AUTO

    # 解析 Prompt 类型
    try:
        prompt_type = PromptType(request.prompt_type)
    except ValueError:
        prompt_type = PromptType.IMPLEMENTATION

    # 创建工作流
    workflow = PromptOptimizationWorkflow(
        session=session,
        llm_service=llm_service,
        vector_store=vector_store,
        user_id=str(desktop_user.id),
    )

    async def event_generator():
        try:
            async for event in workflow.start_optimization(
                project_id=project_id,
                feature_index=request.feature_index,
                dimensions=request.dimensions,
                mode=mode,
                prompt_type=prompt_type,
            ):
                yield event
        except Exception as e:
            logger.exception("优化工作流异常: %s", e)
            from ....services.coding_prompt_optimization import sse_event, OptimizationEventType
            yield sse_event(OptimizationEventType.ERROR, {
                "error": str(e),
            })

    return create_sse_response(event_generator())


@router.post("/coding/{project_id}/optimization/apply")
async def apply_suggestion(
    project_id: str,
    request: ApplySuggestionRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    应用优化建议到 Prompt

    将建议的修改应用到功能 Prompt，创建新版本。
    支持 implementation(实现) 和 review(审查) 两种 Prompt 类型。
    """
    logger.info(
        "应用优化建议: project=%s feature_index=%s suggestion=%s prompt_type=%s",
        project_id, request.feature_index, request.suggestion_id, request.prompt_type
    )

    # 验证项目
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    # 解析 Prompt 类型
    try:
        prompt_type = PromptType(request.prompt_type)
    except ValueError:
        prompt_type = PromptType.IMPLEMENTATION

    # 创建工作流
    workflow = PromptOptimizationWorkflow(
        session=session,
        llm_service=llm_service,
        vector_store=vector_store,
        user_id=str(desktop_user.id),
    )

    # 应用建议
    success = await workflow.apply_suggestion(
        project_id=project_id,
        feature_index=request.feature_index,
        suggestion_id=request.suggestion_id,
        suggested_text=request.suggested_text,
        original_text=request.original_text,
        prompt_type=prompt_type,
    )

    await session.commit()

    return {
        "success": success,
        "feature_index": request.feature_index,
        "suggestion_id": request.suggestion_id,
    }


@router.post("/coding/{project_id}/optimization/pause")
async def pause_session(
    project_id: str,
    request: SessionControlRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    暂停优化会话
    """
    # 验证项目
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    workflow = PromptOptimizationWorkflow(
        session=session,
        llm_service=llm_service,
        vector_store=vector_store,
        user_id=str(desktop_user.id),
    )

    success = workflow.pause_session(request.session_id)

    return {
        "success": success,
        "session_id": request.session_id,
    }


@router.post("/coding/{project_id}/optimization/resume")
async def resume_session(
    project_id: str,
    request: SessionControlRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    恢复优化会话
    """
    # 验证项目
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    workflow = PromptOptimizationWorkflow(
        session=session,
        llm_service=llm_service,
        vector_store=vector_store,
        user_id=str(desktop_user.id),
    )

    success = workflow.resume_session(request.session_id)

    return {
        "success": success,
        "session_id": request.session_id,
    }


@router.post("/coding/{project_id}/optimization/cancel")
async def cancel_session(
    project_id: str,
    request: SessionControlRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    取消优化会话
    """
    # 验证项目
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    workflow = PromptOptimizationWorkflow(
        session=session,
        llm_service=llm_service,
        vector_store=vector_store,
        user_id=str(desktop_user.id),
    )

    success = workflow.cancel_session(request.session_id)

    return {
        "success": success,
        "session_id": request.session_id,
    }


@router.post("/coding/{project_id}/optimization/quick-score")
async def quick_score(
    project_id: str,
    request: StartOptimizationRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    快速评分（轻量级检查）

    对功能 Prompt 进行快速评分，返回总体分数和简要评价。
    """
    logger.info(
        "Prompt 快速评分: project=%s feature_index=%s",
        project_id, request.feature_index
    )

    # 验证项目
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    from ....services.coding_prompt_optimization import PromptChecker

    # 构建上下文
    workflow = PromptOptimizationWorkflow(
        session=session,
        llm_service=llm_service,
        vector_store=vector_store,
        user_id=str(desktop_user.id),
    )

    context = await workflow._build_context(project_id, request.feature_index)
    if not context:
        return {
            "success": False,
            "error": "无法获取功能上下文",
        }

    prompt_content = await workflow._get_prompt_content(project_id, request.feature_index)
    if not prompt_content:
        return {
            "success": False,
            "error": "功能尚无 Prompt 内容",
        }

    # 快速评分
    checker = PromptChecker(llm_service)
    result = await checker.quick_score(
        prompt_content=prompt_content,
        context=context,
        user_id=str(desktop_user.id),
    )

    return result
