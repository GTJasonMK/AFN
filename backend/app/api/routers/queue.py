"""
队列管理API路由

提供队列状态查询和配置管理功能。
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

from ...schemas.queue import (
    QueueStatus,
    QueueStatusResponse,
    QueueConfigResponse,
    QueueConfigUpdate,
)
from ...services.queue import LLMRequestQueue, ImageRequestQueue
from ...core.config import _get_config_file_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/queue", tags=["队列管理"])


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


@router.put("/config", response_model=QueueConfigResponse)
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
    _save_queue_config_to_file(
        llm_max_concurrent=llm_queue.max_concurrent,
        image_max_concurrent=image_queue.max_concurrent,
    )

    return QueueConfigResponse(
        llm_max_concurrent=llm_queue.max_concurrent,
        image_max_concurrent=image_queue.max_concurrent,
    )


def _save_queue_config_to_file(llm_max_concurrent: int, image_max_concurrent: int) -> None:
    """
    将队列配置保存到config.json文件

    与现有的高级配置保存机制保持一致。
    """
    config_file = _get_config_file_path()

    # 读取现有配置
    existing_config = {}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
        except Exception as e:
            logger.warning("读取config.json失败: %s", e)

    # 更新队列配置
    existing_config['llm_max_concurrent'] = llm_max_concurrent
    existing_config['image_max_concurrent'] = image_max_concurrent

    # 确保目录存在
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # 保存配置
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, indent=2, ensure_ascii=False)
        logger.info("队列配置已保存到: %s", config_file)
    except Exception as e:
        logger.error("保存config.json失败: %s", e)
