"""
画格提示词组件构建器

提供各种提示词组件的构建方法，包括：
- 角色描述构建
- 对话视觉效果构建
- 音效视觉效果构建
- 旁白视觉效果构建
- 连贯性描述构建
- 画格特殊效果构建
"""

import logging
from typing import List, Dict, Optional

from ..page_templates import (
    PanelContent,
    PanelSlot,
    PanelShape,
    PanelPurpose,
    SceneMood,
    DialogueBubbleType,
)

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
    COMPOSITION_ZH_MAP,
    SPEAKING_ACTION_MAP,
    BUBBLE_POSITION_MAP,
    EMOTION_EFFECTS_MAP,
    NARRATION_POSITION_MAP,
)

logger = logging.getLogger(__name__)


class CharacterDescriptionBuilder:
    """角色描述构建器"""

    def __init__(self, character_profiles: Optional[Dict[str, str]] = None):
        """
        初始化角色描述构建器

        Args:
            character_profiles: 角色外观描述字典
        """
        self.character_profiles = character_profiles or {}

    def build(
        self,
        characters: List[str],
        emotions: Dict[str, str],
    ) -> str:
        """
        构建角色描述

        确保所有角色（包括次要角色）都有一致的视觉描述
        """
        if not characters:
            return ""

        parts = []
        for char in characters:
            char_parts = []

            # 角色外观（从profiles获取）
            if char in self.character_profiles:
                char_parts.append(self.character_profiles[char])
            else:
                # 次要角色没有profile时，生成基础描述以保持一致性
                fallback_desc = self._generate_fallback_description(char)
                char_parts.append(fallback_desc)
                logger.debug(f"角色 '{char}' 没有profile，使用回退描述: {fallback_desc}")

            # 角色情绪
            if char in emotions:
                emotion = emotions[char]
                char_parts.append(f"with {emotion} expression")

            parts.append(" ".join(char_parts))

        if len(parts) == 1:
            return parts[0]
        else:
            return f"characters: {', '.join(parts)}"

    def _generate_fallback_description(self, character_name: str) -> str:
        """
        为没有profile的角色生成回退描述

        基于角色名中的关键词推断基本特征，确保次要角色也有一致的视觉描述
        """
        name_lower = character_name.lower()

        # 根据常见角色类型生成描述
        if any(word in name_lower for word in ['士兵', 'soldier', '军', 'guard', '卫']):
            return "armored soldier, military uniform, stern expression"
        elif any(word in name_lower for word in ['侍女', 'maid', '女仆', '丫鬟']):
            return "young woman in servant attire, neat appearance"
        elif any(word in name_lower for word in ['店员', 'clerk', '服务员', 'waiter', 'waitress']):
            return "service staff in uniform, professional appearance"
        elif any(word in name_lower for word in ['老', 'elder', '大爷', '大妈', '奶奶', '爷爷']):
            return "elderly person, aged features, traditional clothing"
        elif any(word in name_lower for word in ['小孩', 'child', '孩子', 'kid', '少年', '少女']):
            return "young person, youthful features, casual clothing"
        elif any(word in name_lower for word in ['商人', 'merchant', '老板', 'boss']):
            return "middle-aged person, business attire, confident posture"
        elif any(word in name_lower for word in ['村民', 'villager', '农民', 'farmer']):
            return "rural person, simple clothing, weathered features"
        elif any(word in name_lower for word in ['贵族', 'noble', '公主', 'princess', '王子', 'prince']):
            return "noble person, elegant clothing, refined features"
        elif any(word in name_lower for word in ['路人', 'passerby', '行人', 'stranger']):
            return "ordinary person, casual clothing, nondescript features"
        else:
            # 默认描述：普通成年人
            return f"person named {character_name}, distinct appearance"


class DialogueVisualBuilder:
    """对话视觉效果构建器"""

    def build(self, panel_content: PanelContent) -> str:
        """
        构建对话气泡的视觉提示词

        根据对话内容、气泡类型和情绪生成相应的视觉描述。
        包括角色说话的动作描述和气泡视觉效果。
        """
        if not panel_content.dialogue:
            return ""

        parts = []

        # 1. 添加说话动作描述（核心：让图片体现角色在说话）
        if panel_content.dialogue_speaker:
            parts.append(f"{panel_content.dialogue_speaker} speaking")
        else:
            parts.append("character speaking")

        # 根据气泡类型添加不同的说话动作
        bubble_type = panel_content.get_bubble_type()
        action = SPEAKING_ACTION_MAP.get(bubble_type, "talking")
        if action:
            parts.append(action)

        # 2. 获取气泡类型视觉描述
        bubble_desc = BUBBLE_TYPE_MAP.get(bubble_type, "speech bubble")
        parts.append(bubble_desc)

        # 3. 添加气泡位置
        position = panel_content.dialogue_position
        if position:
            pos_desc = BUBBLE_POSITION_MAP.get(position, "")
            if pos_desc:
                parts.append(pos_desc)

        # 4. 根据情绪添加额外的视觉效果
        emotion = panel_content.dialogue_emotion.lower() if panel_content.dialogue_emotion else ""
        if emotion:
            for key, effect in EMOTION_EFFECTS_MAP.items():
                if key in emotion:
                    parts.append(effect)
                    break

        return ", ".join(parts) if parts else ""


class SoundEffectsVisualBuilder:
    """音效视觉效果构建器"""

    def __init__(self, dialogue_language: str = "chinese"):
        """
        初始化音效视觉效果构建器

        Args:
            dialogue_language: 对话/音效语言（chinese/japanese/english/korean）
        """
        self.dialogue_language = dialogue_language

    def build(self, panel_content: PanelContent) -> str:
        """
        构建音效的视觉提示词

        将音效转换为漫画视觉效果（速度线、冲击波等）
        """
        sfx_list = panel_content.get_sound_effects_info()
        if not sfx_list:
            return ""

        parts = []

        # 获取当前语言的音效映射
        sfx_visual_map = SOUND_VISUAL_MAP_BY_LANGUAGE.get(
            self.dialogue_language,
            SOUND_VISUAL_MAP_BY_LANGUAGE["chinese"]
        )

        for sfx in sfx_list:
            # 基于音效类型添加视觉效果
            visual_effect = SOUND_EFFECT_VISUAL_MAP.get(
                sfx.effect_type,
                "manga sound effect"
            )
            parts.append(visual_effect)

            # 基于强度调整效果
            intensity_effect = SOUND_INTENSITY_MAP.get(
                sfx.intensity,
                ""
            )
            if intensity_effect:
                parts.append(intensity_effect)

            # 添加音效文字的视觉描述（使用语言特定映射）
            if sfx.text:
                special_visual = sfx_visual_map.get(sfx.text)
                if special_visual:
                    parts.append(special_visual)
                else:
                    parts.append("manga sound effect text")

        # 去重并组合
        unique_parts = list(dict.fromkeys(parts))
        return ", ".join(unique_parts) if unique_parts else ""


class NarrationVisualBuilder:
    """旁白视觉效果构建器"""

    def build(self, panel_content: PanelContent) -> str:
        """
        构建旁白的视觉提示词

        为旁白文字添加视觉框和位置描述
        """
        if not panel_content.narration:
            return ""

        parts = ["rectangular narration box", "caption text"]

        # 添加旁白位置
        position = panel_content.narration_position
        if position:
            pos_desc = NARRATION_POSITION_MAP.get(position, "")
            if pos_desc:
                parts.append(pos_desc)

        return ", ".join(parts)


class ContinuityDescriptionBuilder:
    """连贯性描述构建器"""

    def build(
        self,
        current_panel: PanelContent,
        previous_panel: Optional[PanelContent],
    ) -> str:
        """
        构建镜头连贯性描述

        基于前一画格的构图和角度，生成过渡描述以保持视觉连贯性。
        这有助于AI图像生成时保持相邻画格之间的视觉流畅。

        Args:
            current_panel: 当前画格内容
            previous_panel: 前一个画格内容

        Returns:
            连贯性描述字符串
        """
        if not previous_panel:
            # 第一个画格，无需连贯性描述，但添加场景建立提示
            return "establishing shot, scene introduction"

        parts = []

        # 1. 镜头过渡描述
        prev_comp = previous_panel.composition
        curr_comp = current_panel.composition
        transition_key = (prev_comp, curr_comp)
        if transition_key in SHOT_TRANSITION_MAP:
            parts.append(SHOT_TRANSITION_MAP[transition_key])
        elif prev_comp != curr_comp:
            # 未在映射中的过渡，提供通用描述
            parts.append(f"transitioning from {prev_comp}")

        # 2. 角度过渡描述
        prev_angle = previous_panel.camera_angle
        curr_angle = current_panel.camera_angle
        angle_key = (prev_angle, curr_angle)
        if angle_key in ANGLE_TRANSITION_MAP:
            parts.append(ANGLE_TRANSITION_MAP[angle_key])

        # 3. 角色一致性锚定
        # 如果前后画格有相同角色，强调视觉一致性
        prev_chars = set(previous_panel.characters or [])
        curr_chars = set(current_panel.characters or [])
        shared_chars = prev_chars & curr_chars
        if shared_chars:
            char_names = ", ".join(list(shared_chars)[:2])  # 最多列出2个
            parts.append(f"maintaining visual consistency for {char_names}")

        # 4. 环境连贯性
        # 如果前后画格有相同的关键视觉元素，强调场景连续
        prev_elements = set(previous_panel.key_visual_elements or [])
        curr_elements = set(current_panel.key_visual_elements or [])
        shared_elements = prev_elements & curr_elements
        if shared_elements:
            parts.append("continuous environment, same scene")

        # 5. 氛围连贯性
        # 如果前后氛围相同，强调氛围延续
        if previous_panel.atmosphere and current_panel.atmosphere:
            if previous_panel.atmosphere == current_panel.atmosphere:
                parts.append("maintaining atmosphere from previous panel")

        # 6. 光线连贯性
        if previous_panel.lighting and current_panel.lighting:
            if previous_panel.lighting == current_panel.lighting:
                parts.append("consistent lighting")

        return ", ".join(parts) if parts else ""


class PanelEffectsBuilder:
    """画格特殊效果构建器"""

    def build(self, slot: PanelSlot, mood: SceneMood) -> str:
        """获取画格特殊效果"""
        effects = []

        # 根据画格形状添加效果
        if slot.shape == PanelShape.DIAGONAL_LEFT:
            effects.append("diagonal composition, dynamic tension")
        elif slot.shape == PanelShape.DIAGONAL_RIGHT:
            effects.append("diagonal composition, action flow")
        elif slot.shape == PanelShape.BORDERLESS:
            effects.append("soft edges, dreamlike quality, fading borders")
        elif slot.shape == PanelShape.JAGGED:
            effects.append("explosive impact, shattered frame effect")
        elif slot.shape == PanelShape.ROUNDED:
            effects.append("soft vignette, gentle framing")

        # 关键画格效果
        if slot.is_key_panel:
            effects.append("dramatic emphasis, visual impact, detailed rendering")

        # 突破边框效果
        if slot.can_break_frame:
            effects.append("character breaking frame, dynamic overflow")

        # 根据用途添加效果
        if slot.purpose == PanelPurpose.EMPHASIS:
            effects.append("maximum detail, high impact visual")
        elif slot.purpose == PanelPurpose.EMOTION:
            effects.append("emotional depth, expressive rendering")

        return ", ".join(effects) if effects else ""


class NegativePromptBuilder:
    """负向提示词构建器"""

    def __init__(self, style: str = "manga"):
        """
        初始化负向提示词构建器

        Args:
            style: 漫画风格 (manga/anime/comic/webtoon)
        """
        self.style = style

    def build(self, slot: PanelSlot) -> str:
        """构建负向提示词"""
        negative_parts = [BASE_NEGATIVE]

        # 根据风格添加
        if self.style == "manga":
            negative_parts.append("color, colored, photorealistic")
        elif self.style in ["anime", "webtoon"]:
            negative_parts.append("photorealistic, 3D render")

        # 无边框画格不要硬边缘
        if slot.shape == PanelShape.BORDERLESS:
            negative_parts.append("hard edges, sharp borders")

        return ", ".join(negative_parts)


class ChineseDescriptionBuilder:
    """中文描述构建器"""

    def build(self, panel_content: PanelContent, slot: PanelSlot) -> str:
        """构建中文描述"""
        parts = []

        # 构图
        parts.append(COMPOSITION_ZH_MAP.get(panel_content.composition, panel_content.composition))

        # 内容
        if panel_content.content_description:
            parts.append(panel_content.content_description)

        # 角色
        if panel_content.characters:
            chars = "、".join(panel_content.characters)
            parts.append(f"角色：{chars}")

        # 关键画格标记
        if slot.is_key_panel:
            parts.append("[关键画格]")

        return " | ".join(parts)


class FallbackPromptBuilder:
    """
    回退提示词构建器

    当LLM没有生成prompt_en时作为回退使用。
    正常情况下，LLM应该通过 scene_expansion_service.py 的
    PANEL_DISTRIBUTION_PROMPT 直接生成完整的 prompt_en。
    """

    def __init__(
        self,
        style: str = "manga",
        character_profiles: Optional[Dict[str, str]] = None,
        dialogue_language: str = "chinese",
    ):
        self.style = style
        self.character_builder = CharacterDescriptionBuilder(character_profiles)
        self.dialogue_builder = DialogueVisualBuilder()
        self.sfx_builder = SoundEffectsVisualBuilder(dialogue_language)
        self.narration_builder = NarrationVisualBuilder()
        self.continuity_builder = ContinuityDescriptionBuilder()
        self.effects_builder = PanelEffectsBuilder()

    def build(
        self,
        panel_content: PanelContent,
        slot: PanelSlot,
        mood: SceneMood,
        previous_panel: Optional[PanelContent] = None,
    ) -> str:
        """
        使用硬编码映射表构建提示词（回退方案）

        如果此方法被频繁触发，请检查：
        1. LLM是否正确响应了prompt_en字段要求
        2. scene_expansion_service.py中的提示词指导是否足够清晰
        3. LLM模型是否支持复杂的JSON输出
        """
        prompt_parts = []

        # 1. 风格基础
        prompt_parts.append(STYLE_PROMPTS.get(self.style, STYLE_PROMPTS["manga"]))

        # 2. 构图和镜头
        composition_desc = COMPOSITION_MAP.get(
            panel_content.composition,
            panel_content.composition
        )
        prompt_parts.append(composition_desc)

        angle_desc = ANGLE_MAP.get(
            panel_content.camera_angle,
            panel_content.camera_angle
        )
        prompt_parts.append(angle_desc)

        # 3. 情感氛围
        mood_style = MOOD_STYLE_MAP.get(mood, "")
        if mood_style:
            prompt_parts.append(mood_style)

        # 3.5 镜头过渡连贯性（基于前一画格）
        continuity_desc = self.continuity_builder.build(panel_content, previous_panel)
        if continuity_desc:
            prompt_parts.append(continuity_desc)

        # 4. 角色描述
        character_desc = self.character_builder.build(
            panel_content.characters,
            panel_content.character_emotions,
        )
        if character_desc:
            prompt_parts.append(character_desc)

        # 5. 内容描述
        if panel_content.content_description:
            prompt_parts.append(panel_content.content_description)

        # 6. 关键视觉元素
        if panel_content.key_visual_elements:
            elements = ", ".join(panel_content.key_visual_elements)
            prompt_parts.append(f"featuring {elements}")

        # 7. 光线和氛围
        if panel_content.lighting:
            prompt_parts.append(panel_content.lighting)
        if panel_content.atmosphere:
            prompt_parts.append(panel_content.atmosphere)

        # 8. 画格特殊效果
        panel_effects = self.effects_builder.build(slot, mood)
        if panel_effects:
            prompt_parts.append(panel_effects)

        # 9. 对话气泡视觉效果
        dialogue_visual = self.dialogue_builder.build(panel_content)
        if dialogue_visual:
            prompt_parts.append(dialogue_visual)

        # 10. 音效视觉效果
        sfx_visual = self.sfx_builder.build(panel_content)
        if sfx_visual:
            prompt_parts.append(sfx_visual)

        # 11. 旁白视觉效果
        narration_visual = self.narration_builder.build(panel_content)
        if narration_visual:
            prompt_parts.append(narration_visual)

        # 12. 画面填充要求
        prompt_parts.append(
            "detailed background, rich environment, "
            "no empty space, fully composed frame"
        )

        return ", ".join(filter(None, prompt_parts))
