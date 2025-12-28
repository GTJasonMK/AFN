"""
断点管理器

管理漫画生成过程中的断点保存、恢复和数据序列化。
"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.manga_prompt_repository import MangaPromptRepository

from ..page_templates import (
    PageTemplate,
    PanelSlot,
    PanelContent,
    PagePlan,
    SceneExpansion,
    SceneMood,
    PanelPurpose,
    PanelShape,
    get_template,
    TEMPLATE_STANDARD_THREE_TIER,
)

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    断点管理器

    管理漫画生成过程中的断点保存、恢复和数据序列化
    """

    def __init__(self, session: AsyncSession, manga_prompt_repo: MangaPromptRepository):
        """
        初始化管理器

        Args:
            session: 数据库会话
            manga_prompt_repo: 漫画提示词仓库
        """
        self.session = session
        self.manga_prompt_repo = manga_prompt_repo

    async def save_checkpoint(
        self,
        chapter_id: int,
        status: str,
        progress: dict,
        checkpoint_data: dict,
        style: str,
        source_version_id: Optional[int],
    ):
        """保存断点并提交事务"""
        await self.manga_prompt_repo.save_checkpoint(
            chapter_id=chapter_id,
            status=status,
            progress=progress,
            checkpoint_data=checkpoint_data,
            style=style,
            source_version_id=source_version_id,
        )
        await self.session.commit()

    async def get_checkpoint(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Optional[Dict[str, Any]]:
        """获取断点数据"""
        return await self.manga_prompt_repo.get_checkpoint(project_id, chapter_number)

    def optimize_scenes_for_checkpoint(
        self,
        scenes_data: List[Dict[str, Any]],
        current_index: int,
    ) -> List[Dict[str, Any]]:
        """
        优化 scenes_data 以减少断点存储大小

        已完成的场景只保留 summary（用于上下文）
        当前和未来的场景保留完整数据
        """
        result = []
        for i, scene in enumerate(scenes_data):
            if i < current_index:
                # 已完成的场景：只保留 summary
                result.append({"summary": scene.get("summary", "")})
            else:
                # 当前和未来的场景：保留完整数据
                result.append(scene)
        return result

    def serialize_expansions_minimal(self, expansions: List[SceneExpansion]) -> List[dict]:
        """
        最小化序列化展开结果（省略不需要的字段）

        省略的字段（SceneExpansion级别）：
        - original_text: 后续步骤不需要
        - scene_summary: 后续步骤不需要
        - importance: 后续步骤不需要

        保留的字段（PanelContent级别）：
        - 所有字段都保留，因为 build_panel_prompts 需要使用
        - 注意：is_key_panel 来自 PanelSlot（模板），不在 PanelContent 中

        对于动态生成的模板（ID以llm_dynamic_开头），额外保存槽位信息以便恢复
        """
        result = []
        for exp in expansions:
            result.append({
                "scene_id": exp.scene_id,
                "mood": exp.mood.value,
                "pages": [
                    self._serialize_page_plan(page)
                    for page in exp.pages
                ]
            })
        return result

    def _serialize_page_plan(self, page: PagePlan) -> dict:
        """序列化单个页面规划"""
        template_id = page.template.id if page.template else "unknown"

        page_data = {
            "page_number": page.page_number,
            "template_id": template_id,
            "panels": [
                {
                    "slot_id": panel.slot_id,
                    "content_description": panel.content_description,
                    "narrative_purpose": panel.narrative_purpose,
                    "characters": panel.characters,
                    "character_emotions": panel.character_emotions,
                    "composition": panel.composition,
                    "camera_angle": panel.camera_angle,
                    # 文字元素 - 基础字段
                    "dialogue": panel.dialogue,
                    "dialogue_speaker": panel.dialogue_speaker,
                    "narration": panel.narration,
                    "sound_effects": panel.sound_effects,
                    # 文字元素 - 扩展字段
                    "dialogue_bubble_type": panel.dialogue_bubble_type,
                    "dialogue_position": panel.dialogue_position,
                    "dialogue_emotion": panel.dialogue_emotion,
                    "narration_position": panel.narration_position,
                    "sound_effect_details": panel.sound_effect_details,
                    # 视觉指导
                    "key_visual_elements": panel.key_visual_elements,
                    "atmosphere": panel.atmosphere,
                    "lighting": panel.lighting,
                    # LLM生成的提示词（必须保留，否则恢复后会触发回退逻辑）
                    "prompt_en": panel.prompt_en,
                    "negative_prompt": panel.negative_prompt,
                }
                for panel in page.panels
            ]
        }

        # 对于动态模板，保存完整的槽位信息以便精确恢复
        if template_id.startswith("llm_dynamic_") and page.template:
            page_data["template_slots"] = [
                {
                    "slot_id": slot.slot_id,
                    "x": slot.x,
                    "y": slot.y,
                    "width": slot.width,
                    "height": slot.height,
                    "shape": slot.shape.value if hasattr(slot.shape, 'value') else str(slot.shape),
                    "purpose": slot.purpose.value if hasattr(slot.purpose, 'value') else str(slot.purpose),
                    "suggested_composition": slot.suggested_composition,
                    "suggested_angle": slot.suggested_angle,
                    "is_key_panel": slot.is_key_panel,
                }
                for slot in page.template.panel_slots
            ]
            # 保存模板名称
            page_data["template_name_zh"] = page.template.name_zh

        return page_data

    def deserialize_expansions(self, data: List[dict]) -> List[SceneExpansion]:
        """
        从存储的字典列表反序列化展开结果

        注意：断点存储使用精简格式，SceneExpansion 级别的部分字段使用默认值
        对于动态生成的模板（ID以llm_dynamic_开头），优先使用保存的槽位信息恢复
        """
        result = []
        for exp_data in data:
            pages = []
            for page_data in exp_data.get("pages", []):
                template_id = page_data.get("template_id", "")
                template = get_template(template_id)

                # 如果找不到模板（可能是动态生成的模板），尝试从保存的数据恢复
                if template is None:
                    template = self._restore_template_from_page_data(page_data, template_id)

                panels = [
                    PanelContent(
                        slot_id=p["slot_id"],
                        content_description=p.get("content_description", ""),
                        narrative_purpose=p.get("narrative_purpose", ""),
                        characters=p.get("characters", []),
                        character_emotions=p.get("character_emotions", {}),
                        composition=p.get("composition", "medium shot"),
                        camera_angle=p.get("camera_angle", "eye level"),
                        # 文字元素 - 基础字段
                        dialogue=p.get("dialogue"),
                        dialogue_speaker=p.get("dialogue_speaker"),
                        narration=p.get("narration"),
                        sound_effects=p.get("sound_effects", []),
                        # 文字元素 - 扩展字段
                        dialogue_bubble_type=p.get("dialogue_bubble_type", "normal"),
                        dialogue_position=p.get("dialogue_position", "top-right"),
                        dialogue_emotion=p.get("dialogue_emotion", ""),
                        narration_position=p.get("narration_position", "top"),
                        sound_effect_details=p.get("sound_effect_details", []),
                        # 视觉指导
                        key_visual_elements=p.get("key_visual_elements", []),
                        atmosphere=p.get("atmosphere", ""),
                        lighting=p.get("lighting", ""),
                        # LLM生成的提示词（从断点恢复时需要）
                        prompt_en=p.get("prompt_en", ""),
                        negative_prompt=p.get("negative_prompt", ""),
                    )
                    for p in page_data.get("panels", [])
                ]
                pages.append(PagePlan(
                    page_number=page_data["page_number"],
                    template=template,
                    panels=panels,
                ))

            result.append(SceneExpansion(
                scene_id=exp_data["scene_id"],
                scene_summary=exp_data.get("scene_summary", ""),  # 精简格式可能没有
                original_text=exp_data.get("original_text", ""),  # 精简格式可能没有
                pages=pages,
                mood=SceneMood(exp_data.get("mood", "calm")),
                importance=exp_data.get("importance", "normal"),  # 精简格式可能没有
            ))
        return result

    def _restore_template_from_page_data(
        self,
        page_data: dict,
        template_id: str,
    ) -> PageTemplate:
        """
        从页面数据恢复模板

        优先使用保存的 template_slots 信息，否则从面板数据推断
        """
        # 优先使用保存的槽位信息（动态模板）
        template_slots = page_data.get("template_slots")
        if template_slots:
            logger.debug(f"使用保存的槽位信息恢复模板 {template_id}")
            panel_slots = []
            for slot_data in template_slots:
                # 解析枚举值
                try:
                    purpose = PanelPurpose(slot_data.get("purpose", "action"))
                except ValueError:
                    purpose = PanelPurpose.ACTION

                try:
                    shape = PanelShape(slot_data.get("shape", "rectangle"))
                except ValueError:
                    shape = PanelShape.RECTANGLE

                slot = PanelSlot(
                    slot_id=slot_data.get("slot_id", 1),
                    x=slot_data.get("x", 0),
                    y=slot_data.get("y", 0),
                    width=slot_data.get("width", 1.0),
                    height=slot_data.get("height", 0.5),
                    shape=shape,
                    purpose=purpose,
                    suggested_composition=slot_data.get("suggested_composition", "medium shot"),
                    suggested_angle=slot_data.get("suggested_angle", "eye level"),
                    is_key_panel=slot_data.get("is_key_panel", False),
                )
                panel_slots.append(slot)

            return PageTemplate(
                id=template_id,
                name="Restored Dynamic Template",
                name_zh=page_data.get("template_name_zh", "恢复的动态模板"),
                description="从断点数据精确恢复的动态模板",
                suitable_moods=[SceneMood.CALM],
                panel_slots=panel_slots,
            )

        # 回退：从面板数据推断槽位
        panels_data = page_data.get("panels", [])
        if panels_data:
            logger.debug(f"模板 {template_id} 不在注册表中，从面板数据推断槽位")
            panel_slots = []
            for idx, p in enumerate(panels_data):
                slot = PanelSlot(
                    slot_id=p.get("slot_id", idx + 1),
                    x=0,
                    y=idx * (1.0 / len(panels_data)),
                    width=1.0,
                    height=1.0 / len(panels_data),
                    purpose=PanelPurpose.ACTION,
                    suggested_composition=p.get("composition", "medium shot"),
                    suggested_angle=p.get("camera_angle", "eye level"),
                )
                panel_slots.append(slot)

            return PageTemplate(
                id=template_id or f"restored_{page_data.get('page_number', 1)}",
                name="Restored Template",
                name_zh="恢复的模板",
                description="从断点数据恢复的临时模板",
                suitable_moods=[SceneMood.CALM],
                panel_slots=panel_slots,
            )

        # 最后回退：使用标准模板
        return TEMPLATE_STANDARD_THREE_TIER


__all__ = [
    "CheckpointManager",
]
