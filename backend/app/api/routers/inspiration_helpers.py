"""
灵感对话路由辅助函数

用于复用编程/小说两类灵感对话路由中“parsed_result → SSE事件输出”和“history记录格式化”的通用逻辑，
降低重复代码与行为漂移风险。
"""

import asyncio
from typing import Any, AsyncGenerator, Callable, Dict, Iterable, List, Optional

from ...utils.sse_helpers import sse_error_event, sse_event, sse_text_chunk_events


async def stream_inspiration_parsed_result_events(
    *,
    parsed: Dict[str, Any],
    is_complete: bool,
    ready_for_blueprint: bool,
    placeholder_default: str = "输入你的想法...",
    option_delay_seconds: float = 0.15,
    on_ai_message_ready: Optional[Callable[[str], None]] = None,
) -> AsyncGenerator[str, None]:
    """将 InspirationService 的 parsed_result 转换为 SSE 事件流

    事件顺序与现有路由保持一致：
    1) ai_message_chunk（多次）
    2) option（多次，可选）
    3) complete（一次）

    Args:
        parsed: 解析后的响应字典（包含 ai_message、ui_control、conversation_state 等）
        is_complete: 是否完成
        ready_for_blueprint: 是否可生成蓝图
        placeholder_default: ui_control 未提供 placeholder 时的默认文案
        option_delay_seconds: 逐个发送 option 的间隔（用于前端动画效果）
        on_ai_message_ready: 当 ai_message 获取到后触发（用于路由层日志/统计），可选
    """
    ai_message = parsed.get("ai_message", "") or ""
    if on_ai_message_ready:
        on_ai_message_ready(ai_message)

    if ai_message:
        async for chunk_event in sse_text_chunk_events(ai_message):
            yield chunk_event

    ui_control = parsed.get("ui_control", {}) or {}
    if ui_control.get("type") == "inspired_options":
        options = ui_control.get("options", []) or []
        for idx, option in enumerate(options):
            yield sse_event(
                "option",
                {
                    "index": idx,
                    "total": len(options),
                    "option": option,
                },
            )
            if option_delay_seconds:
                await asyncio.sleep(option_delay_seconds)

    yield sse_event(
        "complete",
        {
            "placeholder": ui_control.get("placeholder", placeholder_default),
            "conversation_state": parsed.get("conversation_state", {}) or {},
            "is_complete": is_complete,
            "ready_for_blueprint": ready_for_blueprint,
        },
    )


def format_conversation_history_records(records: Iterable[Any]) -> List[Dict[str, Any]]:
    """将对话记录转换为前端可用的 history 列表结构

    约定输出字段：id/role/content/created_at（ISO字符串或 None）。
    """
    result: List[Dict[str, Any]] = []
    for record in records:
        created_at = getattr(record, "created_at", None)
        result.append(
            {
                "id": getattr(record, "id", None),
                "role": getattr(record, "role", None),
                "content": getattr(record, "content", None),
                "created_at": created_at.isoformat() if created_at else None,
            }
        )
    return result


async def stream_inspiration_service_sse_events(
    *,
    inspiration_service: Any,
    project_id: str,
    user_input: str,
    user_id: int,
    project_type: str,
    error_title: str,
    on_ai_message_ready: Optional[Callable[[str], None]] = None,
) -> AsyncGenerator[str, None]:
    """将 InspirationService 的流式事件转换为 SSE 事件流（路由可直接 yield）

    保持与现有路由一致的事件处理策略：
    - streaming_start：转发到前端
    - llm_chunk：不直接发给前端（仅用于内部聚合）
    - parsed_result：调用 stream_inspiration_parsed_result_events 输出 ai_message_chunk/option/complete
    - 异常：输出 sse_error_event
    """
    try:
        async for event in inspiration_service.process_conversation_stream(
            project_id=project_id,
            user_input=user_input,
            user_id=user_id,
            project_type=project_type,
        ):
            event_type = event["event"]
            data = event["data"]

            if event_type == "streaming_start":
                yield sse_event("streaming_start", data)

            elif event_type == "llm_chunk":
                continue

            elif event_type == "parsed_result":
                parsed = data["parsed"]
                async for chunk_event in stream_inspiration_parsed_result_events(
                    parsed=parsed,
                    is_complete=data["is_complete"],
                    ready_for_blueprint=data["ready_for_blueprint"],
                    on_ai_message_ready=on_ai_message_ready,
                ):
                    yield chunk_event

    except Exception as exc:
        yield sse_error_event(exc, error_title)


__all__ = [
    "stream_inspiration_parsed_result_events",
    "stream_inspiration_service_sse_events",
    "format_conversation_history_records",
]
