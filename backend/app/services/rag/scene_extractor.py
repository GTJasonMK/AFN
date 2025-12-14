"""
场景状态提取器

从前一章的分析数据中提取当前场景状态，用于构建高密度的提示词上下文。
支持优雅降级：没有分析数据时仅使用上一章结尾片段。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ...schemas.novel import ChapterAnalysisData


@dataclass
class SceneState:
    """
    场景状态数据结构

    封装章节生成所需的核心场景信息，提供高信息密度的上下文。

    Attributes:
        time_marker: 时间标记（如"当天傍晚"、"三天后"）
        primary_location: 主要场景地点
        character_positions: 角色位置映射（角色名 -> 位置）
        tone: 情感基调
        active_tensions: 未解悬念列表
        previous_ending: 上一章结尾片段
    """
    time_marker: Optional[str] = None
    primary_location: Optional[str] = None
    character_positions: Dict[str, str] = field(default_factory=dict)
    tone: Optional[str] = None
    active_tensions: List[str] = field(default_factory=list)
    previous_ending: str = ""

    def is_empty(self) -> bool:
        """检查场景状态是否为空（仅有结尾片段）"""
        return (
            not self.time_marker
            and not self.primary_location
            and not self.character_positions
            and not self.tone
            and not self.active_tensions
        )

    def to_prompt_text(self) -> str:
        """
        将场景状态转换为提示词文本

        Returns:
            格式化的场景状态文本
        """
        lines = []

        # 上一章结尾（最重要，放最前）
        if self.previous_ending:
            lines.append(f"上一章结尾:\n> {self.previous_ending}")

        # 角色位置
        if self.character_positions:
            positions = "; ".join(
                f"{name}在{loc}" for name, loc in self.character_positions.items()
            )
            lines.append(f"角色位置: {positions}")

        # 时间和基调
        context_parts = []
        if self.time_marker:
            context_parts.append(f"时间: {self.time_marker}")
        if self.tone:
            context_parts.append(f"氛围: {self.tone}")
        if context_parts:
            lines.append(" | ".join(context_parts))

        # 未解悬念
        if self.active_tensions:
            tensions_text = "; ".join(self.active_tensions[:3])  # 最多3个
            lines.append(f"未解悬念: {tensions_text}")

        return "\n".join(lines)


class SceneStateExtractor:
    """
    场景状态提取器

    从前一章的分析数据和结尾片段中提取场景状态。
    支持优雅降级：没有分析数据时仅返回结尾片段。

    Usage:
        extractor = SceneStateExtractor()
        scene_state = extractor.extract(
            prev_chapter_analysis=analysis_data,
            previous_tail_excerpt="上一章的结尾文本...",
        )
        prompt_text = scene_state.to_prompt_text()
    """

    def __init__(self, tail_length: int = 500):
        """
        初始化提取器

        Args:
            tail_length: 结尾片段的最大长度（字符数）
        """
        self.tail_length = tail_length

    def extract(
        self,
        prev_chapter_analysis: Optional[ChapterAnalysisData],
        previous_tail_excerpt: str,
    ) -> SceneState:
        """
        提取场景状态

        Args:
            prev_chapter_analysis: 前一章的分析数据（可选）
            previous_tail_excerpt: 前一章的结尾片段

        Returns:
            SceneState: 提取的场景状态
        """
        state = SceneState()

        # 处理结尾片段（总是需要）
        state.previous_ending = self._format_ending(previous_tail_excerpt)

        # 如果有分析数据，提取更多信息
        if prev_chapter_analysis:
            self._extract_from_analysis(state, prev_chapter_analysis)

        return state

    def _extract_from_analysis(
        self,
        state: SceneState,
        analysis: ChapterAnalysisData,
    ) -> None:
        """
        从分析数据中提取信息到状态对象

        Args:
            state: 要填充的状态对象
            analysis: 章节分析数据
        """
        # 从元数据提取时间、地点、基调
        if analysis.metadata:
            state.time_marker = analysis.metadata.timeline_marker
            state.tone = analysis.metadata.tone

            # 主要地点取第一个
            if analysis.metadata.locations:
                state.primary_location = analysis.metadata.locations[0]

        # 从角色状态提取位置
        if analysis.character_states:
            state.character_positions = {
                name: cs.location
                for name, cs in analysis.character_states.items()
                if cs.location
            }

        # 从伏笔数据提取未解悬念
        if analysis.foreshadowing and analysis.foreshadowing.tensions:
            state.active_tensions = analysis.foreshadowing.tensions[:3]

    def _format_ending(self, text: str) -> str:
        """
        格式化结尾片段

        截取适当长度，并尝试从完整句子开始。

        Args:
            text: 原始结尾文本

        Returns:
            格式化后的结尾片段
        """
        if not text:
            return ""

        text = text.strip()

        # 如果已经足够短，直接返回
        if len(text) <= self.tail_length:
            return text

        # 截取最后 tail_length 字符
        text = text[-self.tail_length:]

        # 尝试从句号/省略号后开始，保持句子完整
        for marker in ["。", "...", "！", "？", "\n"]:
            idx = text.find(marker)
            if 0 < idx < len(text) - 1:
                text = text[idx + 1:].strip()
                break

        return text


# 模块级单例
_default_extractor: Optional[SceneStateExtractor] = None


def get_scene_extractor() -> SceneStateExtractor:
    """获取默认的场景状态提取器实例"""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = SceneStateExtractor()
    return _default_extractor


__all__ = [
    "SceneState",
    "SceneStateExtractor",
    "get_scene_extractor",
]
