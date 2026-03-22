"""
自动入库触发器

提供异步入库触发功能，在生成完成后自动将数据入库到向量库。
失败不影响主流程，仅记录日志。

重要：后台任务必须创建独立的数据库会话，不能复用路由的会话。
"""

import logging
from .ingestion_service import CodingProjectIngestionService
from ..rag_common.auto_ingestion import (
    build_default_auto_ingestion_hooks,
)

logger = logging.getLogger(__name__)


_, schedule_ingestion = build_default_auto_ingestion_hooks(
    logger=logger,
    ingestion_service_cls=CodingProjectIngestionService,
    task_name_prefix="ingestion_",
    success_log_fmt="自动入库成功: project=%s type=%s total=%d added=%d updated=%d skipped=%d",
    success_log_attrs=("total_records", "added_count", "updated_count", "skipped_count"),
)

__all__ = [
    "schedule_ingestion",
]
