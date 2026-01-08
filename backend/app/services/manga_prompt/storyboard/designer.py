"""
分镜设计器

为每个页面设计详细的分镜。
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from app.exceptions import JSONParseError
from app.services.llm_wrappers import call_llm_json, LLMProfile
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

        Raises:
            JSONParseError: 当LLM返回的JSON无法解析时
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

        response = await call_llm_json(
            self.llm_service,
            LLMProfile.MANGA,  # 使用漫画配置（8192 tokens，避免输出截断）
            system_prompt=system_prompt,
            user_content=prompt,
            user_id=user_id,
        )

        # 解析响应
        data = parse_llm_json_safe(response)

        if not data:
            error_preview = response[:200] if response else "(empty)"
            logger.error(
                "分镜设计失败，LLM返回无法解析的JSON: 第 %d 页。"
                "响应长度: %d, 响应预览: %s",
                page_plan.page_number,
                len(response) if response else 0,
                error_preview
            )
            raise JSONParseError(
                context=f"第 {page_plan.page_number} 页分镜设计",
                detail_msg="AI返回的数据格式错误，请重试。"
            )

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
            raise JSONParseError(
                context=f"第 {page_plan.page_number} 页分镜设计",
                detail_msg=f"解析AI返回数据时出错: {str(e)}"
            ) from e

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

    async def design_all_pages_with_checkpoint(
        self,
        page_plans: List[PagePlanItem],
        chapter_info: ChapterInfo,
        user_id: Optional[int] = None,
        designed_pages_data: Optional[List[Dict[str, Any]]] = None,
        on_page_complete: Optional[Callable[[int, List[Dict[str, Any]]], None]] = None,
    ) -> tuple[StoryboardResult, List[Dict[str, Any]]]:
        """
        设计所有页面的分镜（支持断点恢复）

        每完成一页后调用 on_page_complete 回调，便于保存中间状态。

        Args:
            page_plans: 页面规划列表
            chapter_info: 章节信息
            user_id: 用户ID
            designed_pages_data: 已设计的页面数据列表（用于恢复）
            on_page_complete: 每页完成回调 (page_number, all_designed_pages_data)

        Returns:
            (StoryboardResult, designed_pages_data) 元组
        """
        total_pages = len(page_plans)
        pages: List[PageStoryboard] = []
        previous_panel: Optional[PanelDesign] = None

        # 恢复已设计的页面
        designed_data = list(designed_pages_data) if designed_pages_data else []
        completed_page_numbers = set()

        if designed_data:
            logger.info("从断点恢复 %d 个已设计页面", len(designed_data))
            for page_data in designed_data:
                page_storyboard = PageStoryboard.from_dict(page_data)
                pages.append(page_storyboard)
                completed_page_numbers.add(page_storyboard.page_number)
                # 更新上一格引用
                if page_storyboard.panels:
                    previous_panel = page_storyboard.panels[-1]

        # 继续设计剩余页面
        for page_plan in page_plans:
            if page_plan.page_number in completed_page_numbers:
                logger.debug("页面 %d 已完成，跳过", page_plan.page_number)
                continue

            page_storyboard = await self.design_page(
                page_plan=page_plan,
                chapter_info=chapter_info,
                total_pages=total_pages,
                previous_panel=previous_panel,
                user_id=user_id,
            )
            pages.append(page_storyboard)

            # 保存到断点数据
            designed_data.append(page_storyboard.to_dict())

            # 更新上一格引用
            if page_storyboard.panels:
                previous_panel = page_storyboard.panels[-1]

            # 调用回调保存进度
            if on_page_complete:
                await self._safe_callback(
                    on_page_complete,
                    page_storyboard.page_number,
                    designed_data
                )

        # 按页码排序（确保顺序正确）
        pages.sort(key=lambda p: p.page_number)
        total_panels = sum(p.get_panel_count() for p in pages)

        result = StoryboardResult(
            pages=pages,
            total_pages=total_pages,
            total_panels=total_panels,
            style_notes="",
        )

        return result, designed_data

    async def _safe_callback(
        self,
        callback: Callable,
        page_number: int,
        data: List[Dict[str, Any]]
    ) -> None:
        """安全执行回调，支持同步和异步回调"""
        import asyncio
        try:
            result = callback(page_number, data)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.warning("页面%d完成回调执行失败: %s", page_number, e)

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
                    "emotional_tone": event.emotion_tone,
                })

        # 收集页面相关的对话
        dialogues_data = []
        for idx in page_plan.event_indices:
            for dialogue in chapter_info.get_dialogue_by_event(idx):
                dialogues_data.append({
                    "speaker": dialogue.speaker,
                    "content": dialogue.content,
                    "emotion": dialogue.emotion.value,
                    "is_internal": dialogue.is_internal,
                })

        # 收集页面出场角色信息
        characters_data = {}
        for char_name in page_plan.key_characters:
            char_info = chapter_info.characters.get(char_name)
            if char_info:
                characters_data[char_name] = {
                    "role": char_info.role.value,
                    "appearance": char_info.appearance,
                    "appearance_zh": char_info.appearance_zh,
                    "personality": char_info.personality,
                }

        # 收集页面相关的场景信息（根据事件所属场景）
        scene_indices = set()
        for idx in page_plan.event_indices:
            event = chapter_info.get_event_by_index(idx)
            if event:
                scene_indices.add(event.scene_index)

        scenes_data = []
        for scene_idx in scene_indices:
            if scene_idx < len(chapter_info.scenes):
                scene = chapter_info.scenes[scene_idx]
                scenes_data.append({
                    "location": scene.location,
                    "location_en": scene.location_en,
                    "time_of_day": scene.time_of_day,
                    "atmosphere": scene.atmosphere,
                    "lighting": scene.lighting,
                    "weather": scene.weather,
                    "indoor_outdoor": scene.indoor_outdoor,
                })

        # 上一格信息
        prev_panel_str = "无（本章第一页）"
        if previous_panel:
            prev_panel_str = f"镜头: {previous_panel.shot_type.value}, 内容: {previous_panel.visual_description[:50]}"

        # 计算分镜数量范围
        suggested = page_plan.suggested_panel_count
        min_panels = max(2, suggested - 1)
        max_panels = min(7, suggested + 2)

        # 构建场景上下文字符串
        scene_context = ""
        if scenes_data:
            scene = scenes_data[0]  # 通常一页主要在一个场景
            scene_context = (
                f"场景: {scene.get('location', '')} ({scene.get('location_en', '')}), "
                f"时间: {scene.get('time_of_day', 'day')}, "
                f"光线: {scene.get('lighting', 'natural')}, "
                f"氛围: {scene.get('atmosphere', '')}"
            )
            if scene.get('weather'):
                scene_context += f", 天气: {scene['weather']}"

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
            scene_context=scene_context,  # 新增场景上下文
        )

    async def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return STORYBOARD_SYSTEM_PROMPT

    def _parse_storyboard(self, data: dict, page_number: int) -> PageStoryboard:
        """解析LLM返回的分镜设计（简化版）"""
        panels = []
        panels_data = data.get("panels") or []  # 确保不是 None

        for p in panels_data:
            if not isinstance(p, dict):
                continue

            # 解析对话（确保不是 None）
            dialogues_data = p.get("dialogues") or []
            dialogues = [
                DialogueBubble.from_dict(d) for d in dialogues_data
                if isinstance(d, dict)
            ]

            # 解析音效（确保不是 None）
            sound_effects_data = p.get("sound_effects") or []
            sound_effects = [
                SoundEffect.from_dict(s) for s in sound_effects_data
                if isinstance(s, dict)
            ]

            # from_dict 会自动根据 importance 设置 layout_slot 和 aspect_ratio
            panel = PanelDesign.from_dict(p)
            panel.dialogues = dialogues
            panel.sound_effects = sound_effects
            panels.append(panel)

        return PageStoryboard(
            page_number=page_number,
            panels=panels,
            page_purpose=data.get("page_purpose") or "",
            reading_flow=data.get("reading_flow") or "left_to_right",
            visual_rhythm=data.get("visual_rhythm") or "",
            layout_description=data.get("layout_description") or "",
        )

    def _fallback_design(
        self,
        page_plan: PagePlanItem,
        chapter_info: ChapterInfo,
    ) -> PageStoryboard:
        """回退设计（LLM失败时使用）- 简化版"""
        panels = []
        panel_count = page_plan.suggested_panel_count

        # 重要性到布局槽位和宽高比的映射
        importance_to_slot = {
            "hero": "full_row",
            "major": "half_row",
            "standard": "third_row",
            "minor": "quarter_row",
            "micro": "quarter_row",
        }
        importance_to_aspect = {
            "hero": "16:9",
            "major": "4:3",
            "standard": "1:1",
            "minor": "1:1",
            "micro": "1:1",
        }

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

            # 确定大小和重要性（简化版）
            if i == 0 and page_plan.role.value == "opening":
                size = "large"
                importance = "major"
            elif page_plan.role.value == "climax" and i == panel_count // 2:
                size = "large"
                importance = "major"
            else:
                size = "medium"
                importance = "standard"

            # 根据重要性计算布局槽位和宽高比
            layout_slot = importance_to_slot.get(importance, "third_row")
            aspect_ratio = importance_to_aspect.get(importance, "4:3")

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

            # 构建基础英文描述（回退时比较简单）
            base_en = event_desc_en[:200] if event_desc_en else f"Scene from page {page_plan.page_number}"
            visual_en = f"manga style, black and white, {shot_type} shot, {base_en}"

            panel = PanelDesign(
                panel_id=i + 1,
                importance=importance,
                layout_slot=layout_slot,
                aspect_ratio=aspect_ratio,
                visual_description=event_desc[:100],
                visual_description_en=visual_en,
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
            reading_flow="left_to_right",
            visual_rhythm="fallback: standard rhythm",
            layout_description="fallback: grid layout",
        )

__all__ = [
    "StoryboardDesigner",
]
