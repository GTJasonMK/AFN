"""
章节大纲模块

提供章节大纲相关的UI组件
"""

from .main import ChapterOutlineSection
from .outline_row import OutlineRow
from .outline_list import OutlineListView
from .action_bar import OutlineActionBar
from .chapter_detail_dialog import ChapterOutlineDetailDialog
from .chapter_edit_dialog import ChapterOutlineEditDialog
from .part_detail_dialog import PartOutlineDetailDialog
from .empty_states import LongNovelEmptyState, ShortNovelEmptyState
from .async_helper import AsyncOperationHelper

# 保留旧组件的导出用于兼容性（已弃用）
from .chapter_card import ChapterOutlineCard
from .chapter_list import ChapterOutlineList
from .part_outline_card import PartOutlineCard

__all__ = [
    # 新组件
    'ChapterOutlineSection',
    'OutlineRow',
    'OutlineListView',
    'OutlineActionBar',
    'ChapterOutlineDetailDialog',
    'ChapterOutlineEditDialog',
    'PartOutlineDetailDialog',
    'LongNovelEmptyState',
    'ShortNovelEmptyState',
    'AsyncOperationHelper',
    # 旧组件（已弃用，保留兼容性）
    'ChapterOutlineCard',
    'ChapterOutlineList',
    'PartOutlineCard',
]
