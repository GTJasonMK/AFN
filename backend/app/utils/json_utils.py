import re
import json
import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def remove_think_tags(raw_text: str) -> str:
    """移除 <think></think> 标签，避免污染结果。"""
    if not raw_text:
        return raw_text
    return re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()


def unwrap_markdown_json(raw_text: str) -> str:
    """从 Markdown 或普通文本中提取 JSON 字符串，并替换中文引号。"""
    if not raw_text:
        return raw_text

    trimmed = raw_text.strip()

    fence_match = re.search(r"```(?:json|JSON)?\s*(.*?)\s*```", trimmed, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()
        if candidate:
            return normalize_chinese_quotes(candidate)

    json_start_candidates = [idx for idx in (trimmed.find("{"), trimmed.find("[")) if idx != -1]
    if json_start_candidates:
        start_idx = min(json_start_candidates)
        closing_brace = trimmed.rfind("}")
        closing_bracket = trimmed.rfind("]")
        end_idx = max(closing_brace, closing_bracket)
        if end_idx != -1 and end_idx > start_idx:
            candidate = trimmed[start_idx : end_idx + 1].strip()
            if candidate:
                return normalize_chinese_quotes(candidate)

    return normalize_chinese_quotes(trimmed)


def normalize_chinese_quotes(text: str) -> str:
    """将中文引号（""''）替换为英文引号。"""
    if not text:
        return text

    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    return text


def sanitize_json_like_text(raw_text: str) -> str:
    """对可能含有未转义换行/引号的 JSON 文本进行清洗。"""
    if not raw_text:
        return raw_text

    result = []
    in_string = False
    escape_next = False
    length = len(raw_text)
    i = 0
    while i < length:
        ch = raw_text[i]
        if in_string:
            if escape_next:
                result.append(ch)
                escape_next = False
            elif ch == "\\":
                result.append(ch)
                escape_next = True
            elif ch == '"':
                j = i + 1
                while j < length and raw_text[j] in " \t\r\n":
                    j += 1

                if j >= length or raw_text[j] in "}]" or raw_text[j] == ",":
                    in_string = False
                    result.append(ch)
                else:
                    result.extend(["\\", '"'])
            elif ch == "\n":
                result.extend(["\\", "n"])
            elif ch == "\r":
                result.extend(["\\", "r"])
            elif ch == "\t":
                result.extend(["\\", "t"])
            else:
                result.append(ch)
        else:
            if ch == '"':
                in_string = True
            result.append(ch)
        i += 1

    return "".join(result)


def parse_llm_json_or_fail(
    raw_text: str,
    error_context: str,
    status_code: int = 500
) -> Dict[str, Any]:
    """
    解析LLM返回的JSON，失败时抛出HTTP异常

    自动处理think标签和markdown包装，适用于Router层。

    Args:
        raw_text: LLM返回的原始文本（可能包含markdown、think标签等）
        error_context: 错误上下文描述（用于日志和错误消息）
        status_code: HTTP状态码（默认500）

    Returns:
        解析后的字典

    Raises:
        HTTPException: JSON解析失败

    Example:
        ```python
        blueprint_data = parse_llm_json_or_fail(
            llm_response,
            "蓝图生成失败"
        )
        ```
    """
    try:
        cleaned = remove_think_tags(raw_text)
        normalized = unwrap_markdown_json(cleaned)
        return json.loads(normalized)
    except json.JSONDecodeError as exc:
        logger.error(
            "JSON解析失败: %s, 原始文本长度=%d, 错误位置=%s",
            error_context,
            len(raw_text),
            exc.msg
        )
        raise HTTPException(
            status_code=status_code,
            detail=f"{error_context}: LLM返回格式错误"
        ) from exc
    except Exception as exc:
        logger.exception("JSON解析时发生未预期的错误: %s", error_context)
        raise HTTPException(
            status_code=status_code,
            detail=f"{error_context}: 解析失败"
        ) from exc


def parse_llm_json_safe(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    安全解析LLM返回的JSON，失败返回None（不抛异常）

    适用于循环中的容错解析场景。

    Args:
        raw_text: LLM返回的原始文本

    Returns:
        解析成功返回字典，失败返回None

    Example:
        ```python
        for record in history:
            data = parse_llm_json_safe(record.content)
            if data:
                # 处理成功的数据
                process(data)
            # 失败的跳过，不中断循环
        ```
    """
    try:
        cleaned = remove_think_tags(raw_text)
        normalized = unwrap_markdown_json(cleaned)
        return json.loads(normalized)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None
    except Exception:
        # 记录未预期的异常，但不抛出
        logger.debug("JSON解析失败（安全模式），跳过此条目")
        return None
