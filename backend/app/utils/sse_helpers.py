"""
SSE (Server-Sent Events) 辅助工具

提供SSE事件格式化和流式响应生成功能。
"""

import json
from typing import Any, Dict


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


def sse_message(message: str) -> str:
    """
    发送简单文本消息（无事件类型）

    Args:
        message: 文本消息

    Returns:
        格式化的SSE消息字符串
    """
    return f"data: {message}\n\n"


def sse_comment(comment: str) -> str:
    """
    发送SSE注释（用于保持连接活跃）

    Args:
        comment: 注释内容

    Returns:
        格式化的SSE注释字符串
    """
    return f": {comment}\n\n"


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
