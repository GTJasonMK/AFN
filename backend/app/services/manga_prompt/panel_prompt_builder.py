"""
画格提示词构建器 - 兼容层

此文件为向后兼容保留，实际实现已迁移到 panel_prompt/ 子模块。
请使用新的导入路径：
    from .panel_prompt import PanelPromptBuilder, PanelPrompt

或直接从包级别导入：
    from app.services.manga_prompt import PanelPromptBuilder, PanelPrompt
"""

# 从新位置重新导出，保持向后兼容
from .panel_prompt import (
    PanelPromptBuilder,
    PanelPrompt,
    build_prompts_for_expansion,
    build_prompts_for_expansions,
)

__all__ = [
    "PanelPromptBuilder",
    "PanelPrompt",
    "build_prompts_for_expansion",
    "build_prompts_for_expansions",
]
