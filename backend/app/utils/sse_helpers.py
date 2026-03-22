"""
SSE (Server-Sent Events) 辅助工具

提供SSE事件格式化和流式响应生成功能。
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

from .exception_helpers import get_safe_error_message

logger = logging.getLogger(__name__)


def sse_event(event_type: str, data: Any) -> str:
    """
    格式化SSE事件

    Args:
        event_type: 事件类型（如 "token", "complete", "error"）
        data: 事件数据（将被JSON序列化）

    Returns:
        格式化的SSE事件字符串

    示例:
        >>> sse_event("token", {"content": "你好"})
        'event: token\\ndata: {"content": "你好"}\\n\\n'
    """
    if isinstance(data, str):
        json_data = json.dumps({"content": data}, ensure_ascii=False)
    else:
        json_data = json.dumps(data, ensure_ascii=False)

    return f"event: {event_type}\ndata: {json_data}\n\n"


# SSE响应标准头部
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def create_sse_response(generator):
    """
    创建标准的SSE流式响应

    统一SSE响应的创建方式，避免在各个路由中重复设置头部。

    Args:
        generator: 异步生成器函数，yield SSE事件字符串

    Returns:
        StreamingResponse: FastAPI流式响应对象

    示例:
        async def my_generator():
            yield sse_event("progress", {"status": "starting"})
            # ... 处理逻辑
            yield sse_event("complete", {"message": "完成"})

        return create_sse_response(my_generator())
    """
    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


async def sse_event_stream(
    generator: AsyncGenerator[Dict[str, Any], None],
    *,
    mapper: Optional[Callable[[Dict[str, Any]], Tuple[str, Any]]] = None,
) -> AsyncGenerator[str, None]:
    """将事件字典流包装为 SSE 字符串流

    Args:
        generator: 事件字典的异步生成器
        mapper: 事件映射函数（可选），用于将事件转换为 (event_type, data)

    Yields:
        SSE 格式化后的事件字符串
    """
    async for event in generator:
        if mapper:
            event_type, data = mapper(event)
        else:
            event_type = event.get("event", "")
            data = event.get("data")
        if event_type:
            yield sse_event(event_type, data)


def create_sse_stream_response(
    generator: AsyncGenerator[Dict[str, Any], None],
    *,
    mapper: Optional[Callable[[Dict[str, Any]], Tuple[str, Any]]] = None,
):
    """创建事件字典流的SSE响应

    统一事件流包装逻辑，避免路由层重复组合 create_sse_response 和 sse_event_stream。
    """
    return create_sse_response(sse_event_stream(generator, mapper=mapper))


async def sse_text_chunk_events(
    text: str,
    *,
    event_type: str = "ai_message_chunk",
    payload_key: str = "text",
    chunk_size: int = 15,
    delay_seconds: float = 0.03,
) -> AsyncGenerator[str, None]:
    """将一段文本按固定大小分块，流式输出为 SSE 事件字符串

    主要用于“先拿到完整 ai_message，再模拟打字机效果逐段发送”的场景。
    默认行为与既有灵感对话路由保持一致：15 字符一块，30ms 延迟。
    """
    if not text:
        return

    for i in range(0, len(text), chunk_size):
        chunk_text = text[i:i + chunk_size]
        yield sse_event(event_type, {payload_key: chunk_text})
        if delay_seconds:
            await asyncio.sleep(delay_seconds)


def sse_error_event(
    exc: Exception,
    operation_name: str,
    saved_items: Optional[List] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    生成标准化的SSE错误事件

    统一错误事件的格式，避免在各个路由中重复编写错误处理代码。
    自动使用安全的错误消息过滤，避免泄露敏感信息。

    Args:
        exc: 捕获的异常
        operation_name: 操作名称（如"章节生成"、"大纲生成"）
        saved_items: 已成功保存的项目列表（可选）
        extra_data: 额外的错误数据（可选）

    Returns:
        格式化的SSE error事件字符串

    示例:
        try:
            # ... 处理逻辑
        except Exception as exc:
            yield sse_error_event(exc, "章节生成", saved_items=[1, 2, 3])
    """
    safe_message = get_safe_error_message(exc, f"{operation_name}失败，请稍后重试")

    error_data: Dict[str, Any] = {
        "message": safe_message,
    }

    if saved_items is not None:
        error_data["saved_items"] = saved_items
        error_data["saved_count"] = len(saved_items)

    if extra_data:
        error_data.update(extra_data)

    logger.exception("%s失败: %s", operation_name, exc)

    return sse_event("error", error_data)


def sse_complete_event(
    message: str,
    extra_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    生成标准化的SSE完成事件

    Args:
        message: 完成消息
        extra_data: 额外的完成数据（可选）

    Returns:
        格式化的SSE complete事件字符串
    """
    complete_data: Dict[str, Any] = {
        "message": message,
    }

    if extra_data:
        complete_data.update(extra_data)

    return sse_event("complete", complete_data)

