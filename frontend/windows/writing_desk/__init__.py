"""
写作台模块 - 章节生成与版本管理

目录结构：
writing_desk/
├── main.py                 # WritingDesk 主类
├── header.py               # WDHeader 顶部导航栏
├── sidebar.py              # WDSidebar 左侧章节列表
├── assistant_panel.py      # AssistantPanel 助手面板
├── utils.py                # 工具函数
├── mixins/                 # Mixin 模块
│   ├── chapter_generation_mixin.py
│   ├── content_management_mixin.py
│   ├── version_management_mixin.py
│   └── evaluation_mixin.py
├── dialogs/                # 对话框组件
│   ├── outline_edit_dialog.py
│   ├── prompt_preview_dialog.py
│   └── protagonist_profile_dialog.py
├── components/             # UI组件
│   ├── chapter_card.py
│   ├── flippable_blueprint_card.py
│   ├── thinking_stream.py
│   ├── suggestion_card.py
│   └── paragraph_selector.py
├── panels/                 # 面板组件
├── workspace/              # 工作区组件
└── optimization/           # 优化相关
"""

# 主类
from .main import WritingDesk

# Mixins（从 mixins/ 子目录导入，保持向后兼容）
from .mixins import (
    ChapterGenerationMixin,
    ContentManagementMixin,
    VersionManagementMixin,
    EvaluationMixin,
)

# Dialogs（从 dialogs/ 子目录导入，保持向后兼容）
from .dialogs import (
    OutlineEditDialog,
    PromptPreviewDialog,
    ProtagonistProfileDialog,
)

# Components（从 components/ 子目录导入，保持向后兼容）
from .components import (
    ChapterCard,
    FlippableBlueprintCard,
    ThinkingStreamView,
    SuggestionCard,
    ParagraphSelector,
)

__all__ = [
    # 主类
    'WritingDesk',
    # Mixins
    'ChapterGenerationMixin',
    'ContentManagementMixin',
    'VersionManagementMixin',
    'EvaluationMixin',
    # Dialogs
    'OutlineEditDialog',
    'PromptPreviewDialog',
    'ProtagonistProfileDialog',
    # Components
    'ChapterCard',
    'FlippableBlueprintCard',
    'ThinkingStreamView',
    'SuggestionCard',
    'ParagraphSelector',
]
