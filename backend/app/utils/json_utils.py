import re
import json
import logging
from typing import Any, Dict, Optional, Tuple

from ..exceptions import JSONParseError

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
    """
    智能替换中文引号为英文引号（仅替换JSON结构性引号）

    只替换用作JSON结构的中文引号（键名和值的定界符），
    保留字符串内容中的中文引号不变，避免破坏JSON结构。

    策略：
    1. 先尝试直接解析，如果成功则不需要替换
    2. 如果失败，只替换可能用作JSON结构的中文引号
    """
    if not text:
        return text

    # 快速检查：如果没有中文引号，直接返回
    # 中文双引号: "" (\u201c \u201d)，中文单引号: '' (\u2018 \u2019)
    if '\u201c' not in text and '\u201d' not in text and '\u2018' not in text and '\u2019' not in text:
        return text

    # 尝试直接解析，如果成功说明中文引号只在字符串内容中，无需替换
    try:
        json.loads(text)
        return text  # JSON有效，保持原样
    except json.JSONDecodeError:
        pass  # 需要尝试修复

    # 策略：只替换明确用作JSON结构的中文引号
    # 特征：紧跟在 { , : [ 后面的引号，或紧跟在值后面的引号
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
            # 在字符串内部，保持原样（包括中文引号）
            result.append(char)
            i += 1
            continue

        # 在字符串外部，检查是否是中文引号用作结构
        if char in '\u201c\u201d':
            # 中文双引号在字符串外，替换为英文引号
            result.append('"')
            i += 1
            continue

        if char in '\u2018\u2019':
            # 中文单引号在字符串外（JSON不使用单引号，但以防万一）
            result.append("'")
            i += 1
            continue

        result.append(char)
        i += 1

    return ''.join(result)


def escape_inner_quotes(text: str) -> str:
    """
    转义JSON字符串内部的未转义引号

    当LLM在JSON字符串值内使用未转义的英文引号时（如对话），
    尝试识别并转义这些引号。

    策略：
    1. 解析JSON结构，找出所有字符串值的范围
    2. 在字符串值内部，将未转义的引号转义为 \\"

    注意：这是一个启发式修复，可能不完美，但能处理常见情况。
    """
    if not text:
        return text

    # 首先尝试直接解析
    try:
        json.loads(text)
        return text  # JSON有效，无需修复
    except json.JSONDecodeError:
        pass

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
            if not in_string:
                # 开始字符串
                in_string = True
                string_start = i
                result.append(char)
            else:
                # 可能是结束字符串，也可能是内部的引号
                # 检查下一个字符来判断
                next_i = i + 1
                # 跳过空白
                while next_i < len(text) and text[next_i] in ' \t\n\r':
                    next_i += 1

                if next_i >= len(text):
                    # 到达文本末尾，这是结束引号
                    in_string = False
                    result.append(char)
                elif text[next_i] in ',}]:':
                    # 后面是JSON分隔符，这是结束引号
                    in_string = False
                    result.append(char)
                else:
                    # 后面是其他字符，这可能是内部引号，需要转义
                    # 检查是否是常见的对话模式: "xxx"yyy"
                    # 在这种情况下，转义这个引号
                    result.append('\\')
                    result.append(char)
            i += 1
            continue

        result.append(char)
        i += 1

    return ''.join(result)


def repair_truncated_json(text: str) -> str:
    """
    尝试修复被截断的JSON字符串

    当LLM响应被截断时，JSON可能缺少闭合括号或字符串被中间截断。
    此函数尝试通过多种策略来修复：
    1. 如果字符串被截断，尝试闭合字符串
    2. 移除不完整的键值对
    3. 添加缺失的闭合括号

    Args:
        text: 可能被截断的JSON字符串

    Returns:
        修复后的JSON字符串
    """
    if not text:
        return text

    text = text.rstrip()

    def analyze_json(json_text: str):
        """分析JSON结构，返回括号栈和是否在字符串中"""
        stack = []
        in_str = False
        escape = False
        for c in json_text:
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == '{':
                stack.append('}')
            elif c == '[':
                stack.append(']')
            elif c in '}]':
                if stack and stack[-1] == c:
                    stack.pop()
        return stack, in_str

    bracket_stack, in_string = analyze_json(text)

    # 如果有未闭合的括号或字符串，尝试修复
    if bracket_stack or in_string:
        if in_string:
            # 策略1: 尝试直接闭合字符串
            # 找到最后一个开始字符串的引号位置
            last_quote_pos = text.rfind('"')

            if last_quote_pos > 0:
                # 策略1a: 直接在末尾添加引号闭合字符串
                repaired_v1 = text + '"'
                stack_v1, in_str_v1 = analyze_json(repaired_v1)

                if not in_str_v1:
                    # 字符串已闭合，现在处理括号
                    # 移除末尾可能的不完整内容（如未完成的逗号后的内容）
                    repaired_v1 = repaired_v1.rstrip().rstrip(',')
                    if stack_v1:
                        closing = ''.join(reversed(stack_v1))
                        repaired_v1 += closing
                        logger.info("JSON修复(策略1a): 闭合字符串并添加 '%s'", closing)
                    else:
                        logger.info("JSON修复(策略1a): 仅闭合字符串")

                    # 验证修复后的JSON
                    try:
                        json.loads(repaired_v1)
                        return repaired_v1
                    except json.JSONDecodeError:
                        pass  # 尝试下一个策略

                # 策略1b: 回退到上一个完整的键值对
                # 寻找这个字符串字段的开始位置（键名后的冒号和引号）
                # 格式通常是: "key": "value...
                search_start = max(0, last_quote_pos - 200)
                key_pattern = r'"([^"]+)"\s*:\s*"$'
                text_to_search = text[search_start:last_quote_pos + 1]
                match = re.search(key_pattern, text_to_search)

                if match:
                    # 找到了键名，回退到键名之前
                    key_start_in_search = match.start()
                    absolute_key_start = search_start + key_start_in_search

                    # 回退到这个键之前的逗号或开括号
                    for i in range(absolute_key_start - 1, -1, -1):
                        if text[i] in ',{[':
                            cut_pos = i + 1 if text[i] in '{[' else i
                            text = text[:cut_pos].rstrip()
                            if text.endswith(','):
                                text = text[:-1]
                            logger.info("JSON修复(策略1b): 移除不完整的键值对")
                            break
                else:
                    # 没有找到键名模式，使用简化的回退策略
                    # 回退到最近的完整结构边界
                    for i in range(last_quote_pos - 1, -1, -1):
                        if text[i] in ',{[':
                            # 检查逗号前是否有完整的值
                            if text[i] == ',':
                                # 保留逗号前的内容
                                text = text[:i].rstrip()
                            else:
                                # 保留括号
                                text = text[:i + 1].rstrip()
                            logger.info("JSON修复(策略1b-简化): 回退到边界字符")
                            break

                # 重新分析修复后的文本
                bracket_stack, in_string = analyze_json(text)

        # 移除末尾的逗号和空白
        text = text.rstrip()
        if text.endswith(','):
            text = text[:-1].rstrip()

        # 处理末尾是冒号的情况（键没有值）
        if text.endswith(':'):
            # 回退到冒号前的引号（键名结束）
            for i in range(len(text) - 2, -1, -1):
                if text[i] in ',{[':
                    text = text[:i + 1].rstrip() if text[i] in '{[' else text[:i].rstrip()
                    break
            bracket_stack, in_string = analyze_json(text)

        # 最后移除可能残留的逗号
        text = text.rstrip().rstrip(',')

        # 重新分析并添加闭合符号
        bracket_stack, in_string = analyze_json(text)

        if bracket_stack:
            closing_chars = ''.join(reversed(bracket_stack))
            text += closing_chars
            logger.info("JSON修复: 添加了闭合符号 '%s'", closing_chars)

    return text


def parse_llm_json_or_fail(
    raw_text: str,
    error_context: str,
) -> Dict[str, Any]:
    """
    解析LLM返回的JSON，失败时抛出业务异常

    自动处理think标签和markdown包装，适用于Service/Router层。
    抛出的 JSONParseError 会被全局异常处理器转换为 HTTP 响应。

    Args:
        raw_text: LLM返回的原始文本（可能包含markdown、think标签等）
        error_context: 错误上下文描述（用于日志和错误消息）

    Returns:
        解析后的字典

    Raises:
        JSONParseError: JSON解析失败

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
    except json.JSONDecodeError as first_exc:
        # 第一次解析失败，尝试多种修复策略

        # 策略1: 转义字符串内部的未转义引号
        try:
            escaped = escape_inner_quotes(normalized)
            result = json.loads(escaped)
            logger.info("JSON修复成功(转义内部引号): %s", error_context)
            return result
        except json.JSONDecodeError:
            pass

        # 策略2: 修复截断的JSON
        try:
            repaired = repair_truncated_json(normalized)
            result = json.loads(repaired)
            logger.info("JSON修复成功(截断修复): %s", error_context)
            return result
        except json.JSONDecodeError:
            pass

        # 策略3: 组合 - 先转义引号再修复截断
        try:
            escaped = escape_inner_quotes(normalized)
            repaired = repair_truncated_json(escaped)
            result = json.loads(repaired)
            logger.info("JSON修复成功(组合策略): %s", error_context)
            return result
        except json.JSONDecodeError as exc:
            # 所有策略都失败，记录详细错误
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
                detail_msg = "AI返回了对话内容而不是预期的结构化数据，请重试或调整对话内容"
            else:
                detail_msg = f"{exc.msg} (行{exc.lineno} 列{exc.colno})"

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
