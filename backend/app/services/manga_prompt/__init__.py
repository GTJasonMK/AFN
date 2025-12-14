"""
漫画提示词服务模块

将小说章节内容转化为文生图模型所需的提示词序列。
"""

from .service import MangaPromptService
from .schemas import (
    MangaScene,
    MangaPromptResult,
    MangaPromptRequest,
    MangaStyle,
)

__all__ = [
    "MangaPromptService",
    "MangaScene",
    "MangaPromptResult",
    "MangaPromptRequest",
    "MangaStyle",
]
