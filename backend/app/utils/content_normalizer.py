"""
内容标准化工具模块

提供各种格式的内容转换为标准文本的工具函数。
用于处理LLM返回的不规则JSON、混合格式等内容。
"""

import json
from typing import Any, Optional

# 优先尝试的内容字段名（按优先级排序）
_PREFERRED_CONTENT_KEYS: tuple[str, ...] = (
    "content",
    "chapter_content",
    "chapter_text",
    "full_content",
    "text",
    "body",
    "story",
    "chapter",
    "real_summary",
    "summary",
)


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
    text = _coerce_text(metadata)
    if not text:
        text = _coerce_text(raw_content)
    return text or ""


def _coerce_text(value: Any) -> Optional[str]:
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
            if key in value and value[key]:
                nested = _coerce_text(value[key])
                if nested:
                    return nested
        # 如果没有找到优先字段，序列化整个字典
        return _clean_string(json.dumps(value, ensure_ascii=False))

    if isinstance(value, (list, tuple, set)):
        # 递归处理集合中的每个元素
        parts = [text for text in (_coerce_text(item) for item in value) if text]
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
            coerced = _coerce_text(parsed)
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
