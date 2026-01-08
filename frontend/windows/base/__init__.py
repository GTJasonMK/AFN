"""
通用页面基类模块

提供可被小说系统和编程系统复用的基类组件。
"""

from .detail_page import BaseDetailPage
from .workspace_page import BaseWorkspacePage
from .sections import BaseSection

__all__ = [
    "BaseDetailPage",
    "BaseWorkspacePage",
    "BaseSection",
]
