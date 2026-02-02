"""
Max Tokens 配置路由

包含：
- /max-tokens-config 读取/更新
- /max-tokens-config/export 导出
- /max-tokens-config/import 导入
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

MAX_TOKENS_FIELDS = {
    # 小说系统
    "llm_max_tokens_blueprint": (1024, 32768),
    "llm_max_tokens_chapter": (1024, 32768),
    "llm_max_tokens_outline": (1024, 16384),
    "llm_max_tokens_manga": (1024, 32768),
    "llm_max_tokens_analysis": (1024, 32768),
    "llm_max_tokens_default": (512, 16384),
    # 编程系统
    "llm_max_tokens_coding_blueprint": (1024, 32768),
    "llm_max_tokens_coding_system": (1024, 32768),
    "llm_max_tokens_coding_module": (1024, 32768),
    "llm_max_tokens_coding_feature": (1024, 16384),
    "llm_max_tokens_coding_prompt": (1024, 32768),
    "llm_max_tokens_coding_directory": (4096, 32768),
}


class MaxTokensConfigResponse(BaseModel):
    """Max Tokens配置响应"""

    # 小说系统
    llm_max_tokens_blueprint: int = Field(description="蓝图生成最大tokens")
    llm_max_tokens_chapter: int = Field(description="章节写作最大tokens")
    llm_max_tokens_outline: int = Field(description="大纲生成最大tokens")
    llm_max_tokens_manga: int = Field(description="漫画分镜最大tokens")
    llm_max_tokens_analysis: int = Field(description="分析任务最大tokens")
    llm_max_tokens_default: int = Field(description="默认最大tokens")
    # 编程系统
    llm_max_tokens_coding_blueprint: int = Field(description="编程蓝图最大tokens")
    llm_max_tokens_coding_system: int = Field(description="系统生成最大tokens")
    llm_max_tokens_coding_module: int = Field(description="模块生成最大tokens")
    llm_max_tokens_coding_feature: int = Field(description="功能大纲最大tokens")
    llm_max_tokens_coding_prompt: int = Field(description="功能Prompt最大tokens")
    llm_max_tokens_coding_directory: int = Field(description="目录生成最大tokens")


class MaxTokensConfigUpdate(BaseModel):
    """Max Tokens配置更新请求"""

    # 小说系统
    llm_max_tokens_blueprint: int = Field(ge=1024, le=32768, description="蓝图生成最大tokens")
    llm_max_tokens_chapter: int = Field(ge=1024, le=32768, description="章节写作最大tokens")
    llm_max_tokens_outline: int = Field(ge=1024, le=16384, description="大纲生成最大tokens")
    llm_max_tokens_manga: int = Field(ge=1024, le=32768, description="漫画分镜最大tokens")
    llm_max_tokens_analysis: int = Field(ge=1024, le=32768, description="分析任务最大tokens")
    llm_max_tokens_default: int = Field(ge=512, le=16384, description="默认最大tokens")
    # 编程系统
    llm_max_tokens_coding_blueprint: int = Field(ge=1024, le=32768, description="编程蓝图最大tokens")
    llm_max_tokens_coding_system: int = Field(ge=1024, le=32768, description="系统生成最大tokens")
    llm_max_tokens_coding_module: int = Field(ge=1024, le=32768, description="模块生成最大tokens")
    llm_max_tokens_coding_feature: int = Field(ge=1024, le=16384, description="功能大纲最大tokens")
    llm_max_tokens_coding_prompt: int = Field(ge=1024, le=32768, description="功能Prompt最大tokens")
    llm_max_tokens_coding_directory: int = Field(ge=4096, le=32768, description="目录生成最大tokens")


class MaxTokensConfigExportData(BaseModel):
    """Max Tokens配置导出数据"""

    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="max_tokens", description="导出类型")
    config: Dict[str, Any] = Field(..., description="配置数据")


@router.get("/max-tokens-config", response_model=MaxTokensConfigResponse)
async def get_max_tokens_config() -> MaxTokensConfigResponse:
    """
    获取当前Max Tokens配置

    Returns:
        当前配置值
    """
    return MaxTokensConfigResponse(
        # 小说系统
        llm_max_tokens_blueprint=settings.llm_max_tokens_blueprint,
        llm_max_tokens_chapter=settings.llm_max_tokens_chapter,
        llm_max_tokens_outline=settings.llm_max_tokens_outline,
        llm_max_tokens_manga=settings.llm_max_tokens_manga,
        llm_max_tokens_analysis=settings.llm_max_tokens_analysis,
        llm_max_tokens_default=settings.llm_max_tokens_default,
        # 编程系统
        llm_max_tokens_coding_blueprint=settings.llm_max_tokens_coding_blueprint,
        llm_max_tokens_coding_system=settings.llm_max_tokens_coding_system,
        llm_max_tokens_coding_module=settings.llm_max_tokens_coding_module,
        llm_max_tokens_coding_feature=settings.llm_max_tokens_coding_feature,
        llm_max_tokens_coding_prompt=settings.llm_max_tokens_coding_prompt,
        llm_max_tokens_coding_directory=settings.llm_max_tokens_coding_directory,
    )


@router.put("/max-tokens-config", dependencies=[Depends(require_admin_user)])
async def update_max_tokens_config(
    config: MaxTokensConfigUpdate,
) -> Dict[str, Any]:
    """
    更新Max Tokens配置

    将配置写入 storage/config.json 文件。

    Args:
        config: 配置更新数据

    Returns:
        更新结果
    """
    try:
        updates = config.dict()
        persist_config_updates(updates)
        logger.info("Max Tokens配置已保存到配置文件")

        # 更新运行时配置
        hot_reload_success = try_apply_runtime_settings(settings, updates, warn_logger=logger)
        if hot_reload_success:
            logger.info("运行时Max Tokens配置已更新")
        return build_hot_reload_response(updates, hot_reload_success)

    except Exception as e:
        logger.error("保存Max Tokens配置失败：%s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存配置失败：{str(e)}")


@router.get("/max-tokens-config/export")
async def export_max_tokens_config() -> MaxTokensConfigExportData:
    """
    导出Max Tokens配置

    Returns:
        包含Max Tokens配置的JSON数据
    """
    current_config = load_config()

    return MaxTokensConfigExportData(
        export_time=datetime.now(timezone.utc).isoformat(),
        config={key: current_config.get(key, getattr(settings, key)) for key in MAX_TOKENS_FIELDS},
    )


@router.post("/max-tokens-config/import", response_model=ConfigImportResult, dependencies=[Depends(require_admin_user)])
async def import_max_tokens_config(
    import_data: dict,
) -> ConfigImportResult:
    """
    导入Max Tokens配置

    Args:
        import_data: 导入的配置数据

    Returns:
        导入结果
    """
    details = []

    try:
        # 验证导入数据格式
        if import_data.get("export_type") != "max_tokens":
            return ConfigImportResult(success=False, message="导入数据类型不匹配，期望 'max_tokens'", details=[])

        config_data = import_data.get("config", {})
        if not config_data:
            return ConfigImportResult(success=False, message="导入数据中没有配置信息", details=[])

        # 读取现有配置
        current_config = load_config()

        # 更新配置（带验证）
        for field, (min_val, max_val) in MAX_TOKENS_FIELDS.items():
            if field in config_data:
                value = config_data[field]
                if min_val <= value <= max_val:
                    current_config[field] = value
                    setattr(settings, field, value)
                    details.append(f"{field} 已更新为 {value}")
                else:
                    details.append(f"{field} 值 {value} 超出范围({min_val}-{max_val})，已跳过")

        # 保存配置
        save_config(current_config)

        return ConfigImportResult(success=True, message="Max Tokens配置导入成功", details=details)

    except Exception as e:
        logger.error("导入Max Tokens配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(success=False, message=f"导入失败: {str(e)}", details=details)


__all__ = ["router", "MaxTokensConfigResponse", "MaxTokensConfigUpdate", "MaxTokensConfigExportData"]
