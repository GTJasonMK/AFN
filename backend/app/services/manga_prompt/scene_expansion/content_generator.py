"""
画格内容生成器

负责将场景内容分配到各个画格中。
支持LLM智能分配和基于规则的回退分配。
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

from ..page_templates import (
    PageTemplate,
    PanelContent,
    PagePlan,
    PanelPurpose,
)
from ..language_config import (
    get_language_hint,
    get_sfx_examples,
    get_forbidden_patterns,
    get_forbidden_hint,
)
from app.utils.json_utils import parse_llm_json_safe

from .prompts import PANEL_DISTRIBUTION_PROMPT

logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    画格内容生成器

    将场景内容分配到画格中
    """

    def __init__(self, llm_service=None, prompt_service=None):
        """
        初始化生成器

        Args:
            llm_service: LLM服务实例
            prompt_service: 提示词服务实例
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self._cached_layout_prompt = None

    async def _get_layout_system_prompt(self) -> str:
        """获取布局系统提示词"""
        if self._cached_layout_prompt:
            return self._cached_layout_prompt

        if self.prompt_service:
            try:
                prompt = await self.prompt_service.get_prompt("manga_layout")
                if prompt:
                    self._cached_layout_prompt = prompt
                    return prompt
            except Exception as e:
                logger.warning(f"无法加载 manga_layout 提示词: {e}")

        return "你是专业的漫画分镜师，擅长分析叙事场景并转化为视觉表现。"

    async def distribute_content(
        self,
        scene_content: str,
        scene_summary: str,
        analysis: Dict[str, Any],
        template: PageTemplate,
        characters: List[str],
        user_id: Optional[int],
        dialogue_language: str = "chinese",
    ) -> PagePlan:
        """
        将场景内容分配到画格中

        Args:
            scene_content: 场景内容
            scene_summary: 场景摘要
            analysis: 场景分析结果
            template: 页面模板
            characters: 角色列表
            user_id: 用户ID
            dialogue_language: 对话语言

        Returns:
            PagePlan对象
        """
        if self.llm_service:
            # 使用LLM分配
            panel_slots_desc = self._format_panel_slots(template)
            key_moments = analysis.get("key_moments", [])

            # 获取语言相关信息
            language_hint = get_language_hint(dialogue_language)
            sfx_examples = get_sfx_examples(dialogue_language)
            forbidden_languages = get_forbidden_hint(dialogue_language)

            prompt = PANEL_DISTRIBUTION_PROMPT.format(
                scene_content=scene_content[:2000],
                mood=analysis.get("mood", "calm"),
                key_moments=str(key_moments) if key_moments else "（自动识别）",
                characters=", ".join(characters) if characters else "（自动识别）",
                template_name=template.name_zh,
                template_description=template.description,
                panel_slots_description=panel_slots_desc,
                language_hint=language_hint,
                sfx_examples=sfx_examples,
                forbidden_languages=forbidden_languages,
            )

            try:
                from app.services.llm_wrappers import call_llm, LLMProfile

                # 使用可配置的布局提示词，并添加语言约束
                base_prompt = await self._get_layout_system_prompt()
                system_prompt = f"{base_prompt}\n\n重要：所有对话、旁白、音效必须使用{language_hint}，禁止使用其他语言。"

                response = await call_llm(
                    self.llm_service,
                    LLMProfile.MANGA,
                    system_prompt=system_prompt,
                    user_content=prompt,
                    user_id=user_id,
                )

                result = parse_llm_json_safe(response)
                if result and "panels" in result:
                    panels = self._parse_panel_contents(
                        result["panels"], template, dialogue_language
                    )
                    return PagePlan(
                        page_number=1,
                        template=template,
                        panels=panels,
                        page_purpose=result.get("page_purpose", scene_summary),
                    )

            except Exception as e:
                logger.warning(f"LLM内容分配失败: {e}，使用规则分配")

        # 回退到规则分配
        return self._distribute_by_rules(
            scene_content, scene_summary, analysis, template, characters
        )

    def _format_panel_slots(self, template: PageTemplate) -> str:
        """格式化画格槽位描述"""
        lines = []
        for slot in template.panel_slots:
            size_desc = "大格" if slot.is_key_panel else "标准格"
            lines.append(
                f"- 槽位{slot.slot_id}: {size_desc}, "
                f"用途={slot.purpose.value}, "
                f"建议构图={slot.suggested_composition}, "
                f"建议角度={slot.suggested_angle}"
            )
        return "\n".join(lines)

    def _validate_language(self, text: str, dialogue_language: str) -> Tuple[bool, str]:
        """
        验证文本是否符合目标语言

        Args:
            text: 要验证的文本
            dialogue_language: 目标语言

        Returns:
            (是否有问题, 问题描述)
        """
        if not text:
            return False, ""

        patterns = get_forbidden_patterns(dialogue_language)
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True, f"检测到非目标语言内容: {text}"

        return False, ""

    def _clean_sound_effects(
        self,
        sound_effects: List[str],
        dialogue_language: str,
    ) -> List[str]:
        """
        清理音效列表，移除非目标语言的音效

        Args:
            sound_effects: 原始音效列表
            dialogue_language: 目标语言

        Returns:
            清理后的音效列表
        """
        if not sound_effects:
            return []

        patterns = get_forbidden_patterns(dialogue_language)
        cleaned = []

        for sfx in sound_effects:
            is_invalid = False
            for pattern in patterns:
                if re.search(pattern, sfx, re.IGNORECASE):
                    is_invalid = True
                    logger.warning(f"移除非目标语言音效: {sfx} (目标语言: {dialogue_language})")
                    break
            if not is_invalid:
                cleaned.append(sfx)

        return cleaned

    def _parse_panel_contents(
        self,
        panels_data: List[Dict[str, Any]],
        template: PageTemplate,
        dialogue_language: str = "chinese",
    ) -> List[PanelContent]:
        """解析LLM返回的画格内容，并验证/清理语言"""
        panels = []
        template_slot_ids = {s.slot_id for s in template.panel_slots}

        for panel_data in panels_data:
            slot_id = panel_data.get("slot_id")
            if slot_id not in template_slot_ids:
                continue

            # 获取原始音效列表并清理非目标语言的音效
            raw_sound_effects = panel_data.get("sound_effects", [])
            cleaned_sound_effects = self._clean_sound_effects(
                raw_sound_effects, dialogue_language
            )

            # 清理 sound_effect_details 中的非目标语言音效
            raw_sfx_details = panel_data.get("sound_effect_details", [])
            cleaned_sfx_details = []
            for detail in raw_sfx_details:
                if isinstance(detail, dict):
                    sfx_text = detail.get("text", "")
                    is_invalid, _ = self._validate_language(sfx_text, dialogue_language)
                    if not is_invalid:
                        cleaned_sfx_details.append(detail)
                    else:
                        logger.warning(f"移除非目标语言音效详情: {sfx_text} (目标语言: {dialogue_language})")

            # 验证对话和旁白语言（只记录警告，不移除）
            dialogue = panel_data.get("dialogue")
            if dialogue:
                is_invalid, msg = self._validate_language(dialogue, dialogue_language)
                if is_invalid:
                    logger.warning(f"对话可能包含非目标语言: {msg}")

            narration = panel_data.get("narration")
            if narration:
                is_invalid, msg = self._validate_language(narration, dialogue_language)
                if is_invalid:
                    logger.warning(f"旁白可能包含非目标语言: {msg}")

            panel = PanelContent(
                slot_id=slot_id,
                content_description=panel_data.get("content_description", ""),
                narrative_purpose=panel_data.get("narrative_purpose", ""),
                characters=panel_data.get("characters", []),
                character_emotions=panel_data.get("character_emotions", {}),
                composition=panel_data.get("composition", "medium shot"),
                camera_angle=panel_data.get("camera_angle", "eye level"),
                # 文字元素 - 基础字段（使用清理后的音效）
                dialogue=dialogue,
                dialogue_speaker=panel_data.get("dialogue_speaker"),
                narration=narration,
                sound_effects=cleaned_sound_effects,
                # 文字元素 - 扩展字段（使用清理后的详情）
                dialogue_bubble_type=panel_data.get("dialogue_bubble_type", "normal"),
                dialogue_position=panel_data.get("dialogue_position", "top-right"),
                dialogue_emotion=panel_data.get("dialogue_emotion", ""),
                narration_position=panel_data.get("narration_position", "top"),
                sound_effect_details=cleaned_sfx_details,
                # 视觉指导
                key_visual_elements=panel_data.get("key_visual_elements", []),
                atmosphere=panel_data.get("atmosphere", ""),
                lighting=panel_data.get("lighting", ""),
                # LLM生成的提示词（优先使用）
                prompt_en=panel_data.get("prompt_en", ""),
                negative_prompt=panel_data.get("negative_prompt", ""),
            )
            panels.append(panel)

        # 确保所有槽位都有内容
        existing_ids = {p.slot_id for p in panels}
        for slot in template.panel_slots:
            if slot.slot_id not in existing_ids:
                panels.append(
                    PanelContent(
                        slot_id=slot.slot_id,
                        content_description="场景延续",
                        narrative_purpose=slot.purpose.value,
                        composition=slot.suggested_composition,
                        camera_angle=slot.suggested_angle,
                    )
                )

        # 按slot_id排序
        panels.sort(key=lambda p: p.slot_id)
        return panels

    def _distribute_by_rules(
        self,
        scene_content: str,
        scene_summary: str,
        analysis: Dict[str, Any],
        template: PageTemplate,
        characters: List[str],
    ) -> PagePlan:
        """
        基于规则的内容分配（LLM不可用时的回退）
        """
        panels = []

        for slot in template.panel_slots:
            # 根据画格用途生成内容
            content_desc, narrative_purpose = self._generate_panel_content_by_purpose(
                slot.purpose,
                scene_summary,
                characters,
            )

            panel = PanelContent(
                slot_id=slot.slot_id,
                content_description=content_desc,
                narrative_purpose=narrative_purpose,
                characters=characters[:2] if characters else [],
                composition=slot.suggested_composition,
                camera_angle=slot.suggested_angle,
                atmosphere=analysis.get("atmosphere", ""),
            )
            panels.append(panel)

        return PagePlan(
            page_number=1,
            template=template,
            panels=panels,
            page_purpose=scene_summary,
        )

    def _generate_panel_content_by_purpose(
        self,
        purpose: PanelPurpose,
        scene_summary: str,
        characters: List[str],
    ) -> Tuple[str, str]:
        """根据画格用途生成内容描述"""
        char_str = characters[0] if characters else "角色"

        content_map = {
            PanelPurpose.ESTABLISHING: (
                f"场景全景：{scene_summary[:20]}的环境",
                "建立场景环境和氛围"
            ),
            PanelPurpose.ACTION: (
                f"{char_str}的动作",
                "展示关键动作"
            ),
            PanelPurpose.REACTION: (
                f"{char_str}的反应表情",
                "展示角色对事件的反应"
            ),
            PanelPurpose.CLOSEUP: (
                f"{char_str}的面部特写",
                "聚焦角色情感"
            ),
            PanelPurpose.DETAIL: (
                "关键细节特写",
                "突出重要道具或细节"
            ),
            PanelPurpose.EMOTION: (
                f"{char_str}的情感表达",
                "深入展示角色内心"
            ),
            PanelPurpose.TRANSITION: (
                "过渡画面",
                "连接前后场景"
            ),
            PanelPurpose.EMPHASIS: (
                scene_summary[:30],
                "场景高潮或关键时刻"
            ),
        }

        return content_map.get(
            purpose,
            (scene_summary[:30], "叙事推进")
        )


__all__ = [
    "ContentGenerator",
]
