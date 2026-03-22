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

__all__ = [
    'ChapterOutlineSection',
]
