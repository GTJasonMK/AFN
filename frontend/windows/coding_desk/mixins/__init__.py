"""
编程项目工作台 Mixin 模块

将功能拆分为独立的 Mixin，提高代码可维护性。
"""

from .file_generation_mixin import FileGenerationMixin
from .content_management_mixin import ContentManagementMixin

__all__ = [
    "FileGenerationMixin",
    "ContentManagementMixin",
]
