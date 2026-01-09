"""
通用对话框组件

提供常用的对话框组件：
- ConfirmDialog: 确认对话框
- AlertDialog: 警告/错误对话框
- InputDialog: 单行文本输入对话框
- TextInputDialog: 多行文本输入对话框
- IntInputDialog: 整数输入对话框
- LoadingDialog: 加载中对话框
- SaveDiscardDialog: 保存/不保存/取消 三按钮对话框
- RegenerateDialog: 重新生成确认对话框（带偏好输入）
"""

from .confirm_dialog import ConfirmDialog
from .alert_dialog import AlertDialog
from .input_dialog import InputDialog
from .text_input_dialog import TextInputDialog
from .int_input_dialog import IntInputDialog
from .loading_dialog import LoadingDialog
from .save_discard_dialog import SaveDiscardDialog, SaveDiscardResult
from .regenerate_dialog import RegenerateDialog, get_regenerate_preference

__all__ = [
    "ConfirmDialog",
    "AlertDialog",
    "InputDialog",
    "TextInputDialog",
    "IntInputDialog",
    "LoadingDialog",
    "SaveDiscardDialog",
    "SaveDiscardResult",
    "RegenerateDialog",
    "get_regenerate_preference",
]
