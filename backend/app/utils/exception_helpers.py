"""
异常处理辅助工具

提供统一的异常日志记录和转换函数，改善代码一致性。
"""

import logging
import traceback
from typing import Optional, Type
from fastapi import HTTPException

from ..exceptions import AFNException

logger = logging.getLogger(__name__)


def log_exception(
    exc: Exception,
    context: str,
    logger_instance: Optional[logging.Logger] = None,
    level: str = "error",
    include_traceback: bool = True,
    **extra_context
) -> None:
    """
    统一的异常日志记录函数

    Args:
        exc: 异常对象
        context: 上下文描述（如"生成章节大纲"）
        logger_instance: 自定义logger，默认使用模块logger
        level: 日志级别（error/warning/info）
        include_traceback: 是否包含完整堆栈
        **extra_context: 额外上下文信息（如project_id, user_id等）

    Example:
        log_exception(
            exc,
            "生成蓝图",
            project_id=project_id,
            user_id=user_id,
            total_chapters=150
        )
    """
    log = logger_instance or logger
    log_func = getattr(log, level, log.error)

    # 构建上下文字符串
    context_parts = [f"{k}={v}" for k, v in extra_context.items() if v is not None]
    context_str = f" ({', '.join(context_parts)})" if context_parts else ""

    # 构建错误消息
    exc_type = type(exc).__name__
    exc_msg = str(exc)

    full_msg = f"{context}失败 [{exc_type}]: {exc_msg}{context_str}"

    if include_traceback:
        log_func(full_msg, exc_info=True)
    else:
        log_func(full_msg)


def convert_to_http_exception(
    exc: Exception,
    default_status_code: int = 500,
    default_message: str = "操作失败",
    context: Optional[str] = None,
    **log_context
) -> HTTPException:
    """
    将通用异常转换为HTTPException

    统一处理异常转换逻辑，避免重复代码。

    Args:
        exc: 原始异常
        default_status_code: 默认HTTP状态码
        default_message: 默认错误消息
        context: 操作上下文（用于日志）
        **log_context: 日志上下文信息

    Returns:
        HTTPException: 转换后的HTTP异常

    Example:
        try:
            result = await some_operation()
        except Exception as exc:
            raise convert_to_http_exception(
                exc,
                default_status_code=500,
                default_message="操作失败",
                context="生成章节",
                project_id=project_id
            )
    """
    # 记录异常日志
    if context:
        log_exception(exc, context, **log_context)

    # 如果已经是HTTPException，直接返回
    if isinstance(exc, HTTPException):
        return exc

    # 转换为HTTPException
    detail = str(exc) or default_message
    return HTTPException(
        status_code=default_status_code,
        detail=detail
    )


class ExceptionContext:
    """
    异常上下文管理器，用于自动记录异常

    Example:
        async with ExceptionContext("生成蓝图", project_id=project_id):
            result = await blueprint_service.generate(project_id)
    """

    def __init__(
        self,
        context: str,
        logger_instance: Optional[logging.Logger] = None,
        **extra_context
    ):
        self.context = context
        self.logger = logger_instance or logger
        self.extra_context = extra_context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            log_exception(
                exc_val,
                self.context,
                logger_instance=self.logger,
                **self.extra_context
            )
        return False  # 不抑制异常

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            log_exception(
                exc_val,
                self.context,
                logger_instance=self.logger,
                **self.extra_context
            )
        return False  # 不抑制异常


def format_exception_chain(exc: Exception, max_depth: int = 5) -> str:
    """
    格式化异常链，用于详细日志

    Args:
        exc: 异常对象
        max_depth: 最大追溯深度

    Returns:
        str: 格式化的异常链信息

    Example:
        logger.error("异常链: %s", format_exception_chain(exc))
    """
    chain = []
    current = exc
    depth = 0

    while current and depth < max_depth:
        exc_type = type(current).__name__
        exc_msg = str(current)
        chain.append(f"{exc_type}: {exc_msg}")

        # 检查是否有__cause__或__context__
        current = getattr(current, '__cause__', None) or getattr(current, '__context__', None)
        depth += 1

    if depth >= max_depth and current:
        chain.append("... (异常链过长，已截断)")

    return " -> ".join(chain)


def get_safe_error_message(exc: Exception, default_message: str = "服务内部错误，请稍后重试") -> str:
    """
    获取安全的用户端错误消息，过滤敏感信息

    此函数用于SSE流式响应等场景，确保不向客户端暴露敏感信息（如数据库连接串、API密钥、文件路径等）。

    过滤规则：
    1. AFNException: 使用其已清洗的 message 属性
    2. HTTPException: 使用其 detail 属性（通常已清洗）
    3. 其他异常: 返回通用错误消息，避免泄露内部细节

    Args:
        exc: 异常对象
        default_message: 未知异常时返回的默认消息

    Returns:
        str: 安全的用户端错误消息

    Example:
        try:
            await some_operation()
        except Exception as exc:
            yield sse_event("error", {"message": get_safe_error_message(exc)})
    """
    # AFNException 及其子类已经设计了用户友好的 message 属性
    if isinstance(exc, AFNException):
        return exc.message

    # HTTPException 的 detail 通常是安全的
    if isinstance(exc, HTTPException):
        return str(exc.detail) if exc.detail else default_message

    # 对于已知的、消息本身安全的标准异常类型
    if isinstance(exc, (ValueError, TypeError)):
        # 这些异常的消息可能包含变量名，但通常不包含敏感信息
        # 但为了安全起见，仍然返回通用消息
        return default_message

    # 其他所有异常返回通用消息，避免泄露敏感信息
    return default_message
