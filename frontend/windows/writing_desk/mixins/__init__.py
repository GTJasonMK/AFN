"""
写作台Mixin模块

提供写作台功能的各个Mixin组件：
- ChapterGenerationMixin: 章节生成、SSE流式处理、提示词预览
- ContentManagementMixin: 内容保存、RAG入库、编辑
- VersionManagementMixin: 版本选择、重试生成
- EvaluationMixin: 章节分析评估
"""

from .chapter_generation_mixin import ChapterGenerationMixin
from .content_management_mixin import ContentManagementMixin
from .version_management_mixin import VersionManagementMixin
from .evaluation_mixin import EvaluationMixin

__all__ = [
    "ChapterGenerationMixin",
    "ContentManagementMixin",
    "VersionManagementMixin",
    "EvaluationMixin",
]
