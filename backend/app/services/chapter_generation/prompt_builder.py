"""
章节生成提示词构建器

负责构建章节写作的提示词，采用"场景聚焦"结构，
将信息按优先级组织为高密度的上下文。
"""

import json
from typing import Any, Dict, List, Optional

from ...models.novel import ChapterOutline
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
                positions = []
                for name, state in prev_states.items():
                    if isinstance(state, dict) and state.get("location"):
                        positions.append(f"{name}在{state['location']}")
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

        包含：涉及角色详情、待回收伏笔、相关段落、前情摘要
        """
        lines = ["## 关键参考"]
        has_content = False

        # 1. 涉及角色详情（从 generation_context 获取）
        involved_chars = self._get_involved_characters(blueprint_dict, generation_context)
        if involved_chars:
            lines.append("### 涉及角色")
            for char in involved_chars[:5]:  # 最多5个
                char_line = f"- {char.get('name', '未知')}"
                if char.get("identity"):
                    char_line += f" ({char['identity']})"
                if char.get("personality"):
                    char_line += f": {char['personality'][:50]}"
                lines.append(char_line)
            has_content = True

        # 2. 待回收伏笔（从 generation_context 获取）
        foreshadowing = self._get_foreshadowing(generation_context)
        if foreshadowing:
            lines.append("### 待回收伏笔")
            for fs in foreshadowing[:3]:  # 最多3个
                priority = fs.get("priority", "medium")
                marker = "[重要]" if priority == "high" else ""
                description = fs.get("description", fs.get("hint", ""))
                if description:
                    lines.append(f"- {marker} {description[:80]}")
            has_content = True

        # 3. 相关段落（RAG检索结果）
        rag_text = self._format_rag_context(rag_context)
        if rag_text:
            lines.append("### 相关段落")
            lines.append(rag_text)
            has_content = True

        # 4. 前情摘要（仅首次生成时）
        if completed_chapters:
            from ...utils.writer_helpers import build_layered_summary
            summary_text = build_layered_summary(completed_chapters, chapter_number)
            if summary_text and summary_text != "暂无前情摘要":
                lines.append("### 前情摘要")
                lines.append(summary_text)
                has_content = True

        return "\n".join(lines) if has_content else ""

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

    def _format_rag_context(self, rag_context: Any) -> str:
        """
        格式化RAG上下文

        将检索到的chunks和summaries格式化为简洁的文本
        """
        if not rag_context:
            return ""

        parts = []

        # 处理chunks
        if hasattr(rag_context, "chunks") and rag_context.chunks:
            for chunk in rag_context.chunks[:3]:  # 最多3个片段
                if hasattr(chunk, "chapter_number") and hasattr(chunk, "content"):
                    title = getattr(chunk, "chapter_title", f"第{chunk.chapter_number}章")
                    content = chunk.content[:200]  # 截断
                    if len(chunk.content) > 200:
                        content += "..."
                    parts.append(f"[{title}] {content}")

        # 处理summaries
        if hasattr(rag_context, "summaries") and rag_context.summaries:
            for summary in rag_context.summaries[:2]:  # 最多2个摘要
                if hasattr(summary, "chapter_number"):
                    title = getattr(summary, "title", f"第{summary.chapter_number}章")
                    text = getattr(summary, "summary", "")[:100]
                    parts.append(f"[{title}摘要] {text}")

        return "\n".join(parts) if parts else ""

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
