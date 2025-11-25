"""
写作相关的辅助函数

提供章节生成和管理过程中使用的工具函数。
"""

from typing import Dict, List, Optional


def extract_tail_excerpt(text: Optional[str], limit: int = 1000) -> str:
    """
    截取章节结尾文本，默认保留 1000 字。

    Args:
        text: 原始文本
        limit: 保留的字符数限制

    Returns:
        截取后的文本
    """
    if not text:
        return ""
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[-limit:]


def build_layered_summary(completed_chapters: List[Dict], current_chapter_number: int) -> str:
    """
    构建分层摘要：
    - 最近10章：完整摘要（每章50-100字）
    - 其余章节：超简摘要（每章1句话，约20字）

    这样既保证了完整的前情脉络，又控制了token消耗。

    Args:
        completed_chapters: 已完成章节列表
        current_chapter_number: 当前章节号

    Returns:
        分层摘要文本
    """
    if not completed_chapters:
        return "暂无前情摘要"

    recent_threshold = max(1, current_chapter_number - 10)
    recent_summaries = []
    old_summaries = []

    for ch in completed_chapters:
        chapter_num = ch['chapter_number']
        title = ch['title']
        summary = ch['summary']

        if chapter_num >= recent_threshold:
            # 最近10章：完整摘要
            recent_summaries.append(f"- 第{chapter_num}章《{title}》：{summary}")
        else:
            # 早期章节：只保留第一句话作为超简摘要
            brief = summary.split('。')[0] if summary else title
            if len(brief) > 30:
                brief = brief[:30] + '...'
            old_summaries.append(f"- 第{chapter_num}章：{brief}")

    result_parts = []
    if old_summaries:
        result_parts.append("【早期章节】\n" + "\n".join(old_summaries))
    if recent_summaries:
        result_parts.append("【最近章节（详细）】\n" + "\n".join(recent_summaries))

    return "\n\n".join(result_parts) if result_parts else "暂无前情摘要"
