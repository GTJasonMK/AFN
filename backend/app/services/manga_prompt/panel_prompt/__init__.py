"""
画格提示词构建器模块

此模块提供画格级提示词生成功能，将画格内容转换为AI图像生成提示词。

主要组件：
- PanelPromptBuilder: 主构建器类
- PanelPrompt: 提示词数据结构
- 映射表: 各种元素到提示词的映射
- 组件构建器: 各种提示词组件的独立构建器
"""

# 主要类和数据结构
from .builder import (
    PanelPromptBuilder,
    PanelPrompt,
    build_prompts_for_expansion,
    build_prompts_for_expansions,
)

# 映射表（供需要直接访问的场景使用）
from .mappings import (
    COMPOSITION_MAP,
    ANGLE_MAP,
    MOOD_STYLE_MAP,
    BASE_NEGATIVE,
    BUBBLE_TYPE_MAP,
    SOUND_EFFECT_VISUAL_MAP,
    SOUND_INTENSITY_MAP,
    SOUND_VISUAL_MAP_BY_LANGUAGE,
    SHOT_TRANSITION_MAP,
    ANGLE_TRANSITION_MAP,
    STYLE_PROMPTS,
)

# 组件构建器（供需要自定义构建流程的场景使用）
from .component_builders import (
    CharacterDescriptionBuilder,
    DialogueVisualBuilder,
    SoundEffectsVisualBuilder,
    NarrationVisualBuilder,
    ContinuityDescriptionBuilder,
    PanelEffectsBuilder,
    NegativePromptBuilder,
    ChineseDescriptionBuilder,
    FallbackPromptBuilder,
)

__all__ = [
    # 主要导出（向后兼容）
    "PanelPromptBuilder",
    "PanelPrompt",
    "build_prompts_for_expansion",
    "build_prompts_for_expansions",
    # 映射表
    "COMPOSITION_MAP",
    "ANGLE_MAP",
    "MOOD_STYLE_MAP",
    "BASE_NEGATIVE",
    "BUBBLE_TYPE_MAP",
    "SOUND_EFFECT_VISUAL_MAP",
    "SOUND_INTENSITY_MAP",
    "SOUND_VISUAL_MAP_BY_LANGUAGE",
    "SHOT_TRANSITION_MAP",
    "ANGLE_TRANSITION_MAP",
    "STYLE_PROMPTS",
    # 组件构建器
    "CharacterDescriptionBuilder",
    "DialogueVisualBuilder",
    "SoundEffectsVisualBuilder",
    "NarrationVisualBuilder",
    "ContinuityDescriptionBuilder",
    "PanelEffectsBuilder",
    "NegativePromptBuilder",
    "ChineseDescriptionBuilder",
    "FallbackPromptBuilder",
]
