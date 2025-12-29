"""
漫画提示词服务模块

基于页面驱动的漫画分镜生成服务。

核心流程：
1. 信息提取 - 从章节内容提取结构化信息（角色、对话、事件、场景）
2. 页面规划 - 全局页面规划，确定页数和事件分配
3. 分镜设计 - 为每页设计详细分镜
4. 提示词构建 - 生成AI绘图提示词

模块结构：
- extraction/ - 章节信息提取
- planning/ - 页面规划
- storyboard/ - 分镜设计
- prompt_builder/ - 提示词构建
- core/ - 主服务
"""

# 主服务
from .core import (
    MangaPromptServiceV2,
    MangaStyle,
    generate_manga_prompts,
)

# 信息提取
from .extraction import (
    ChapterInfoExtractor,
    ChapterInfo,
    CharacterInfo,
    DialogueInfo,
    EventInfo,
    SceneInfo,
    ItemInfo,
)

# 页面规划
from .planning import (
    PagePlanner,
    PagePlanResult,
    PagePlanItem,
    PacingType,
    PageRole,
)

# 分镜设计
from .storyboard import (
    StoryboardDesigner,
    StoryboardResult,
    PageStoryboard,
    PanelDesign,
    DialogueBubble,
    SoundEffect,
    ShotType,
    PanelSize,
    PanelShape,
)

# 提示词构建
from .prompt_builder import (
    PromptBuilder,
    MangaPromptResult,
    PagePromptResult,
    PanelPrompt,
)


__all__ = [
    # 主服务
    "MangaPromptServiceV2",
    "MangaStyle",
    "generate_manga_prompts",
    # 信息提取
    "ChapterInfoExtractor",
    "ChapterInfo",
    "CharacterInfo",
    "DialogueInfo",
    "EventInfo",
    "SceneInfo",
    "ItemInfo",
    # 页面规划
    "PagePlanner",
    "PagePlanResult",
    "PagePlanItem",
    "PacingType",
    "PageRole",
    # 分镜设计
    "StoryboardDesigner",
    "StoryboardResult",
    "PageStoryboard",
    "PanelDesign",
    "DialogueBubble",
    "SoundEffect",
    "ShotType",
    "PanelSize",
    "PanelShape",
    # 提示词构建
    "PromptBuilder",
    "MangaPromptResult",
    "PagePromptResult",
    "PanelPrompt",
]
