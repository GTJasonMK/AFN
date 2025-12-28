"""
正文优化模块

提供正文优化内容组件和相关类。

模块结构：
    - content.py: 主OptimizationContent组件
    - models.py: 数据模型（OptimizationMode枚举）
    - sse_handler.py: SSE事件处理Mixin
    - suggestion_handler.py: 建议处理Mixin
    - mode_control.py: 模式控制Mixin
"""

from .content import OptimizationContent
from .models import OptimizationMode
from .sse_handler import SSEHandlerMixin
from .suggestion_handler import SuggestionHandlerMixin
from .mode_control import ModeControlMixin

__all__ = [
    "OptimizationContent",
    "OptimizationMode",
    # Mixin类（高级用法）
    "SSEHandlerMixin",
    "SuggestionHandlerMixin",
    "ModeControlMixin",
]
