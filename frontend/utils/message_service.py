"""
消息服务 - 统一的用户消息展示

提供统一的消息框接口，避免代码重复
"""

from PyQt6.QtWidgets import QMessageBox, QWidget
from typing import Optional


class MessageService:
    """统一的消息服务类"""

    @staticmethod
    def show_error(
        parent: Optional[QWidget],
        message: str,
        title: str = "错误",
        details: Optional[str] = None
    ) -> None:
        """
        显示错误消息

        Args:
            parent: 父窗口
            message: 错误消息
            title: 标题
            details: 详细信息（可选）
        """
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        if details:
            msg_box.setDetailedText(details)

        msg_box.exec()

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
        QMessageBox.information(parent, title, message)

    @staticmethod
    def show_warning(
        parent: Optional[QWidget],
        message: str,
        title: str = "警告"
    ) -> None:
        """
        显示警告消息

        Args:
            parent: 父窗口
            message: 警告消息
            title: 标题
        """
        QMessageBox.warning(parent, title, message)

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
        QMessageBox.information(parent, title, message)

    @staticmethod
    def confirm(
        parent: Optional[QWidget],
        message: str,
        title: str = "确认"
    ) -> bool:
        """
        显示确认对话框

        Args:
            parent: 父窗口
            message: 确认消息
            title: 标题

        Returns:
            用户是否点击了"是"
        """
        reply = QMessageBox.question(
            parent,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def show_api_error(
        parent: Optional[QWidget],
        operation: str,
        error: Exception
    ) -> None:
        """
        显示API错误消息（标准格式）

        Args:
            parent: 父窗口
            operation: 操作名称（如"加载项目"、"保存内容"）
            error: 异常对象
        """
        message = f"{operation}失败：{str(error)}"
        MessageService.show_error(parent, message)

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
        message = f"{operation}成功！"
        if details:
            message += f"\n{details}"
        MessageService.show_success(parent, message)


# 便捷函数（仅保留使用的）
def show_api_error(parent: Optional[QWidget], operation: str, error: Exception) -> None:
    """便捷函数：显示API错误"""
    MessageService.show_api_error(parent, operation, error)


def confirm(parent: Optional[QWidget], message: str, title: str = "确认") -> bool:
    """便捷函数：确认对话框"""
    return MessageService.confirm(parent, message, title)
