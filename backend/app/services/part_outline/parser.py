"""
部分大纲LLM响应解析器

负责解析LLM返回的部分大纲JSON数据。
采用简洁直接的方式，解析失败直接报错，依靠完善的提示词确保格式正确。
"""

import json
import logging
from typing import Dict, List

from ...exceptions import JSONParseError
from ...utils.json_utils import remove_think_tags, unwrap_markdown_json

logger = logging.getLogger(__name__)


class PartOutlineParser:
    """
    部分大纲解析器

    负责解析LLM返回的部分大纲JSON，支持批量解析和单个解析两种模式。
    解析失败直接报错，不尝试猜测修复。
    """

    def _parse_json(self, text: str, context: str) -> Dict:
        """
        解析JSON，失败直接报错

        Args:
            text: 待解析的JSON文本
            context: 错误上下文描述

        Returns:
            Dict: 解析后的字典

        Raises:
            JSONParseError: 如果解析失败
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # 检测是否是截断问题
            is_truncated = self._detect_truncation(text)

            logger.error(
                "解析%sJSON失败: %s\n位置: 行%d 列%d\n是否截断: %s\n内容预览: %s",
                context,
                exc.msg,
                exc.lineno,
                exc.colno,
                is_truncated,
                text[:500] if text else "空"
            )

            if is_truncated:
                raise JSONParseError(
                    context,
                    "LLM输出被截断，请在设置中增加 max_tokens 或使用输出能力更强的模型"
                ) from exc
            else:
                raise JSONParseError(
                    context,
                    f"JSON格式错误: {exc.msg} (行{exc.lineno} 列{exc.colno})"
                ) from exc

    def _detect_truncation(self, text: str) -> bool:
        """
        检测JSON是否被截断

        通过检查括号是否匹配来判断
        """
        if not text:
            return False

        # 统计括号
        brace_count = 0  # {}
        bracket_count = 0  # []
        in_string = False
        escape_next = False

        for char in text:
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue

            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1

        # 如果括号不匹配，说明被截断
        return brace_count != 0 or bracket_count != 0 or in_string

    def parse_multiple_parts(self, response: str) -> List[Dict]:
        """
        解析LLM返回的多个部分大纲JSON（批量模式）

        Args:
            response: LLM响应字符串

        Returns:
            List[Dict]: 部分大纲数据列表

        Raises:
            JSONParseError: 如果解析失败或数据无效
        """
        cleaned = remove_think_tags(response)
        unwrapped = unwrap_markdown_json(cleaned)
        result = self._parse_json(unwrapped, "部分大纲")

        parts_data = result.get("parts", [])
        if not parts_data:
            raise JSONParseError("部分大纲", "LLM未返回有效的部分大纲（缺少parts字段）")

        return parts_data

    def parse_single_part(self, response: str, expected_part_number: int) -> Dict:
        """
        解析LLM返回的单个部分大纲JSON（串行生成模式）

        支持两种格式：
        1. 平面对象: {"part_number": 1, "title": "...", ...}
        2. 包装数组: {"parts": [{"part_number": 1, ...}]}（会自动提取）

        Args:
            response: LLM响应字符串
            expected_part_number: 期望的部分编号

        Returns:
            Dict: 部分大纲数据

        Raises:
            JSONParseError: 如果解析失败或数据无效
        """
        cleaned = remove_think_tags(response)
        unwrapped = unwrap_markdown_json(cleaned)
        parsed = self._parse_json(unwrapped, f"部分大纲第{expected_part_number}部分")

        # 处理LLM可能返回的两种格式
        if "parts" in parsed and isinstance(parsed.get("parts"), list):
            # 包装数组格式，提取数据
            parts_list = parsed["parts"]
            if not parts_list:
                raise JSONParseError(
                    f"部分大纲第{expected_part_number}部分",
                    "LLM返回的parts数组为空"
                )

            # 尝试找到匹配期望编号的部分
            part_data = None
            for part in parts_list:
                if part.get("part_number") == expected_part_number:
                    part_data = part
                    logger.info("从parts数组中提取第%d部分", expected_part_number)
                    break

            if part_data is None:
                # 没找到匹配的，使用第一个
                part_data = parts_list[0]
                logger.warning(
                    "parts数组中未找到第%d部分，使用第一个元素",
                    expected_part_number
                )
        else:
            # 平面对象格式，直接使用
            part_data = parsed

        # 验证part_number
        if part_data.get("part_number") != expected_part_number:
            logger.warning(
                "LLM返回的部分编号(%s)与期望(%s)不符，使用期望值",
                part_data.get("part_number"),
                expected_part_number
            )
            part_data["part_number"] = expected_part_number

        # 记录解析结果
        logger.info(
            "第%d部分解析成功: title=%s, summary_len=%d, theme_len=%d, events=%d",
            expected_part_number,
            part_data.get("title", "无"),
            len(part_data.get("summary", "") or ""),
            len(part_data.get("theme", "") or ""),
            len(part_data.get("key_events", []) or []),
        )

        # 检查关键字段是否过于简略（仅警告，不阻止）
        summary = part_data.get("summary", "") or ""
        key_events = part_data.get("key_events", []) or []

        if len(summary) < 50:
            logger.warning(
                "第%d部分摘要过短(%d字符)，建议检查提示词或重新生成",
                expected_part_number,
                len(summary),
            )

        if len(key_events) < 3:
            logger.warning(
                "第%d部分关键事件过少(%d个)，建议检查提示词或重新生成",
                expected_part_number,
                len(key_events),
            )

        return part_data

    def parse_chapter_outlines(self, response: str) -> List[Dict]:
        """
        解析LLM返回的章节大纲JSON

        Args:
            response: LLM响应字符串

        Returns:
            List[Dict]: 章节大纲数据列表

        Raises:
            JSONParseError: 如果解析失败或数据无效
        """
        cleaned = remove_think_tags(response)
        unwrapped = unwrap_markdown_json(cleaned)
        result = self._parse_json(unwrapped, "章节大纲")

        chapters_data = result.get("chapter_outline", [])
        if not chapters_data:
            raise JSONParseError("章节大纲", "LLM未返回有效的章节大纲（缺少chapter_outline字段）")

        return chapters_data


# 模块级单例
_default_parser = None


def get_part_outline_parser() -> PartOutlineParser:
    """获取默认的部分大纲解析器实例"""
    global _default_parser
    if _default_parser is None:
        _default_parser = PartOutlineParser()
    return _default_parser


__all__ = [
    "PartOutlineParser",
    "get_part_outline_parser",
]
