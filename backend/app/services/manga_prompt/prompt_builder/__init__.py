"""
提示词构建模块

基于分镜设计结果生成最终的AI绘图提示词。
"""

from .models import (
    PanelPrompt,
    PagePrompt,
    PagePromptResult,
    MangaPromptResult,
)
from .builder import PromptBuilder
from .page_prompt_generator import PagePromptGenerator

__all__ = [
    # 数据类
    "PanelPrompt",
    "PagePrompt",
    "PagePromptResult",
    "MangaPromptResult",
    # 构建器
    "PromptBuilder",
    "PagePromptGenerator",
]
