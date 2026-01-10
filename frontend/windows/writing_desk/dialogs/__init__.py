"""
写作台对话框模块

提供写作台使用的各类对话框：
- OutlineEditDialog: 大纲编辑对话框
- PromptPreviewDialog: 提示词预览对话框
- ProtagonistProfileDialog: 主角档案对话框
- ProtagonistCreateDialog: 主角档案创建对话框
- AttributeEvidenceDialog: 属性溯源对话框
"""

from .outline_edit_dialog import OutlineEditDialog
from .prompt_preview_dialog import PromptPreviewDialog
from .protagonist_profile_dialog import ProtagonistProfileDialog
from .protagonist_create_dialog import ProtagonistCreateDialog
from .attribute_evidence_dialog import AttributeEvidenceDialog

__all__ = [
    "OutlineEditDialog",
    "PromptPreviewDialog",
    "ProtagonistProfileDialog",
    "ProtagonistCreateDialog",
    "AttributeEvidenceDialog",
]
