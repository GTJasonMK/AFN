"""
章节大纲处理器模块

提供章节大纲操作的Mixin组件：
- PartOutlineHandlerMixin: 部分大纲操作处理器
- ChapterOutlineHandlerMixin: 章节大纲操作处理器
"""

from .part_outline_handler import PartOutlineHandlerMixin
from .chapter_outline_handler import ChapterOutlineHandlerMixin

__all__ = [
    "PartOutlineHandlerMixin",
    "ChapterOutlineHandlerMixin",
]
