"""
灵感对话路由

处理用户与AI的灵感对话，引导蓝图筹备。
路由层仅负责HTTP协议适配，业务逻辑委托给InspirationService。
"""

import logging

from fastapi import APIRouter

from ..inspiration_router_registry import register_inspiration_routes
from ....core.dependencies import get_conversation_service, get_novel_service

logger = logging.getLogger(__name__)

router = APIRouter()

register_inspiration_routes(
    router,
    path_prefix="",
    project_type="novel",
    error_title="灵感对话",
    project_service_dep=get_novel_service,
    conversation_service_dep=get_conversation_service,
    history_log_label="项目",
    enable_ai_message_log=False,
    logger=logger,
)

__all__ = ["router"]

