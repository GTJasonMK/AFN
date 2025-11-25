"""
错误处理装饰器 - 统一的异常处理

简化重复的 try-except 代码块
"""

from functools import wraps
from typing import Callable, Optional, Any
from PyQt6.QtWidgets import QWidget
import logging

logger = logging.getLogger(__name__)


def handle_errors(
    operation: str,
    show_message: bool = True,
    parent_attr: str = "self",
    default_return: Any = None
):
    """
    处理函数中的异常

    Args:
        operation: 操作名称（用于错误消息）
        show_message: 是否显示错误消息框
        parent_attr: 父窗口属性名（默认"self"）
        default_return: 异常时的默认返回值

    Example:
        @handle_errors("加载项目")
        def loadProject(self):
            result = self.api_client.get_novel(self.project_id)
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录日志
                logger.error(f"{operation}失败: {str(e)}", exc_info=True)

                # 显示错误消息
                if show_message:
                    # 尝试获取父窗口
                    parent = None
                    if args and hasattr(args[0], '__class__'):
                        # 第一个参数通常是self
                        parent = args[0]

                    if parent:
                        from utils.message_service import show_api_error
                        show_api_error(parent, operation, e)

                return default_return

        return wrapper
    return decorator
