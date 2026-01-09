"""
自动入库触发器

提供异步入库触发功能，在生成完成后自动将数据入库到向量库。
失败不影响主流程，仅记录日志。

重要：后台任务必须创建独立的数据库会话，不能复用路由的会话。
"""

import asyncio
import logging
from typing import Any, Optional

from .data_types import CodingDataType, BLUEPRINT_INGESTION_TYPES
from .ingestion_service import CodingProjectIngestionService

logger = logging.getLogger(__name__)


async def trigger_async_ingestion(
    project_id: str,
    user_id: str,
    data_type: CodingDataType,
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> None:
    """
    异步触发入库

    在后台执行入库操作，失败不影响主流程。
    重要：此函数会创建独立的数据库会话，避免与路由会话冲突。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        data_type: 数据类型
        vector_store: 向量库服务（可选，为None时跳过）
        llm_service: LLM服务（可选，为None时跳过）
    """
    if not vector_store or not llm_service:
        logger.debug(
            "跳过自动入库: project=%s type=%s (服务未启用)",
            project_id, data_type.value
        )
        return

    try:
        # 创建独立的数据库会话，避免与路由会话冲突
        from ...db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            service = CodingProjectIngestionService(
                session=session,
                vector_store=vector_store,
                llm_service=llm_service,
                user_id=user_id
            )

            result = await service.ingest_by_type(project_id, data_type)

            if result.success:
                logger.info(
                    "自动入库成功: project=%s type=%s total=%d added=%d updated=%d skipped=%d",
                    project_id, data_type.value,
                    result.total_records, result.added_count,
                    result.updated_count, result.skipped_count
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
    data_type: CodingDataType,
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
        name=f"ingestion_{project_id}_{data_type.value}"
    )

    logger.debug(
        "已调度入库任务: project=%s type=%s",
        project_id, data_type.value
    )


async def trigger_blueprint_ingestion(
    project_id: str,
    user_id: str,
    vector_store: Optional[any] = None,
    llm_service: Optional[any] = None,
) -> None:
    """
    触发蓝图相关数据入库

    蓝图生成完成后调用，入库：架构设计、技术栈、核心需求、技术挑战。
    后台任务会创建独立的数据库会话，避免与路由会话冲突。

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


__all__ = [
    "trigger_async_ingestion",
    "schedule_ingestion",
    "trigger_blueprint_ingestion",
]
