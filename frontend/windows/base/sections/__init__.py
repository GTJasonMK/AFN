"""
通用Section组件

提供可被小说系统和编程系统复用的Section基类。
"""

from .base_section import BaseSection, toggle_expand_state

__all__ = [
    "BaseSection",
    "toggle_expand_state",
]
