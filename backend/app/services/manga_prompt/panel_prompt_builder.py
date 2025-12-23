"""
画格级提示词构建器

为每个画格生成专属的AI图像生成提示词。
考虑画格在页面中的位置、用途、与其他画格的关系。

核心功能：
1. 根据画格内容生成精确的文生图提示词
2. 保持角色在不同画格间的视觉一致性
3. 根据画格比例优化构图描述
4. 添加漫画特有的视觉效果提示
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .page_templates import (
    PanelContent,
    PanelSlot,
    PagePlan,
    SceneExpansion,
    PanelShape,
    PanelPurpose,
    SceneMood,
    DialogueBubbleType,
    SoundEffectType,
    SoundEffectIntensity,
    SoundEffectInfo,
)

logger = logging.getLogger(__name__)


@dataclass
class PanelPrompt:
    """
    画格提示词结果

    包含生成单个画格图像所需的所有提示词信息
    """
    # 标识
    panel_id: str  # 格式: "scene{scene_id}_page{page}_panel{slot_id}"
    scene_id: int
    page_number: int
    slot_id: int

    # 画格元信息
    aspect_ratio: str  # 生成图片的比例
    composition: str  # 构图方式
    camera_angle: str  # 镜头角度

    # 提示词
    prompt_en: str  # 英文正向提示词
    prompt_zh: str  # 中文描述
    negative_prompt: str  # 负向提示词

    # 文字元素 - 基础字段（后期合成用）
    dialogue: Optional[str] = None
    dialogue_speaker: Optional[str] = None
    narration: Optional[str] = None
    sound_effects: Optional[List[str]] = None

    # 文字元素 - 扩展字段（新增）
    dialogue_bubble_type: str = "normal"  # 气泡类型
    dialogue_position: str = "top-right"  # 气泡位置
    dialogue_emotion: str = ""  # 说话情绪
    narration_position: str = "top"  # 旁白位置
    sound_effect_details: Optional[List[Dict[str, Any]]] = None  # 详细音效信息

    # 视觉信息
    characters: Optional[List[str]] = None
    is_key_panel: bool = False

    # 参考图（用于 img2img）
    reference_image_paths: Optional[List[str]] = None  # 角色立绘路径列表


class PanelPromptBuilder:
    """
    画格提示词构建器

    将画格内容转换为AI图像生成提示词
    """

    # 构图描述映射
    COMPOSITION_MAP = {
        "wide shot": "wide shot, full scene view, establishing shot",
        "medium shot": "medium shot, waist-up view, conversational framing",
        "medium close-up": "medium close-up, chest-up view, intimate framing",
        "close-up": "close-up shot, face focus, emotional emphasis",
        "extreme close-up": "extreme close-up, eye or detail focus, intense emotion",
        "dynamic wide shot": "dynamic wide shot, action framing, motion blur",
        "dynamic composition": "dynamic composition, diagonal lines, movement emphasis",
    }

    # 镜头角度映射
    ANGLE_MAP = {
        "eye level": "eye level shot, neutral perspective",
        "low angle": "low angle shot, looking up, heroic perspective",
        "high angle": "high angle shot, looking down, vulnerable perspective",
        "bird's eye": "bird's eye view, overhead shot, god's perspective",
        "dutch angle": "dutch angle, tilted frame, tension and unease",
        "dynamic": "dynamic angle, action perspective, dramatic viewpoint",
        "dramatic": "dramatic angle, cinematic framing, high contrast",
    }

    # 情感到视觉风格的映射
    MOOD_STYLE_MAP = {
        SceneMood.CALM: "soft lighting, peaceful atmosphere, warm tones",
        SceneMood.TENSION: "high contrast, sharp shadows, cold tones",
        SceneMood.ACTION: "motion lines, dynamic lighting, speed effects",
        SceneMood.EMOTIONAL: "soft focus, dramatic lighting, emotional depth",
        SceneMood.MYSTERY: "low key lighting, shadows, mysterious atmosphere",
        SceneMood.COMEDY: "bright lighting, exaggerated expressions, cheerful",
        SceneMood.DRAMATIC: "chiaroscuro lighting, dramatic shadows, cinematic",
        SceneMood.ROMANTIC: "soft glow, warm colors, dreamy atmosphere",
        SceneMood.HORROR: "dark shadows, unsettling lighting, ominous",
        SceneMood.FLASHBACK: "desaturated, soft edges, nostalgic filter",
    }

    # 基础负向提示词
    BASE_NEGATIVE = (
        "low quality, blurry, distorted face, plastic skin, waxy appearance, "
        "extra limbs, bad anatomy, deformed, ugly, amateur, "
        "empty background, plain white background, "
        "text, watermark, signature, logo"
    )

    # 对话气泡类型到提示词的映射
    BUBBLE_TYPE_MAP = {
        DialogueBubbleType.NORMAL: "speech bubble, dialogue balloon, round border",
        DialogueBubbleType.SHOUT: "jagged speech bubble, explosion bubble, spiky border, excited shout",
        DialogueBubbleType.WHISPER: "dotted speech bubble, soft bubble, dashed border, whisper",
        DialogueBubbleType.THOUGHT: "thought bubble, cloud bubble, thought balloon, fluffy cloud shape",
        DialogueBubbleType.NARRATION: "rectangular text box, caption box, narration box",
        DialogueBubbleType.ELECTRONIC: "wavy speech bubble, digital text bubble, electronic device speech",
    }

    # 音效类型到视觉效果的映射
    SOUND_EFFECT_VISUAL_MAP = {
        SoundEffectType.ACTION: "speed lines, motion lines, action lines",
        SoundEffectType.IMPACT: "impact lines, radial lines, shockwave effect, explosion effect",
        SoundEffectType.AMBIENT: "ambient particles, environmental effect",
        SoundEffectType.EMOTIONAL: "emotion symbols, manga emotion effects",
        SoundEffectType.VOCAL: "vocal expression marks",
    }

    # 音效强度到视觉效果的映射
    SOUND_INTENSITY_MAP = {
        SoundEffectIntensity.SMALL: "subtle effect, small text",
        SoundEffectIntensity.MEDIUM: "moderate effect, medium emphasis",
        SoundEffectIntensity.LARGE: "dramatic effect, large bold text, screen-filling effect",
    }

    # 各语言音效到视觉效果的映射
    SOUND_VISUAL_MAP_BY_LANGUAGE = {
        "chinese": {
            "砰": "explosion effect, impact burst",
            "嗖": "speed lines, motion blur",
            "咚": "impact vibration, ground shake",
            "嘭": "explosion effect, dust cloud",
            "哗": "splash effect, water spray",
            "轰": "massive explosion, shockwave",
            "咚咚": "heartbeat rhythm effect",
            "沙沙": "subtle particle effect",
            "嘶": "sharp sound effect, hiss",
            "呼": "wind effect, breath",
        },
        "japanese": {
            "ドン": "explosion effect, impact burst",
            "シュッ": "speed lines, motion blur",
            "バン": "impact effect, bang",
            "ゴゴゴ": "rumbling effect, menacing aura",
            "ドキドキ": "heartbeat rhythm effect",
            "サラサラ": "flowing effect, gentle movement",
            "ザザ": "rough texture effect, static",
            "ガッ": "sudden grab effect, sharp motion",
            "ヒュー": "wind whistle effect, swoosh",
        },
        "english": {
            "BANG": "explosion effect, impact burst",
            "WHOOSH": "speed lines, motion blur",
            "THUD": "impact vibration, ground shake",
            "SPLASH": "splash effect, water spray",
            "BOOM": "massive explosion, shockwave",
            "CRACK": "breaking effect, sharp impact",
            "RUSTLE": "subtle particle effect, leaves",
            "CRASH": "destruction effect, debris",
            "SLAM": "door impact effect, sudden close",
        },
        "korean": {
            "쾅": "explosion effect, impact burst",
            "슉": "speed lines, motion blur",
            "쿵": "impact vibration, ground shake",
            "콰광": "massive explosion, shockwave",
            "두근두근": "heartbeat rhythm effect",
            "사각사각": "subtle particle effect",
            "펑": "burst effect, pop",
            "찰칵": "click effect, mechanical sound",
        },
    }

    def __init__(
        self,
        style: str = "manga",
        character_profiles: Optional[Dict[str, str]] = None,
        dialogue_language: str = "chinese",
        character_portraits: Optional[Dict[str, str]] = None,
    ):
        """
        初始化构建器

        Args:
            style: 漫画风格 (manga/anime/comic/webtoon)
            character_profiles: 角色外观描述字典
            dialogue_language: 对话/音效语言（chinese/japanese/english/korean）
            character_portraits: 角色立绘路径字典 {角色名: 立绘图片路径}
        """
        self.style = style
        self.character_profiles = character_profiles or {}
        self.dialogue_language = dialogue_language
        self.character_portraits = character_portraits or {}

        # 风格基础提示词
        self.style_prompts = {
            "manga": (
                "manga style, Japanese comic art, clean bold ink lines, "
                "screentone shading, black and white, high contrast, "
                "professional manga panel, detailed linework"
            ),
            "anime": (
                "anime style, clean line art, cel shading, vibrant colors, "
                "expressive eyes, Japanese animation aesthetic, "
                "digital illustration, smooth coloring"
            ),
            "comic": (
                "Western comic book style, bold black outlines, "
                "flat colors, graphic novel art, dynamic composition, "
                "American comic aesthetic, strong shadows"
            ),
            "webtoon": (
                "Korean webtoon style, clean digital lines, "
                "soft cel shading, pastel colors, modern illustration, "
                "vertical scroll format optimized"
            ),
        }

    def build_panel_prompts(
        self,
        expansion: SceneExpansion,
    ) -> List[PanelPrompt]:
        """
        为场景展开结果中的所有画格生成提示词

        Args:
            expansion: 场景展开结果

        Returns:
            画格提示词列表
        """
        prompts = []

        for page in expansion.pages:
            for panel_content in page.panels:
                # 获取对应的槽位信息
                slot = self._get_slot(page.template, panel_content.slot_id)
                if not slot:
                    continue

                prompt = self._build_single_panel_prompt(
                    panel_content=panel_content,
                    slot=slot,
                    scene_id=expansion.scene_id,
                    page_number=page.page_number,
                    mood=expansion.mood,
                )
                prompts.append(prompt)

        return prompts

    def _get_slot(self, template, slot_id: int) -> Optional[PanelSlot]:
        """获取模板中的槽位"""
        for slot in template.panel_slots:
            if slot.slot_id == slot_id:
                return slot
        return None

    def _build_single_panel_prompt(
        self,
        panel_content: PanelContent,
        slot: PanelSlot,
        scene_id: int,
        page_number: int,
        mood: SceneMood,
    ) -> PanelPrompt:
        """
        为单个画格生成提示词

        Args:
            panel_content: 画格内容
            slot: 画格槽位信息
            scene_id: 场景ID
            page_number: 页码
            mood: 场景情感

        Returns:
            画格提示词
        """
        # 构建英文提示词
        prompt_parts = []

        # 1. 风格基础
        prompt_parts.append(self.style_prompts.get(self.style, self.style_prompts["manga"]))

        # 2. 构图和镜头
        composition_desc = self.COMPOSITION_MAP.get(
            panel_content.composition,
            panel_content.composition
        )
        prompt_parts.append(composition_desc)

        angle_desc = self.ANGLE_MAP.get(
            panel_content.camera_angle,
            panel_content.camera_angle
        )
        prompt_parts.append(angle_desc)

        # 3. 情感氛围
        mood_style = self.MOOD_STYLE_MAP.get(mood, "")
        if mood_style:
            prompt_parts.append(mood_style)

        # 4. 角色描述
        character_desc = self._build_character_description(
            panel_content.characters,
            panel_content.character_emotions,
        )
        if character_desc:
            prompt_parts.append(character_desc)

        # 5. 内容描述
        content_desc = self._build_content_description(panel_content)
        if content_desc:
            prompt_parts.append(content_desc)

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
        panel_effects = self._get_panel_effects(slot, mood)
        if panel_effects:
            prompt_parts.append(panel_effects)

        # 9. 对话气泡视觉效果（新增）
        dialogue_visual = self._build_dialogue_visual(panel_content)
        if dialogue_visual:
            prompt_parts.append(dialogue_visual)

        # 10. 音效视觉效果（新增）
        sfx_visual = self._build_sound_effects_visual(panel_content)
        if sfx_visual:
            prompt_parts.append(sfx_visual)

        # 11. 旁白视觉效果（新增）
        narration_visual = self._build_narration_visual(panel_content)
        if narration_visual:
            prompt_parts.append(narration_visual)

        # 12. 画面填充要求
        prompt_parts.append(
            "detailed background, rich environment, "
            "no empty space, fully composed frame"
        )

        # 组合提示词
        prompt_en = ", ".join(filter(None, prompt_parts))

        # 中文描述
        prompt_zh = self._build_chinese_description(panel_content, slot)

        # 负向提示词
        negative_prompt = self._build_negative_prompt(slot)

        # 获取画格中角色的立绘路径
        reference_image_paths = self._get_character_portrait_paths(panel_content.characters)

        return PanelPrompt(
            panel_id=f"scene{scene_id}_page{page_number}_panel{slot.slot_id}",
            scene_id=scene_id,
            page_number=page_number,
            slot_id=slot.slot_id,
            aspect_ratio=slot.aspect_ratio,
            composition=panel_content.composition,
            camera_angle=panel_content.camera_angle,
            prompt_en=prompt_en,
            prompt_zh=prompt_zh,
            negative_prompt=negative_prompt,
            # 文字元素 - 基础字段
            dialogue=panel_content.dialogue,
            dialogue_speaker=panel_content.dialogue_speaker,
            narration=panel_content.narration,
            sound_effects=panel_content.sound_effects or [],
            # 文字元素 - 扩展字段
            dialogue_bubble_type=panel_content.dialogue_bubble_type,
            dialogue_position=panel_content.dialogue_position,
            dialogue_emotion=panel_content.dialogue_emotion,
            narration_position=panel_content.narration_position,
            sound_effect_details=panel_content.sound_effect_details or [],
            # 视觉信息
            characters=panel_content.characters or [],
            is_key_panel=slot.is_key_panel,
            # 参考图
            reference_image_paths=reference_image_paths,
        )

    def _build_character_description(
        self,
        characters: List[str],
        emotions: Dict[str, str],
    ) -> str:
        """构建角色描述"""
        if not characters:
            return ""

        parts = []
        for char in characters:
            char_parts = []

            # 角色外观（从profiles获取）
            if char in self.character_profiles:
                char_parts.append(self.character_profiles[char])
            else:
                char_parts.append(char)

            # 角色情绪
            if char in emotions:
                emotion = emotions[char]
                char_parts.append(f"with {emotion} expression")

            parts.append(" ".join(char_parts))

        if len(parts) == 1:
            return parts[0]
        else:
            return f"characters: {', '.join(parts)}"

    def _get_character_portrait_paths(
        self,
        characters: Optional[List[str]],
    ) -> Optional[List[str]]:
        """
        获取画格中角色的立绘路径

        Args:
            characters: 画格中的角色名列表

        Returns:
            角色立绘路径列表，如果没有则返回 None
        """
        if not characters or not self.character_portraits:
            return None

        paths = []
        for char in characters:
            if char in self.character_portraits:
                paths.append(self.character_portraits[char])

        return paths if paths else None

    def _build_content_description(self, panel_content: PanelContent) -> str:
        """构建内容描述"""
        desc = panel_content.content_description
        if not desc:
            return ""

        # 简单翻译/转换常见中文描述
        # 实际项目中可以使用翻译API
        return desc

    def _build_dialogue_visual(self, panel_content: PanelContent) -> str:
        """
        构建对话气泡的视觉提示词

        根据对话内容、气泡类型和情绪生成相应的视觉描述
        """
        if not panel_content.dialogue:
            return ""

        parts = []

        # 获取气泡类型
        bubble_type = panel_content.get_bubble_type()
        bubble_desc = self.BUBBLE_TYPE_MAP.get(bubble_type, "speech bubble")
        parts.append(bubble_desc)

        # 添加气泡位置
        position = panel_content.dialogue_position
        if position:
            position_map = {
                "top-right": "at top right corner",
                "top-left": "at top left corner",
                "top-center": "at top center",
                "bottom-right": "at bottom right corner",
                "bottom-left": "at bottom left corner",
                "bottom-center": "at bottom center",
                "middle-right": "at middle right",
                "middle-left": "at middle left",
            }
            pos_desc = position_map.get(position, "")
            if pos_desc:
                parts.append(pos_desc)

        # 添加说话者相关的视觉提示
        if panel_content.dialogue_speaker:
            parts.append(f"pointing to {panel_content.dialogue_speaker}")

        # 根据情绪添加额外的视觉效果
        emotion = panel_content.dialogue_emotion.lower() if panel_content.dialogue_emotion else ""
        if emotion:
            emotion_effects = {
                "angry": "anger vein, intense expression",
                "happy": "sparkle effect, bright expression",
                "sad": "tear drop, melancholic expression",
                "surprised": "shock lines, wide eyes",
                "scared": "sweat drops, trembling",
                "excited": "sparkle eyes, energetic pose",
                "shy": "blush lines, embarrassed expression",
                "determined": "focused eyes, firm expression",
            }
            for key, effect in emotion_effects.items():
                if key in emotion:
                    parts.append(effect)
                    break

        return ", ".join(parts) if parts else ""

    def _build_sound_effects_visual(self, panel_content: PanelContent) -> str:
        """
        构建音效的视觉提示词

        将音效转换为漫画视觉效果（速度线、冲击波等）
        """
        sfx_list = panel_content.get_sound_effects_info()
        if not sfx_list:
            return ""

        parts = []

        # 获取当前语言的音效映射
        sfx_visual_map = self.SOUND_VISUAL_MAP_BY_LANGUAGE.get(
            self.dialogue_language,
            self.SOUND_VISUAL_MAP_BY_LANGUAGE["chinese"]
        )

        for sfx in sfx_list:
            # 基于音效类型添加视觉效果
            visual_effect = self.SOUND_EFFECT_VISUAL_MAP.get(
                sfx.effect_type,
                "manga sound effect"
            )
            parts.append(visual_effect)

            # 基于强度调整效果
            intensity_effect = self.SOUND_INTENSITY_MAP.get(
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

    def _build_narration_visual(self, panel_content: PanelContent) -> str:
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
            position_map = {
                "top": "at top of panel",
                "bottom": "at bottom of panel",
                "left": "on left side",
                "right": "on right side",
            }
            pos_desc = position_map.get(position, "")
            if pos_desc:
                parts.append(pos_desc)

        return ", ".join(parts)

    def _get_panel_effects(self, slot: PanelSlot, mood: SceneMood) -> str:
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

    def _build_chinese_description(
        self,
        panel_content: PanelContent,
        slot: PanelSlot,
    ) -> str:
        """构建中文描述"""
        parts = []

        # 构图
        comp_zh = {
            "wide shot": "全景",
            "medium shot": "中景",
            "medium close-up": "中近景",
            "close-up": "特写",
            "extreme close-up": "大特写",
            "dynamic wide shot": "动态全景",
            "dynamic composition": "动态构图",
        }
        parts.append(comp_zh.get(panel_content.composition, panel_content.composition))

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

    def _build_negative_prompt(self, slot: PanelSlot) -> str:
        """构建负向提示词"""
        negative_parts = [self.BASE_NEGATIVE]

        # 根据风格添加
        if self.style == "manga":
            negative_parts.append("color, colored, photorealistic")
        elif self.style in ["anime", "webtoon"]:
            negative_parts.append("photorealistic, 3D render")

        # 无边框画格不要硬边缘
        if slot.shape == PanelShape.BORDERLESS:
            negative_parts.append("hard edges, sharp borders")

        return ", ".join(negative_parts)


def build_prompts_for_expansion(
    expansion: SceneExpansion,
    style: str = "manga",
    character_profiles: Optional[Dict[str, str]] = None,
    character_portraits: Optional[Dict[str, str]] = None,
) -> List[PanelPrompt]:
    """
    便捷函数：为场景展开生成所有画格提示词

    Args:
        expansion: 场景展开结果
        style: 漫画风格
        character_profiles: 角色外观描述
        character_portraits: 角色立绘路径字典 {角色名: 立绘图片路径}

    Returns:
        画格提示词列表
    """
    builder = PanelPromptBuilder(
        style=style,
        character_profiles=character_profiles,
        character_portraits=character_portraits,
    )
    return builder.build_panel_prompts(expansion)


def build_prompts_for_expansions(
    expansions: List[SceneExpansion],
    style: str = "manga",
    character_profiles: Optional[Dict[str, str]] = None,
    character_portraits: Optional[Dict[str, str]] = None,
) -> List[PanelPrompt]:
    """
    便捷函数：为多个场景展开生成所有画格提示词

    Args:
        expansions: 场景展开结果列表
        style: 漫画风格
        character_profiles: 角色外观描述
        character_portraits: 角色立绘路径字典 {角色名: 立绘图片路径}

    Returns:
        所有画格提示词列表
    """
    builder = PanelPromptBuilder(
        style=style,
        character_profiles=character_profiles,
        character_portraits=character_portraits,
    )

    all_prompts = []
    for expansion in expansions:
        prompts = builder.build_panel_prompts(expansion)
        all_prompts.extend(prompts)

    return all_prompts
