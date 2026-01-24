"""
小说项目自动入库触发器

提供异步入库触发功能，在生成完成后自动将数据入库到向量库。
失败不影响主流程，仅记录日志。

重要：后台任务必须创建独立的数据库会话，不能复用路由的会话。
"""

import asyncio
import logging
from typing import List, Optional

from .data_types import (
    NovelDataType,
    BLUEPRINT_INGESTION_TYPES,
    PART_OUTLINE_INGESTION_TYPES,
    CHAPTER_OUTLINE_INGESTION_TYPES,
    CHAPTER_VERSION_INGESTION_TYPES,
    PROTAGONIST_INGESTION_TYPES,
)
from .ingestion_service import NovelProjectIngestionService
from ..rag_common.auto_ingestion import run_ingestion_task

logger = logging.getLogger(__name__)


async def trigger_async_ingestion(
    project_id: str,
    user_id: str,
    data_type: NovelDataType,
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
) -> None:
    """
    异步触发入库

    在后台执行入库操作，失败不影响主流程。
    重要：此函数会创建独立的数据库会话和LLM服务，避免与路由会话冲突。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        data_type: 数据类型
        vector_store: 向量库服务（可选，为None时跳过）
        llm_service: LLM服务（可选，仅用于检查是否启用，实际使用独立实例）
    """
    if not vector_store or not llm_service:
        logger.debug(
            "跳过自动入库: project=%s type=%s (服务未启用)",
            project_id, data_type.value
        )
        return

    try:
        from ...services.llm_service import LLMService

        result = await run_ingestion_task(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
            service_factory=lambda session, store, _llm, uid: NovelProjectIngestionService(
                session=session,
                vector_store=store,
                llm_service=LLMService(session),
                user_id=uid
            ),
        )

        if result.success:
            logger.info(
                "自动入库成功: project=%s type=%s total=%d added=%d",
                project_id, data_type.value,
                result.total_records, result.added_count
            )
        else:
            logger.warning(
                "自动入库失败: project=%s type=%s error=%s",
                project_id, data_type.value, result.error_message
            )

    except Exception as e:
        # 入库失败不影响主流程
        logger.error(
            "自动入库异常: project=%s type=%s error=%s",
            project_id, data_type.value, str(e)
        )


def schedule_ingestion(
    project_id: str,
    user_id: str,
    data_type: NovelDataType,
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
) -> None:
    """
    调度异步入库任务

    创建异步任务在后台执行入库，不阻塞当前流程。
    后台任务会创建独立的数据库会话，避免与路由会话冲突。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        data_type: 数据类型
        vector_store: 向量库服务
        llm_service: LLM服务
    """
    if not vector_store or not llm_service:
        return

    # 创建异步任务（使用独立的数据库会话）
    asyncio.create_task(
        trigger_async_ingestion(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
        ),
        name=f"novel_ingestion_{project_id}_{data_type.value}"
    )

    logger.debug(
        "已调度入库任务: project=%s type=%s",
        project_id, data_type.value
    )


def schedule_multiple_ingestions(
    project_id: str,
    user_id: str,
    data_types: List[NovelDataType],
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
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
    for data_type in data_types:
        schedule_ingestion(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
        )


async def trigger_blueprint_ingestion(
    project_id: str,
    user_id: str,
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
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
    if not vector_store or not llm_service:
        return

    for data_type in BLUEPRINT_INGESTION_TYPES:
        schedule_ingestion(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
        )


async def trigger_inspiration_ingestion(
    project_id: str,
    user_id: str,
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
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
    user_id: str,
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
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
    for data_type in PART_OUTLINE_INGESTION_TYPES:
        schedule_ingestion(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
        )


async def trigger_chapter_outline_ingestion(
    project_id: str,
    user_id: str,
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
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
    for data_type in CHAPTER_OUTLINE_INGESTION_TYPES:
        schedule_ingestion(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
        )


async def trigger_chapter_version_ingestion(
    project_id: str,
    user_id: str,
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
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
    for data_type in CHAPTER_VERSION_INGESTION_TYPES:
        schedule_ingestion(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
        )


async def trigger_protagonist_ingestion(
    project_id: str,
    user_id: str,
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
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
    for data_type in PROTAGONIST_INGESTION_TYPES:
        schedule_ingestion(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
        )


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
