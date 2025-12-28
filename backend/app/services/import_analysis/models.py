"""
导入分析数据结构

定义导入分析相关的数据类型。
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ChapterSummary:
    """章节摘要"""
    chapter_number: int
    title: str
    summary: str
    key_characters: List[str]
    key_events: List[str]


@dataclass
class ImportResult:
    """导入结果"""
    total_chapters: int
    chapters: List[Dict[str, Any]]
    parse_info: Dict[str, Any]


__all__ = [
    "ChapterSummary",
    "ImportResult",
]
