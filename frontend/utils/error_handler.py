"""
错误处理装饰器 - 统一的异常处理

简化重复的 try-except 代码块

设计原则：
1. 不捕获系统异常（SystemExit、KeyboardInterrupt等）
2. 优先处理已知的业务异常（APIError及其子类）
3. 对于未知异常，记录详细日志便于调试
4. 提供灵活的错误展示选项
"""

from functools import wraps
from typing import Callable, Any, Tuple, Type
import logging

logger = logging.getLogger(__name__)


# 不应被装饰器捕获的系统异常
# 这些异常应该被传播，让程序正常退出或被上层处理
_SYSTEM_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    SystemExit,
    KeyboardInterrupt,
    GeneratorExit,
)


def handle_errors(
    operation: str,
    show_message: bool = True,
    default_return: Any = None,
    log_level: int = logging.ERROR,
    reraise_unknown: bool = False
):
    """
    处理函数中的异常

    Args:
        operation: 操作名称（用于错误消息和日志）
        show_message: 是否显示错误消息框（默认True）
        default_return: 异常时的默认返回值（默认None）
        log_level: 日志级别（默认ERROR）
        reraise_unknown: 是否重新抛出未知异常（默认False）
                        设为True时，非APIError的异常会被重新抛出

    注意事项：
    - 不会捕获 SystemExit、KeyboardInterrupt、GeneratorExit
    - 优先处理 APIError 及其子类
    - 对于其他 Exception，根据 reraise_unknown 决定是否重新抛出

    Example:
        # 基本用法 - 捕获所有业务异常
        @handle_errors("加载项目")
        def loadProject(self):
            result = self.api_client.get_novel(self.project_id)
            return result

        # 高级用法 - 只处理API异常，其他异常继续抛出
        @handle_errors("保存数据", reraise_unknown=True)
        def saveData(self):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)

            except _SYSTEM_EXCEPTIONS:
                # 系统异常不捕获，直接传播
                raise

            except Exception as e:
                # 导入放在这里避免循环导入
                from api.exceptions import APIError

                # 判断是否为已知的业务异常
                is_api_error = isinstance(e, APIError)

                # 记录日志
                if is_api_error:
                    # API异常通常是预期内的，使用配置的日志级别
                    logger.log(log_level, "%s失败: %s", operation, str(e))
                else:
                    # 未知异常，总是记录完整堆栈
                    logger.error(
                        "%s发生未知错误: %s (%s)",
                        operation, str(e), type(e).__name__,
                        exc_info=True
                    )

                # 显示错误消息
                if show_message:
                    parent = _get_parent_widget(args)
                    if parent:
                        from utils.message_service import show_exception_error
                        show_exception_error(parent, e, operation)

                # 对于未知异常，根据配置决定是否重新抛出
                if reraise_unknown and not is_api_error:
                    raise

                return default_return

        return wrapper
    return decorator


def _get_parent_widget(args: tuple):
    """尝试从参数中获取父窗口widget

    Args:
        args: 函数参数元组，通常第一个是self

    Returns:
        QWidget实例或None
    """
    if not args:
        return None

    first_arg = args[0]

    # 检查是否是QWidget实例
    if hasattr(first_arg, '__class__'):
        # 避免在顶层导入PyQt，减少启动时间
        try:
            from PyQt6.QtWidgets import QWidget
            if isinstance(first_arg, QWidget):
                return first_arg
        except ImportError:
            pass

        # 如果不是QWidget，但有类，也返回它（兼容旧行为）
        return first_arg

    return None


def handle_api_errors(operation: str, **kwargs):
    """专门处理API错误的装饰器

    这是 handle_errors 的特化版本，只处理 APIError，
    其他异常会被重新抛出。

    Args:
        operation: 操作名称
        **kwargs: 传递给 handle_errors 的其他参数

    Example:
        @handle_api_errors("获取项目列表")
        def fetchProjects(self):
            return self.api_client.get_novels()
    """
    return handle_errors(operation, reraise_unknown=True, **kwargs)
