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


def format_rag_chunk_line(
    chapter_number: Any,
    title: Optional[str],
    content: str,
    max_content_length: int = 200,
) -> str:
    """
    格式化RAG片段行

    Args:
        chapter_number: 章节号
        title: 章节标题（可选）
        content: 片段内容
        max_content_length: 最大内容长度
    """
    display_title = title or f"第{chapter_number}章"
    truncated = truncate_text(content, max_content_length)
    return f"[{display_title}] {truncated}"


def format_rag_summary_line(
    chapter_number: Any,
    title: Optional[str],
    summary: str,
    max_summary_length: int = 100,
) -> str:
    """
    格式化RAG摘要行

    Args:
        chapter_number: 章节号
        title: 章节标题（可选）
        summary: 摘要文本
        max_summary_length: 摘要最大长度
    """
    display_title = title or f"第{chapter_number}章"
    truncated = truncate_text(summary, max_summary_length)
    return f"[{display_title}摘要] {truncated}"


def format_foreshadowing_lines(
    foreshadowing: List[Dict[str, Any]],
    *,
    max_items: int = 3,
    description_limit: int = 60,
    add_ellipsis: bool = True,
    use_priority_marker: bool = False,
    marker_for_high: str = "[重要]",
    default_marker: str = "[重要]",
    description_key: str = "description",
    fallback_key: Optional[str] = None,
) -> List[str]:
    """
    格式化伏笔列表为文本行

    Args:
        foreshadowing: 伏笔列表
        max_items: 最多输出条数
        description_limit: 描述截断长度
        add_ellipsis: 是否在截断时添加省略号
        use_priority_marker: 是否根据 priority 输出标记
        marker_for_high: high 优先级标记
        default_marker: 默认标记（priority 非 high 时使用）
        description_key: 描述字段
        fallback_key: 描述缺失时的回退字段
    """
    if not foreshadowing:
        return []

    lines = []
    for fs in foreshadowing[:max_items]:
        desc = fs.get(description_key, "")
        if not desc and fallback_key:
            desc = fs.get(fallback_key, "")
        if not desc:
            continue

        if description_limit > 0 and len(desc) > description_limit:
            if add_ellipsis:
                desc = desc[:max(description_limit - 3, 0)] + "..."
            else:
                desc = desc[:description_limit]

        marker = default_marker
        if use_priority_marker:
            priority = fs.get("priority", "medium")
            marker = marker_for_high if priority == "high" else default_marker

        lines.append(f"- {marker} {desc}")

    return lines


def format_character_lines(
    characters: List[Dict[str, Any]],
    *,
    max_items: int = 3,
    default_name: str = "",
    identity_key: str = "identity",
    personality_key: str = "personality",
    personality_limit: int = 30,
    add_ellipsis: bool = True,
) -> List[str]:
    """
    格式化涉及角色列表

    Args:
        characters: 角色列表
        max_items: 最多输出条数
        default_name: 角色名缺失时的默认值
        identity_key: 身份字段
        personality_key: 性格字段
        personality_limit: 性格描述最大长度
        add_ellipsis: 截断时是否追加省略号
    """
    if not characters:
        return []

    lines: List[str] = []
    for char in characters[:max_items]:
        name = char.get("name", default_name)
        identity = char.get(identity_key, "")
        line = f"- {name}"
        if identity:
            line += f" ({identity})"

        personality = char.get(personality_key, "")
        if personality:
            if personality_limit > 0 and len(personality) > personality_limit:
                if add_ellipsis:
                    personality = personality[:max(personality_limit - 3, 0)] + "..."
                else:
                    personality = personality[:personality_limit]
            line += f": {personality}"
        lines.append(line)

    return lines


def format_character_state_lines(
    states: Dict[str, Any],
    *,
    max_items: int = 4,
    status_limit: int = 20,
    add_ellipsis: bool = True,
) -> List[str]:
    """
    格式化角色状态列表

    Args:
        states: 角色状态字典
        max_items: 最多输出条数
        status_limit: 状态描述最大长度
        add_ellipsis: 截断时是否追加省略号
    """
    if not states:
        return []

    lines: List[str] = []
    for name, state in list(states.items())[:max_items]:
        parts = [name]
        if isinstance(state, dict):
            if state.get("location"):
                parts.append(f"在{state['location']}")
            if state.get("status"):
                status = state["status"]
                if status_limit > 0 and len(status) > status_limit:
                    if add_ellipsis:
                        status = status[:max(status_limit - 3, 0)] + "..."
                    else:
                        status = status[:status_limit]
                parts.append(status)
        lines.append(f"- {' '.join(parts)}")

    return lines


def format_character_positions(
    states: Dict[str, Any],
    *,
    max_items: int = 5,
) -> List[str]:
    """
    格式化角色位置列表

    Args:
        states: 角色状态字典
        max_items: 最多输出条数
    """
    if not states:
        return []

    positions: List[str] = []
    for name, state in list(states.items())[:max_items]:
        if isinstance(state, dict) and state.get("location"):
            positions.append(f"{name}在{state['location']}")
    return positions


__all__ = [
    "extract_involved_characters",
    "truncate_text",
    "build_outline_text",
    "format_chapter_reference",
    "format_rag_chunk_line",
    "format_rag_summary_line",
    "format_foreshadowing_lines",
    "format_character_lines",
    "format_character_state_lines",
    "format_character_positions",
]
