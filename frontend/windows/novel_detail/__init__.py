"""
项目详情模块 - 展示项目完整信息

目录结构：
novel_detail/
├── main.py                 # NovelDetail 主页面类
├── dirty_tracker.py        # 脏数据追踪器
├── section_styles.py       # Section 样式工具
├── mixins/                 # Mixin 模块
│   ├── header_manager.py
│   ├── tab_manager.py
│   ├── section_loader.py
│   ├── avatar_handler.py
│   ├── edit_dispatcher.py
│   ├── save_manager.py
│   ├── blueprint_refiner.py
│   └── import_analyzer.py
├── sections/               # Section 页面组件
│   ├── overview_section.py
│   ├── world_setting_section.py
│   ├── characters_section.py
│   ├── relationships_section.py
│   └── chapters_section.py
├── dialogs/                # 对话框组件
│   ├── edit_dialog.py
│   ├── refine_dialog.py
│   ├── list_edit_dialog.py
│   ├── character_edit_dialog.py
│   └── relationship_edit_dialog.py
├── components/             # 子组件
│   ├── character_row.py
│   ├── relationship_row.py
│   └── character_portraits_widget.py
└── chapter_outline/        # 章节大纲子模块
    └── ...
"""

# 主类
from .main import NovelDetail


__all__ = [
    'NovelDetail',
]
