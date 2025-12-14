"""
API路由模块
"""
from fastapi import APIRouter

from .chat import router as chat_router
from .models import router as models_router
from .files import router as files_router
from .conversations import router as conversations_router
from .admin import router as admin_router

api_router = APIRouter()

# 聊天和模型路由（内部已包含/v1前缀）
api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(models_router, tags=["Models"])
api_router.include_router(files_router, tags=["Files"])

# 会话管理路由
api_router.include_router(conversations_router, prefix="/api/conversations", tags=["Conversations"])

# 管理员路由
api_router.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

__all__ = ["api_router"]
