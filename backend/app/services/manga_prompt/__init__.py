"""
漫画提示词服务模块

将小说章节内容转化为文生图模型所需的提示词序列。
支持专业漫画排版：先生成排版方案，再基于排版生成提示词。
"""

from .service import MangaPromptService
from .layout_service import LayoutService
from .schemas import (
    MangaScene,
    MangaPromptResult,
    MangaPromptRequest,
    MangaStyle,
    PanelInfo,
    LayoutInfo,
)
from .layout_schemas import (
    LayoutType,
    PageSize,
    PanelShape,
    PanelImportance,
    CompositionHint,
    Panel,
    Page,
    MangaLayout,
    LayoutGenerationRequest,
    LayoutGenerationResult,
)

__all__ = [
    # 主服务
    "MangaPromptService",
    "LayoutService",
    # 提示词相关
    "MangaScene",
    "MangaPromptResult",
    "MangaPromptRequest",
    "MangaStyle",
    "PanelInfo",
    "LayoutInfo",
    # 排版相关
    "LayoutType",
    "PageSize",
    "PanelShape",
    "PanelImportance",
    "CompositionHint",
    "Panel",
    "Page",
    "MangaLayout",
    "LayoutGenerationRequest",
    "LayoutGenerationResult",
]
