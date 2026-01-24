"""
Markdown标题分割工具

提供通用的Markdown标题分割逻辑，供不同RAG分割器复用。
"""

import re
from typing import Callable, List


def split_markdown_sections(
    content: str,
    min_level: int,
    max_level: int,
    section_factory: Callable[..., any],
) -> List[any]:
    """
    按Markdown标题分割内容

    Args:
        content: 原始Markdown内容
        min_level: 最小标题级别（2 = ##）
        max_level: 最大标题级别（3 = ###）
        section_factory: Section 构造器，需支持 title/content/index/level 参数

    Returns:
        分割后的Section列表
    """
    if not content or not content.strip():
        return []

    header_pattern = r'^(#{' + str(min_level) + ',' + str(max_level) + r'})\s+(.+)$'
    lines = content.split('\n')

    sections: List[any] = []
    current_title = ""
    current_level = min_level
    current_lines: List[str] = []
    section_index = 0

    for line in lines:
        match = re.match(header_pattern, line)
        if match:
            if current_lines:
                section_content = '\n'.join(current_lines).strip()
                if section_content:
                    sections.append(section_factory(
                        title=current_title,
                        content=section_content,
                        index=section_index,
                        level=current_level
                    ))
                    section_index += 1

            current_level = len(match.group(1))
            current_title = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        section_content = '\n'.join(current_lines).strip()
        if section_content:
            sections.append(section_factory(
                title=current_title,
                content=section_content,
                index=section_index,
                level=current_level
            ))

    return sections


__all__ = ["split_markdown_sections"]
