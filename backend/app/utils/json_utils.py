import re
import json
import logging
from typing import Any, Dict, Optional, Tuple

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


def repair_truncated_json(text: str) -> str:
    """
    尝试修复被截断的JSON字符串

    当LLM响应被截断时，JSON可能缺少闭合括号。
    此函数尝试通过添加缺失的闭合符号来修复。

    Args:
        text: 可能被截断的JSON字符串

    Returns:
        修复后的JSON字符串
    """
    if not text:
        return text

    text = text.rstrip()

    # 统计未闭合的括号
    open_braces = 0  # {
    open_brackets = 0  # [
    in_string = False
    escape_next = False

    for char in text:
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == '{':
            open_braces += 1
        elif char == '}':
            open_braces -= 1
        elif char == '[':
            open_brackets += 1
        elif char == ']':
            open_brackets -= 1

    # 如果有未闭合的括号，尝试修复
    if open_braces > 0 or open_brackets > 0:
        # 移除可能被截断的不完整部分（如未闭合的字符串）
        # 从末尾向前找到最后一个完整的值
        last_valid_pos = len(text)

        # 检查是否在字符串中间被截断
        if in_string:
            # 找到最后一个未闭合的引号位置
            last_quote = text.rfind('"')
            if last_quote > 0:
                # 回退到引号前的逗号或冒号
                for i in range(last_quote - 1, -1, -1):
                    if text[i] in ',:[{':
                        last_valid_pos = i + 1
                        break
                text = text[:last_valid_pos].rstrip()
                # 重新统计
                open_braces = text.count('{') - text.count('}')
                open_brackets = text.count('[') - text.count(']')

        # 移除末尾的逗号（如果有）
        text = text.rstrip().rstrip(',')

        # 添加缺失的闭合符号
        # 按照JSON规范，先闭合内层再闭合外层
        text += ']' * open_brackets
        text += '}' * open_braces

        logger.info("JSON修复: 添加了 %d 个 '}' 和 %d 个 ']'",
                   max(0, open_braces), max(0, open_brackets))

    return text


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
        # 详细日志：显示原始响应的预览
        preview_len = 500
        raw_preview = raw_text[:preview_len] + "..." if len(raw_text) > preview_len else raw_text
        cleaned_preview = normalized[:preview_len] + "..." if len(normalized) > preview_len else normalized
        logger.error(
            "JSON解析失败: %s\n"
            "  错误信息: %s (位置: 行%d 列%d)\n"
            "  原始响应预览: %s\n"
            "  清理后预览: %s",
            error_context,
            exc.msg,
            exc.lineno,
            exc.colno,
            raw_preview,
            cleaned_preview
        )

        # 生成更友好的错误消息
        # 检测是否返回的是普通文本而不是JSON
        stripped = normalized.strip()
        if stripped and not stripped.startswith('{') and not stripped.startswith('['):
            # LLM返回了普通文本而不是JSON
            user_message = f"{error_context}: AI返回了对话内容而不是预期的结构化数据，请重试或调整对话内容"
        else:
            user_message = f"{error_context}: LLM返回格式错误"

        raise HTTPException(
            status_code=status_code,
            detail=user_message
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
    会自动尝试修复被截断的JSON。

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
    if not raw_text:
        return None

    try:
        cleaned = remove_think_tags(raw_text)
        normalized = unwrap_markdown_json(cleaned)
        return json.loads(normalized)
    except json.JSONDecodeError as e:
        # 第一次解析失败，尝试修复被截断的JSON
        try:
            repaired = repair_truncated_json(normalized)
            result = json.loads(repaired)
            logger.info("JSON修复成功，原长度: %d, 修复后长度: %d",
                       len(normalized), len(repaired))
            return result
        except json.JSONDecodeError:
            # 修复也失败了，记录详细信息以便调试
            logger.warning(
                "JSON解析失败（修复后仍失败）: %s, 位置: %d, 原文长度: %d, 预处理后长度: %d",
                str(e)[:100], e.pos if hasattr(e, 'pos') else -1,
                len(raw_text) if raw_text else 0,
                len(normalized) if normalized else 0
            )
            # 尝试记录解析失败的位置附近的内容
            if hasattr(e, 'pos') and normalized:
                start = max(0, e.pos - 50)
                end = min(len(normalized), e.pos + 50)
                logger.warning("解析失败位置附近的内容: ...%s...", normalized[start:end])
            return None
    except (AttributeError, TypeError):
        # 预期的解析失败，静默返回None
        return None
    except Exception as exc:
        # 未预期的异常，记录详情但不抛出
        logger.warning(
            "JSON解析时发生未预期异常（安全模式）: type=%s msg=%s",
            type(exc).__name__,
            str(exc)[:100],
        )
        return None


# 可能包含章节内容的字段名（按优先级排序）
# 与 version_processor.py 保持一致
CONTENT_FIELD_NAMES = [
    "full_content",
    "chapter_content",
    "content",
    "chapter_text",
    "text",
    "body",
    "story",
    "chapter",
    "output",
    "result",
    "response",
]


def extract_llm_content(
    raw_response: str,
    content_key: str = "content"
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    从LLM响应中提取内容和元数据

    统一处理LLM返回的各种格式：
    1. 纯文本响应
    2. JSON包装的响应 {"content": "...", "metadata": {...}}
    3. Markdown代码块包装的JSON

    内容提取优先级：
    1. 如果指定了 content_key 且存在，使用该字段
    2. 否则按 CONTENT_FIELD_NAMES 优先级查找
    3. 如果都没有，查找最长的字符串字段
    4. 最后返回清理后的纯文本

    Args:
        raw_response: LLM原始响应文本
        content_key: JSON中内容字段的键名，默认为"content"

    Returns:
        Tuple[str, Optional[Dict]]:
            - 提取的内容文本
            - 元数据字典（如果存在），否则None

    Example:
        ```python
        # 在章节生成中使用
        content, metadata = extract_llm_content(llm_response)
        chapter.content = content
        if metadata:
            chapter.metadata = metadata
        ```
    """
    if not raw_response:
        return "", None

    # 第一步：清理think标签
    cleaned = remove_think_tags(raw_response)

    # 第二步：尝试解析为JSON
    parsed = parse_llm_json_safe(cleaned)

    if parsed and isinstance(parsed, dict):
        content = ""
        used_key = None

        # 1. 首先检查指定的 content_key
        if content_key in parsed and isinstance(parsed[content_key], str) and parsed[content_key].strip():
            content = parsed[content_key]
            used_key = content_key
        else:
            # 2. 按优先级检查已知的内容字段名
            for field_name in CONTENT_FIELD_NAMES:
                if field_name in parsed and isinstance(parsed[field_name], str) and parsed[field_name].strip():
                    content = parsed[field_name]
                    used_key = field_name
                    break

        # 3. 如果仍未找到，查找最长的字符串字段
        if not content:
            longest_str = ""
            longest_key = ""
            for key, value in parsed.items():
                if isinstance(value, str) and len(value) > len(longest_str):
                    longest_str = value
                    longest_key = key
            if longest_str.strip():
                content = longest_str
                used_key = longest_key

        # 4. 如果有内容，返回内容和元数据
        if content:
            # 提取元数据（排除内容字段后的所有字段）
            metadata = {k: v for k, v in parsed.items() if k != used_key}
            return str(content), metadata if metadata else None

        # 如果JSON中没有找到有效内容，返回清理后的文本
        return unwrap_markdown_json(cleaned), None

    # 解析失败，返回清理后的纯文本
    return unwrap_markdown_json(cleaned), None


# ==================== 数字格式化工具 ====================

def fix_number_format(text: str, use_chinese_units: bool = True) -> str:
    """
    修复文本中的数字格式错误

    常见错误模式：
    - "50,0000" (错误的中式逗号分隔) -> "500,000" 或 "50万"
    - "120,0000" -> "1,200,000" 或 "120万"
    - "1000,0000" -> "10,000,000" 或 "1000万"

    Args:
        text: 需要处理的文本
        use_chinese_units: 是否使用中文单位（万、亿），默认True

    Returns:
        修复后的文本
    """
    if not text:
        return text

    # 模式1: 匹配错误的逗号分隔格式 (如 50,0000 或 120,0000)
    # 这种格式是每4位一个逗号，是错误的
    pattern_wrong_comma = r'\b(\d{1,3}),(\d{4})\b'

    def fix_wrong_comma(match):
        """修复错误的逗号分隔"""
        before_comma = match.group(1)
        after_comma = match.group(2)

        # 合并数字
        full_number = int(before_comma + after_comma)

        if use_chinese_units:
            return format_number_chinese(full_number)
        else:
            return format_number_western(full_number)

    result = re.sub(pattern_wrong_comma, fix_wrong_comma, text)

    # 模式2: 匹配连续两个4位数字用逗号分隔的情况 (如 1000,0000,0000)
    pattern_double_wrong = r'\b(\d{1,4}),(\d{4}),(\d{4})\b'

    def fix_double_wrong(match):
        """修复多个错误逗号的情况"""
        full_number = int(match.group(1) + match.group(2) + match.group(3))
        if use_chinese_units:
            return format_number_chinese(full_number)
        else:
            return format_number_western(full_number)

    result = re.sub(pattern_double_wrong, fix_double_wrong, result)

    return result


def format_number_chinese(number: int) -> str:
    """
    将数字格式化为中文格式

    Args:
        number: 数字

    Returns:
        格式化后的字符串，如 "50万"、"1.2亿"
    """
    if number >= 100000000:  # 亿
        value = number / 100000000
        if value == int(value):
            return f"{int(value)}亿"
        else:
            return f"{value:.1f}亿"
    elif number >= 10000:  # 万
        value = number / 10000
        if value == int(value):
            return f"{int(value)}万"
        else:
            return f"{value:.1f}万"
    else:
        return str(number)


def format_number_western(number: int) -> str:
    """
    将数字格式化为西方格式（千分位逗号）

    Args:
        number: 数字

    Returns:
        格式化后的字符串，如 "500,000"、"1,200,000"
    """
    return f"{number:,}"


def normalize_number_display(text: str, prefer_chinese: bool = True) -> str:
    """
    规范化文本中的数字显示

    这是一个综合函数，会：
    1. 修复错误的逗号分隔格式
    2. 统一数字显示风格

    Args:
        text: 需要处理的文本
        prefer_chinese: 是否优先使用中文单位

    Returns:
        处理后的文本
    """
    return fix_number_format(text, use_chinese_units=prefer_chinese)
