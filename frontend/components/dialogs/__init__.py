"""
自定义对话框组件 - 主题适配

目录结构：
dialogs/
├── base.py                 # 无边框自定义对话框基类
├── styles.py               # 对话框样式工具
├── common/                 # 通用对话框
│   ├── confirm_dialog.py
│   ├── alert_dialog.py
│   ├── input_dialog.py
│   ├── text_input_dialog.py
│   ├── int_input_dialog.py
│   ├── loading_dialog.py
│   └── save_discard_dialog.py
├── config/                 # 配置对话框
│   └── config_dialogs.py
└── special/                # 特殊对话框
    ├── book_style_dialog.py
    ├── create_mode_dialog.py
    └── import_progress_dialog.py
"""

# 样式工具
from .styles import DialogStyles

# 基类
from .base import BaseDialog

# 通用对话框（从 common/ 子目录导入，保持向后兼容）
from .common import (
    ConfirmDialog,
    AlertDialog,
    InputDialog,
    TextInputDialog,
    IntInputDialog,
    LoadingDialog,
    SaveDiscardDialog,
    SaveDiscardResult,
    RegenerateDialog,
    get_regenerate_preference,
)

# 配置对话框（从 config/ 子目录导入，保持向后兼容）
from .config import PartOutlineConfigDialog

# 特殊对话框（从 special/ 子目录导入，保持向后兼容）
from .special import (
    BookStyleDialog,
    CreateModeDialog,
    CodingModeDialog,
    ImportProgressDialog,
)

__all__ = [
    # 基类和样式
    'DialogStyles',
    'BaseDialog',
    'BookStyleDialog',
    # 通用对话框
    'ConfirmDialog',
    'AlertDialog',
    'InputDialog',
    'TextInputDialog',
    'IntInputDialog',
    'LoadingDialog',
    'SaveDiscardDialog',
    'SaveDiscardResult',
    'RegenerateDialog',
    'get_regenerate_preference',
    # 配置对话框
    'PartOutlineConfigDialog',
    # 特殊对话框
    'CreateModeDialog',
    'CodingModeDialog',
    'ImportProgressDialog',
]
