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

    @staticmethod
    def show_exception_error(
        parent: Optional[QWidget],
        exception: Exception,
        operation: str = "操作"
    ) -> None:
        """
        根据异常类型显示错误消息

        此方法会根据异常类型提供不同的错误消息和建议操作，
        为用户提供更有用的错误反馈。

        Args:
            parent: 父窗口
            exception: 异常对象
            operation: 操作名称（如"加载项目"、"生成章节"）
        """
        from api.exceptions import (
            APIError,
            LLMServiceError,
            BlueprintNotReadyError,
            ChapterNotGeneratedError,
            InvalidStateTransitionError,
            ConversationExtractionError,
            GenerationCancelledError,
            ConnectionError as APIConnectionError,
            TimeoutError as APITimeoutError,
        )

        # 根据异常类型生成消息
        if isinstance(exception, LLMServiceError):
            title = "AI服务错误"
            message = f"{operation}失败：AI服务暂时不可用\n\n请检查：\n- LLM配置是否正确\n- API密钥是否有效\n- 网络连接是否正常"
        elif isinstance(exception, BlueprintNotReadyError):
            title = "蓝图未就绪"
            message = f"{operation}失败：项目蓝图尚未生成\n\n请先完成灵感对话，生成项目蓝图后再进行此操作。"
        elif isinstance(exception, ChapterNotGeneratedError):
            title = "章节未生成"
            message = f"{operation}失败：该章节尚未生成内容\n\n请先生成章节内容后再进行此操作。"
        elif isinstance(exception, InvalidStateTransitionError):
            title = "状态错误"
            message = f"{operation}失败：当前项目状态不允许此操作\n\n{str(exception)}"
        elif isinstance(exception, ConversationExtractionError):
            title = "对话错误"
            message = f"{operation}失败：对话历史格式异常\n\n建议重新开始灵感对话。"
        elif isinstance(exception, GenerationCancelledError):
            title = "已取消"
            message = f"{operation}已被取消"
        elif isinstance(exception, APIConnectionError):
            title = "连接失败"
            message = f"{operation}失败：无法连接到后端服务\n\n请检查：\n- 后端服务是否已启动\n- 网络连接是否正常"
        elif isinstance(exception, APITimeoutError):
            title = "请求超时"
            message = f"{operation}失败：服务器响应超时\n\n这可能是因为：\n- 生成内容较长，需要更多时间\n- 服务器负载较高\n\n请稍后重试。"
        elif isinstance(exception, APIError):
            # 通用API错误
            title = f"{operation}失败"
            message = f"{operation}失败：{exception.message}"
        else:
            # 未知异常
            title = "发生错误"
            message = f"{operation}时发生未知错误：{str(exception)}"

        MessageService.show_error(parent, message, title=title)


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


def show_exception_error(
    parent: Optional[QWidget],
    exception: Exception,
    operation: str = "操作"
) -> None:
    """便捷函数：根据异常类型显示错误消息

    此函数会根据异常类型提供不同的错误消息和建议操作。

    Args:
        parent: 父窗口
        exception: 异常对象
        operation: 操作名称（如"加载项目"、"生成章节"）
    """
    MessageService.show_exception_error(parent, exception, operation)
