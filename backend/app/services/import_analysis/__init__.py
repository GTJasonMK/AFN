"""
导入分析服务模块

提供外部小说TXT文件导入和智能分析功能。

模块结构：
    - service.py: 主服务类，协调导入和分析流程
    - txt_parser.py: TXT文件解析器（支持自定义）
    - progress_tracker.py: 分析进度跟踪
    - models.py: 数据结构定义
    - data_helper.py: 数据库操作辅助
    - summary_generator.py: 摘要生成器
    - outline_generator.py: 大纲生成器
    - blueprint_extractor.py: 蓝图提取器

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
from .models import ChapterSummary, ImportResult
from .data_helper import DataHelper
from .summary_generator import SummaryGenerator
from .outline_generator import OutlineGenerator
from .blueprint_extractor import BlueprintExtractor

__all__ = [
    # 主服务
    "ImportAnalysisService",
    # 解析器类
    "BaseTxtParser",
    "DefaultTxtParser",
    "SimpleSplitParser",
    "TxtParser",
    # 数据类
    "ParsedChapter",
    "ParseResult",
    "ChapterSummary",
    "ImportResult",
    # 工具函数
    "count_chinese_characters",
    "cn_to_arabic",
    # 进度追踪
    "ProgressTracker",
    # 子组件（高级用法）
    "DataHelper",
    "SummaryGenerator",
    "OutlineGenerator",
    "BlueprintExtractor",
]
