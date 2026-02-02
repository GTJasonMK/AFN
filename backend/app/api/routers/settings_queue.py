"""
队列配置导入导出路由

包含：
- /queue-config/export 导出
- /queue-config/import 导入
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...core.dependencies import require_admin_user
from .settings_models import ConfigImportResult
from .settings_utils import load_config, save_config

logger = logging.getLogger(__name__)
router = APIRouter()


class QueueConfigExportData(BaseModel):
    """队列配置导出数据"""

    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="queue", description="导出类型")
    config: Dict[str, Any] = Field(..., description="配置数据")


@router.get("/queue-config/export")
async def export_queue_config() -> QueueConfigExportData:
    """
    导出队列配置

    Returns:
        包含队列配置的JSON数据
    """
    from ...services.queue import ImageRequestQueue, LLMRequestQueue

    llm_queue = LLMRequestQueue.get_instance()
    image_queue = ImageRequestQueue.get_instance()

    return QueueConfigExportData(
        export_time=datetime.now(timezone.utc).isoformat(),
        config={
            "llm_max_concurrent": llm_queue.max_concurrent,
            "image_max_concurrent": image_queue.max_concurrent,
        },
    )


@router.post("/queue-config/import", response_model=ConfigImportResult, dependencies=[Depends(require_admin_user)])
async def import_queue_config(import_data: dict) -> ConfigImportResult:
    """
    导入队列配置

    Args:
        import_data: 导入的配置数据

    Returns:
        导入结果
    """
    from ...services.queue import ImageRequestQueue, LLMRequestQueue

    details = []

    try:
        # 验证导入数据格式
        if import_data.get("export_type") != "queue":
            return ConfigImportResult(success=False, message="导入数据类型不匹配，期望 'queue'", details=[])

        config_data = import_data.get("config", {})
        if not config_data:
            return ConfigImportResult(success=False, message="导入数据中没有配置信息", details=[])

        llm_queue = LLMRequestQueue.get_instance()
        image_queue = ImageRequestQueue.get_instance()

        # 更新LLM队列并发数
        if "llm_max_concurrent" in config_data:
            value = config_data["llm_max_concurrent"]
            if 1 <= value <= 10:
                llm_queue.set_max_concurrent(value)
                details.append(f"LLM队列并发数已更新为 {value}")
            else:
                details.append(f"LLM队列并发数 {value} 超出范围(1-10)，已跳过")

        # 更新图片队列并发数
        if "image_max_concurrent" in config_data:
            value = config_data["image_max_concurrent"]
            if 1 <= value <= 10:
                image_queue.set_max_concurrent(value)
                details.append(f"图片队列并发数已更新为 {value}")
            else:
                details.append(f"图片队列并发数 {value} 超出范围(1-10)，已跳过")

        # 持久化到config.json
        current_config = load_config()
        current_config["llm_max_concurrent"] = llm_queue.max_concurrent
        current_config["image_max_concurrent"] = image_queue.max_concurrent
        save_config(current_config)

        return ConfigImportResult(success=True, message="队列配置导入成功", details=details)

    except Exception as e:
        logger.error("导入队列配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(success=False, message=f"导入失败: {str(e)}", details=details)


__all__ = ["router", "QueueConfigExportData", "import_queue_config"]
