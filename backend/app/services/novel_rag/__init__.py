"""
小说项目RAG入库服务包

提供小说项目的向量入库、检索和完整性检查功能。
支持12种数据类型：灵感对话、故事概述、世界观设定、角色设定、角色关系、
角色状态、主角档案、分部大纲、章节大纲、章节正文、章节摘要、伏笔记录。
"""

from .data_types import (
    NovelDataType,
    BLUEPRINT_INGESTION_TYPES,
    PART_OUTLINE_INGESTION_TYPES,
    CHAPTER_OUTLINE_INGESTION_TYPES,
    CHAPTER_VERSION_INGESTION_TYPES,
    PROTAGONIST_INGESTION_TYPES,
)
from .content_splitter import NovelContentSplitter, NovelIngestionRecord, Section
from .ingestion_service import (
    NovelProjectIngestionService,
    IngestionResult,
    CompletenessReport,
)
from .auto_ingestion import (
    trigger_async_ingestion,
    schedule_ingestion,
    schedule_multiple_ingestions,
    trigger_blueprint_ingestion,
    trigger_inspiration_ingestion,
    trigger_part_outline_ingestion,
    trigger_chapter_outline_ingestion,
    trigger_chapter_version_ingestion,
    trigger_protagonist_ingestion,
)

__all__ = [
    # 数据类型
    "NovelDataType",
    "BLUEPRINT_INGESTION_TYPES",
    "PART_OUTLINE_INGESTION_TYPES",
    "CHAPTER_OUTLINE_INGESTION_TYPES",
    "CHAPTER_VERSION_INGESTION_TYPES",
    "PROTAGONIST_INGESTION_TYPES",
    # 内容分割
    "NovelContentSplitter",
    "NovelIngestionRecord",
    "Section",
    # 入库服务
    "NovelProjectIngestionService",
    "IngestionResult",
    "CompletenessReport",
    # 自动入库
    "trigger_async_ingestion",
    "schedule_ingestion",
    "schedule_multiple_ingestions",
    "trigger_blueprint_ingestion",
    "trigger_inspiration_ingestion",
    "trigger_part_outline_ingestion",
    "trigger_chapter_outline_ingestion",
    "trigger_chapter_version_ingestion",
    "trigger_protagonist_ingestion",
]
