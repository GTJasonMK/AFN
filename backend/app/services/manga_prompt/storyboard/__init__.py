"""
分镜设计模块

为每个页面设计详细的分镜：
- 确定每格的镜头类型和大小
- 分配对话和音效
- 描述视觉内容
- 生成英文描述用于AI绘图
"""

from .models import (
    ShotType,
    PanelSize,
    PanelShape,
    DialogueBubble,
    SoundEffect,
    PanelDesign,
    PageStoryboard,
    StoryboardResult,
)
from .prompts import (
    PROMPT_NAME,
    STORYBOARD_DESIGN_PROMPT,
    STORYBOARD_SYSTEM_PROMPT,
)
from .designer import StoryboardDesigner

__all__ = [
    # 枚举类型
    "ShotType",
    "PanelSize",
    "PanelShape",
    # 数据类
    "DialogueBubble",
    "SoundEffect",
    "PanelDesign",
    "PageStoryboard",
    "StoryboardResult",
    # 设计器
    "StoryboardDesigner",
    # 提示词
    "PROMPT_NAME",
    "STORYBOARD_DESIGN_PROMPT",
    "STORYBOARD_SYSTEM_PROMPT",
]
