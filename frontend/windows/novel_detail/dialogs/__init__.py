"""
NovelDetail Dialogs - 编辑对话框组件

- EditDialog: 通用编辑对话框
- RefineDialog: 蓝图优化对话框
- ListEditDialog: 列表编辑对话框
- CharacterListEditDialog: 角色列表编辑对话框
- RelationshipListEditDialog: 关系列表编辑对话框
"""

from .edit_dialog import EditDialog
from .refine_dialog import RefineDialog
from .list_edit_dialog import ListEditDialog
from .character_edit_dialog import CharacterListEditDialog
from .relationship_edit_dialog import RelationshipListEditDialog

__all__ = [
    'EditDialog',
    'RefineDialog',
    'ListEditDialog',
    'CharacterListEditDialog',
    'RelationshipListEditDialog',
]
