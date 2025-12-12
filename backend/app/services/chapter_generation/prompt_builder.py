"""
章节生成提示词构建器

负责构建章节写作的提示词，包括首次生成和重试两种模式。
"""

import json
from typing import Any, Dict, List, Optional

from ...models.novel import ChapterOutline


class ChapterPromptBuilder:
    """
    章节提示词构建器

    负责构建章节写作的提示词，支持两种模式：
    - 首次生成模式：包含完整前情摘要
    - 重试模式：简化版提示词

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
    ) -> str:
        """
        构建章节写作提示词（统一方法）

        支持两种模式：
        - 首次生成模式：传入completed_chapters，包含完整前情摘要
        - 重试模式：不传completed_chapters，使用简化版提示词

        Args:
            outline: 章节大纲
            blueprint_dict: 蓝图字典
            previous_summary_text: 上一章摘要
            previous_tail_excerpt: 上一章结尾
            rag_context: RAG检索上下文
            writing_notes: 写作备注
            chapter_number: 当前章节号（首次生成时用于构建分层摘要）
            completed_chapters: 已完成章节列表（None时为重试模式）

        Returns:
            str: 完整的写作提示词
        """
        outline_title = outline.title or f"第{outline.chapter_number}章"
        outline_summary = outline.summary or "暂无摘要"

        blueprint_text = json.dumps(blueprint_dict, ensure_ascii=False, indent=2)

        previous_summary_text = previous_summary_text or "暂无可用摘要"
        previous_tail_excerpt = previous_tail_excerpt or "暂无上一章结尾内容"

        # 处理RAG上下文
        rag_chunks_text = "未检索到章节片段"
        rag_summaries_text = "未检索到章节摘要"
        if rag_context:
            if rag_context.chunks:
                rag_chunks_text = "\n\n".join(rag_context.chunk_texts())
            if rag_context.summaries:
                rag_summaries_text = "\n".join(rag_context.summary_lines())

        writing_notes = writing_notes or "无额外写作指令"

        # 构建prompt_sections，根据是否有completed_chapters决定是否包含前情摘要
        prompt_sections = [("[世界蓝图](JSON)", blueprint_text)]

        # 首次生成模式：包含前情摘要
        if completed_chapters is not None:
            from ...utils.writer_helpers import build_layered_summary
            completed_section = build_layered_summary(completed_chapters, chapter_number)
            prompt_sections.append(("[前情摘要]", completed_section))

        # 公共部分
        prompt_sections.extend([
            ("[上一章摘要]", previous_summary_text),
            ("[上一章结尾]", previous_tail_excerpt),
            ("[检索到的剧情上下文](Markdown)", rag_chunks_text),
            ("[检索到的章节摘要]", rag_summaries_text),
            (
                "[当前章节目标]",
                f"标题：{outline_title}\n摘要：{outline_summary}\n写作要求：{writing_notes}",
            ),
        ])

        return "\n\n".join(f"{title}\n{content}" for title, content in prompt_sections if content)

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

        此方法是build_writing_prompt的简化调用，用于版本重试场景。
        """
        return self.build_writing_prompt(
            outline=outline,
            blueprint_dict=blueprint_dict,
            previous_summary_text=previous_summary_text,
            previous_tail_excerpt=previous_tail_excerpt,
            rag_context=rag_context,
            writing_notes=writing_notes,
            chapter_number=0,
            completed_chapters=None,  # None表示重试模式
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
