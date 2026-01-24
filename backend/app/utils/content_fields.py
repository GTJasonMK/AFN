"""
LLM 内容字段别名常量（按优先级排序）

用途：
- 统一从 LLM 返回的 dict/JSON 中提取“正文内容”的字段名集合，避免多处重复维护。
"""

from __future__ import annotations


# full_content 应该排在最前面，因为它明确表示“完整内容”
CONTENT_FIELD_NAMES: tuple[str, ...] = (
    "full_content",
    "chapter_content",
    "content",
    "chapter_text",
    "text",
    "body",
    "story",
    "chapter",
    "output",
    "result",
    "response",
)

