"""
Markdown 标题分割 Mixin

为不同业务分割器提供统一的 split_by_markdown_headers 实现，避免两端复制“兼容方法”导致漂移。
"""

from __future__ import annotations

from typing import Any, List

from .content_splitter_utils import split_by_markdown_headers


class MarkdownHeaderSplitMixin:
    """为 splitter 提供按 Markdown 标题分割的通用实现。"""

    SECTION_FACTORY: Any = None

    def split_by_markdown_headers(
        self,
        content: str,
        min_level: int = 2,
        max_level: int = 3,
    ) -> List[Any]:
        """按 Markdown 标题分割内容（具体 Section 类型由 SECTION_FACTORY 决定）。"""
        if self.SECTION_FACTORY is None:
            raise ValueError("SECTION_FACTORY 未配置，无法执行 Markdown 标题分割")

        return split_by_markdown_headers(
            content=content,
            min_level=min_level,
            max_level=max_level,
            section_factory=self.SECTION_FACTORY,
        )


__all__ = ["MarkdownHeaderSplitMixin"]

