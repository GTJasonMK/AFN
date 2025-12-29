"""
提示词构建模块

基于分镜设计结果生成最终的AI绘图提示词。
"""

from .models import (
    PanelPrompt,
    PagePromptResult,
    MangaPromptResult,
)
from .builder import PromptBuilder

__all__ = [
    # 数据类
    "PanelPrompt",
    "PagePromptResult",
    "MangaPromptResult",
    # 构建器
    "PromptBuilder",
]
