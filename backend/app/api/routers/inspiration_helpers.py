"""
灵感对话路由辅助函数

用于复用编程/小说两类灵感对话路由中“parsed_result → SSE事件输出”和“history记录格式化”的通用逻辑，
降低重复代码与行为漂移风险。
"""

import asyncio
import re
from typing import Any, AsyncGenerator, Callable, Dict, Iterable, List, Optional

from ...utils.sse_helpers import sse_error_event, sse_event, sse_text_chunk_events


class AiMessageJsonStreamExtractor:
    """从 LLM 流式返回的 JSON 文本中，增量提取 ai_message 字段内容。

    背景：
    - 灵感对话/需求分析阶段要求 LLM 严格输出 JSON；
    - LLM 原生流式输出的内容也是“整段 JSON 的增量片段”，直接透传会把 JSON 甩到前端；
    - 该提取器只提取 ai_message 的字符串值，并做基础的 JSON 转义解码，
      从而实现“原生流式”的对话气泡展示。

    说明：
    - 这里不做完整 JSON 解析，仅做足够可靠的状态机抽取；
    - 流结束后，仍以最终解析出的 ai_message 为准（complete 事件会携带最终 ai_message，用于校准）。
    """

    _START_RE = re.compile(r"\"ai_message\"\s*:\s*\"")

    def __init__(self, *, max_search_buffer: int = 4096):
        self._max_search_buffer = max(128, int(max_search_buffer))
        self._search_buffer = ""
        self._started = False
        self._done = False

        self._in_escape = False
        self._unicode_pending: Optional[str] = None
        self._pending_high_surrogate: Optional[int] = None

    @property
    def started(self) -> bool:
        return self._started

    @property
    def done(self) -> bool:
        return self._done

    def feed(self, chunk_text: str) -> str:
        """喂入一段 JSON 文本增量，返回本次新增的 ai_message 文本（可能为空）。"""
        if not chunk_text:
            return ""
        if self._done:
            return ""

        if not self._started:
            combined = self._search_buffer + chunk_text
            match = self._START_RE.search(combined)
            if not match:
                self._search_buffer = combined[-self._max_search_buffer :]
                return ""

            self._started = True
            after = combined[match.end() :]
            self._search_buffer = ""
            return self._consume_ai_message_string(after)

        return self._consume_ai_message_string(chunk_text)

    def _consume_ai_message_string(self, text: str) -> str:
        """消费 ai_message 字符串值内部内容，返回本次新增的已解码文本。"""
        if not text:
            return ""
        if self._done:
            return ""

        out: List[str] = []

        def flush_pending_high_surrogate() -> None:
            # 避免输出不成对 surrogate 导致 UTF-8 编码异常，用 U+FFFD 兜底
            if self._pending_high_surrogate is not None:
                out.append("\ufffd")
                self._pending_high_surrogate = None

        for ch in text:
            if self._done:
                break

            # 处理 \uXXXX
            if self._unicode_pending is not None:
                if ch.lower() in "0123456789abcdef":
                    self._unicode_pending += ch
                    if len(self._unicode_pending) >= 4:
                        codepoint = int(self._unicode_pending[:4], 16)
                        self._unicode_pending = None

                        # surrogate pair 处理
                        if 0xD800 <= codepoint <= 0xDBFF:
                            flush_pending_high_surrogate()
                            self._pending_high_surrogate = codepoint
                        elif 0xDC00 <= codepoint <= 0xDFFF:
                            if self._pending_high_surrogate is not None:
                                high = self._pending_high_surrogate
                                self._pending_high_surrogate = None
                                combined = 0x10000 + ((high - 0xD800) << 10) + (codepoint - 0xDC00)
                                out.append(chr(combined))
                            else:
                                out.append("\ufffd")
                        else:
                            flush_pending_high_surrogate()
                            out.append(chr(codepoint))
                    continue

                # 非法 \u 转义，按容错处理：输出替换符并继续
                self._unicode_pending = None
                flush_pending_high_surrogate()
                out.append("\ufffd")
                continue

            # 处理反斜杠转义
            if self._in_escape:
                self._in_escape = False
                if ch == "u":
                    self._unicode_pending = ""
                    continue

                flush_pending_high_surrogate()
                escape_map = {
                    '"': '"',
                    "\\": "\\",
                    "/": "/",
                    "b": "\b",
                    "f": "\f",
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                }
                out.append(escape_map.get(ch, ch))
                continue

            # 正常状态
            if ch == "\\":
                self._in_escape = True
                continue

            if ch == '"':
                # 字符串结束
                self._done = True
                flush_pending_high_surrogate()
                break

            flush_pending_high_surrogate()
            out.append(ch)

        return "".join(out)


async def stream_inspiration_parsed_result_events(
    *,
    parsed: Dict[str, Any],
    is_complete: bool,
    ready_for_blueprint: bool,
    placeholder_default: str = "输入你的想法...",
    option_delay_seconds: float = 0.15,
    on_ai_message_ready: Optional[Callable[[str], None]] = None,
    skip_ai_message_chunks: bool = False,
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
        skip_ai_message_chunks: 是否跳过 ai_message_chunk（用于“原生流式”已提前输出的场景）
    """
    ai_message = parsed.get("ai_message", "") or ""
    if on_ai_message_ready:
        on_ai_message_ready(ai_message)

    if ai_message and not skip_ai_message_chunks:
        async for chunk_event in sse_text_chunk_events(ai_message):
            yield chunk_event

    ui_control = parsed.get("ui_control", {}) or {}
    ui_control_type = ui_control.get("type", None)
    options = ui_control.get("options", []) or []
    options_list = options if isinstance(options, list) else []
    # 兼容多种 UI 控件类型：
    # - inspired_options：灵感卡片
    # - single_choice：简单单选（同样需要把 options 透传给前端）
    # 只要 options 是非空 list，就按 option 事件逐个发送，避免前端丢失可选项。
    if options_list:
        for idx, option in enumerate(options_list):
            yield sse_event(
                "option",
                {
                    "index": idx,
                    "total": len(options_list),
                    "option": option,
                },
            )
            if option_delay_seconds:
                await asyncio.sleep(option_delay_seconds)

    next_question = parsed.get("next_question", None)
    if not next_question:
        conversation_state = parsed.get("conversation_state", {}) or {}
        if isinstance(conversation_state, dict):
            next_question = conversation_state.get("next_question", None)

    next_question_points = parsed.get("next_question_points", None)
    if not next_question_points:
        conversation_state = parsed.get("conversation_state", {}) or {}
        if isinstance(conversation_state, dict):
            next_question_points = conversation_state.get("next_question_points", None)

    progress_summary = parsed.get("progress_summary", None)
    if not progress_summary:
        conversation_state = parsed.get("conversation_state", {}) or {}
        if isinstance(conversation_state, dict):
            progress_summary = conversation_state.get("progress_summary", None)

    yield sse_event(
        "complete",
        {
            "placeholder": ui_control.get("placeholder", placeholder_default),
            "ai_message": ai_message,
            "ui_control_type": ui_control_type,
            "options": options_list,
            "conversation_state": parsed.get("conversation_state", {}) or {},
            "next_question": next_question,
            "next_question_points": next_question_points,
            "progress_summary": progress_summary,
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
    - llm_chunk：从 JSON 流中抽取 ai_message 并转发为 ai_message_chunk（原生流式）
    - parsed_result：调用 stream_inspiration_parsed_result_events 输出 ai_message_chunk/option/complete
    - 异常：输出 sse_error_event
    """
    try:
        ai_message_extractor = AiMessageJsonStreamExtractor()
        native_stream_started = False

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
                chunk_text = data.get("content") if isinstance(data, dict) else None
                if chunk_text:
                    delta = ai_message_extractor.feed(str(chunk_text))
                    if ai_message_extractor.started:
                        native_stream_started = True
                    if delta:
                        yield sse_event("ai_message_chunk", {"text": delta, "source": "native"})
                continue

            elif event_type == "parsed_result":
                parsed = data["parsed"]
                async for chunk_event in stream_inspiration_parsed_result_events(
                    parsed=parsed,
                    is_complete=data["is_complete"],
                    ready_for_blueprint=data["ready_for_blueprint"],
                    on_ai_message_ready=on_ai_message_ready,
                    skip_ai_message_chunks=native_stream_started,
                ):
                    yield chunk_event

    except Exception as exc:
        yield sse_error_event(exc, error_title)


__all__ = [
    "stream_inspiration_parsed_result_events",
    "stream_inspiration_service_sse_events",
    "format_conversation_history_records",
]
