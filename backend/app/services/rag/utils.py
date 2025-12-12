"""
RAG模块公共工具函数

提供RAG检索相关的通用工具函数，消除模块间的代码重复。
"""

from typing import Any, Dict, List, Optional


def extract_involved_characters(
    outline: Dict[str, Any],
    blueprint_characters: List[Dict[str, Any]],
    include_details: bool = False,
) -> List[Dict[str, Any]]:
    """
    从大纲中提取涉及的角色

    通过匹配角色名称在大纲文本中出现来确定涉及的角色。

    Args:
        outline: 章节大纲 {"title": str, "summary": str, ...}
        blueprint_characters: 蓝图角色列表 [{"name": str, "identity": str, ...}]
        include_details: 是否包含角色详细信息（identity, personality, goals）

    Returns:
        涉及角色列表
    """
    # 组合大纲文本
    outline_text = " ".join([
        outline.get("title", ""),
        outline.get("summary", ""),
    ])

    involved = []
    for char in blueprint_characters:
        char_name = char.get("name", "")
        if char_name and char_name in outline_text:
            if include_details:
                # 返回详细信息（用于上下文构建）
                involved.append({
                    "name": char_name,
                    "identity": char.get("identity", ""),
                    "personality": char.get("personality", ""),
                    "goals": char.get("goals", ""),
                })
            else:
                # 返回完整角色数据（用于查询构建）
                involved.append(char)

    return involved


def truncate_text(
    text: str,
    max_length: int,
    suffix: str = "...",
) -> str:
    """
    截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后的后缀（默认"..."）

    Returns:
        截断后的文本
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    # 确保后缀长度不超过max_length
    suffix_len = len(suffix)
    if suffix_len >= max_length:
        return text[:max_length]
    return text[:max_length - suffix_len] + suffix


def build_outline_text(outline: Dict[str, Any]) -> str:
    """
    构建大纲文本（用于检索和匹配）

    Args:
        outline: 章节大纲字典

    Returns:
        合并后的大纲文本
    """
    parts = []
    if title := outline.get("title"):
        parts.append(title)
    if summary := outline.get("summary"):
        parts.append(summary)
    return " ".join(parts)


def format_chapter_reference(
    chapter_number: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    max_content_length: int = 200,
) -> str:
    """
    格式化章节引用文本

    Args:
        chapter_number: 章节号
        title: 章节标题（可选）
        content: 章节内容（可选）
        max_content_length: 内容最大长度

    Returns:
        格式化的章节引用
    """
    if title:
        header = f"[第{chapter_number}章《{title}》]"
    else:
        header = f"[第{chapter_number}章]"

    if content:
        truncated = truncate_text(content, max_content_length)
        return f"{header} {truncated}"

    return header


__all__ = [
    "extract_involved_characters",
    "truncate_text",
    "build_outline_text",
    "format_chapter_reference",
]
