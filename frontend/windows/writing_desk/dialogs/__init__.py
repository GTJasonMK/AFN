"""
写作台对话框模块

提供写作台使用的各类对话框：
- OutlineEditDialog: 大纲编辑对话框
- PromptPreviewDialog: 提示词预览对话框
- ProtagonistProfileDialog: 主角档案对话框
"""

from .outline_edit_dialog import OutlineEditDialog
from .prompt_preview_dialog import PromptPreviewDialog
from .protagonist_profile_dialog import ProtagonistProfileDialog

__all__ = [
    "OutlineEditDialog",
    "PromptPreviewDialog",
    "ProtagonistProfileDialog",
]
