"""
导入分析服务模块

提供外部小说TXT文件导入和智能分析功能。

TXT解析器支持自定义：
    - BaseTxtParser: 解析器基类，用户可继承实现自定义解析逻辑
    - DefaultTxtParser: 默认实现，支持常见章节格式
    - SimpleSplitParser: 简单分隔符解析器示例
    - TxtParser: DefaultTxtParser的别名（向后兼容）

使用自定义解析器：
    from app.services.import_analysis import BaseTxtParser, ParsedChapter

    class MyParser(BaseTxtParser):
        def parse_chapters(self, content: str):
            chapters = []
            # 自定义解析逻辑...
            return chapters, "my_parser", []

    parser = MyParser()
    result = parser.parse(file_bytes)
"""

from .service import ImportAnalysisService
from .txt_parser import (
    BaseTxtParser,
    DefaultTxtParser,
    SimpleSplitParser,
    TxtParser,  # 向后兼容别名
    ParsedChapter,
    ParseResult,
    count_chinese_characters,
    cn_to_arabic,
)
from .progress_tracker import ProgressTracker

__all__ = [
    "ImportAnalysisService",
    # 解析器类
    "BaseTxtParser",
    "DefaultTxtParser",
    "SimpleSplitParser",
    "TxtParser",
    # 数据类
    "ParsedChapter",
    "ParseResult",
    # 工具函数
    "count_chinese_characters",
    "cn_to_arabic",
    # 进度追踪
    "ProgressTracker",
]
