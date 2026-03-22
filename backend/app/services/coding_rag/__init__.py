"""
编程项目RAG入库服务包

提供编程项目的向量入库、检索和完整性检查功能。
支持11种数据类型：灵感对话、架构设计、技术栈、核心需求、技术挑战、
系统划分、模块定义、功能大纲、依赖关系、功能Prompt、测试Prompt。

支持可配置的分块策略，可通过 ChunkStrategyManager 切换不同策略。
"""

from .data_types import CodingDataType
from .ingestion_service import CodingProjectIngestionService
from .auto_ingestion import schedule_ingestion

__all__ = [
    "CodingDataType",
    "CodingProjectIngestionService",
    "schedule_ingestion",
]
