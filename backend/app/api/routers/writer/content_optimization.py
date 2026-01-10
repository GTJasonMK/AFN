"""
正文优化API路由

提供章节内容优化的流式API端点。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_llm_service,
    get_prompt_service,
    get_vector_store,
)
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....services.content_optimization.schemas import OptimizeContentRequest
from ....services.content_optimization.service import ContentOptimizationService
from ....services.content_optimization.session_manager import get_session_manager
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from ....services.vector_store_service import VectorStoreService
from ....utils.sse_helpers import create_sse_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/novels/{project_id}/chapters/{chapter_number}/optimize")
async def optimize_chapter_content(
    project_id: str,
    chapter_number: int,
    request: OptimizeContentRequest,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    流式优化章节内容

    对章节正文进行逐段分析，检查逻辑连贯性、角色一致性等维度，
    并生成修改建议。

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        request: 优化请求
            - content: 章节正文
            - scope: 分析范围 (full/selected)
            - selected_paragraphs: 选中的段落索引列表
            - dimensions: 检查维度列表
            - mode: 优化模式 (auto/review/plan)
                - auto: 自动模式，不暂停
                - review: 审核模式，每个建议后暂停等待确认
                - plan: 计划模式，完成全部分析后暂停，用户选择性应用

    Returns:
        SSE流式响应，包含以下事件类型：
        - workflow_start: 工作流开始
        - paragraph_start: 开始处理段落
        - thinking: Agent思考过程
        - action: Agent执行动作
        - observation: 观察结果
        - suggestion: 修改建议
        - paragraph_complete: 段落处理完成
        - workflow_paused: 工作流暂停（Review模式）
        - workflow_resumed: 工作流恢复
        - plan_ready: 分析完成等待用户选择（Plan模式）
        - workflow_complete: 工作流完成
        - error: 错误信息
    """
    logger.info(
        "用户 %s 请求优化项目 %s 第 %s 章内容",
        desktop_user.id,
        project_id,
        chapter_number,
    )

    service = ContentOptimizationService(
        session=session,
        llm_service=llm_service,
        vector_store=vector_store,
        prompt_service=prompt_service,
        embedding_service=llm_service.embedding_service,
    )

    return create_sse_response(
        service.optimize_chapter_stream(
            project_id=project_id,
            chapter_number=chapter_number,
            request=request,
            user_id=desktop_user.id,
        )
    )


@router.post("/novels/{project_id}/chapters/preview-paragraphs")
async def preview_paragraphs(
    project_id: str,
    request: OptimizeContentRequest,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    预览段落分割结果

    用于前端展示段落分割预览，帮助用户选择要分析的段落。

    Args:
        project_id: 项目ID
        request: 请求（只需要content字段）

    Returns:
        段落预览信息：
        - total_paragraphs: 总段落数
        - paragraphs: 段落列表，每项包含 index, preview, length
    """
    service = ContentOptimizationService(
        session=session,
        llm_service=llm_service,
    )

    return await service.get_paragraph_preview(request.content)


class SessionActionResponse(BaseModel):
    """会话操作响应"""
    success: bool
    message: str


class ContinueSessionRequest(BaseModel):
    """继续会话请求"""
    content: Optional[str] = None  # 前端发送的最新编辑器内容


@router.post("/optimization-sessions/{session_id}/continue")
async def continue_optimization_session(
    session_id: str,
    request: Optional[ContinueSessionRequest] = None,
    desktop_user: UserInDB = Depends(get_default_user),
) -> SessionActionResponse:
    """
    继续暂停的优化会话

    在以下场景调用此接口：
    - Review模式：用户处理完单个建议后，让分析继续进行
    - Plan模式：用户审阅完所有建议后，确认完成工作流
    - Auto模式：前端自动应用建议后，自动调用继续

    重要：调用时应传入当前编辑器的最新内容，确保后端使用最新数据继续分析。

    Args:
        session_id: 会话ID（从workflow_start或plan_ready事件获取）
        request: 请求体，包含可选的 content 字段

    Returns:
        操作结果
    """
    logger.info("用户 %s 请求继续会话 %s", desktop_user.id, session_id)

    content = request.content if request else None
    if content:
        logger.info("收到新内容，长度: %d", len(content))

    session_manager = get_session_manager()
    success = session_manager.resume_session(session_id, content=content)

    if success:
        return SessionActionResponse(success=True, message="会话已恢复")
    else:
        raise HTTPException(
            status_code=404,
            detail=f"会话不存在或已结束: {session_id}"
        )


@router.post("/optimization-sessions/{session_id}/cancel")
async def cancel_optimization_session(
    session_id: str,
    desktop_user: UserInDB = Depends(get_default_user),
) -> SessionActionResponse:
    """
    取消优化会话

    取消正在进行的优化分析。

    Args:
        session_id: 会话ID

    Returns:
        操作结果
    """
    logger.info("用户 %s 请求取消会话 %s", desktop_user.id, session_id)

    session_manager = get_session_manager()
    success = session_manager.cancel_session(session_id)

    if success:
        return SessionActionResponse(success=True, message="会话已取消")
    else:
        raise HTTPException(
            status_code=404,
            detail=f"会话不存在: {session_id}"
        )


@router.get("/optimization-sessions/{session_id}")
async def get_optimization_session(
    session_id: str,
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    获取优化会话状态

    Args:
        session_id: 会话ID

    Returns:
        会话状态信息
    """
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"会话不存在: {session_id}"
        )

    return {
        "session_id": session.session_id,
        "project_id": session.project_id,
        "chapter_number": session.chapter_number,
        "is_paused": session.is_paused,
        "is_cancelled": session.is_cancelled,
        "current_paragraph": session.current_paragraph,
        "total_paragraphs": session.total_paragraphs,
    }
