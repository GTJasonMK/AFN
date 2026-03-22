"""
小说项目RAG入库服务包

提供小说项目的向量入库、检索和完整性检查功能。
支持16种数据类型：灵感对话、故事概述、世界观设定、蓝图元数据、角色设定、角色关系、
角色状态、主角档案、主角属性变更、分部大纲、章节大纲、章节正文、章节摘要、
关键事件、章节元数据、伏笔记录。

支持可配置的分块策略，可通过 NovelChunkStrategyManager 切换不同策略。
"""

from .data_types import (
    NovelDataType,
)
from .ingestion_service import NovelProjectIngestionService
from .auto_ingestion import (
    trigger_blueprint_ingestion,
    trigger_inspiration_ingestion,
    trigger_part_outline_ingestion,
    trigger_chapter_outline_ingestion,
    trigger_chapter_version_ingestion,
)

__all__ = [
    "NovelDataType",
    "NovelProjectIngestionService",
    "trigger_blueprint_ingestion",
    "trigger_inspiration_ingestion",
    "trigger_part_outline_ingestion",
    "trigger_chapter_outline_ingestion",
    "trigger_chapter_version_ingestion",
]
