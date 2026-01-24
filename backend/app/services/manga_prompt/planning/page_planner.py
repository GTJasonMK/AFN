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
from app.services.scene_descriptor import SceneDescriptor
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
        # 尝试从PromptService加载，失败时回退到默认模板
        prompt_template = PAGE_PLANNING_PROMPT
        if self.prompt_service:
            prompt_template = await self.prompt_service.get_prompt_or_fallback(
                PROMPT_NAME,
                PAGE_PLANNING_PROMPT,
                logger=logger,
            )

        # 准备事件列表JSON - 增加复杂度信息
        events_data = []
        for event in chapter_info.events:
            # 统计该事件关联的对话数量
            dialogue_count = len(chapter_info.get_dialogue_by_event(event.index))
            # 判断是否是高潮事件
            is_climax = (
                event.is_climax or
                event.type.value in ("climax", "conflict") or
                event.importance.value in ("critical", "high")
            )
            events_data.append({
                "index": event.index,
                "type": event.type.value,
                "description": event.description,
                "participants": event.participants,
                "importance": event.importance.value if hasattr(event.importance, 'value') else str(event.importance),
                "dialogue_count": dialogue_count,
                "is_climax": is_climax,
            })

        # 准备场景列表JSON
        scenes_data = []
        for scene in chapter_info.scenes:
            scenes_data.append({
                "index": scene.index,
                "location": scene.location,
                "event_indices": scene.event_indices,
                "scene_descriptor": SceneDescriptor.from_scene_info(scene).to_dict(),
            })

        # 准备角色列表
        characters_list = list(chapter_info.characters.keys())

        # 识别高潮事件索引
        climax_indices = [
            event.index for event in chapter_info.events
            if event.is_climax or event.type.value in ("climax", "conflict", "action")
               or (hasattr(event.importance, 'value') and event.importance.value in ("critical", "high"))
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
            logger.warning("有 %d 个事件未被分配，按顺序插入到合适的页面", len(missing_events))
            # 按事件索引排序遗漏的事件
            missing_sorted = sorted(missing_events)

            for missing_idx in missing_sorted:
                # 找到应该插入的页面：选择包含相邻事件的页面
                inserted = False
                for page in pages:
                    if not page.event_indices:
                        continue
                    # 检查该页面是否包含相邻事件
                    min_idx = min(page.event_indices)
                    max_idx = max(page.event_indices)
                    # 如果遗漏事件在该页面事件范围内或紧邻，则插入
                    if min_idx - 1 <= missing_idx <= max_idx + 1:
                        page.event_indices.append(missing_idx)
                        page.event_indices.sort()  # 保持顺序
                        inserted = True
                        break

                # 如果没有找到合适的页面，插入到第一个事件索引大于它的页面之前的页面
                if not inserted:
                    for i, page in enumerate(pages):
                        if page.event_indices and min(page.event_indices) > missing_idx:
                            # 插入到前一个页面（如果存在）
                            if i > 0:
                                pages[i - 1].event_indices.append(missing_idx)
                                pages[i - 1].event_indices.sort()
                            else:
                                pages[0].event_indices.append(missing_idx)
                                pages[0].event_indices.sort()
                            inserted = True
                            break

                    # 最后的回退：添加到最后一页
                    if not inserted and pages:
                        pages[-1].event_indices.append(missing_idx)
                        pages[-1].event_indices.sort()

        return PagePlanResult(
            total_pages=data.get("total_pages", len(pages)),
            pages=pages,
        )

    def _simple_plan(
        self,
        chapter_info: ChapterInfo,
        min_pages: int,
    ) -> PagePlanResult:
        """简单规划（事件很少时使用）

        当事件数量少于3个时使用此方法。
        不再添加空白页，因为空白页会导致分镜设计和提示词构建产生无意义内容。
        如果事件确实很少，生成的页数也会相应较少。
        """
        pages = []
        events = chapter_info.events

        if not events:
            # 如果完全没有事件，创建一个基于章节摘要的单页
            pages.append(PagePlanItem(
                page_number=1,
                event_indices=[],
                content_summary=chapter_info.chapter_summary[:100] if chapter_info.chapter_summary else "章节概览",
                key_characters=list(chapter_info.characters.keys())[:3],
                has_dialogue=len(chapter_info.dialogues) > 0,
                has_action=False,
                suggested_panel_count=4,
            ))
        else:
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

        return PagePlanResult(
            total_pages=len(pages),
            pages=pages,
        )


__all__ = [
    "PagePlanner",
]
