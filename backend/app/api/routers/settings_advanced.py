"""
高级配置（advanced-config）路由

包含：
- /advanced-config 读取/更新
- /advanced-config/export 导出
- /advanced-config/import 导入
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...core.config import settings
from .settings_models import ConfigImportResult
from .settings_utils import (
    build_hot_reload_response,
    load_config,
    persist_config_updates,
    save_config,
    try_apply_runtime_settings,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class AdvancedConfigResponse(BaseModel):
    """高级配置响应"""

    writer_chapter_version_count: int = Field(description="章节候选版本数量")
    writer_parallel_generation: bool = Field(description="是否启用并行生成")
    part_outline_threshold: int = Field(description="长篇分部大纲阈值")
    agent_context_max_chars: int = Field(description="Agent上下文最大字符数")


class AdvancedConfigUpdate(BaseModel):
    """高级配置更新请求"""

    writer_chapter_version_count: int = Field(ge=1, le=5, description="章节候选版本数量（1-5）")
    writer_parallel_generation: bool = Field(description="是否启用并行生成")
    part_outline_threshold: int = Field(ge=10, le=100, description="长篇分部大纲阈值（10-100）")
    agent_context_max_chars: int = Field(ge=50000, le=500000, description="Agent上下文最大字符数（50000-500000）")


class AdvancedConfigExportData(BaseModel):
    """高级配置导出数据"""

    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="advanced", description="导出类型")
    config: Dict[str, Any] = Field(..., description="配置数据")


@router.get("/advanced-config", response_model=AdvancedConfigResponse)
async def get_advanced_config() -> AdvancedConfigResponse:
    """
    获取当前高级配置

    Returns:
        当前配置值
    """
    return AdvancedConfigResponse(
        writer_chapter_version_count=settings.writer_chapter_versions,
        writer_parallel_generation=settings.writer_parallel_generation,
        part_outline_threshold=settings.part_outline_threshold,
        agent_context_max_chars=settings.agent_context_max_chars,
    )


@router.put("/advanced-config")
async def update_advanced_config(config: AdvancedConfigUpdate) -> Dict[str, Any]:
    """
    更新高级配置

    将配置写入 storage/config.json 文件。

    Args:
        config: 配置更新数据

    Returns:
        更新结果
    """
    try:
        updates = config.dict()
        persist_config_updates(updates)
        logger.info("高级配置已保存到配置文件")

        # 更新运行时配置
        hot_reload_success = try_apply_runtime_settings(
            settings,
            updates,
            key_map={"writer_chapter_version_count": "writer_chapter_versions"},
            warn_logger=logger,
        )
        if hot_reload_success:
            logger.info("运行时配置已更新")
        return build_hot_reload_response(updates, hot_reload_success)

    except Exception as e:
        logger.error("保存配置失败：%s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存配置失败：{str(e)}")


@router.get("/advanced-config/export")
async def export_advanced_config() -> AdvancedConfigExportData:
    """
    导出高级配置

    Returns:
        包含高级配置的JSON数据
    """
    current_config = load_config()

    return AdvancedConfigExportData(
        export_time=datetime.now(timezone.utc).isoformat(),
        config={
            "writer_chapter_version_count": current_config.get(
                "writer_chapter_version_count", settings.writer_chapter_versions
            ),
            "writer_parallel_generation": current_config.get(
                "writer_parallel_generation", settings.writer_parallel_generation
            ),
            "part_outline_threshold": current_config.get("part_outline_threshold", settings.part_outline_threshold),
            "agent_context_max_chars": current_config.get("agent_context_max_chars", settings.agent_context_max_chars),
        },
    )


@router.post("/advanced-config/import", response_model=ConfigImportResult)
async def import_advanced_config(import_data: dict) -> ConfigImportResult:
    """
    导入高级配置

    Args:
        import_data: 导入的配置数据

    Returns:
        导入结果
    """
    details = []

    try:
        # 验证导入数据格式
        if import_data.get("export_type") != "advanced":
            return ConfigImportResult(success=False, message="导入数据类型不匹配，期望 'advanced'", details=[])

        config_data = import_data.get("config", {})
        if not config_data:
            return ConfigImportResult(success=False, message="导入数据中没有配置信息", details=[])

        # 读取现有配置
        current_config = load_config()

        # 更新配置（带验证）
        if "writer_chapter_version_count" in config_data:
            value = config_data["writer_chapter_version_count"]
            if 1 <= value <= 5:
                current_config["writer_chapter_version_count"] = value
                settings.writer_chapter_versions = value
                details.append(f"章节版本数量已更新为 {value}")
            else:
                details.append(f"章节版本数量 {value} 超出范围(1-5)，已跳过")

        if "writer_parallel_generation" in config_data:
            value = bool(config_data["writer_parallel_generation"])
            current_config["writer_parallel_generation"] = value
            settings.writer_parallel_generation = value
            details.append(f"并行生成已{'启用' if value else '禁用'}")

        if "part_outline_threshold" in config_data:
            value = config_data["part_outline_threshold"]
            if 10 <= value <= 100:
                current_config["part_outline_threshold"] = value
                settings.part_outline_threshold = value
                details.append(f"分部大纲阈值已更新为 {value}")
            else:
                details.append(f"分部大纲阈值 {value} 超出范围(10-100)，已跳过")

        if "agent_context_max_chars" in config_data:
            value = config_data["agent_context_max_chars"]
            if 50000 <= value <= 500000:
                current_config["agent_context_max_chars"] = value
                settings.agent_context_max_chars = value
                details.append(f"Agent上下文最大字符数已更新为 {value}")
            else:
                details.append(f"Agent上下文最大字符数 {value} 超出范围(50000-500000)，已跳过")

        # 保存配置
        save_config(current_config)

        return ConfigImportResult(success=True, message="高级配置导入成功", details=details)

    except Exception as e:
        logger.error("导入高级配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(success=False, message=f"导入失败: {str(e)}", details=details)


__all__ = [
    "router",
    "AdvancedConfigResponse",
    "AdvancedConfigUpdate",
    "AdvancedConfigExportData",
    "import_advanced_config",
]
