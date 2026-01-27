"""
小说项目自动入库触发器

提供异步入库触发功能，在生成完成后自动将数据入库到向量库。
失败不影响主流程，仅记录日志。

重要：后台任务必须创建独立的数据库会话，不能复用路由的会话。
"""

import logging
from typing import Any, Optional, Sequence

from .data_types import (
    NovelDataType,
    BLUEPRINT_INGESTION_TYPES,
    PART_OUTLINE_INGESTION_TYPES,
    CHAPTER_OUTLINE_INGESTION_TYPES,
    CHAPTER_VERSION_INGESTION_TYPES,
    PROTAGONIST_INGESTION_TYPES,
)
from .ingestion_service import NovelProjectIngestionService
from ..rag_common.auto_ingestion import (
    build_default_auto_ingestion_hooks,
    schedule_multiple_ingestions as _schedule_multiple_ingestions,
)

logger = logging.getLogger(__name__)


trigger_async_ingestion, schedule_ingestion = build_default_auto_ingestion_hooks(
    logger=logger,
    ingestion_service_cls=NovelProjectIngestionService,
    task_name_prefix="novel_ingestion_",
    success_log_fmt="自动入库成功: project=%s type=%s total=%d added=%d",
    success_log_attrs=("total_records", "added_count"),
)


def schedule_multiple_ingestions(
    project_id: str,
    user_id: int,
    data_types: Sequence[NovelDataType],
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> None:
    """
    调度多个类型的异步入库任务

    Args:
        project_id: 项目ID
        user_id: 用户ID
        data_types: 数据类型列表
        vector_store: 向量库服务
        llm_service: LLM服务
    """
    _schedule_multiple_ingestions(schedule_ingestion, project_id, user_id, data_types, vector_store, llm_service)


async def trigger_blueprint_ingestion(
    project_id: str,
    user_id: int,
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> None:
    """
    触发蓝图相关数据入库

    蓝图生成完成后调用，入库：故事概述、世界观设定、角色设定、角色关系。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        vector_store: 向量库服务
        llm_service: LLM服务
    """
    schedule_multiple_ingestions(project_id, user_id, BLUEPRINT_INGESTION_TYPES, vector_store, llm_service)


async def trigger_inspiration_ingestion(
    project_id: str,
    user_id: int,
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> None:
    """
    触发灵感对话入库

    蓝图生成完成后调用，入库灵感对话历史。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        vector_store: 向量库服务
        llm_service: LLM服务
    """
    schedule_ingestion(
        project_id=project_id,
        user_id=user_id,
        data_type=NovelDataType.INSPIRATION,
        vector_store=vector_store,
        llm_service=llm_service,
    )


async def trigger_part_outline_ingestion(
    project_id: str,
    user_id: int,
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> None:
    """
    触发分部大纲入库

    分部大纲生成完成后调用。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        vector_store: 向量库服务
        llm_service: LLM服务
    """
    schedule_multiple_ingestions(project_id, user_id, PART_OUTLINE_INGESTION_TYPES, vector_store, llm_service)


async def trigger_chapter_outline_ingestion(
    project_id: str,
    user_id: int,
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> None:
    """
    触发章节大纲入库

    章节大纲生成完成后调用。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        vector_store: 向量库服务
        llm_service: LLM服务
    """
    schedule_multiple_ingestions(project_id, user_id, CHAPTER_OUTLINE_INGESTION_TYPES, vector_store, llm_service)


async def trigger_chapter_version_ingestion(
    project_id: str,
    user_id: int,
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> None:
    """
    触发章节版本选择后的入库

    章节版本选择后调用，入库：章节正文、章节摘要、伏笔记录、角色状态。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        vector_store: 向量库服务
        llm_service: LLM服务
    """
    schedule_multiple_ingestions(project_id, user_id, CHAPTER_VERSION_INGESTION_TYPES, vector_store, llm_service)


async def trigger_protagonist_ingestion(
    project_id: str,
    user_id: int,
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> None:
    """
    触发主角档案入库

    主角档案更新后调用。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        vector_store: 向量库服务
        llm_service: LLM服务
    """
    schedule_multiple_ingestions(project_id, user_id, PROTAGONIST_INGESTION_TYPES, vector_store, llm_service)


__all__ = [
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
