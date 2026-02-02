"""
Temperature 配置路由

包含：
- /temperature-config 读取/更新
- /temperature-config/export 导出
- /temperature-config/import 导入
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core.config import settings
from ...core.dependencies import require_admin_user
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

TEMPERATURE_FIELDS = (
    "llm_temp_inspiration",
    "llm_temp_blueprint",
    "llm_temp_outline",
    "llm_temp_writing",
    "llm_temp_evaluation",
    "llm_temp_summary",
)


class TemperatureConfigResponse(BaseModel):
    """Temperature配置响应"""

    llm_temp_inspiration: float = Field(description="灵感对话Temperature")
    llm_temp_blueprint: float = Field(description="蓝图生成Temperature")
    llm_temp_outline: float = Field(description="大纲生成Temperature")
    llm_temp_writing: float = Field(description="章节写作Temperature")
    llm_temp_evaluation: float = Field(description="章节评审Temperature")
    llm_temp_summary: float = Field(description="摘要生成Temperature")


class TemperatureConfigUpdate(BaseModel):
    """Temperature配置更新请求"""

    llm_temp_inspiration: float = Field(ge=0.0, le=2.0, description="灵感对话Temperature（0.0-2.0）")
    llm_temp_blueprint: float = Field(ge=0.0, le=2.0, description="蓝图生成Temperature（0.0-2.0）")
    llm_temp_outline: float = Field(ge=0.0, le=2.0, description="大纲生成Temperature（0.0-2.0）")
    llm_temp_writing: float = Field(ge=0.0, le=2.0, description="章节写作Temperature（0.0-2.0）")
    llm_temp_evaluation: float = Field(ge=0.0, le=2.0, description="章节评审Temperature（0.0-2.0）")
    llm_temp_summary: float = Field(ge=0.0, le=2.0, description="摘要生成Temperature（0.0-2.0）")


class TemperatureConfigExportData(BaseModel):
    """Temperature配置导出数据"""

    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="temperature", description="导出类型")
    config: Dict[str, Any] = Field(..., description="配置数据")


@router.get("/temperature-config", response_model=TemperatureConfigResponse)
async def get_temperature_config() -> TemperatureConfigResponse:
    """
    获取当前Temperature配置

    Returns:
        当前配置值
    """
    return TemperatureConfigResponse(
        llm_temp_inspiration=settings.llm_temp_inspiration,
        llm_temp_blueprint=settings.llm_temp_blueprint,
        llm_temp_outline=settings.llm_temp_outline,
        llm_temp_writing=settings.llm_temp_writing,
        llm_temp_evaluation=settings.llm_temp_evaluation,
        llm_temp_summary=settings.llm_temp_summary,
    )


@router.put("/temperature-config", dependencies=[Depends(require_admin_user)])
async def update_temperature_config(
    config: TemperatureConfigUpdate,
) -> Dict[str, Any]:
    """
    更新Temperature配置

    将配置写入 storage/config.json 文件。

    Args:
        config: 配置更新数据

    Returns:
        更新结果
    """
    try:
        updates = config.dict()
        persist_config_updates(updates)
        logger.info("Temperature配置已保存到配置文件")

        # 更新运行时配置
        hot_reload_success = try_apply_runtime_settings(settings, updates, warn_logger=logger)
        if hot_reload_success:
            logger.info("运行时Temperature配置已更新")
        return build_hot_reload_response(updates, hot_reload_success)

    except Exception as e:
        logger.error("保存Temperature配置失败：%s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存配置失败：{str(e)}")


@router.get("/temperature-config/export")
async def export_temperature_config() -> TemperatureConfigExportData:
    """
    导出Temperature配置

    Returns:
        包含Temperature配置的JSON数据
    """
    current_config = load_config()

    return TemperatureConfigExportData(
        export_time=datetime.now(timezone.utc).isoformat(),
        config={key: current_config.get(key, getattr(settings, key)) for key in TEMPERATURE_FIELDS},
    )


@router.post("/temperature-config/import", response_model=ConfigImportResult, dependencies=[Depends(require_admin_user)])
async def import_temperature_config(
    import_data: dict,
) -> ConfigImportResult:
    """
    导入Temperature配置

    Args:
        import_data: 导入的配置数据

    Returns:
        导入结果
    """
    details = []

    try:
        # 验证导入数据格式
        if import_data.get("export_type") != "temperature":
            return ConfigImportResult(success=False, message="导入数据类型不匹配，期望 'temperature'", details=[])

        config_data = import_data.get("config", {})
        if not config_data:
            return ConfigImportResult(success=False, message="导入数据中没有配置信息", details=[])

        # 读取现有配置
        current_config = load_config()

        # 更新配置（带验证）
        for field in TEMPERATURE_FIELDS:
            if field in config_data:
                value = config_data[field]
                if 0.0 <= value <= 2.0:
                    current_config[field] = value
                    setattr(settings, field, value)
                    details.append(f"{field} 已更新为 {value}")
                else:
                    details.append(f"{field} 值 {value} 超出范围(0.0-2.0)，已跳过")

        # 保存配置
        save_config(current_config)

        return ConfigImportResult(success=True, message="Temperature配置导入成功", details=details)

    except Exception as e:
        logger.error("导入Temperature配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(success=False, message=f"导入失败: {str(e)}", details=details)


__all__ = ["router", "TemperatureConfigResponse", "TemperatureConfigUpdate", "TemperatureConfigExportData"]
