"""
场景展开服务

将叙事场景展开为专业漫画分镜（页面+画格）。
这是实现真正漫画效果的核心服务。

核心流程：
1. 分析场景的情感、重要性、内容类型
2. 选择合适的页面模板（支持LLM动态布局或硬编码模板）
3. 将场景内容分配到各个画格
4. 生成画格级别的内容描述

v2更新：
- 支持LLM动态布局，替代硬编码模板
- 考虑上下页连续性，避免布局重复
- 支持格间过渡类型、间白策略、翻页钩子
"""

import logging
from typing import List, Dict, Any, Optional

from ..page_templates import (
    PagePlan,
    SceneExpansion,
)

from .scene_analyzer import SceneAnalyzer
from .layout_selector import LayoutSelector
from .content_generator import ContentGenerator
from .history_manager import HistoryManager

logger = logging.getLogger(__name__)


class SceneExpansionService:
    """
    场景展开服务

    将单个叙事场景展开为专业漫画分镜
    """

    def __init__(self, llm_service=None, prompt_service=None):
        """
        初始化服务

        Args:
            llm_service: LLM服务实例（用于智能分析）
            prompt_service: 提示词服务实例（用于加载可配置提示词）
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service

        # 初始化子组件
        self._scene_analyzer = SceneAnalyzer(llm_service, prompt_service)
        self._layout_selector = LayoutSelector(llm_service, prompt_service)
        self._content_generator = ContentGenerator(llm_service, prompt_service)
        self._history_manager = HistoryManager()

    @property
    def _previous_pages(self):
        """向后兼容：访问历史页面列表"""
        return self._history_manager.previous_pages

    async def expand_scene(
        self,
        scene_id: int,
        scene_summary: str,
        scene_content: str,
        characters: List[str],
        previous_scene: Optional[str] = None,
        next_scene: Optional[str] = None,
        chapter_position: str = "middle",  # beginning/middle/climax/ending
        user_id: Optional[int] = None,
        dialogue_language: str = "chinese",  # 对话/音效语言
        use_dynamic_layout: bool = True,  # 是否使用LLM动态布局
    ) -> SceneExpansion:
        """
        将场景展开为漫画分镜

        Args:
            scene_id: 场景ID
            scene_summary: 场景摘要
            scene_content: 场景原文内容
            characters: 出场角色列表
            previous_scene: 前一场景摘要
            next_scene: 后一场景摘要
            chapter_position: 在章节中的位置
            user_id: 用户ID
            dialogue_language: 对话/音效语言（chinese/japanese/english/korean）
            use_dynamic_layout: 是否使用LLM动态布局（True=动态布局，False=硬编码模板）

        Returns:
            场景展开结果
        """
        logger.info(f"展开场景 {scene_id}: {scene_summary[:30]}... (动态布局={use_dynamic_layout})")

        # 步骤1：分析场景
        analysis = await self._scene_analyzer.analyze_scene(
            scene_content=scene_content,
            scene_summary=scene_summary,
            previous_scene=previous_scene,
            next_scene=next_scene,
            chapter_position=chapter_position,
            user_id=user_id,
        )

        # 步骤2：选择/生成页面布局
        if use_dynamic_layout and self.llm_service:
            # 使用LLM动态布局
            template, dynamic_page = await self._layout_selector.get_dynamic_layout(
                scene_id=scene_id,
                scene_content=scene_content,
                scene_summary=scene_summary,
                analysis=analysis,
                characters=characters,
                chapter_position=chapter_position,
                user_id=user_id,
                previous_pages=self._history_manager.previous_pages,
            )
            if dynamic_page:
                self._history_manager.add_page(dynamic_page)
            logger.info(f"使用LLM动态布局: {len(template.panel_slots)} 格")
        else:
            # 回退到硬编码模板
            template = self._layout_selector.select_template(analysis)
            logger.info(f"选择硬编码模板: {template.name_zh}")

        # 步骤3：分配画格内容
        page_plan = await self._content_generator.distribute_content(
            scene_content=scene_content,
            scene_summary=scene_summary,
            analysis=analysis,
            template=template,
            characters=characters,
            user_id=user_id,
            dialogue_language=dialogue_language,
        )

        # 步骤4：构建展开结果
        expansion = SceneExpansion(
            scene_id=scene_id,
            scene_summary=scene_summary,
            original_text=scene_content,
            pages=[page_plan],
            mood=self._scene_analyzer.parse_mood(analysis.get("mood", "calm")),
            importance=analysis.get("importance", "normal"),
        )

        logger.info(
            f"场景 {scene_id} 展开完成: "
            f"{len(expansion.pages)} 页, {expansion.get_total_panels()} 格"
        )

        return expansion

    async def expand_scenes_batch(
        self,
        scenes: List[Dict[str, Any]],
        user_id: Optional[int] = None,
        dialogue_language: str = "chinese",
        use_dynamic_layout: bool = True,
    ) -> List[SceneExpansion]:
        """
        批量展开多个场景

        Args:
            scenes: 场景列表，每个包含 scene_id, summary, content, characters
            user_id: 用户ID
            dialogue_language: 对话/音效语言
            use_dynamic_layout: 是否使用LLM动态布局

        Returns:
            场景展开结果列表
        """
        # 重置页面历史（新批次开始）
        self._history_manager.reset()
        expansions = []

        for i, scene in enumerate(scenes):
            # 获取上下文
            previous_scene = scenes[i - 1].get("summary") if i > 0 else None
            next_scene = scenes[i + 1].get("summary") if i < len(scenes) - 1 else None

            # 判断章节位置
            if i == 0:
                position = "beginning"
            elif i == len(scenes) - 1:
                position = "ending"
            elif i >= len(scenes) * 0.7:
                position = "climax"
            else:
                position = "middle"

            expansion = await self.expand_scene(
                scene_id=scene.get("scene_id", i + 1),
                scene_summary=scene.get("summary", ""),
                scene_content=scene.get("content", scene.get("original_text", "")),
                characters=scene.get("characters", []),
                previous_scene=previous_scene,
                next_scene=next_scene,
                chapter_position=position,
                user_id=user_id,
                dialogue_language=dialogue_language,
                use_dynamic_layout=use_dynamic_layout,
            )

            expansions.append(expansion)

        return expansions

    def restore_previous_pages_from_expansions(
        self,
        expansions: List[SceneExpansion],
        max_pages: int = 5,
    ) -> None:
        """
        从已完成的展开结果中恢复布局历史

        用于断点续传时恢复 _previous_pages，以保持后续页面布局的连续性。

        Args:
            expansions: 已完成的场景展开结果列表
            max_pages: 最多恢复多少页的历史（默认5页）
        """
        self._history_manager.restore_from_expansions(expansions, max_pages)


# 便捷函数
async def expand_scene_to_manga(
    scene_id: int,
    scene_summary: str,
    scene_content: str,
    characters: List[str],
    llm_service=None,
    user_id: Optional[int] = None,
) -> SceneExpansion:
    """
    便捷函数：将场景展开为漫画分镜

    Args:
        scene_id: 场景ID
        scene_summary: 场景摘要
        scene_content: 场景内容
        characters: 角色列表
        llm_service: LLM服务
        user_id: 用户ID

    Returns:
        场景展开结果
    """
    service = SceneExpansionService(llm_service)
    return await service.expand_scene(
        scene_id=scene_id,
        scene_summary=scene_summary,
        scene_content=scene_content,
        characters=characters,
        user_id=user_id,
    )


__all__ = [
    "SceneExpansionService",
    "expand_scene_to_manga",
]
