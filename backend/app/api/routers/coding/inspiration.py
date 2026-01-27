"""
编程项目灵感对话路由

处理用户与AI的需求分析对话，引导架构设计蓝图筹备。
路由层仅负责HTTP协议适配，业务逻辑委托给InspirationService。
"""

import logging

from fastapi import APIRouter

from ..inspiration_router_registry import register_inspiration_routes
from ....core.dependencies import (
    get_coding_conversation_service,
    get_coding_project_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()

register_inspiration_routes(
    router,
    path_prefix="/coding",
    project_type="coding",
    error_title="需求分析对话",
    project_service_dep=get_coding_project_service,
    conversation_service_dep=get_coding_conversation_service,
    history_log_label="编程项目",
    enable_ai_message_log=True,
    logger=logger,
)

__all__ = ["router"]

