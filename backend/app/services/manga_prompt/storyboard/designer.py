"""
分镜设计器

为每个页面设计详细的分镜。
"""

import json
import logging
from typing import Optional, TYPE_CHECKING

from app.services.llm_wrappers import call_llm, LLMProfile
from app.utils.json_utils import parse_llm_json_safe

from ..extraction import ChapterInfo
from ..planning import PagePlanItem
from .models import (
    PageStoryboard,
    PanelDesign,
    StoryboardResult,
    DialogueBubble,
    SoundEffect,
)
from .prompts import PROMPT_NAME, STORYBOARD_DESIGN_PROMPT, STORYBOARD_SYSTEM_PROMPT

if TYPE_CHECKING:
    from app.services.prompt_service import PromptService
    from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class StoryboardDesigner:
    """
    分镜设计器

    为每个页面设计详细的分镜：
    - 确定每格的镜头类型和大小
    - 分配对话和音效
    - 描述视觉内容
    - 生成英文描述用于AI绘图
    """

    def __init__(
        self,
        llm_service: "LLMService",
        prompt_service: Optional["PromptService"] = None,
    ):
        """
        初始化设计器

        Args:
            llm_service: LLM服务实例
            prompt_service: 提示词服务实例（可选）
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def design_page(
        self,
        page_plan: PagePlanItem,
        chapter_info: ChapterInfo,
        total_pages: int,
        previous_panel: Optional[PanelDesign] = None,
        user_id: Optional[int] = None,
    ) -> PageStoryboard:
        """
        设计单页分镜

        Args:
            page_plan: 页面规划
            chapter_info: 章节信息
            total_pages: 总页数
            previous_panel: 上一页最后一格（用于保持连贯性）
            user_id: 用户ID

        Returns:
            PageStoryboard: 页面分镜设计
        """
        # 构建提示词
        prompt = await self._build_prompt(
            page_plan, chapter_info, total_pages, previous_panel
        )

        # 获取系统提示词
        system_prompt = await self._get_system_prompt()

        # 调用LLM
        logger.info(
            "开始设计第 %d 页分镜: %d 个事件, 建议 %d 格",
            page_plan.page_number,
            len(page_plan.event_indices),
            page_plan.suggested_panel_count,
        )

        response = await call_llm(
            self.llm_service,
            LLMProfile.CREATIVE,  # 使用创意型配置
            system_prompt=system_prompt,
            user_content=prompt,
            user_id=user_id,
        )

        # 解析响应
        data = parse_llm_json_safe(response)

        if not data:
            logger.warning("分镜设计失败，使用回退设计: 第 %d 页", page_plan.page_number)
            return self._fallback_design(page_plan, chapter_info)

        try:
            result = self._parse_storyboard(data, page_plan.page_number)
            logger.info(
                "分镜设计完成: 第 %d 页, %d 格",
                result.page_number,
                result.get_panel_count(),
            )
            return result
        except Exception as e:
            logger.error("解析分镜设计失败: %s", e)
            return self._fallback_design(page_plan, chapter_info)

    async def design_all_pages(
        self,
        page_plans: list[PagePlanItem],
        chapter_info: ChapterInfo,
        user_id: Optional[int] = None,
    ) -> StoryboardResult:
        """
        设计所有页面的分镜

        Args:
            page_plans: 页面规划列表
            chapter_info: 章节信息
            user_id: 用户ID

        Returns:
            StoryboardResult: 完整分镜结果
        """
        total_pages = len(page_plans)
        pages = []
        previous_panel = None

        for page_plan in page_plans:
            page_storyboard = await self.design_page(
                page_plan=page_plan,
                chapter_info=chapter_info,
                total_pages=total_pages,
                previous_panel=previous_panel,
                user_id=user_id,
            )
            pages.append(page_storyboard)

            # 更新上一格引用
            if page_storyboard.panels:
                previous_panel = page_storyboard.panels[-1]

        total_panels = sum(p.get_panel_count() for p in pages)

        return StoryboardResult(
            pages=pages,
            total_pages=total_pages,
            total_panels=total_panels,
            style_notes="",
        )

    async def _build_prompt(
        self,
        page_plan: PagePlanItem,
        chapter_info: ChapterInfo,
        total_pages: int,
        previous_panel: Optional[PanelDesign],
    ) -> str:
        """构建分镜设计提示词"""
        # 尝试从PromptService加载
        prompt_template = None
        if self.prompt_service:
            try:
                prompt_template = await self.prompt_service.get_prompt(PROMPT_NAME)
            except Exception as e:
                logger.warning("无法加载 %s 提示词: %s", PROMPT_NAME, e)

        if not prompt_template:
            prompt_template = STORYBOARD_DESIGN_PROMPT

        # 收集页面相关的事件
        events_data = []
        for idx in page_plan.event_indices:
            event = chapter_info.get_event_by_index(idx)
            if event:
                events_data.append({
                    "index": event.index,
                    "type": event.type.value,
                    "description": event.description,
                    "description_en": event.description_en,
                    "participants": event.participants,
                    "importance": event.importance.value,
                    "is_climax": event.is_climax,
                    "emotional_tone": event.emotional_tone,
                })

        # 收集页面相关的对话
        dialogues_data = []
        for idx in page_plan.event_indices:
            for dialogue in chapter_info.get_dialogue_by_event(idx):
                dialogues_data.append({
                    "speaker": dialogue.speaker,
                    "content": dialogue.content,
                    "emotion": dialogue.emotion.value,
                    "importance": dialogue.importance.value,
                })

        # 收集页面出场角色信息
        characters_data = {}
        for char_name in page_plan.key_characters:
            char_info = chapter_info.characters.get(char_name)
            if char_info:
                characters_data[char_name] = {
                    "role": char_info.role.value,
                    "appearance": char_info.appearance,
                    "appearance_en": char_info.appearance_en,
                    "current_emotion": char_info.current_emotion,
                }

        # 上一格信息
        prev_panel_str = "无（本章第一页）"
        if previous_panel:
            prev_panel_str = f"镜头: {previous_panel.shot_type.value}, 内容: {previous_panel.visual_description[:50]}"

        # 计算分镜数量范围
        suggested = page_plan.suggested_panel_count
        min_panels = max(2, suggested - 1)
        max_panels = min(7, suggested + 2)

        return prompt_template.format(
            page_number=page_plan.page_number,
            total_pages=total_pages,
            page_role=page_plan.role.value,
            pacing=page_plan.pacing.value,
            events_json=json.dumps(events_data, ensure_ascii=False, indent=2),
            dialogues_json=json.dumps(dialogues_data, ensure_ascii=False, indent=2),
            characters_json=json.dumps(characters_data, ensure_ascii=False, indent=2),
            suggested_panel_count=suggested,
            previous_panel=prev_panel_str,
            min_panels=min_panels,
            max_panels=max_panels,
        )

    async def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return STORYBOARD_SYSTEM_PROMPT

    def _parse_storyboard(self, data: dict, page_number: int) -> PageStoryboard:
        """解析LLM返回的分镜设计"""
        panels = []
        for p in data.get("panels", []):
            # 解析对话
            dialogues = [
                DialogueBubble.from_dict(d) for d in p.get("dialogues", [])
            ]

            # 解析音效
            sound_effects = [
                SoundEffect.from_dict(s) for s in p.get("sound_effects", [])
            ]

            panel = PanelDesign.from_dict(p)
            panel.dialogues = dialogues
            panel.sound_effects = sound_effects
            panels.append(panel)

        return PageStoryboard(
            page_number=page_number,
            panels=panels,
            page_purpose=data.get("page_purpose", ""),
            reading_flow=data.get("reading_flow", "right_to_left"),
            visual_rhythm=data.get("visual_rhythm", ""),
            layout_description=data.get("layout_description", ""),
        )

    def _fallback_design(
        self,
        page_plan: PagePlanItem,
        chapter_info: ChapterInfo,
    ) -> PageStoryboard:
        """回退设计（LLM失败时使用）"""
        panels = []
        panel_count = page_plan.suggested_panel_count

        # 收集页面的对话
        all_dialogues = []
        for idx in page_plan.event_indices:
            all_dialogues.extend(chapter_info.get_dialogue_by_event(idx))

        # 收集页面的事件
        events = [
            chapter_info.get_event_by_index(idx)
            for idx in page_plan.event_indices
        ]
        events = [e for e in events if e is not None]

        # 分配对话到各格
        dialogues_per_panel = max(1, len(all_dialogues) // panel_count) if all_dialogues else 0

        for i in range(panel_count):
            # 确定镜头类型（交替使用）
            shot_types = ["medium", "close_up", "long", "over_shoulder"]
            shot_type = shot_types[i % len(shot_types)]

            # 确定大小
            if i == 0 and page_plan.role.value == "opening":
                size = "large"
            elif page_plan.role.value == "climax" and i == panel_count // 2:
                size = "large"
            else:
                size = "medium"

            # 分配对话
            panel_dialogues = []
            if dialogues_per_panel > 0:
                start_idx = i * dialogues_per_panel
                end_idx = start_idx + dialogues_per_panel
                for d in all_dialogues[start_idx:end_idx]:
                    panel_dialogues.append(DialogueBubble(
                        speaker=d.speaker,
                        content=d.content,
                        bubble_type="normal",
                        position="top_right",
                        emotion=d.emotion.value,
                    ))

            # 生成描述
            event_desc = events[min(i, len(events) - 1)].description if events else page_plan.content_summary
            event_desc_en = events[min(i, len(events) - 1)].description_en if events else ""

            panel = PanelDesign(
                panel_id=i + 1,
                visual_description=event_desc[:100],
                visual_description_en=event_desc_en[:200] if event_desc_en else f"Scene from page {page_plan.page_number}",
                characters=page_plan.key_characters[:3],
                dialogues=panel_dialogues,
                event_indices=page_plan.event_indices[:1] if page_plan.event_indices else [],
            )
            # 设置枚举值
            from .models import PanelSize, ShotType
            panel.size = PanelSize.from_string(size)
            panel.shot_type = ShotType.from_string(shot_type)

            panels.append(panel)

        return PageStoryboard(
            page_number=page_plan.page_number,
            panels=panels,
            page_purpose=page_plan.content_summary,
            reading_flow="right_to_left",
            visual_rhythm="回退设计：均匀节奏",
            layout_description="回退设计：标准网格布局",
        )


__all__ = [
    "StoryboardDesigner",
]
