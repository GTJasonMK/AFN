"""
分镜设计模块

为每个页面设计分镜：
- 使用横框/竖框/方框布局
- 支持宽度占比和宽高比设置
- 分配对话
- 描述视觉内容
"""

from .models import (
    ShotType,
    PanelShape,
    WidthRatio,
    AspectRatio,
    DialogueBubble,
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
    "PanelShape",
    "WidthRatio",
    "AspectRatio",
    # 数据类
    "DialogueBubble",
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
