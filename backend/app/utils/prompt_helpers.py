"""
提示词辅助工具

提供提示词相关的通用工具函数。
"""

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
