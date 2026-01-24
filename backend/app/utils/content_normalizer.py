"""
内容标准化工具模块

提供各种格式的内容转换为标准文本的工具函数。
用于处理LLM返回的不规则JSON、混合格式等内容。
"""

import json
import logging
import re
from typing import Any, Optional

from .content_fields import CONTENT_FIELD_NAMES

logger = logging.getLogger(__name__)

# 优先尝试的内容字段名（按优先级排序）
_PREFERRED_CONTENT_KEYS: tuple[str, ...] = CONTENT_FIELD_NAMES


def normalize_version_content(raw_content: Any, metadata: Any) -> str:
    """
    标准化版本内容为文本字符串

    优先从metadata中提取内容，如果失败则从raw_content中提取。
    支持多种数据格式：字符串、字典、列表等。

    Args:
        raw_content: 原始内容（可能是任意类型）
        metadata: 元数据（可能包含结构化的内容字段）

    Returns:
        标准化后的文本字符串

    Example:
        ```python
        # 情况1：metadata中有content字段
        result = normalize_version_content(
            raw_content="...",
            metadata={"content": "正文内容"}
        )  # 返回: "正文内容"

        # 情况2：只有raw_content
        result = normalize_version_content(
            raw_content={"chapter_text": "正文"},
            metadata=None
        )  # 返回: "正文"
        ```
    """
    logger.info("[DEBUG] normalize_version_content - raw_content类型=%s, metadata类型=%s",
                type(raw_content).__name__, type(metadata).__name__)
    if isinstance(metadata, dict):
        logger.info("[DEBUG] normalize_version_content - metadata键=%s", list(metadata.keys()))

    text = _coerce_text(metadata, "metadata")
    if not text:
        text = _coerce_text(raw_content, "raw_content")

    logger.info("[DEBUG] normalize_version_content - 最终结果前200字符=%s",
                repr(text[:200]) if text else "EMPTY")
    return text or ""


def _coerce_text(value: Any, source: str = "") -> Optional[str]:
    """
    强制将任意类型的值转换为文本

    处理策略：
    1. None → None
    2. 字符串 → 清理后返回
    3. 数字 → 转字符串
    4. 字典 → 尝试提取优先字段，失败则JSON序列化
    5. 列表/元组/集合 → 递归处理每个元素，用换行拼接
    6. 其他类型 → str()转换

    Args:
        value: 任意类型的值
        source: 调试用来源标识

    Returns:
        转换后的文本，如果无法提取有效内容则返回None
    """
    if value is None:
        return None

    if isinstance(value, str):
        return _clean_string(value)

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, dict):
        # 尝试按优先级提取内容字段
        for key in _PREFERRED_CONTENT_KEYS:
            # 使用 'key in value' 检查键存在，然后检查值不是 None
            # 注意：空字符串 "" 在布尔上下文中是 False，但我们仍然要处理它
            if key in value:
                field_value = value[key]
                # 只跳过 None，允许空字符串通过（虽然空字符串会在后面被过滤）
                if field_value is not None:
                    logger.info("[DEBUG] _coerce_text(%s) - 找到字段 '%s', 类型=%s",
                                source, key, type(field_value).__name__)
                    nested = _coerce_text(field_value, f"{source}.{key}")
                    if nested:
                        logger.info("[DEBUG] _coerce_text(%s) - 从字段 '%s' 提取成功，长度=%d",
                                    source, key, len(nested))
                        return nested
                    else:
                        logger.info("[DEBUG] _coerce_text(%s) - 字段 '%s' 提取结果为空，继续检查下一个字段",
                                    source, key)
        # 如果没有找到优先字段，序列化整个字典
        logger.warning("[DEBUG] _coerce_text(%s) - 未找到优先字段，将返回JSON序列化。键=%s",
                       source, list(value.keys()))
        return _clean_string(json.dumps(value, ensure_ascii=False))

    if isinstance(value, (list, tuple, set)):
        # 递归处理集合中的每个元素
        parts = [text for text in (_coerce_text(item, f"{source}[item]") for item in value) if text]
        if parts:
            return "\n".join(parts)
        return None

    # 其他类型直接转字符串
    return _clean_string(str(value))


def _clean_string(text: str) -> str:
    """
    清理字符串中的特殊格式

    处理：
    1. 去除首尾空白
    2. 尝试解析JSON包装的字符串
    3. 去除多余的引号
    4. 还原转义字符（\\n → 换行）

    Args:
        text: 待清理的字符串

    Returns:
        清理后的字符串
    """
    stripped = text.strip()
    if not stripped:
        return stripped

    # 如果整个字符串是JSON对象，尝试解析
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
            coerced = _coerce_text(parsed, "_clean_string.parsed")
            if coerced:
                return coerced
        except json.JSONDecodeError:
            pass

    # 去除外层引号
    if stripped.startswith('"') and stripped.endswith('"') and len(stripped) >= 2:
        stripped = stripped[1:-1]

    # 还原常见的转义字符
    return (
        stripped.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def count_chinese_characters(text: str) -> int:
    """
    统计文本中的中文字符数量（只统计汉字，不包括标点、英文、空格等）

    这是用于章节字数统计的标准函数，确保前后端字数一致。

    Args:
        text: 要统计的文本内容

    Returns:
        中文汉字数量
    """
    if not text:
        return 0
    # 统计Unicode范围 U+4E00 到 U+9FFF 的汉字（CJK统一汉字基本区）
    # 这与前端 frontend/utils/formatters.py 中的 count_chinese_characters 保持一致
    return len([c for c in text if '\u4e00' <= c <= '\u9fff'])
