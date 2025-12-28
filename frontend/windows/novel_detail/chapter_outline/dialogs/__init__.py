"""
章节大纲对话框模块

提供章节大纲使用的各类对话框：
- PartOutlineDetailDialog: 部分大纲详情对话框
- ChapterOutlineDetailDialog: 章节大纲详情对话框
- ChapterOutlineEditDialog: 章节大纲编辑对话框
"""

from .part_detail_dialog import PartOutlineDetailDialog
from .chapter_detail_dialog import ChapterOutlineDetailDialog
from .chapter_edit_dialog import ChapterOutlineEditDialog

__all__ = [
    "PartOutlineDetailDialog",
    "ChapterOutlineDetailDialog",
    "ChapterOutlineEditDialog",
]
