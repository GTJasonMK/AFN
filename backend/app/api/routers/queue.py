"""
队列管理API路由

提供队列状态查询和配置管理功能。
"""

import logging

from fastapi import APIRouter, Depends

from ...schemas.queue import (
    QueueStatus,
    QueueStatusResponse,
    QueueConfigResponse,
    QueueConfigUpdate,
)
from ...services.queue import LLMRequestQueue, ImageRequestQueue
from ...core.dependencies import get_default_user, require_admin_user
from .settings_utils import persist_config_updates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/queue", tags=["队列管理"], dependencies=[Depends(get_default_user)])


@router.get("/status", response_model=QueueStatusResponse)
async def get_queue_status() -> QueueStatusResponse:
    """
    获取所有队列的当前状态

    返回LLM队列和图片生成队列的状态信息，包括：
    - active: 正在执行的请求数
    - waiting: 等待中的请求数
    - max_concurrent: 最大并发数
    - total_processed: 已处理总数
    """
    llm_queue = LLMRequestQueue.get_instance()
    image_queue = ImageRequestQueue.get_instance()

    return QueueStatusResponse(
        llm=QueueStatus(**llm_queue.get_status()),
        image=QueueStatus(**image_queue.get_status()),
    )


@router.get("/config", response_model=QueueConfigResponse)
async def get_queue_config() -> QueueConfigResponse:
    """
    获取当前队列配置

    返回LLM和图片生成队列的最大并发数配置。
    """
    llm_queue = LLMRequestQueue.get_instance()
    image_queue = ImageRequestQueue.get_instance()

    return QueueConfigResponse(
        llm_max_concurrent=llm_queue.max_concurrent,
        image_max_concurrent=image_queue.max_concurrent,
    )


@router.put("/config", response_model=QueueConfigResponse, dependencies=[Depends(require_admin_user)])
async def update_queue_config(config: QueueConfigUpdate) -> QueueConfigResponse:
    """
    更新队列配置（运行时生效并持久化到config.json）

    可以单独更新LLM或图片生成队列的并发数，不需要的字段可以不传。
    配置会同时保存到config.json文件，重启后仍然生效。
    """
    llm_queue = LLMRequestQueue.get_instance()
    image_queue = ImageRequestQueue.get_instance()

    # 更新运行时配置
    if config.llm_max_concurrent is not None:
        llm_queue.set_max_concurrent(config.llm_max_concurrent)
        logger.info("LLM队列并发数已更新为: %d", config.llm_max_concurrent)

    if config.image_max_concurrent is not None:
        image_queue.set_max_concurrent(config.image_max_concurrent)
        logger.info("图片队列并发数已更新为: %d", config.image_max_concurrent)

    # 持久化到config.json
    persist_config_updates(
        {
            "llm_max_concurrent": llm_queue.max_concurrent,
            "image_max_concurrent": image_queue.max_concurrent,
        }
    )

    return QueueConfigResponse(
        llm_max_concurrent=llm_queue.max_concurrent,
        image_max_concurrent=image_queue.max_concurrent,
    )
