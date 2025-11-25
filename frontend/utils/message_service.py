"""
消息服务 - 统一的用户消息展示

提供统一的消息接口：
- 成功/信息/警告/错误提示 -> AlertDialog 对话框（阻塞式）
- 确认对话框 -> ConfirmDialog
"""

from PyQt6.QtWidgets import QWidget, QDialog
from typing import Optional

from components.dialogs import ConfirmDialog, AlertDialog


class MessageService:
    """统一的消息服务类

    使用 AlertDialog 进行消息通知
    """

    @staticmethod
    def show_error(
        parent: Optional[QWidget],
        message: str,
        title: str = "错误",
        details: Optional[str] = None,
        use_dialog: bool = True  # 保留参数兼容性，但默认使用对话框
    ) -> None:
        """
        显示错误消息

        Args:
            parent: 父窗口
            message: 错误消息
            title: 标题
            details: 详细信息（可选）
            use_dialog: 是否使用对话框（现在默认True）
        """
        full_message = message
        if details:
            full_message = f"{message}\n{details}"

        dialog = AlertDialog(
            parent=parent,
            title=title,
            message=full_message,
            button_text="知道了",
            dialog_type="error"
        )
        dialog.exec()

    @staticmethod
    def show_success(
        parent: Optional[QWidget],
        message: str,
        title: str = "成功"
    ) -> None:
        """
        显示成功消息

        Args:
            parent: 父窗口
            message: 成功消息
            title: 标题
        """
        dialog = AlertDialog(
            parent=parent,
            title=title,
            message=message,
            button_text="确定",
            dialog_type="success"
        )
        dialog.exec()

    @staticmethod
    def show_warning(
        parent: Optional[QWidget],
        message: str,
        title: str = "警告",
        use_dialog: bool = True  # 保留参数兼容性，但默认使用对话框
    ) -> None:
        """
        显示警告消息

        Args:
            parent: 父窗口
            message: 警告消息
            title: 标题
            use_dialog: 是否使用对话框（现在默认True）
        """
        dialog = AlertDialog(
            parent=parent,
            title=title,
            message=message,
            button_text="知道了",
            dialog_type="warning"
        )
        dialog.exec()

    @staticmethod
    def show_info(
        parent: Optional[QWidget],
        message: str,
        title: str = "提示"
    ) -> None:
        """
        显示信息提示

        Args:
            parent: 父窗口
            message: 提示消息
            title: 标题
        """
        dialog = AlertDialog(
            parent=parent,
            title=title,
            message=message,
            button_text="确定",
            dialog_type="info"
        )
        dialog.exec()

    @staticmethod
    def confirm(
        parent: Optional[QWidget],
        message: str,
        title: str = "确认",
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        dialog_type: str = "normal"
    ) -> bool:
        """
        显示确认对话框

        Args:
            parent: 父窗口
            message: 确认消息
            title: 标题
            confirm_text: 确认按钮文本
            cancel_text: 取消按钮文本
            dialog_type: 对话框类型（normal/danger/warning）

        Returns:
            用户是否点击了确认
        """
        dialog = ConfirmDialog(
            parent=parent,
            title=title,
            message=message,
            confirm_text=confirm_text,
            cancel_text=cancel_text,
            dialog_type=dialog_type
        )
        return dialog.exec() == QDialog.DialogCode.Accepted

    @staticmethod
    def confirm_danger(
        parent: Optional[QWidget],
        message: str,
        title: str = "确认删除",
        confirm_text: str = "删除",
        cancel_text: str = "取消"
    ) -> bool:
        """
        显示危险操作确认对话框（红色主题）

        Args:
            parent: 父窗口
            message: 确认消息
            title: 标题
            confirm_text: 确认按钮文本
            cancel_text: 取消按钮文本

        Returns:
            用户是否点击了确认
        """
        return MessageService.confirm(
            parent=parent,
            message=message,
            title=title,
            confirm_text=confirm_text,
            cancel_text=cancel_text,
            dialog_type="danger"
        )

    @staticmethod
    def show_api_error(
        parent: Optional[QWidget],
        error_msg: str,
        operation: str = "操作"
    ) -> None:
        """
        显示API错误消息（标准格式）

        Args:
            parent: 父窗口
            error_msg: 错误消息
            operation: 操作名称（如"加载项目"、"保存内容"）
        """
        message = f"{operation}失败：{error_msg}"
        MessageService.show_error(parent, message, title=f"{operation}失败")

    @staticmethod
    def show_operation_success(
        parent: Optional[QWidget],
        operation: str,
        details: Optional[str] = None
    ) -> None:
        """
        显示操作成功消息（标准格式）

        Args:
            parent: 父窗口
            operation: 操作名称
            details: 额外信息（可选）
        """
        message = f"{operation}成功"
        if details:
            message += f"\n{details}"
        MessageService.show_success(parent, message, title="操作成功")


# 便捷函数
def show_api_error(parent: Optional[QWidget], error_msg: str, operation: str = "操作") -> None:
    """便捷函数：显示API错误"""
    MessageService.show_api_error(parent, error_msg, operation)


def confirm(
    parent: Optional[QWidget],
    message: str,
    title: str = "确认",
    confirm_text: str = "确认",
    cancel_text: str = "取消"
) -> bool:
    """便捷函数：确认对话框"""
    return MessageService.confirm(parent, message, title, confirm_text, cancel_text)


def confirm_danger(
    parent: Optional[QWidget],
    message: str,
    title: str = "确认删除"
) -> bool:
    """便捷函数：危险操作确认对话框"""
    return MessageService.confirm_danger(parent, message, title)
