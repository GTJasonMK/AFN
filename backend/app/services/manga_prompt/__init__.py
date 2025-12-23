"""
漫画提示词服务模块

基于专业漫画分镜理念设计的服务。

核心流程：
1. 提取场景 - 从章节内容中识别关键叙事场景
2. 展开场景 - 将每个场景展开为页面+画格（使用专业模板）
3. 生成提示词 - 为每个画格生成专属提示词
4. 页面合成 - 将生成的图片合成为漫画页面

专业漫画分镜特点：
- 页面模板系统：8种专业布局模板适配不同场景
- 画格用途标注：建立镜头、动作、反应、特写等
- 情感几何：通过画格形状传达情绪
- 视觉节奏：正反打、蒙太奇等专业技法
"""

# 主服务
from .core_v2 import (
    MangaPromptServiceV2,
    MangaGenerationResult,
    MangaStyle,
    generate_manga_prompts,
)

# 页面模板系统
from .page_templates import (
    PageTemplate,
    PanelSlot,
    PanelContent,
    PagePlan,
    SceneExpansion,
    SceneMood,
    PanelShape,
    PanelPurpose,
    ALL_TEMPLATES,
    get_template,
    get_templates_for_mood,
    recommend_template,
)

# 场景展开服务
from .scene_expansion_service import (
    SceneExpansionService,
    expand_scene_to_manga,
)

# 画格提示词构建器
from .panel_prompt_builder import (
    PanelPromptBuilder,
    PanelPrompt,
    build_prompts_for_expansion,
    build_prompts_for_expansions,
)

__all__ = [
    # 主服务
    "MangaPromptServiceV2",
    "MangaGenerationResult",
    "MangaStyle",
    "generate_manga_prompts",
    # 页面模板
    "PageTemplate",
    "PanelSlot",
    "PanelContent",
    "PagePlan",
    "SceneExpansion",
    "SceneMood",
    "PanelShape",
    "PanelPurpose",
    "ALL_TEMPLATES",
    "get_template",
    "get_templates_for_mood",
    "recommend_template",
    # 场景展开
    "SceneExpansionService",
    "expand_scene_to_manga",
    # 画格提示词
    "PanelPromptBuilder",
    "PanelPrompt",
    "build_prompts_for_expansion",
    "build_prompts_for_expansions",
]
