"""
响应解析Mixin

提供LLM响应解析相关的方法。
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from .schemas import (
    MangaPromptResult,
    MangaScene,
    MangaStyle,
    PanelInfo,
    LayoutInfo,
    DialogueItem,
    SoundEffectItem,
)
from ...utils.json_utils import parse_llm_json_safe, fix_number_format

if TYPE_CHECKING:
    from .layout_schemas import LayoutGenerationResult

logger = logging.getLogger(__name__)

# 构图类型列表，用于多样性调整
COMPOSITION_TYPES = [
    "extreme close-up",  # 极特写
    "close-up",          # 特写
    "medium shot",       # 中景
    "full shot",         # 全身
    "wide shot",         # 远景
    "bird's eye view",   # 鸟瞰
    "low angle shot",    # 仰视
    "dutch angle",       # 倾斜
]

# 构图分组：用于选择不同类型的替换
COMPOSITION_GROUPS = {
    "close": ["extreme close-up", "close-up"],
    "medium": ["medium shot", "full shot"],
    "wide": ["wide shot", "bird's eye view"],
    "angle": ["low angle shot", "dutch angle"],
}


class ResponseParserMixin:
    """LLM响应解析相关方法的Mixin"""

    # 需要被主类提供的属性
    layout_service: Any

    def _get_composition_group(self, composition: str) -> str:
        """获取构图所属的分组"""
        composition_lower = composition.lower()
        for group, compositions in COMPOSITION_GROUPS.items():
            for comp in compositions:
                if comp in composition_lower or composition_lower in comp:
                    return group
        return "medium"  # 默认分组

    def _get_alternative_composition(self, current: str, avoid: List[str]) -> str:
        """
        获取替代构图，避免与指定构图相同

        Args:
            current: 当前构图
            avoid: 需要避免的构图列表

        Returns:
            替代构图
        """
        current_group = self._get_composition_group(current)
        avoid_groups = [self._get_composition_group(c) for c in avoid]

        # 按优先级选择不同分组的构图
        group_priority = ["medium", "wide", "close", "angle"]

        for group in group_priority:
            if group != current_group and group not in avoid_groups:
                return COMPOSITION_GROUPS[group][0]

        # 如果所有分组都被使用，返回同组的另一个构图
        compositions_in_group = COMPOSITION_GROUPS.get(current_group, ["medium shot"])
        for comp in compositions_in_group:
            if comp.lower() not in current.lower():
                return comp

        return "medium shot"

    def _validate_composition_diversity(self, scenes: List[MangaScene]) -> List[MangaScene]:
        """
        验证并调整构图多样性，避免连续3个以上相同构图

        Args:
            scenes: 场景列表

        Returns:
            调整后的场景列表
        """
        if len(scenes) < 3:
            return scenes

        # 检测连续相同构图
        consecutive_count = 1
        adjusted_count = 0

        for i in range(1, len(scenes)):
            current_group = self._get_composition_group(scenes[i].composition)
            prev_group = self._get_composition_group(scenes[i - 1].composition)

            if current_group == prev_group:
                consecutive_count += 1
            else:
                consecutive_count = 1

            # 如果连续3个或以上相同构图，调整当前场景
            if consecutive_count >= 3:
                # 获取前两个场景的构图作为避免列表
                avoid_list = [scenes[i - 1].composition, scenes[i - 2].composition]
                new_composition = self._get_alternative_composition(
                    scenes[i].composition, avoid_list
                )

                logger.info(
                    "构图多样性调整: 场景%d 从 '%s' 改为 '%s' (连续%d个相似构图)",
                    scenes[i].scene_id,
                    scenes[i].composition,
                    new_composition,
                    consecutive_count,
                )

                # 创建新的场景对象（因为Pydantic模型可能是不可变的）
                scenes[i] = MangaScene(
                    scene_id=scenes[i].scene_id,
                    scene_summary=scenes[i].scene_summary,
                    original_text=scenes[i].original_text,
                    characters=scenes[i].characters,
                    dialogues=scenes[i].dialogues,
                    narration=scenes[i].narration,
                    sound_effects=scenes[i].sound_effects,
                    prompt_en=scenes[i].prompt_en,
                    prompt_zh=scenes[i].prompt_zh,
                    negative_prompt=scenes[i].negative_prompt,
                    style_tags=scenes[i].style_tags,
                    composition=new_composition,
                    emotion=scenes[i].emotion,
                    lighting=scenes[i].lighting,
                    panel_info=scenes[i].panel_info,
                )

                adjusted_count += 1
                consecutive_count = 1  # 重置计数

        if adjusted_count > 0:
            logger.info("构图多样性检查完成: 共调整 %d 个场景的构图", adjusted_count)

        return scenes

    def _fix_scene_number_formats(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        修复场景数据中的数字格式问题

        将错误的数字格式（如 50,0000）修正为正确格式（如 50万）

        Args:
            scene_data: 原始场景数据字典

        Returns:
            修复后的场景数据字典
        """
        # 需要检查数字格式的文本字段
        text_fields = [
            "scene_summary",
            "original_text",
            "prompt_zh",
            "narration",
        ]

        for field in text_fields:
            if field in scene_data and isinstance(scene_data[field], str):
                scene_data[field] = fix_number_format(scene_data[field])

        # 处理对话中的数字
        if "dialogues" in scene_data and isinstance(scene_data["dialogues"], list):
            for dialogue in scene_data["dialogues"]:
                if isinstance(dialogue, dict) and "text" in dialogue:
                    dialogue["text"] = fix_number_format(dialogue["text"])

        return scene_data

    def _parse_llm_response_with_layout(
        self,
        response: str,
        chapter_number: int,
        style: MangaStyle,
        layout_result: Optional["LayoutGenerationResult"],
    ) -> MangaPromptResult:
        """
        解析LLM响应并附加排版信息

        Args:
            response: LLM响应文本
            chapter_number: 章节号
            style: 漫画风格
            layout_result: 排版结果

        Returns:
            解析后的结果
        """
        data = parse_llm_json_safe(response)

        if not data:
            # 记录更详细的错误信息用于调试
            logger.error(
                "LLM响应解析失败，原始响应长度: %d", len(response) if response else 0
            )
            logger.error(
                "LLM响应前1000字符: %s", response[:1000] if response else "(空)"
            )
            logger.error(
                "LLM响应后500字符: %s",
                response[-500:] if response and len(response) > 500 else "(短)",
            )
            raise ValueError("LLM响应解析失败，请检查后端日志获取详细信息")

        # 解析角色外观
        character_profiles = data.get("character_profiles", {})

        # 构建场景到格子的映射
        panel_map = {}
        if layout_result and layout_result.success:
            layout = layout_result.layout
            for page in layout.pages:
                for panel in page.panels:
                    panel_map[panel.scene_id] = {
                        "panel_id": panel.panel_id,
                        "page_number": page.page_number,
                        "importance": panel.importance.value,
                        "x": panel.x,
                        "y": panel.y,
                        "width": panel.width,
                        "height": panel.height,
                        "aspect_ratio": self.layout_service.get_panel_aspect_ratio(
                            layout, panel.scene_id
                        )
                        or "1:1",
                        "camera_angle": panel.camera_angle,
                    }

        # 解析场景
        scenes = []
        for scene_data in data.get("scenes", []):
            try:
                # 修复数字格式问题（如 50,0000 -> 50万）
                scene_data = self._fix_scene_number_formats(scene_data)

                scene_id = scene_data.get("scene_id", len(scenes) + 1)

                # 附加排版信息
                panel_info = None
                if scene_id in panel_map:
                    panel_info = PanelInfo(**panel_map[scene_id])

                scene = MangaScene(
                    scene_id=scene_id,
                    scene_summary=scene_data.get("scene_summary", ""),
                    original_text=scene_data.get("original_text", ""),
                    characters=scene_data.get("characters", []),
                    # 对话和文字元素
                    dialogues=self._parse_dialogues(scene_data.get("dialogues", [])),
                    narration=scene_data.get("narration"),
                    sound_effects=self._parse_sound_effects(
                        scene_data.get("sound_effects", [])
                    ),
                    # 核心提示词
                    prompt_en=scene_data.get("prompt_en", ""),
                    prompt_zh=scene_data.get("prompt_zh", ""),
                    negative_prompt=scene_data.get("negative_prompt", ""),
                    style_tags=scene_data.get("style_tags", []),
                    composition=scene_data.get("composition", "medium shot"),
                    emotion=scene_data.get("emotion", ""),
                    lighting=scene_data.get("lighting", ""),
                    panel_info=panel_info,
                )
                scenes.append(scene)
            except Exception as e:
                logger.warning("解析场景失败: %s, 错误: %s", scene_data, e)

        # 验证并调整构图多样性
        scenes = self._validate_composition_diversity(scenes)

        # 构建排版信息摘要
        layout_info = None
        if layout_result and layout_result.success:
            layout = layout_result.layout
            layout_info = LayoutInfo(
                layout_type=layout.layout_type.value,
                page_size=layout.page_size.value,
                reading_direction=layout.reading_direction,
                total_pages=layout.total_pages,
                total_panels=layout.total_panels,
            )

        return MangaPromptResult(
            chapter_number=chapter_number,
            character_profiles=character_profiles,
            scenes=scenes,
            style_guide=data.get("style_guide", ""),
            total_scenes=len(scenes),
            style=style,
            layout_info=layout_info,
        )

    def _parse_llm_response(
        self,
        response: str,
        chapter_number: int,
        style: MangaStyle,
    ) -> MangaPromptResult:
        """
        解析LLM响应（不含排版信息的简化版本）

        Args:
            response: LLM响应文本
            chapter_number: 章节号
            style: 漫画风格

        Returns:
            解析后的结果
        """
        data = parse_llm_json_safe(response)

        if not data:
            logger.error("无法解析LLM响应: %s", response[:500])
            raise ValueError("LLM响应解析失败")

        # 解析角色外观
        character_profiles = data.get("character_profiles", {})

        # 解析场景
        scenes = []
        for scene_data in data.get("scenes", []):
            try:
                # 修复数字格式问题（如 50,0000 -> 50万）
                scene_data = self._fix_scene_number_formats(scene_data)

                scene = MangaScene(
                    scene_id=scene_data.get("scene_id", len(scenes) + 1),
                    scene_summary=scene_data.get("scene_summary", ""),
                    original_text=scene_data.get("original_text", ""),
                    characters=scene_data.get("characters", []),
                    prompt_en=scene_data.get("prompt_en", ""),
                    prompt_zh=scene_data.get("prompt_zh", ""),
                    negative_prompt=scene_data.get("negative_prompt", ""),
                    style_tags=scene_data.get("style_tags", []),
                    composition=scene_data.get("composition", "medium shot"),
                    emotion=scene_data.get("emotion", ""),
                    lighting=scene_data.get("lighting", ""),
                )
                scenes.append(scene)
            except Exception as e:
                logger.warning("解析场景失败: %s, 错误: %s", scene_data, e)

        # 验证并调整构图多样性
        scenes = self._validate_composition_diversity(scenes)

        return MangaPromptResult(
            chapter_number=chapter_number,
            character_profiles=character_profiles,
            scenes=scenes,
            style_guide=data.get("style_guide", ""),
            total_scenes=len(scenes),
            style=style,
        )

    def _parse_dialogues(self, dialogues_data: List[Dict[str, Any]]) -> List[DialogueItem]:
        """
        解析对话数据

        Args:
            dialogues_data: 对话数据列表

        Returns:
            DialogueItem列表
        """
        result = []
        for d in dialogues_data:
            try:
                item = DialogueItem(
                    speaker=d.get("speaker", ""),
                    text=d.get("text", ""),
                    bubble_type=d.get("bubble_type", "normal"),
                    position=d.get("position", "top-right"),
                )
                result.append(item)
            except Exception as e:
                logger.warning("解析对话失败: %s, 错误: %s", d, e)
        return result

    def _parse_sound_effects(
        self, sfx_data: List[Dict[str, Any]]
    ) -> List[SoundEffectItem]:
        """
        解析音效数据

        Args:
            sfx_data: 音效数据列表

        Returns:
            SoundEffectItem列表
        """
        result = []
        for s in sfx_data:
            try:
                item = SoundEffectItem(
                    text=s.get("text", ""),
                    type=s.get("type", "action"),
                    intensity=s.get("intensity", "medium"),
                )
                result.append(item)
            except Exception as e:
                logger.warning("解析音效失败: %s, 错误: %s", s, e)
        return result
