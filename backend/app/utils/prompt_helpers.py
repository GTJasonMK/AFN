"""
提示词辅助工具

提供提示词相关的通用工具函数。
"""

import json
from typing import Any, Iterable

from ..exceptions import PromptTemplateNotFoundError


def ensure_prompt(prompt: str | None, name: str) -> str:
    """
    确保提示词存在，否则抛出异常

    Args:
        prompt: 提示词内容（可能为None）
        name: 提示词名称（用于错误消息）

    Returns:
        str: 非空的提示词内容

    Raises:
        PromptTemplateNotFoundError: 当提示词为空时
    """
    if not prompt:
        raise PromptTemplateNotFoundError(name)
    return prompt


def format_prompt_json(data: Any) -> str:
    """格式化提示词中的JSON块（统一缩进与编码）"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def join_prompt_lines(lines: Iterable[str]) -> str:
    """拼接提示词行，过滤空行"""
    return "\n".join([line for line in lines if line])


def build_prompt_section(title: str, content: str | Iterable[str], level: int = 2) -> str:
    """构建带标题的提示词片段（默认二级标题）"""
    if isinstance(content, str):
        content_text = content.strip()
    else:
        content_text = join_prompt_lines(content).strip()

    if not content_text:
        return ""

    prefix = "#" * max(level, 1)
    return f"{prefix} {title}\n{content_text}"


def build_prompt_block(title: str, sections: Iterable[str]) -> str:
    """构建包含多个子段落的提示词块（保持原有空行格式）"""
    parts = [section for section in sections if section]
    if not parts:
        return ""

    return "\n\n## " + title + "\n\n" + "\n\n".join(parts)
