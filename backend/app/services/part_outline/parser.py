"""
部分大纲LLM响应解析器

负责解析LLM返回的部分大纲JSON数据。
"""

import json
import logging
from typing import Dict, List

from ...exceptions import JSONParseError
from ...utils.json_utils import remove_think_tags, unwrap_markdown_json, repair_truncated_json

logger = logging.getLogger(__name__)


class PartOutlineParser:
    """
    部分大纲解析器

    负责解析LLM返回的部分大纲JSON，支持批量解析和单个解析两种模式。
    """

    def _parse_json_with_repair(self, text: str, context: str) -> Dict:
        """
        解析JSON，失败时尝试修复

        Args:
            text: 待解析的JSON文本
            context: 错误上下文描述

        Returns:
            Dict: 解析后的字典

        Raises:
            JSONParseError: 如果解析和修复都失败
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("JSON解析失败，尝试修复: %s", exc)
            # 尝试修复被截断的JSON
            try:
                repaired = repair_truncated_json(text)
                result = json.loads(repaired)
                logger.info("JSON修复成功: %s", context)
                return result
            except json.JSONDecodeError as repair_exc:
                # 记录更详细的错误信息
                logger.error(
                    "解析%sJSON失败（修复后仍失败）: %s\n原始位置: 行%d 列%d\n内容预览: %s",
                    context,
                    str(repair_exc),
                    exc.lineno,
                    exc.colno,
                    text[:500] if text else "空"
                )
                raise JSONParseError(context, "格式错误") from repair_exc

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
        result = self._parse_json_with_repair(unwrapped, "部分大纲")

        parts_data = result.get("parts", [])
        if not parts_data:
            raise JSONParseError("部分大纲", "LLM未返回有效的部分大纲")

        return parts_data

    def parse_single_part(self, response: str, expected_part_number: int) -> Dict:
        """
        解析LLM返回的单个部分大纲JSON（串行生成模式）

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
        part_data = self._parse_json_with_repair(unwrapped, f"部分大纲第{expected_part_number}部分")

        # 验证part_number
        if part_data.get("part_number") != expected_part_number:
            logger.warning(
                "LLM返回的部分编号(%s)与期望(%s)不符，使用期望值",
                part_data.get("part_number"),
                expected_part_number
            )
            part_data["part_number"] = expected_part_number

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
        result = self._parse_json_with_repair(unwrapped, "章节大纲")

        chapters_data = result.get("chapter_outline", [])
        if not chapters_data:
            raise JSONParseError("章节大纲", "LLM未返回有效的章节大纲")

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
