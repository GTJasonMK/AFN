"""
章节版本处理器

负责处理LLM生成的章节版本数据，包括解析和提取内容。
"""

import logging
import json
from typing import Any, Dict, List, Tuple

from ...utils.json_utils import remove_think_tags

logger = logging.getLogger(__name__)


class ChapterVersionProcessor:
    """
    章节版本处理器

    负责处理LLM生成的版本数据，提取content和metadata。

    使用方式：
        processor = ChapterVersionProcessor()
        contents, metadata = processor.process_versions(raw_versions)
    """

    # 可能包含章节内容的字段名（按优先级排序）
    # full_content 应该排在最前面，因为它明确表示"完整内容"
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

    def process_versions(self, raw_versions: List[Any]) -> Tuple[List[str], List[Dict]]:
        """
        处理生成的版本数据，提取content和metadata

        Args:
            raw_versions: 原始版本数据列表

        Returns:
            tuple: (contents, metadata)
        """
        contents: List[str] = []
        metadata: List[Dict] = []

        for idx, variant in enumerate(raw_versions):
            if isinstance(variant, dict):
                # 按优先级检查可能的内容字段
                content = self._extract_content_from_dict(variant)
                # 清理可能残留的think标签
                content = remove_think_tags(content)
                contents.append(content)
                metadata.append(variant)
                logger.debug("版本 %d 内容提取完成，长度: %d", idx + 1, len(content))
            else:
                # 纯文本，清理think标签
                content = remove_think_tags(str(variant))
                contents.append(content)
                metadata.append({"raw": variant})
                logger.debug("版本 %d 为纯文本，长度: %d", idx + 1, len(content))

        return contents, metadata

    def _extract_content_from_dict(self, variant: Dict[str, Any]) -> str:
        """
        从字典中提取内容

        按优先级检查多种可能的字段名，如果都不存在则尝试提取
        最长的字符串值作为内容。

        Args:
            variant: 版本数据字典

        Returns:
            提取的内容字符串
        """
        # 调试：打印字典的所有键
        logger.info("[DEBUG] _extract_content_from_dict - 输入字典键: %s", list(variant.keys()))

        # 1. 按优先级检查已知的内容字段名
        for field_name in self.CONTENT_FIELD_NAMES:
            if field_name in variant:
                value = variant[field_name]
                logger.info(
                    "[DEBUG] _extract_content_from_dict - 检查字段 '%s': 类型=%s, 是字符串=%s, 值前100字符=%s",
                    field_name,
                    type(value).__name__,
                    isinstance(value, str),
                    repr(str(value)[:100]) if value else "None"
                )
                # 如果是字符串，直接返回（不再尝试解析为JSON，避免复杂问题）
                if isinstance(value, str) and value.strip():
                    logger.info("[DEBUG] _extract_content_from_dict - 成功从字段 '%s' 提取，长度: %d", field_name, len(value))
                    return value
                # 如果是字典，递归提取
                elif isinstance(value, dict):
                    nested = self._extract_content_from_dict(value)
                    if nested and not nested.strip().startswith("{"):
                        logger.info("[DEBUG] _extract_content_from_dict - 从嵌套字段 '%s' 提取，长度: %d", field_name, len(nested))
                        return nested

        # 2. 找到字典中最长的字符串值
        longest_str = ""
        longest_key = ""
        for key, value in variant.items():
            if isinstance(value, str) and len(value) > len(longest_str):
                longest_str = value
                longest_key = key

        # 如果找到了字符串，返回它
        if longest_str.strip():
            logger.info("[DEBUG] _extract_content_from_dict - 使用最长字符串字段 '%s'，长度: %d", longest_key, len(longest_str))
            return longest_str

        # 3. 检查是否有嵌套的字典内容
        for key, value in variant.items():
            if isinstance(value, dict):
                nested_content = self._extract_content_from_dict(value)
                if nested_content.strip() and not nested_content.startswith("{"):
                    logger.info("[DEBUG] _extract_content_from_dict - 从嵌套字段 '%s' 提取到内容", key)
                    return nested_content

        # 4. 最后的fallback：记录警告并返回JSON
        logger.warning(
            "[DEBUG] _extract_content_from_dict - 无法提取内容，返回JSON。字典键: %s",
            list(variant.keys())
        )
        # 过滤掉明显的元数据字段
        metadata_fields = {"metadata", "meta", "info", "stats", "analysis", "notes"}
        filtered = {k: v for k, v in variant.items() if k.lower() not in metadata_fields}

        if filtered:
            return json.dumps(filtered, ensure_ascii=False, indent=2)
        return json.dumps(variant, ensure_ascii=False, indent=2)


# 模块级单例
_default_processor: ChapterVersionProcessor = None


def get_version_processor() -> ChapterVersionProcessor:
    """获取默认的版本处理器实例"""
    global _default_processor
    if _default_processor is None:
        _default_processor = ChapterVersionProcessor()
    return _default_processor


__all__ = [
    "ChapterVersionProcessor",
    "get_version_processor",
]
