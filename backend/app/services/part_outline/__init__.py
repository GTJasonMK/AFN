"""
部分大纲模块

将原来的部分大纲服务拆分为多个职责单一的子模块：
- parser: LLM响应解析
- model_factory: 模型创建
- context_retriever: 上下文检索
- workflow: 部分大纲生成工作流
- chapter_outline_workflow: 章节大纲生成工作流
- service: 核心服务（协调者）
"""

from .parser import PartOutlineParser, get_part_outline_parser
from .model_factory import PartOutlineModelFactory, get_part_outline_factory
from .context_retriever import PartOutlineContextRetriever
from .workflow import PartOutlineWorkflow
from .chapter_outline_workflow import (
    ChapterOutlineWorkflow,
    GenerationCancelledException,
    get_chapter_outline_workflow,
)
from .service import PartOutlineService

__all__ = [
    # 解析器
    "PartOutlineParser",
    "get_part_outline_parser",
    # 模型工厂
    "PartOutlineModelFactory",
    "get_part_outline_factory",
    # 上下文检索
    "PartOutlineContextRetriever",
    # 工作流
    "PartOutlineWorkflow",
    "ChapterOutlineWorkflow",
    "get_chapter_outline_workflow",
    # 核心服务
    "PartOutlineService",
    # 异常
    "GenerationCancelledException",
]
