"""
布局选择器

负责根据场景分析结果选择合适的页面布局。
支持LLM动态布局和硬编码模板两种模式。
"""

import logging
from typing import Dict, Any, List, Optional

from ..page_templates import (
    PageTemplate,
    SceneMood,
    recommend_template,
)
from ..llm_layout_service import LLMLayoutService, DynamicPage

from .scene_analyzer import SceneAnalyzer

logger = logging.getLogger(__name__)


class LayoutSelector:
    """
    布局选择器

    根据场景特性选择或生成页面布局
    """

    def __init__(self, llm_service=None, prompt_service=None):
        """
        初始化选择器

        Args:
            llm_service: LLM服务实例
            prompt_service: 提示词服务实例
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        # 初始化LLM动态布局服务
        self._layout_service = LLMLayoutService(llm_service, prompt_service)

    async def get_dynamic_layout(
        self,
        scene_id: int,
        scene_content: str,
        scene_summary: str,
        analysis: Dict[str, Any],
        characters: List[str],
        chapter_position: str,
        user_id: Optional[int],
        previous_pages: List[DynamicPage],
    ) -> PageTemplate:
        """
        使用LLM生成动态布局

        Args:
            scene_id: 场景ID
            scene_content: 场景内容
            scene_summary: 场景摘要
            analysis: 场景分析结果
            characters: 角色列表
            chapter_position: 章节位置
            user_id: 用户ID
            previous_pages: 之前生成的页面列表（用于保持连续性）

        Returns:
            PageTemplate对象（从动态布局转换）
        """
        # 构建场景信息
        scene_info = {
            "scene_id": scene_id,
            "summary": scene_summary,
            "content": scene_content,
            "mood": analysis.get("mood", "calm"),
            "characters": characters,
            "is_climax": analysis.get("is_climax", False),
            "has_dialogue": analysis.get("has_dialogue", False),
            "is_action": analysis.get("is_action", False),
        }

        try:
            # 获取前一页布局（用于避免重复）
            previous_page = previous_pages[-1] if previous_pages else None

            # 使用LLM布局服务生成动态布局
            dynamic_page = await self._layout_service.generate_layout_for_single_scene(
                scene=scene_info,
                previous_page=previous_page,
                next_scene_hint=None,  # 可以后续扩展
                user_id=user_id,
            )

            # 转换为PageTemplate格式（兼容现有代码）
            template = self._layout_service.convert_to_template(dynamic_page)
            return template, dynamic_page

        except Exception as e:
            logger.warning(f"LLM动态布局生成失败: {e}，回退到硬编码模板")
            # 回退到硬编码模板
            return self.select_template(analysis), None

    def select_template(self, analysis: Dict[str, Any]) -> PageTemplate:
        """
        根据分析结果选择页面模板（硬编码模板）

        Args:
            analysis: 场景分析结果

        Returns:
            PageTemplate对象
        """
        # 解析 mood，处理 LLM 可能返回的复合值如 "calm/dramatic"
        mood_str = analysis.get("mood", "calm")
        mood = SceneAnalyzer.parse_mood(mood_str)

        is_climax = analysis.get("is_climax", False)
        has_dialogue = analysis.get("has_dialogue", False)
        is_action = analysis.get("is_action", False)

        return recommend_template(
            mood=mood,
            is_climax=is_climax,
            has_dialogue=has_dialogue,
            is_action=is_action,
        )


__all__ = [
    "LayoutSelector",
]
