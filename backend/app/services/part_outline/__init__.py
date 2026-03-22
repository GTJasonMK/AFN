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

from .workflow import PartOutlineWorkflow
from .service import PartOutlineService

__all__ = [
    # 工作流
    "PartOutlineWorkflow",
    # 核心服务
    "PartOutlineService",
]
