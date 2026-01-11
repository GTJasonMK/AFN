"""
页面规划器

基于章节信息进行全局页面规划。
简化版：移除复杂的节奏和角色概念。
"""

import json
import logging
from typing import Optional, TYPE_CHECKING

from app.exceptions import JSONParseError
from app.services.llm_wrappers import call_llm_json, LLMProfile
from app.utils.json_utils import parse_llm_json_safe

from ..extraction import ChapterInfo
from .models import PagePlanResult, PagePlanItem
from .prompts import PROMPT_NAME, PAGE_PLANNING_PROMPT, PLANNING_SYSTEM_PROMPT

if TYPE_CHECKING:
    from app.services.prompt_service import PromptService
    from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class PagePlanner:
    """
    全局页面规划器（简化版）

    基于提取的章节信息，规划整章的页面结构：
    - 确定总页数
    - 分配事件到各页面
    """

    def __init__(
        self,
        llm_service: "LLMService",
        prompt_service: Optional["PromptService"] = None,
    ):
        """
        初始化规划器

        Args:
            llm_service: LLM服务实例
            prompt_service: 提示词服务实例（可选）
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def plan(
        self,
        chapter_info: ChapterInfo,
        min_pages: int = 8,
        max_pages: int = 15,
        user_id: Optional[int] = None,
    ) -> PagePlanResult:
        """
        规划页面

        Args:
            chapter_info: 章节信息
            min_pages: 最少页数
            max_pages: 最多页数
            user_id: 用户ID

        Returns:
            PagePlanResult: 页面规划结果

        Raises:
            JSONParseError: 当LLM返回的JSON无法解析时
        """
        # 如果事件太少，使用简单规划
        if len(chapter_info.events) < 3:
            logger.info("事件数量少于3，使用简单规划")
            return self._simple_plan(chapter_info, min_pages)

        # 构建提示词
        prompt = await self._build_prompt(chapter_info, min_pages, max_pages)

        # 获取系统提示词
        system_prompt = await self._get_system_prompt()

        # 调用LLM
        logger.info(
            "开始页面规划: %d 事件, 目标 %d-%d 页",
            len(chapter_info.events),
            min_pages,
            max_pages,
        )

        response = await call_llm_json(
            self.llm_service,
            LLMProfile.ANALYTICAL,
            system_prompt=system_prompt,
            user_content=prompt,
            user_id=user_id,
        )

        # 解析响应
        data = parse_llm_json_safe(response)

        if not data:
            error_preview = response[:200] if response else "(empty)"
            logger.error(
                "页面规划失败，LLM返回无法解析的JSON。"
                "响应长度: %d, 响应预览: %s",
                len(response) if response else 0,
                error_preview
            )
            raise JSONParseError(
                context="页面规划",
                detail_msg="AI返回的数据格式错误，请重试。"
            )

        try:
            result = self._parse_plan_result(data, chapter_info)
            logger.info(
                "页面规划完成: %d 页",
                result.total_pages,
            )
            return result
        except Exception as e:
            logger.error("解析规划结果失败: %s", e)
            raise JSONParseError(
                context="页面规划",
                detail_msg=f"解析AI返回数据时出错: {str(e)}"
            ) from e

    async def _build_prompt(
        self,
        chapter_info: ChapterInfo,
        min_pages: int,
        max_pages: int,
    ) -> str:
        """构建规划提示词"""
        # 尝试从PromptService加载
        prompt_template = None
        if self.prompt_service:
            try:
                prompt_template = await self.prompt_service.get_prompt(PROMPT_NAME)
            except Exception as e:
                logger.warning("无法加载 %s 提示词: %s", PROMPT_NAME, e)

        if not prompt_template:
            prompt_template = PAGE_PLANNING_PROMPT

        # 准备事件列表JSON
        events_data = []
        for event in chapter_info.events:
            events_data.append({
                "index": event.index,
                "type": event.type.value,
                "description": event.description,
                "participants": event.participants,
            })

        # 准备场景列表JSON
        scenes_data = []
        for scene in chapter_info.scenes:
            scenes_data.append({
                "index": scene.index,
                "location": scene.location,
                "event_indices": scene.event_indices,
            })

        # 准备角色列表
        characters_list = list(chapter_info.characters.keys())

        # 识别高潮事件索引（类型为 climax 或 conflict 的事件）
        climax_indices = [
            event.index for event in chapter_info.events
            if event.type.value in ("climax", "conflict", "action")
        ]

        return prompt_template.format(
            chapter_summary=chapter_info.chapter_summary,
            events_json=json.dumps(events_data, ensure_ascii=False, indent=2),
            scenes_json=json.dumps(scenes_data, ensure_ascii=False, indent=2),
            characters_json=json.dumps(characters_list, ensure_ascii=False),
            climax_indices=json.dumps(climax_indices, ensure_ascii=False),
            min_pages=min_pages,
            max_pages=max_pages,
        )

    async def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return PLANNING_SYSTEM_PROMPT

    def _parse_plan_result(
        self,
        data: dict,
        chapter_info: ChapterInfo,
    ) -> PagePlanResult:
        """解析LLM返回的规划结果"""
        pages = []
        for p in data.get("pages", []):
            pages.append(PagePlanItem.from_dict(p))

        # 验证和修复：确保所有事件都被分配
        assigned_events = set()
        for page in pages:
            assigned_events.update(page.event_indices)

        all_event_indices = {e.index for e in chapter_info.events}
        missing_events = all_event_indices - assigned_events

        if missing_events:
            logger.warning("有 %d 个事件未被分配，添加到最后一页", len(missing_events))
            if pages:
                pages[-1].event_indices.extend(sorted(missing_events))
            else:
                # 没有页面，创建一个
                pages.append(PagePlanItem(
                    page_number=1,
                    event_indices=sorted(missing_events),
                    content_summary="补充内容",
                ))

        return PagePlanResult(
            total_pages=data.get("total_pages", len(pages)),
            pages=pages,
        )

    def _simple_plan(
        self,
        chapter_info: ChapterInfo,
        min_pages: int,
    ) -> PagePlanResult:
        """简单规划（事件很少时使用）"""
        pages = []
        events = chapter_info.events

        for i, event in enumerate(events):
            pages.append(PagePlanItem(
                page_number=i + 1,
                event_indices=[event.index],
                content_summary=event.description[:50],
                key_characters=event.participants,
                has_dialogue=len(chapter_info.get_dialogue_by_event(event.index)) > 0,
                has_action=event.type.value in ("action", "conflict"),
                suggested_panel_count=4,
            ))

        # 如果页数不够，补充空白页
        while len(pages) < min_pages:
            pages.append(PagePlanItem(
                page_number=len(pages) + 1,
                event_indices=[],
                content_summary="补充画面",
                suggested_panel_count=3,
            ))

        return PagePlanResult(
            total_pages=len(pages),
            pages=pages,
        )

    def _fallback_plan(
        self,
        chapter_info: ChapterInfo,
        min_pages: int,
        max_pages: int,
    ) -> PagePlanResult:
        """回退规划（LLM失败时使用）"""
        events = chapter_info.events
        if not events:
            return self._simple_plan(chapter_info, min_pages)

        # 计算目标页数
        target_pages = min(max(min_pages, len(events) // 2), max_pages)

        # 平均分配事件到页面
        events_per_page = max(1, len(events) // target_pages)

        pages = []
        current_events = []
        page_number = 1

        for i, event in enumerate(events):
            current_events.append(event.index)

            # 当前页事件够了，或者到达最后一个事件
            if len(current_events) >= events_per_page or i == len(events) - 1:
                # 收集角色
                key_chars = []
                has_dialogue = False
                has_action = False
                for idx in current_events:
                    if idx < len(events):
                        key_chars.extend(events[idx].participants)
                        if chapter_info.get_dialogue_by_event(idx):
                            has_dialogue = True
                        if events[idx].type.value in ("action", "conflict"):
                            has_action = True

                pages.append(PagePlanItem(
                    page_number=page_number,
                    event_indices=list(current_events),
                    content_summary=events[current_events[0]].description[:50] if current_events else "",
                    key_characters=list(set(key_chars))[:3],
                    has_dialogue=has_dialogue,
                    has_action=has_action,
                    suggested_panel_count=4,
                ))

                current_events = []
                page_number += 1

        return PagePlanResult(
            total_pages=len(pages),
            pages=pages,
        )


__all__ = [
    "PagePlanner",
]
