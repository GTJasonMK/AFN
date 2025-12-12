"""
章节版本处理器

负责处理LLM生成的章节版本数据，包括解析和提取内容。
"""

import json
from typing import Any, Dict, List, Tuple


class ChapterVersionProcessor:
    """
    章节版本处理器

    负责处理LLM生成的版本数据，提取content和metadata。

    使用方式：
        processor = ChapterVersionProcessor()
        contents, metadata = processor.process_versions(raw_versions)
    """

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

        for variant in raw_versions:
            if isinstance(variant, dict):
                # 按优先级检查可能的内容字段（writing.md提示词中使用的是full_content）
                content = self._extract_content_from_dict(variant)
                contents.append(content)
                metadata.append(variant)
            else:
                contents.append(str(variant))
                metadata.append({"raw": variant})

        return contents, metadata

    def _extract_content_from_dict(self, variant: Dict[str, Any]) -> str:
        """
        从字典中提取内容

        按优先级检查以下字段:
        1. content
        2. full_content (writing.md提示词要求的格式)
        3. chapter_content

        Args:
            variant: 版本数据字典

        Returns:
            提取的内容字符串
        """
        # 优先检查 content 字段
        if "content" in variant and isinstance(variant["content"], str):
            return variant["content"]

        # 检查 full_content 字段（writing.md提示词要求的格式）
        if "full_content" in variant and isinstance(variant["full_content"], str):
            return variant["full_content"]

        # 检查 chapter_content 字段
        if "chapter_content" in variant:
            return str(variant["chapter_content"])

        # 如果所有预期字段都不存在，fallback到整个dict的序列化
        return json.dumps(variant, ensure_ascii=False)


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
