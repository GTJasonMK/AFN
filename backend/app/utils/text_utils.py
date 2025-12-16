"""
文本处理工具

提供文本截断、预览生成等通用功能。
统一项目中的文本截断逻辑，避免重复代码。
"""

from typing import Optional


def truncate(
    text: Optional[str],
    max_length: int,
    suffix: str = "...",
    strip: bool = True,
) -> str:
    """
    截断文本到指定长度

    Args:
        text: 原始文本，None 会返回空字符串
        max_length: 最大长度（不含后缀）
        suffix: 截断后缀，默认 "..."
        strip: 是否去除首尾空白，默认 True

    Returns:
        截断后的文本

    Examples:
        >>> truncate("Hello World", 5)
        'Hello...'
        >>> truncate("Hi", 5)
        'Hi'
        >>> truncate(None, 10)
        ''
    """
    if not text:
        return ""

    if strip:
        text = text.strip()

    if len(text) <= max_length:
        return text

    return text[:max_length] + suffix


def truncate_preview(
    text: Optional[str],
    max_length: int = 100,
) -> str:
    """
    生成文本预览（专用于UI展示）

    总是使用 "..." 作为后缀，适合用于日志、UI预览等场景。

    Args:
        text: 原始文本
        max_length: 最大长度，默认 100

    Returns:
        预览文本

    Examples:
        >>> truncate_preview("这是一段很长的文本...", 10)
        '这是一段很长的文...'
    """
    return truncate(text, max_length, suffix="...")


def truncate_middle(
    text: Optional[str],
    max_length: int,
    separator: str = "...",
) -> str:
    """
    中间截断，保留首尾

    适用于文件路径、长标识符等场景。

    Args:
        text: 原始文本
        max_length: 最大长度（含分隔符）
        separator: 中间分隔符，默认 "..."

    Returns:
        截断后的文本

    Examples:
        >>> truncate_middle("abcdefghij", 7)
        'ab...ij'
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    sep_len = len(separator)
    if max_length <= sep_len:
        return separator[:max_length]

    available = max_length - sep_len
    head_len = (available + 1) // 2  # 首部稍多
    tail_len = available - head_len

    return text[:head_len] + separator + text[-tail_len:]


def mask_sensitive(
    text: Optional[str],
    visible_prefix: int = 4,
    visible_suffix: int = 4,
    mask_char: str = "*",
) -> str:
    """
    敏感信息脱敏

    用于API密钥、密码等敏感信息的安全显示。

    Args:
        text: 原始文本
        visible_prefix: 可见前缀长度，默认 4
        visible_suffix: 可见后缀长度，默认 4
        mask_char: 掩码字符，默认 "*"

    Returns:
        脱敏后的文本

    Examples:
        >>> mask_sensitive("sk-1234567890abcdef")
        'sk-1************cdef'
    """
    if not text:
        return ""

    text_len = len(text)
    min_length = visible_prefix + visible_suffix + 4  # 至少4个掩码字符

    if text_len <= min_length:
        # 太短，只显示前后各2个字符
        if text_len <= 4:
            return mask_char * text_len
        return text[:2] + mask_char * (text_len - 4) + text[-2:]

    mask_length = text_len - visible_prefix - visible_suffix
    return text[:visible_prefix] + mask_char * mask_length + text[-visible_suffix:]


def safe_slice(
    text: Optional[str],
    start: int = 0,
    end: Optional[int] = None,
) -> str:
    """
    安全的字符串切片

    避免 None 值和边界问题。

    Args:
        text: 原始文本
        start: 起始位置
        end: 结束位置（不含）

    Returns:
        切片结果
    """
    if not text:
        return ""

    if end is None:
        return text[start:]

    return text[start:end]
