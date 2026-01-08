"""
编程项目RAG入库服务包

提供编程项目的向量入库、检索和完整性检查功能。
支持10种数据类型：灵感对话、架构设计、技术栈、核心需求、技术挑战、
系统划分、模块定义、功能大纲、依赖关系、功能Prompt。
"""

from .data_types import CodingDataType, BLUEPRINT_INGESTION_TYPES
from .content_splitter import ContentSplitter, IngestionRecord, Section
from .ingestion_service import (
    CodingProjectIngestionService,
    IngestionResult,
    CompletenessReport,
)
from .auto_ingestion import (
    trigger_async_ingestion,
    schedule_ingestion,
    trigger_blueprint_ingestion,
)

__all__ = [
    # 数据类型
    "CodingDataType",
    "BLUEPRINT_INGESTION_TYPES",
    # 内容分割
    "ContentSplitter",
    "IngestionRecord",
    "Section",
    # 入库服务
    "CodingProjectIngestionService",
    "IngestionResult",
    "CompletenessReport",
    # 自动入库
    "trigger_async_ingestion",
    "schedule_ingestion",
    "trigger_blueprint_ingestion",
]
