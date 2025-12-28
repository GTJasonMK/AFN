"""
画格提示词构建器

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

from ..page_templates import (
    PanelContent,
    PanelSlot,
    SceneExpansion,
    SceneMood,
)

from .component_builders import (
    CharacterDescriptionBuilder,
    NegativePromptBuilder,
    ChineseDescriptionBuilder,
    FallbackPromptBuilder,
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

    # 文字元素 - 扩展字段
    dialogue_bubble_type: str = "normal"  # 气泡类型
    dialogue_position: str = "top-right"  # 气泡位置
    dialogue_emotion: str = ""  # 说话情绪
    narration_position: str = "top"  # 旁白位置
    sound_effect_details: Optional[List[Dict[str, Any]]] = None  # 详细音效信息

    # 视觉信息
    characters: Optional[List[str]] = None
    is_key_panel: bool = False

    # 视觉氛围信息
    lighting: str = ""  # 光线描述
    atmosphere: str = ""  # 氛围描述
    key_visual_elements: Optional[List[str]] = None  # 关键视觉元素

    # 参考图（用于 img2img）
    reference_image_paths: Optional[List[str]] = None  # 角色立绘路径列表


class PanelPromptBuilder:
    """
    画格提示词构建器

    将画格内容转换为AI图像生成提示词
    """

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

        # 日志计数器（避免重复警告刷屏）
        self._missing_prompt_count = 0
        self._missing_negative_count = 0

        # 初始化子构建器
        self._negative_builder = NegativePromptBuilder(style)
        self._chinese_builder = ChineseDescriptionBuilder()
        self._fallback_builder = FallbackPromptBuilder(
            style=style,
            character_profiles=character_profiles,
            dialogue_language=dialogue_language,
        )

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
        previous_panel: Optional[PanelContent] = None  # 追踪前一个画格

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
                    previous_panel=previous_panel,  # 传递前一个画格用于连贯性
                )
                prompts.append(prompt)

                # 更新前一个画格引用
                previous_panel = panel_content

        return prompts

    def _get_slot(self, template, slot_id: int) -> Optional[PanelSlot]:
        """获取模板中的槽位"""
        if template is None:
            return None
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
        previous_panel: Optional[PanelContent] = None,
    ) -> PanelPrompt:
        """
        为单个画格生成提示词

        Args:
            panel_content: 画格内容
            slot: 画格槽位信息
            scene_id: 场景ID
            page_number: 页码
            mood: 场景情感
            previous_panel: 前一个画格内容，用于生成连贯性描述

        Returns:
            画格提示词
        """
        # 优先使用LLM直接生成的提示词
        if panel_content.prompt_en:
            prompt_en = panel_content.prompt_en
            logger.debug(f"使用LLM生成的提示词: {prompt_en[:100]}...")
        else:
            # 回退：使用硬编码映射表构建提示词
            # 这种情况应该很少发生，如果频繁触发，说明LLM提示词需要优化
            self._missing_prompt_count += 1
            if self._missing_prompt_count <= 3:
                logger.warning(
                    f"画格 slot_id={slot.slot_id} 没有LLM生成的prompt_en，使用回退映射表。"
                    f"建议检查 scene_expansion_service.py 中的 PANEL_DISTRIBUTION_PROMPT 配置。"
                )
            elif self._missing_prompt_count == 4:
                logger.warning(f"已有 {self._missing_prompt_count} 个画格缺少prompt_en，后续类似警告将被抑制")
            prompt_en = self._fallback_builder.build(panel_content, slot, mood, previous_panel)

        # 优先使用LLM直接生成的负面提示词
        if panel_content.negative_prompt:
            negative_prompt = panel_content.negative_prompt
        else:
            self._missing_negative_count += 1
            if self._missing_negative_count <= 1:
                logger.debug(f"画格 slot_id={slot.slot_id} 没有LLM生成的negative_prompt，使用默认值")
            negative_prompt = self._negative_builder.build(slot)

        # 中文描述
        prompt_zh = self._chinese_builder.build(panel_content, slot)

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


# ============================================================================
# 便捷函数
# ============================================================================

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
