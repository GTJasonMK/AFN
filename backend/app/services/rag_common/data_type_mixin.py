"""
RAG 数据类型枚举通用 Mixin

将“权重/显示名/来源表”三类映射读取模板集中维护，避免 Coding/Novel 两套枚举并行维护导致漂移。
"""

from __future__ import annotations

from typing import Dict


class RAGDataTypeMixin:
    """为 RAG DataType 枚举提供通用映射读取方法。"""

    WEIGHTS: Dict[str, float] = {}
    DISPLAY_NAMES: Dict[str, str] = {}
    SOURCE_TABLES: Dict[str, str] = {}

    DEFAULT_WEIGHT: float = 0.5
    DEFAULT_SOURCE_TABLE: str = "unknown"

    @classmethod
    def get_weight(cls, data_type: str) -> float:
        """获取数据类型的检索权重（默认 0.5）。"""
        return cls.WEIGHTS.get(data_type, cls.DEFAULT_WEIGHT)

    @classmethod
    def get_display_name(cls, data_type: str) -> str:
        """获取数据类型的中文显示名称（默认回退到 data_type）。"""
        return cls.DISPLAY_NAMES.get(data_type, data_type)

    @classmethod
    def get_source_table(cls, data_type: str) -> str:
        """获取数据类型对应的数据库表名（默认 unknown）。"""
        return cls.SOURCE_TABLES.get(data_type, cls.DEFAULT_SOURCE_TABLE)


__all__ = ["RAGDataTypeMixin"]

