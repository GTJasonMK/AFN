"""
布局历史管理器

管理页面布局历史，用于保持连续性和支持断点恢复。
"""

import logging
from typing import List, Optional

from ..page_templates import (
    PagePlan,
    PanelContent,
    SceneExpansion,
    SceneMood,
    PanelPurpose,
    PanelShape,
    PageTemplate,
    PanelSlot,
)
from ..llm_layout_service import DynamicPage, DynamicPanel

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    布局历史管理器

    管理页面布局历史，支持连续性保持和断点恢复
    """

    def __init__(self, max_history: int = 5):
        """
        初始化管理器

        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self._previous_pages: List[DynamicPage] = []

    @property
    def previous_pages(self) -> List[DynamicPage]:
        """获取历史页面列表"""
        return self._previous_pages

    def add_page(self, page: DynamicPage) -> None:
        """
        添加页面到历史

        Args:
            page: 要添加的页面
        """
        self._previous_pages.append(page)
        # 只保留最近的页面
        if len(self._previous_pages) > self.max_history:
            self._previous_pages = self._previous_pages[-self.max_history:]

    def reset(self) -> None:
        """重置历史记录"""
        self._previous_pages = []

    def restore_from_expansions(
        self,
        expansions: List[SceneExpansion],
        max_pages: Optional[int] = None,
    ) -> None:
        """
        从已完成的展开结果中恢复布局历史

        用于断点续传时恢复 _previous_pages，以保持后续页面布局的连续性。

        Args:
            expansions: 已完成的场景展开结果列表
            max_pages: 最多恢复多少页的历史（默认使用 max_history）
        """
        if not expansions:
            return

        max_pages = max_pages or self.max_history

        # 收集所有页面
        all_pages = []
        for exp in expansions:
            for page in exp.pages:
                all_pages.append((exp, page))

        # 只保留最后 max_pages 页
        recent_pages = all_pages[-max_pages:] if len(all_pages) > max_pages else all_pages

        # 转换为 DynamicPage 格式
        self._previous_pages = []
        for exp, page in recent_pages:
            dynamic_page = self._convert_page_plan_to_dynamic_page(page, exp)
            if dynamic_page:
                self._previous_pages.append(dynamic_page)

        if self._previous_pages:
            logger.info(f"从断点恢复了 {len(self._previous_pages)} 页布局历史")

    def _convert_page_plan_to_dynamic_page(
        self,
        page: PagePlan,
        expansion: SceneExpansion,
    ) -> Optional[DynamicPage]:
        """
        将 PagePlan 转换为 DynamicPage 格式

        用于从已完成的展开结果中恢复布局历史。
        注意：这是一个近似转换，不能完全还原原始的动态布局细节。

        Args:
            page: 页面规划
            expansion: 所属的场景展开

        Returns:
            DynamicPage 对象，或 None（如果转换失败）
        """
        try:
            # 构建动态画格列表
            dynamic_panels = []
            for i, panel in enumerate(page.panels):
                # 从模板槽位获取位置信息（如果可用）
                slot = None
                if page.template:
                    for s in page.template.panel_slots:
                        if s.slot_id == panel.slot_id:
                            slot = s
                            break

                # 推断 story_beat
                story_beat = self._infer_story_beat(panel, expansion.mood)

                dynamic_panel = DynamicPanel(
                    panel_id=panel.slot_id,
                    scene_id=expansion.scene_id,
                    x=slot.x if slot else 0,
                    y=slot.y if slot else i * (1.0 / len(page.panels)),
                    width=slot.width if slot else 1.0,
                    height=slot.height if slot else 1.0 / len(page.panels),
                    story_beat=story_beat,
                    importance="major" if (slot and slot.is_key_panel) else "standard",
                    composition=panel.composition or "medium shot",
                    camera_angle=panel.camera_angle or "eye level",
                )
                dynamic_panels.append(dynamic_panel)

            # 推断页面功能
            page_function = self._infer_page_function(expansion.mood, page.panels)
            page_rhythm = self._infer_page_rhythm(expansion.mood)

            return DynamicPage(
                page_number=page.page_number,
                panels=dynamic_panels,
                page_function=page_function,
                page_rhythm=page_rhythm,
                gutter_style="standard",
            )

        except Exception as e:
            logger.warning(f"转换 PagePlan 到 DynamicPage 失败: {e}")
            return None

    def _infer_story_beat(self, panel: PanelContent, mood: SceneMood) -> str:
        """根据画格内容和场景情感推断 story_beat"""
        # 根据对话判断
        if panel.dialogue:
            return "dialogue"
        # 根据情感判断
        if mood == SceneMood.ACTION:
            return "action"
        if mood == SceneMood.DRAMATIC:
            return "climax"
        if mood == SceneMood.EMOTIONAL:
            return "build-up"
        # 默认
        return "standard"

    def _infer_page_function(self, mood: SceneMood, panels: List[PanelContent]) -> str:
        """根据场景情感和画格内容推断页面功能"""
        has_dialogue = any(p.dialogue for p in panels)
        if has_dialogue:
            return "dialogue"
        if mood == SceneMood.ACTION:
            return "action"
        if mood == SceneMood.DRAMATIC:
            return "climax"
        return "build"

    def _infer_page_rhythm(self, mood: SceneMood) -> str:
        """根据场景情感推断页面节奏"""
        rhythm_map = {
            SceneMood.CALM: "slow",
            SceneMood.TENSION: "medium",
            SceneMood.ACTION: "fast",
            SceneMood.EMOTIONAL: "medium",
            SceneMood.MYSTERY: "slow",
            SceneMood.COMEDY: "fast",
            SceneMood.DRAMATIC: "explosive",
            SceneMood.ROMANTIC: "slow",
            SceneMood.HORROR: "medium",
            SceneMood.FLASHBACK: "slow",
        }
        return rhythm_map.get(mood, "medium")


__all__ = [
    "HistoryManager",
]
