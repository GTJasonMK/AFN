"""
部分大纲服务 - 向后兼容模块

此文件作为兼容性shim，所有实现已迁移至 part_outline/ 子模块。
新代码请直接导入 from app.services.part_outline import ...

模块结构：
- part_outline/parser.py: LLM响应解析
- part_outline/model_factory.py: 模型创建
- part_outline/context_retriever.py: 上下文检索
- part_outline/workflow.py: 完整工作流
- part_outline/service.py: 核心服务（协调者）
"""

import warnings

warnings.warn(
    "从 'app.services.part_outline_service' 导入已废弃，"
    "请改用 'from app.services.part_outline import ...'",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有公开API，保持向后兼容
from .part_outline import (
    # 解析器
    PartOutlineParser,
    get_part_outline_parser,
    # 模型工厂
    PartOutlineModelFactory,
    get_part_outline_factory,
    # 上下文检索
    PartOutlineContextRetriever,
    # 工作流
    PartOutlineWorkflow,
    # 核心服务
    PartOutlineService,
    GenerationCancelledException,
)

__all__ = [
    "PartOutlineParser",
    "get_part_outline_parser",
    "PartOutlineModelFactory",
    "get_part_outline_factory",
    "PartOutlineContextRetriever",
    "PartOutlineWorkflow",
    "PartOutlineService",
    "GenerationCancelledException",
]
