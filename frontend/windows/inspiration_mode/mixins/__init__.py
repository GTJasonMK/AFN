"""
灵感模式Mixin模块

提供灵感模式功能的各个Mixin组件：
- InspirationBaseUIMixin: 通用UI与主题构建
- BlueprintHandlerMixin: 蓝图生成和处理
- ConversationManagerMixin: 对话管理（SSE流式、消息处理）
"""

from .base_ui_mixin import InspirationBaseUIMixin
from .blueprint_handler import BlueprintHandlerMixin
from .conversation_manager import ConversationManagerMixin

__all__ = [
    "InspirationBaseUIMixin",
    "BlueprintHandlerMixin",
    "ConversationManagerMixin",
]
