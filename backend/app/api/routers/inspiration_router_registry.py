"""
灵感对话路由注册器

目标：进一步收敛 coding/novels 两套灵感对话路由的注册骨架，减少重复与行为漂移风险。
仅收敛“路由层 HTTP 适配模板”，业务逻辑仍由 InspirationService 承担。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_default_user, get_inspiration_service
from ...db.session import get_session
from ...schemas.novel import ConverseRequest, ConverseResponse
from ...schemas.user import UserInDB
from ...utils.sse_helpers import create_sse_response
from .inspiration_helpers import (
    format_conversation_history_records,
    stream_inspiration_service_sse_events,
)


def register_inspiration_routes(
    router: APIRouter,
    *,
    path_prefix: str,
    project_type: str,
    error_title: str,
    project_service_dep: Any,
    conversation_service_dep: Any,
    history_log_label: str,
    enable_ai_message_log: bool,
    logger: Optional[logging.Logger] = None,
) -> None:
    """在指定 router 上注册灵感对话相关端点（converse/stream/history）。"""
    log = logger or logging.getLogger(__name__)
    prefix = path_prefix.rstrip("/")

    @router.post(f"{prefix}/{{project_id}}/inspiration/converse", response_model=ConverseResponse)
    async def converse_with_inspiration(
        project_id: str,
        request: ConverseRequest,
        project_service: Any = Depends(project_service_dep),
        inspiration_service: Any = Depends(get_inspiration_service),
        session: AsyncSession = Depends(get_session),
        desktop_user: UserInDB = Depends(get_default_user),
    ) -> ConverseResponse:
        """与AI进行灵感对话/需求分析对话（非流式）。"""
        await project_service.ensure_project_owner(project_id, desktop_user.id)

        result = await inspiration_service.process_conversation(
            project_id=project_id,
            user_input=request.user_input,
            user_id=desktop_user.id,
            project_type=project_type,
        )
        await session.commit()

        return ConverseResponse(**result.parsed_response)

    @router.post(f"{prefix}/{{project_id}}/inspiration/converse-stream")
    async def converse_with_inspiration_stream(
        project_id: str,
        request: ConverseRequest,
        project_service: Any = Depends(project_service_dep),
        inspiration_service: Any = Depends(get_inspiration_service),
        desktop_user: UserInDB = Depends(get_default_user),
    ):
        """与AI进行灵感对话/需求分析对话（SSE流式）。"""
        await project_service.ensure_project_owner(project_id, desktop_user.id)

        def _log_ai_message_ready(ai_message: str) -> None:
            if not enable_ai_message_log:
                return
            log.debug(
                "项目 %s 发送ai_message_chunk, 长度=%d",
                project_id,
                len(ai_message) if ai_message else 0,
            )

        async def event_generator():
            async for chunk_event in stream_inspiration_service_sse_events(
                inspiration_service=inspiration_service,
                project_id=project_id,
                user_input=request.user_input,
                user_id=desktop_user.id,
                project_type=project_type,
                error_title=error_title,
                on_ai_message_ready=_log_ai_message_ready if enable_ai_message_log else None,
            ):
                yield chunk_event

        return create_sse_response(event_generator())

    @router.get(f"{prefix}/{{project_id}}/inspiration/history", response_model=List[Dict[str, Any]])
    async def get_conversation_history(
        project_id: str,
        project_service: Any = Depends(project_service_dep),
        conversation_service: Any = Depends(conversation_service_dep),
        desktop_user: UserInDB = Depends(get_default_user),
    ) -> List[Dict[str, Any]]:
        """获取项目的对话历史（用于恢复对话）。"""
        await project_service.ensure_project_owner(project_id, desktop_user.id)

        history_records = await conversation_service.list_conversations(project_id)
        result = format_conversation_history_records(history_records)

        log.info(
            "%s %s 获取对话历史，用户 %s，记录数 %d",
            history_log_label,
            project_id,
            desktop_user.id,
            len(result),
        )

        return result


__all__ = ["register_inspiration_routes"]

