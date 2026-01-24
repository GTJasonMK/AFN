"""
章节大纲模块

目录结构：
chapter_outline/
├── main.py                 # ChapterOutlineSection 主组件
├── handlers/               # 操作处理器（Mixin）
│   ├── part_outline_handler.py
│   └── chapter_outline_handler.py
├── dialogs/                # 对话框组件
│   ├── part_detail_dialog.py
│   ├── chapter_detail_dialog.py
│   └── chapter_edit_dialog.py
├── components/             # UI组件
│   ├── outline_row.py
│   ├── outline_list.py
│   ├── action_bar.py
│   └── empty_states.py
└── utils/                  # 工具类
"""

# 主组件
from .main import ChapterOutlineSection

# Handlers（从 handlers/ 子目录导入，保持向后兼容）
from .handlers import PartOutlineHandlerMixin, ChapterOutlineHandlerMixin

# Dialogs（从 dialogs/ 子目录导入，保持向后兼容）
from .dialogs import (
    PartOutlineDetailDialog,
    ChapterOutlineDetailDialog,
    ChapterOutlineEditDialog,
)

# Components（从 components/ 子目录导入，保持向后兼容）
from .components import (
    OutlineRow,
    OutlineListView,
    OutlineActionBar,
    LongNovelEmptyState,
    ShortNovelEmptyState,
)

__all__ = [
    # 主组件
    'ChapterOutlineSection',
    # Handlers
    'PartOutlineHandlerMixin',
    'ChapterOutlineHandlerMixin',
    # Dialogs
    'PartOutlineDetailDialog',
    'ChapterOutlineDetailDialog',
    'ChapterOutlineEditDialog',
    # Components
    'OutlineRow',
    'OutlineListView',
    'OutlineActionBar',
    'LongNovelEmptyState',
    'ShortNovelEmptyState',
]
