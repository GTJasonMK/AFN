"""
自动入库触发器

提供异步入库触发功能，在生成完成后自动将数据入库到向量库。
失败不影响主流程，仅记录日志。

重要：后台任务必须创建独立的数据库会话，不能复用路由的会话。
"""

import logging
from typing import Any, Optional

from .data_types import CodingDataType, BLUEPRINT_INGESTION_TYPES
from .ingestion_service import CodingProjectIngestionService
from ..rag_common.auto_ingestion import (
    build_default_auto_ingestion_hooks,
    schedule_multiple_ingestions,
)

logger = logging.getLogger(__name__)


trigger_async_ingestion, schedule_ingestion = build_default_auto_ingestion_hooks(
    logger=logger,
    ingestion_service_cls=CodingProjectIngestionService,
    task_name_prefix="ingestion_",
    success_log_fmt="自动入库成功: project=%s type=%s total=%d added=%d updated=%d skipped=%d",
    success_log_attrs=("total_records", "added_count", "updated_count", "skipped_count"),
)


async def trigger_blueprint_ingestion(
    project_id: str,
    user_id: int,
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
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
    schedule_multiple_ingestions(schedule_ingestion, project_id, user_id, BLUEPRINT_INGESTION_TYPES, vector_store, llm_service)


__all__ = [
    "trigger_async_ingestion",
    "schedule_ingestion",
    "trigger_blueprint_ingestion",
]
