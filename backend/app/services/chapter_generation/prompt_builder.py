"""
章节生成提示词构建器

负责构建章节写作的提示词，采用"场景聚焦"结构，
将信息按优先级组织为高密度的上下文。
"""

import json
from typing import Any, Dict, List, Optional

from ...models.novel import ChapterOutline
from ..rag.utils import format_character_positions
from ..rag.context_builder import GenerationContext
from ..rag.context_compressor import ContextCompressor
from ..rag.scene_extractor import SceneState


class ChapterPromptBuilder:
    """
    章节提示词构建器

    采用"场景聚焦"结构，分为以下层次：
    1. 核心设定：题材、风格、角色名单
    2. 当前任务：章节号、标题、大纲
    3. 场景状态：角色位置、未解悬念、上一章结尾
    4. 关键参考：涉及角色、待回收伏笔、相关段落

    使用方式：
        builder = ChapterPromptBuilder()
        prompt = builder.build_writing_prompt(...)
    """

    def build_writing_prompt(
        self,
        outline: ChapterOutline,
        blueprint_dict: Dict,
        previous_summary_text: str,
        previous_tail_excerpt: str,
        rag_context: Any,
        writing_notes: Optional[str],
        chapter_number: int = 0,
        completed_chapters: Optional[List[Dict]] = None,
        scene_state: Optional[SceneState] = None,
        generation_context: Optional[Any] = None,
    ) -> str:
        """
        构建章节写作提示词（场景聚焦结构）

        Args:
            outline: 章节大纲
            blueprint_dict: 蓝图字典
            previous_summary_text: 上一章摘要
            previous_tail_excerpt: 上一章结尾
            rag_context: RAG检索上下文
            writing_notes: 写作备注
            chapter_number: 当前章节号
            completed_chapters: 已完成章节列表（用于分层摘要）
            scene_state: 场景状态（新增）
            generation_context: 生成上下文（来自SmartContextBuilder）

        Returns:
            str: 完整的写作提示词
        """
        sections = []

        # === 第一部分：核心设定 ===
        sections.append(self._build_core_section(blueprint_dict))

        # === 第二部分：当前任务 ===
        sections.append(self._build_task_section(outline, writing_notes))

        # === 第三部分：场景状态 ===
        scene_section = self._build_scene_section(
            scene_state=scene_state,
            previous_tail_excerpt=previous_tail_excerpt,
            previous_summary_text=previous_summary_text,
            generation_context=generation_context,
        )
        if scene_section:
            sections.append(scene_section)

        # === 第四部分：关键参考 ===
        reference_section = self._build_reference_section(
            blueprint_dict=blueprint_dict,
            rag_context=rag_context,
            generation_context=generation_context,
            completed_chapters=completed_chapters,
            chapter_number=chapter_number,
        )
        if reference_section:
            sections.append(reference_section)

        return "\n\n".join(filter(None, sections))

    def _build_core_section(self, blueprint_dict: Dict) -> str:
        """
        构建核心设定部分

        只包含最关键的信息：题材、风格、基调、角色名单
        """
        lines = ["## 核心设定"]

        # 基本信息（单行）
        basics = []
        if blueprint_dict.get("genre"):
            basics.append(f"题材: {blueprint_dict['genre']}")
        if blueprint_dict.get("style"):
            basics.append(f"风格: {blueprint_dict['style']}")
        if blueprint_dict.get("tone"):
            basics.append(f"基调: {blueprint_dict['tone']}")
        if basics:
            lines.append(" | ".join(basics))

        # 一句话概括（如果有）
        if blueprint_dict.get("one_sentence_summary"):
            lines.append(f"故事: {blueprint_dict['one_sentence_summary']}")

        # 角色名单（只列名字，最重要的约束）
        characters = blueprint_dict.get("characters", [])
        if characters:
            names = [c.get("name", "") for c in characters if c.get("name")]
            if names:
                lines.append(f"角色名单: {', '.join(names)}")

        return "\n".join(lines)

    def _build_task_section(
        self,
        outline: ChapterOutline,
        writing_notes: Optional[str],
    ) -> str:
        """
        构建当前任务部分
        """
        outline_title = outline.title or f"第{outline.chapter_number}章"
        outline_summary = outline.summary or "暂无摘要"

        lines = [
            "## 当前任务",
            f"第{outline.chapter_number}章: {outline_title}",
            f"大纲: {outline_summary}",
        ]

        if writing_notes:
            lines.append(f"写作指令: {writing_notes}")

        return "\n".join(lines)

    def _build_scene_section(
        self,
        scene_state: Optional[SceneState],
        previous_tail_excerpt: str,
        previous_summary_text: str,
        generation_context: Optional[Any],
    ) -> str:
        """
        构建场景状态部分

        优先使用 SceneState，降级时使用原始数据
        """
        lines = ["## 场景状态"]
        has_content = False

        # 如果有场景状态对象，使用它
        if scene_state and not scene_state.is_empty():
            scene_text = scene_state.to_prompt_text()
            if scene_text:
                lines.append(scene_text)
                has_content = True
        else:
            # 降级：使用原始数据
            if previous_tail_excerpt:
                # 截取适当长度
                tail = previous_tail_excerpt.strip()
                if len(tail) > 500:
                    tail = tail[-500:]
                lines.append(f"上一章结尾:\n> {tail}")
                has_content = True

        # 从 generation_context 提取角色位置（如果有）
        if generation_context:
            prev_states = None
            if hasattr(generation_context, "important"):
                prev_states = generation_context.important.get("prev_character_states")
            elif isinstance(generation_context, dict):
                prev_states = generation_context.get("important", {}).get("prev_character_states")

            if prev_states:
                positions = format_character_positions(
                    prev_states,
                    max_items=5,
                )
                if positions:
                    lines.append(f"角色位置: {'; '.join(positions)}")
                    has_content = True

        # 上一章摘要（简化）
        if previous_summary_text and previous_summary_text != "暂无可用摘要":
            # 只保留前100字
            summary = previous_summary_text[:100]
            if len(previous_summary_text) > 100:
                summary += "..."
            lines.append(f"上一章摘要: {summary}")
            has_content = True

        return "\n".join(lines) if has_content else ""

    def _build_reference_section(
        self,
        blueprint_dict: Dict,
        rag_context: Any,
        generation_context: Optional[Any],
        completed_chapters: Optional[List[Dict]],
        chapter_number: int,
    ) -> str:
        """
        构建关键参考部分

        包含：涉及角色详情、主角档案约束、待回收伏笔、相关段落、前情摘要
        """
        lines: List[str] = []
        has_content = False

        reference_text = self._format_reference_layers_from_context(
            blueprint_dict=blueprint_dict,
            rag_context=rag_context,
            generation_context=generation_context,
        )
        if reference_text:
            lines.append(reference_text)
            has_content = True

        # 主角档案约束（从 generation_context 获取）
        protagonist_section = self._format_protagonist_profiles(generation_context)
        if protagonist_section:
            if not reference_text:
                lines.append("## 关键参考")
            lines.append(protagonist_section)
            has_content = True

        # 前情摘要（仅首次生成时）
        if completed_chapters:
            from ...utils.writer_helpers import build_layered_summary
            summary_text = build_layered_summary(completed_chapters, chapter_number)
            if summary_text and summary_text != "暂无前情摘要":
                if not reference_text and not protagonist_section:
                    lines.append("## 关键参考")
                lines.append("### 前情摘要")
                lines.append(summary_text)
                has_content = True

        return "\n".join(lines) if has_content else ""

    def _format_reference_layers_from_context(
        self,
        blueprint_dict: Dict,
        rag_context: Any,
        generation_context: Optional[Any],
    ) -> str:
        """基于生成上下文格式化关键参考内容"""
        important: Dict[str, Any] = {}
        reference: Dict[str, Any] = {}

        if isinstance(generation_context, GenerationContext):
            important = dict(generation_context.important or {})
            reference = dict(generation_context.reference or {})
        elif isinstance(generation_context, dict):
            important = dict(generation_context.get("important", {}) or {})
            reference = dict(generation_context.get("reference", {}) or {})

        if rag_context:
            if not important.get("relevant_summaries"):
                summaries = self._extract_relevant_summaries(rag_context)
                if summaries:
                    important["relevant_summaries"] = summaries
            if not reference.get("relevant_passages"):
                passages = self._extract_relevant_passages(rag_context)
                if passages:
                    reference["relevant_passages"] = passages

        if not important.get("involved_characters"):
            important["involved_characters"] = self._get_involved_characters(
                blueprint_dict,
                generation_context,
            )

        if not important.get("high_priority_foreshadowing"):
            important["high_priority_foreshadowing"] = self._get_foreshadowing(
                generation_context,
            )

        if not any(important.values()) and not any(reference.values()):
            return ""

        context = GenerationContext(
            important=important,
            reference=reference,
        )

        compressor = ContextCompressor(max_context_tokens=10000)
        return compressor.format_reference_layers(context, include_reference=True)

    def _extract_relevant_summaries(self, rag_context: Any) -> List[Dict[str, Any]]:
        """从RAG上下文提取摘要列表，供压缩器统一格式化"""
        summaries: List[Dict[str, Any]] = []
        if hasattr(rag_context, "summaries") and rag_context.summaries:
            for summary in rag_context.summaries[:3]:
                if hasattr(summary, "chapter_number"):
                    summaries.append({
                        "chapter": summary.chapter_number,
                        "title": getattr(summary, "title", ""),
                        "summary": getattr(summary, "summary", ""),
                    })
        return summaries

    def _extract_relevant_passages(self, rag_context: Any) -> List[Dict[str, Any]]:
        """从RAG上下文提取段落列表，供压缩器统一格式化"""
        passages: List[Dict[str, Any]] = []
        if hasattr(rag_context, "chunks") and rag_context.chunks:
            for chunk in rag_context.chunks[:3]:
                if hasattr(chunk, "chapter_number") and hasattr(chunk, "content"):
                    passages.append({
                        "chapter": chunk.chapter_number,
                        "title": getattr(chunk, "chapter_title", None),
                        "content": getattr(chunk, "content", ""),
                    })
        return passages

    def _format_protagonist_profiles(self, generation_context: Optional[Any]) -> str:
        """
        格式化主角档案信息为提示词文本

        从 generation_context 中提取主角档案，格式化为约束信息。
        帮助LLM保持角色行为的一致性。

        Args:
            generation_context: 生成上下文（包含protagonist_profiles）

        Returns:
            str: 格式化的主角档案文本，无档案时返回空字符串
        """
        if not generation_context:
            return ""

        # 获取主角档案列表
        profiles = None
        if hasattr(generation_context, "protagonist_profiles"):
            profiles = generation_context.protagonist_profiles
        elif isinstance(generation_context, dict):
            profiles = generation_context.get("protagonist_profiles")

        if not profiles:
            return ""

        lines = ["### 主角档案约束", "请确保角色行为与以下档案设定保持一致："]

        for profile in profiles[:3]:  # 最多3个主角
            name = profile.get("name", "未知")
            lines.append(f"\n**{name}**:")

            # 显性属性（外貌、装备等可观察特征）
            if explicit := profile.get("explicit"):
                if isinstance(explicit, dict) and explicit:
                    attrs = ", ".join(
                        f"{k}: {self._truncate_value(v)}"
                        for k, v in list(explicit.items())[:5]
                    )
                    lines.append(f"  - 显性特征: {attrs}")

            # 隐性属性（性格、习惯等内在特质）
            if implicit := profile.get("implicit"):
                if isinstance(implicit, dict) and implicit:
                    attrs = ", ".join(
                        f"{k}: {self._truncate_value(v)}"
                        for k, v in list(implicit.items())[:3]
                    )
                    lines.append(f"  - 性格特质: {attrs}")

            # 社会属性（关系、地位等社交特征）
            if social := profile.get("social"):
                if isinstance(social, dict) and social:
                    attrs = ", ".join(
                        f"{k}: {self._truncate_value(v)}"
                        for k, v in list(social.items())[:3]
                    )
                    lines.append(f"  - 社会关系: {attrs}")

        return "\n".join(lines)

    def _truncate_value(self, value: Any, max_length: int = 30) -> str:
        """截断属性值为合适长度的字符串"""
        if isinstance(value, str):
            return value[:max_length] + "..." if len(value) > max_length else value
        elif isinstance(value, list):
            return ", ".join(str(v)[:15] for v in value[:3])
        elif isinstance(value, dict):
            return str(value)[:max_length] + "..."
        else:
            return str(value)[:max_length]

    def _get_involved_characters(
        self,
        blueprint_dict: Dict,
        generation_context: Optional[Any],
    ) -> List[Dict]:
        """
        获取涉及角色列表

        优先从 generation_context 获取，否则返回前几个角色
        """
        # 尝试从 generation_context 获取
        if generation_context:
            involved = None
            if hasattr(generation_context, "important"):
                involved = generation_context.important.get("involved_characters")
            elif isinstance(generation_context, dict):
                involved = generation_context.get("important", {}).get("involved_characters")
            if involved:
                return involved

        # 降级：返回前5个角色
        characters = blueprint_dict.get("characters", [])
        return characters[:5]

    def _get_foreshadowing(self, generation_context: Optional[Any]) -> List[Dict]:
        """
        获取待回收伏笔

        从 generation_context 的 important 层获取高优先级伏笔
        """
        if not generation_context:
            return []

        foreshadowing = None
        if hasattr(generation_context, "important"):
            foreshadowing = generation_context.important.get("high_priority_foreshadowing")
        elif isinstance(generation_context, dict):
            foreshadowing = generation_context.get("important", {}).get("high_priority_foreshadowing")

        return foreshadowing or []


    def build_retry_prompt(
        self,
        outline: ChapterOutline,
        blueprint_dict: Dict,
        previous_summary_text: str,
        previous_tail_excerpt: str,
        rag_context: Any,
        writing_notes: Optional[str],
    ) -> str:
        """
        构建章节重试提示词（简化版，不包含完整前情摘要）

        此方法用于版本重试场景。
        """
        return self.build_writing_prompt(
            outline=outline,
            blueprint_dict=blueprint_dict,
            previous_summary_text=previous_summary_text,
            previous_tail_excerpt=previous_tail_excerpt,
            rag_context=rag_context,
            writing_notes=writing_notes,
            chapter_number=0,
            completed_chapters=None,  # None表示重试模式，不包含前情摘要
        )


# 模块级单例（可选）
_default_builder: Optional[ChapterPromptBuilder] = None


def get_chapter_prompt_builder() -> ChapterPromptBuilder:
    """获取默认的章节提示词构建器实例"""
    global _default_builder
    if _default_builder is None:
        _default_builder = ChapterPromptBuilder()
    return _default_builder


__all__ = [
    "ChapterPromptBuilder",
    "get_chapter_prompt_builder",
]
