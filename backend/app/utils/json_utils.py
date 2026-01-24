"""
JSON解析工具

负责LLM响应的JSON解析，采用简洁直接的方式：
- 只做必要的清理（think标签、markdown包装、中文引号）
- 解析失败直接报错，不尝试猜测修复
- 依靠完善的提示词确保LLM返回正确格式
"""

import re
import json
import logging
from typing import Any, Dict, Optional, Tuple

from ..exceptions import JSONParseError
from .content_fields import CONTENT_FIELD_NAMES

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

    # 尝试从markdown代码块中提取（完整闭合的代码块）
    fence_match = re.search(r"```(?:json|JSON)?\s*(.*?)\s*```", trimmed, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()
        if candidate:
            return normalize_chinese_quotes(candidate)

    # 处理未闭合的 markdown 代码块（如 ```json 开头但没有闭合的 ```）
    unclosed_fence_match = re.match(r"```(?:json|JSON)?\s*\n?", trimmed)
    if unclosed_fence_match:
        # 移除开头的 ```json 标记
        content_after_fence = trimmed[unclosed_fence_match.end():]
        # 如果有闭合标记在后面，截取到那里
        end_fence_pos = content_after_fence.rfind("```")
        if end_fence_pos != -1:
            content_after_fence = content_after_fence[:end_fence_pos]
        trimmed = content_after_fence.strip()

    # 尝试找到JSON的起始和结束位置
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


def escape_control_chars_in_strings(text: str) -> str:
    """
    转义JSON字符串值中的控制字符（换行符、制表符等）

    LLM有时会在JSON字符串值中直接包含换行符，而JSON标准要求
    这些字符必须被转义（如 \\n）。此函数会找到字符串值中的
    控制字符并正确转义它们。

    Args:
        text: JSON文本

    Returns:
        转义后的JSON文本
    """
    if not text:
        return text

    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(text):
        char = text[i]

        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        if in_string:
            # 在字符串内部，转义控制字符
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif ord(char) < 32:
                # 其他控制字符转义为Unicode
                result.append(f'\\u{ord(char):04x}')
            else:
                result.append(char)
        else:
            result.append(char)

        i += 1

    return ''.join(result)


def normalize_chinese_quotes(text: str) -> str:
    """
    智能替换中文引号为英文引号（仅替换JSON结构性引号）

    只替换用作JSON结构的中文引号（键名和值的定界符），
    保留字符串内容中的中文引号不变，避免破坏JSON结构。
    """
    if not text:
        return text

    # 快速检查：如果没有中文引号，直接返回
    if '\u201c' not in text and '\u201d' not in text and '\u2018' not in text and '\u2019' not in text:
        return text

    # 尝试直接解析，如果成功说明中文引号只在字符串内容中，无需替换
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 只替换JSON结构外的中文引号
    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(text):
        char = text[i]

        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        if in_string:
            result.append(char)
            i += 1
            continue

        # 在字符串外部，替换中文引号
        if char in '\u201c\u201d':
            result.append('"')
            i += 1
            continue

        if char in '\u2018\u2019':
            result.append("'")
            i += 1
            continue

        result.append(char)
        i += 1

    return ''.join(result)


def try_fix_inner_quotes(text: str) -> str:
    """
    尝试修复JSON字符串值内的未转义双引号

    LLM有时会在JSON字符串值中使用未转义的双引号（如"穿越者"），
    这会导致JSON解析失败。此函数尝试将这些内部引号转义。

    修复策略：
    1. 首先尝试直接解析，成功则返回
    2. 使用启发式方法识别字符串内的引号并转义

    Args:
        text: 可能包含格式问题的JSON文本

    Returns:
        修复后的文本
    """
    if not text:
        return text

    # 先尝试直接解析，如果成功则无需修复
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError as e:
        error_pos = e.pos if hasattr(e, 'pos') else -1
        logger.debug("JSON解析失败，尝试修复。错误位置: %d, 错误: %s", error_pos, e.msg)

    # 策略1：扫描并转义字符串值内的双引号
    fixed_text = _fix_quotes_by_scanning(text)
    try:
        json.loads(fixed_text)
        logger.debug("JSON内部引号修复成功（扫描方式）")
        return fixed_text
    except json.JSONDecodeError:
        pass

    # 策略2：替换所有可能有问题的引号模式
    fixed_text = _fix_quotes_by_pattern(text)
    try:
        json.loads(fixed_text)
        logger.debug("JSON内部引号修复成功（模式匹配方式）")
        return fixed_text
    except json.JSONDecodeError:
        pass

    # 修复失败，返回原文本
    return text


def _fix_quotes_by_scanning(text: str) -> str:
    """
    通过扫描方式修复字符串内的引号

    启发式规则：
    - 如果一个双引号后面紧跟 `,` `:` `]` `}` 或空白字符后跟这些符号，则是字符串结束
    - 否则可能是字符串内的引号，需要转义
    """
    result = []
    i = 0
    in_string = False

    while i < len(text):
        char = text[i]

        # 处理转义字符
        if char == '\\' and i + 1 < len(text):
            result.append(char)
            result.append(text[i + 1])
            i += 2
            continue

        if char == '"':
            if not in_string:
                # 进入字符串
                in_string = True
                result.append(char)
            else:
                # 检查这是否是字符串结束引号
                next_non_space = i + 1
                while next_non_space < len(text) and text[next_non_space] in ' \t\n\r':
                    next_non_space += 1

                # 如果后面是 , : ] } 或文件结束，说明这是字符串结束
                if next_non_space >= len(text) or text[next_non_space] in ',:]}\n':
                    in_string = False
                    result.append(char)
                else:
                    # 这可能是字符串内的引号，需要转义
                    result.append('\\')
                    result.append(char)
            i += 1
            continue

        result.append(char)
        i += 1

    return ''.join(result)


def _fix_quotes_by_pattern(text: str) -> str:
    """
    通过模式匹配方式修复常见的引号问题

    处理模式：
    1. "word" 形式的引用词（如 a "casual" outfit）
    2. 连续的未转义引号
    """
    # 模式1：匹配 ": "...text "word" more text..."
    # 在JSON字符串值中，如果出现 空格"单词"空格 的模式，将引号替换为单引号
    def fix_quoted_words(match):
        # 保留前后空格，将双引号替换为单引号
        before = match.group(1)  # 前面的空格或字符
        word = match.group(2)    # 被引用的单词
        after = match.group(3)   # 后面的空格或字符
        return f"{before}'{word}'{after}"

    # 匹配 空格/逗号 + "单词" + 空格/逗号/句号 的模式
    # 但不匹配JSON结构性引号（如 ": " 或 ", "）
    pattern = r'([,\.\s])\"([^\"]{1,30})\"([,\.\s])'
    fixed = re.sub(pattern, fix_quoted_words, text)

    # 如果没有变化，尝试更激进的修复
    if fixed == text:
        # 替换所有 英文字母后的引号+英文字母 模式中的引号为单引号
        # 例如: wearing a "casual" outfit -> wearing a 'casual' outfit
        pattern2 = r'([a-zA-Z])\s*\"\s*([a-zA-Z][^\"]{0,20})\s*\"\s*([a-zA-Z])'
        fixed = re.sub(pattern2, r"\1 '\2' \3", text)

    return fixed


def parse_llm_json_or_fail(
    raw_text: str,
    error_context: str,
) -> Dict[str, Any]:
    """
    解析LLM返回的JSON，失败时直接抛出异常

    采用简洁直接的方式：
    1. 移除think标签
    2. 提取JSON（去除markdown包装）
    3. 替换中文引号
    4. 尝试修复字符串内的未转义引号
    5. 解析JSON，失败直接报错

    Args:
        raw_text: LLM返回的原始文本
        error_context: 错误上下文描述

    Returns:
        解析后的字典

    Raises:
        JSONParseError: JSON解析失败
    """
    try:
        cleaned = remove_think_tags(raw_text)
        normalized = unwrap_markdown_json(cleaned)
        # 转义字符串值中的控制字符（如换行符）
        normalized = escape_control_chars_in_strings(normalized)
        # 尝试修复字符串内的未转义引号
        normalized = try_fix_inner_quotes(normalized)
        return json.loads(normalized)

    except json.JSONDecodeError as exc:
        # 记录详细错误信息
        preview_len = 500
        raw_preview = raw_text[:preview_len] + "..." if len(raw_text) > preview_len else raw_text
        normalized_preview = normalized[:preview_len] + "..." if len(normalized) > preview_len else normalized

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
            normalized_preview
        )

        # 生成友好的错误消息
        stripped = normalized.strip() if normalized else ""
        if stripped and not stripped.startswith('{') and not stripped.startswith('['):
            detail_msg = "AI返回了普通文本而不是JSON格式，请检查提示词或重试"
        else:
            detail_msg = f"JSON格式错误: {exc.msg} (行{exc.lineno} 列{exc.colno})"

        raise JSONParseError(
            context=error_context,
            detail_msg=detail_msg
        ) from exc

    except Exception as exc:
        logger.exception("JSON解析时发生未预期的错误: %s", error_context)
        raise JSONParseError(
            context=error_context,
            detail_msg=f"未预期错误: {type(exc).__name__}"
        ) from exc


def parse_llm_json_safe(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    安全解析LLM返回的JSON，失败返回None

    适用于循环中的容错解析场景，不尝试修复，失败就跳过。

    Args:
        raw_text: LLM返回的原始文本

    Returns:
        解析成功返回字典，失败返回None
    """
    if not raw_text:
        return None

    try:
        cleaned = remove_think_tags(raw_text)
        normalized = unwrap_markdown_json(cleaned)
        # 转义字符串值中的控制字符（如换行符）
        normalized = escape_control_chars_in_strings(normalized)
        # 尝试修复字符串内的未转义引号
        normalized = try_fix_inner_quotes(normalized)
        return json.loads(normalized)

    except json.JSONDecodeError as e:
        logger.warning(
            "JSON解析失败: %s, 位置: %d, 内容长度: %d, 错误位置附近内容: %s",
            str(e)[:100],
            e.pos if hasattr(e, 'pos') else -1,
            len(raw_text) if raw_text else 0,
            normalized[max(0, e.pos - 50):e.pos + 50] if hasattr(e, 'pos') and normalized and e.pos else "(无)"
        )
        return None

    except Exception as exc:
        logger.debug(
            "JSON解析时发生异常: type=%s msg=%s",
            type(exc).__name__,
            str(exc)[:100],
        )
        return None


def parse_llm_json_with_context(
    raw_text: str,
    logger: logging.Logger,
    context: str,
    level: int = logging.WARNING,
    preview_len: int = 200,
) -> Optional[Dict[str, Any]]:
    """
    解析 LLM 返回 JSON，并在失败时输出带上下文的日志。

    Args:
        raw_text: LLM 返回的原始文本
        logger: 记录日志的 logger
        context: 业务上下文描述
        level: 失败时的日志级别
        preview_len: 失败时输出的文本预览长度

    Returns:
        解析成功返回字典，失败返回 None
    """
    data = parse_llm_json_safe(raw_text)
    if not data:
        preview = raw_text[:preview_len] if raw_text else ""
        logger.log(level, "%s解析失败: %s", context, preview)
    return data


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

    Args:
        text: 需要处理的文本
        use_chinese_units: 是否使用中文单位（万、亿），默认True

    Returns:
        修复后的文本
    """
    if not text:
        return text

    pattern_wrong_comma = r'\b(\d{1,3}),(\d{4})\b'

    def fix_wrong_comma(match):
        before_comma = match.group(1)
        after_comma = match.group(2)
        full_number = int(before_comma + after_comma)
        if use_chinese_units:
            return format_number_chinese(full_number)
        else:
            return format_number_western(full_number)

    result = re.sub(pattern_wrong_comma, fix_wrong_comma, text)

    pattern_double_wrong = r'\b(\d{1,4}),(\d{4}),(\d{4})\b'

    def fix_double_wrong(match):
        full_number = int(match.group(1) + match.group(2) + match.group(3))
        if use_chinese_units:
            return format_number_chinese(full_number)
        else:
            return format_number_western(full_number)

    result = re.sub(pattern_double_wrong, fix_double_wrong, result)
    return result


def format_number_chinese(number: int) -> str:
    """将数字格式化为中文格式（万、亿）"""
    if number >= 100000000:
        value = number / 100000000
        if value == int(value):
            return f"{int(value)}亿"
        else:
            return f"{value:.1f}亿"
    elif number >= 10000:
        value = number / 10000
        if value == int(value):
            return f"{int(value)}万"
        else:
            return f"{value:.1f}万"
    else:
        return str(number)


def format_number_western(number: int) -> str:
    """将数字格式化为西方格式（千分位逗号）"""
    return f"{number:,}"


def normalize_number_display(text: str, prefer_chinese: bool = True) -> str:
    """规范化文本中的数字显示"""
    return fix_number_format(text, use_chinese_units=prefer_chinese)


# ==================== 兼容性别名（已废弃，保留以避免导入错误） ====================

def repair_truncated_json(text: str) -> str:
    """
    已废弃：不再尝试修复截断的JSON

    保留此函数是为了向后兼容，直接返回原文本。
    截断的JSON即使被修复成可解析格式，内容也是不完整的，
    强行解析会导致数据丢失。应该通过增加max_tokens或使用更强模型来解决。
    """
    logger.warning("repair_truncated_json 已废弃，不再尝试修复JSON")
    return text


def escape_inner_quotes(text: str) -> str:
    """
    已废弃：不再尝试转义内部引号

    保留此函数是为了向后兼容，直接返回原文本。
    如果JSON格式错误，应该通过完善提示词来解决，而不是猜测修复。
    """
    logger.warning("escape_inner_quotes 已废弃，不再尝试修复JSON")
    return text
