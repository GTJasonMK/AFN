"""
场景分析器

提供场景的情感、重要性、关键时刻分析功能。
支持LLM分析和基于规则的回退分析。
"""

import logging
from typing import Dict, Any, Optional

from ..page_templates import SceneMood
from app.utils.json_utils import parse_llm_json_safe

from .prompts import SCENE_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class SceneAnalyzer:
    """
    场景分析器

    分析场景的情感、重要性、关键时刻等特性
    """

    def __init__(self, llm_service=None, prompt_service=None):
        """
        初始化分析器

        Args:
            llm_service: LLM服务实例
            prompt_service: 提示词服务实例
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self._cached_layout_prompt = None

    async def _get_layout_system_prompt(self) -> str:
        """
        获取布局系统提示词

        优先从提示词服务加载，失败则返回默认值
        """
        # 使用缓存
        if self._cached_layout_prompt:
            return self._cached_layout_prompt

        # 尝试从提示词服务加载
        if self.prompt_service:
            try:
                prompt = await self.prompt_service.get_prompt("manga_layout")
                if prompt:
                    self._cached_layout_prompt = prompt
                    return prompt
            except Exception as e:
                logger.warning(f"无法加载 manga_layout 提示词: {e}")

        # 返回默认值
        return "你是专业的漫画分镜师，擅长分析叙事场景并转化为视觉表现。"

    async def analyze_scene(
        self,
        scene_content: str,
        scene_summary: str,
        previous_scene: Optional[str],
        next_scene: Optional[str],
        chapter_position: str,
        user_id: Optional[int],
    ) -> Dict[str, Any]:
        """
        分析场景特性

        使用LLM分析场景的情感、重要性、关键时刻等

        Args:
            scene_content: 场景内容
            scene_summary: 场景摘要
            previous_scene: 前一场景摘要
            next_scene: 后一场景摘要
            chapter_position: 章节位置
            user_id: 用户ID

        Returns:
            场景分析结果字典
        """
        if self.llm_service:
            # 使用LLM分析
            prompt = SCENE_ANALYSIS_PROMPT.format(
                scene_content=scene_content[:2000],
                scene_summary=scene_summary,
                previous_scene=previous_scene or "（无）",
                next_scene=next_scene or "（无）",
                chapter_position=chapter_position,
            )

            try:
                from app.services.llm_wrappers import call_llm, LLMProfile

                # 使用可配置的布局提示词
                system_prompt = await self._get_layout_system_prompt()

                response = await call_llm(
                    self.llm_service,
                    LLMProfile.ANALYTICAL,
                    system_prompt=system_prompt,
                    user_content=prompt,
                    user_id=user_id,
                )

                analysis = parse_llm_json_safe(response)
                if analysis:
                    return analysis

            except Exception as e:
                logger.warning(f"LLM场景分析失败: {e}，使用规则分析")

        # 回退到规则分析
        return self.analyze_scene_by_rules(
            scene_content, scene_summary, chapter_position
        )

    def analyze_scene_by_rules(
        self,
        scene_content: str,
        scene_summary: str,
        chapter_position: str,
    ) -> Dict[str, Any]:
        """
        基于规则的场景分析（LLM不可用时的回退）

        Args:
            scene_content: 场景内容
            scene_summary: 场景摘要
            chapter_position: 章节位置

        Returns:
            场景分析结果字典
        """
        content_lower = scene_content.lower()
        summary_lower = scene_summary.lower()
        combined = content_lower + summary_lower

        # 情感检测
        mood = "calm"
        if any(word in combined for word in ["战斗", "打", "攻击", "冲", "fight", "attack"]):
            mood = "action"
        elif any(word in combined for word in ["紧张", "对峙", "威胁", "危险"]):
            mood = "tension"
        elif any(word in combined for word in ["哭", "泪", "悲伤", "痛苦", "感动"]):
            mood = "emotional"
        elif any(word in combined for word in ["笑", "搞笑", "有趣", "开心"]):
            mood = "comedy"
        elif any(word in combined for word in ["神秘", "奇怪", "疑惑", "秘密"]):
            mood = "mystery"
        elif any(word in combined for word in ["回忆", "过去", "曾经", "记得"]):
            mood = "flashback"
        elif any(word in combined for word in ["爱", "喜欢", "心动", "浪漫"]):
            mood = "romantic"
        elif any(word in combined for word in ["恐怖", "害怕", "阴森", "黑暗"]):
            mood = "horror"

        # 重要性判断
        importance = "normal"
        if chapter_position == "climax":
            importance = "high"
        elif chapter_position in ["beginning", "ending"]:
            importance = "normal"
        if any(word in combined for word in ["关键", "重要", "转折", "决定"]):
            importance = "high"

        # 对话检测
        has_dialogue = '"' in scene_content or '"' in scene_content or "说" in scene_content

        # 动作检测
        is_action = mood == "action" or any(
            word in combined for word in ["跑", "跳", "飞", "冲", "打"]
        )

        # 高潮检测
        is_climax = chapter_position == "climax" or importance == "critical"

        return {
            "mood": mood,
            "importance": importance,
            "has_dialogue": has_dialogue,
            "is_action": is_action,
            "is_climax": is_climax,
            "key_moments": [],
            "characters_present": [],
            "atmosphere": "",
            "pacing_suggestion": "fast" if is_action else "normal",
            "recommended_panel_count": 6 if is_action else 5,
        }

    @staticmethod
    def parse_mood(mood_str: str) -> SceneMood:
        """
        解析 mood 字符串，处理复合值和无效值

        Args:
            mood_str: 情感字符串（可能包含复合值如 "calm/dramatic"）

        Returns:
            SceneMood 枚举值
        """
        if not mood_str:
            return SceneMood.CALM

        # 处理复合值如 "calm/dramatic"
        candidates = mood_str.replace("/", ",").replace("|", ",").split(",")

        for candidate in candidates:
            candidate = candidate.strip().lower()
            try:
                return SceneMood(candidate)
            except ValueError:
                continue

        # 如果都无效，返回默认值
        return SceneMood.CALM


__all__ = [
    "SceneAnalyzer",
]
