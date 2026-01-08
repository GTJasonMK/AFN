"""
高级配置管理路由

提供系统配置的读取和更新接口。
桌面版：配置保存到 storage 目录的 config.json 文件中。
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings, reload_settings
from ...core.dependencies import get_default_user
from ...db.session import get_session
from ...schemas.user import UserInDB

logger = logging.getLogger(__name__)
router = APIRouter()


def get_config_file() -> Path:
    """获取配置文件路径（适配打包环境）"""
    if getattr(sys, 'frozen', False):
        # 打包环境：配置保存到 exe 所在目录的 storage 文件夹
        work_dir = Path(sys.executable).parent
    else:
        # 开发环境：配置保存到项目根目录的 storage 文件夹
        # 从 backend/app/api/routers/settings.py 向上4级到达项目根目录
        work_dir = Path(__file__).resolve().parents[4]

    storage_dir = work_dir / 'storage'
    storage_dir.mkdir(exist_ok=True)
    return storage_dir / 'config.json'


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_file = get_config_file()
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning("读取配置文件失败：%s", str(e))
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """保存配置文件"""
    config_file = get_config_file()
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


class AdvancedConfigResponse(BaseModel):
    """高级配置响应"""
    writer_chapter_version_count: int = Field(description="章节候选版本数量")
    writer_parallel_generation: bool = Field(description="是否启用并行生成")
    part_outline_threshold: int = Field(description="长篇分部大纲阈值")


class AdvancedConfigUpdate(BaseModel):
    """高级配置更新请求"""
    writer_chapter_version_count: int = Field(ge=1, le=5, description="章节候选版本数量（1-5）")
    writer_parallel_generation: bool = Field(description="是否启用并行生成")
    part_outline_threshold: int = Field(ge=10, le=100, description="长篇分部大纲阈值（10-100）")


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


# ==================== 导入导出相关 ====================

class AdvancedConfigExportData(BaseModel):
    """高级配置导出数据"""
    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="advanced", description="导出类型")
    config: Dict[str, Any] = Field(..., description="配置数据")


class QueueConfigExportData(BaseModel):
    """队列配置导出数据"""
    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="queue", description="导出类型")
    config: Dict[str, Any] = Field(..., description="配置数据")


class TemperatureConfigExportData(BaseModel):
    """Temperature配置导出数据"""
    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="temperature", description="导出类型")
    config: Dict[str, Any] = Field(..., description="配置数据")


class AllConfigExportData(BaseModel):
    """全局配置导出数据"""
    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="all", description="导出类型")
    llm_configs: Optional[List[Dict[str, Any]]] = None
    embedding_configs: Optional[List[Dict[str, Any]]] = None
    image_configs: Optional[List[Dict[str, Any]]] = None
    advanced_config: Optional[Dict[str, Any]] = None
    queue_config: Optional[Dict[str, Any]] = None
    max_tokens_config: Optional[Dict[str, Any]] = None  # Max Tokens配置
    temperature_config: Optional[Dict[str, Any]] = None  # Temperature配置
    prompt_configs: Optional[Dict[str, Any]] = None  # 提示词配置
    theme_configs: Optional[Dict[str, Any]] = None  # 主题配置


class ConfigImportResult(BaseModel):
    """配置导入结果"""
    success: bool
    message: str
    details: List[str] = []


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
        # 读取现有配置
        current_config = load_config()

        # 更新配置
        current_config['writer_chapter_version_count'] = config.writer_chapter_version_count
        current_config['writer_parallel_generation'] = config.writer_parallel_generation
        current_config['part_outline_threshold'] = config.part_outline_threshold

        # 保存配置
        save_config(current_config)
        logger.info("高级配置已保存到配置文件")

        # 更新运行时配置
        try:
            # 直接修改 settings 对象的值
            settings.writer_chapter_versions = config.writer_chapter_version_count
            settings.writer_parallel_generation = config.writer_parallel_generation
            settings.part_outline_threshold = config.part_outline_threshold
            logger.info("运行时配置已更新")
            hot_reload_success = True
        except Exception as reload_error:
            logger.warning("运行时配置更新失败: %s", str(reload_error), exc_info=True)
            hot_reload_success = False

        return {
            "success": True,
            "message": "配置已保存并立即生效" if hot_reload_success else "配置已保存，重启应用后生效",
            "hot_reload": hot_reload_success,
            "updated_config": config.dict()
        }

    except Exception as e:
        logger.error("保存配置失败：%s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"保存配置失败：{str(e)}"
        )


# ==================== Max Tokens 配置 ====================

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
    )


@router.put("/max-tokens-config")
async def update_max_tokens_config(config: MaxTokensConfigUpdate) -> Dict[str, Any]:
    """
    更新Max Tokens配置

    将配置写入 storage/config.json 文件。

    Args:
        config: 配置更新数据

    Returns:
        更新结果
    """
    try:
        # 读取现有配置
        current_config = load_config()

        # 更新配置 - 小说系统
        current_config['llm_max_tokens_blueprint'] = config.llm_max_tokens_blueprint
        current_config['llm_max_tokens_chapter'] = config.llm_max_tokens_chapter
        current_config['llm_max_tokens_outline'] = config.llm_max_tokens_outline
        current_config['llm_max_tokens_manga'] = config.llm_max_tokens_manga
        current_config['llm_max_tokens_analysis'] = config.llm_max_tokens_analysis
        current_config['llm_max_tokens_default'] = config.llm_max_tokens_default

        # 更新配置 - 编程系统
        current_config['llm_max_tokens_coding_blueprint'] = config.llm_max_tokens_coding_blueprint
        current_config['llm_max_tokens_coding_system'] = config.llm_max_tokens_coding_system
        current_config['llm_max_tokens_coding_module'] = config.llm_max_tokens_coding_module
        current_config['llm_max_tokens_coding_feature'] = config.llm_max_tokens_coding_feature
        current_config['llm_max_tokens_coding_prompt'] = config.llm_max_tokens_coding_prompt

        # 保存配置
        save_config(current_config)
        logger.info("Max Tokens配置已保存到配置文件")

        # 更新运行时配置
        try:
            # 小说系统
            settings.llm_max_tokens_blueprint = config.llm_max_tokens_blueprint
            settings.llm_max_tokens_chapter = config.llm_max_tokens_chapter
            settings.llm_max_tokens_outline = config.llm_max_tokens_outline
            settings.llm_max_tokens_manga = config.llm_max_tokens_manga
            settings.llm_max_tokens_analysis = config.llm_max_tokens_analysis
            settings.llm_max_tokens_default = config.llm_max_tokens_default
            # 编程系统
            settings.llm_max_tokens_coding_blueprint = config.llm_max_tokens_coding_blueprint
            settings.llm_max_tokens_coding_system = config.llm_max_tokens_coding_system
            settings.llm_max_tokens_coding_module = config.llm_max_tokens_coding_module
            settings.llm_max_tokens_coding_feature = config.llm_max_tokens_coding_feature
            settings.llm_max_tokens_coding_prompt = config.llm_max_tokens_coding_prompt

            logger.info("运行时Max Tokens配置已更新")
            hot_reload_success = True
        except Exception as reload_error:
            logger.warning("运行时配置更新失败: %s", str(reload_error), exc_info=True)
            hot_reload_success = False

        return {
            "success": True,
            "message": "配置已保存并立即生效" if hot_reload_success else "配置已保存，重启应用后生效",
            "hot_reload": hot_reload_success,
            "updated_config": config.dict()
        }

    except Exception as e:
        logger.error("保存Max Tokens配置失败：%s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"保存配置失败：{str(e)}"
        )


# ==================== Max Tokens 配置导入导出 ====================

class MaxTokensConfigExportData(BaseModel):
    """Max Tokens配置导出数据"""
    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="max_tokens", description="导出类型")
    config: Dict[str, Any] = Field(..., description="配置数据")


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
        config={
            # 小说系统
            "llm_max_tokens_blueprint": current_config.get(
                "llm_max_tokens_blueprint", settings.llm_max_tokens_blueprint
            ),
            "llm_max_tokens_chapter": current_config.get(
                "llm_max_tokens_chapter", settings.llm_max_tokens_chapter
            ),
            "llm_max_tokens_outline": current_config.get(
                "llm_max_tokens_outline", settings.llm_max_tokens_outline
            ),
            "llm_max_tokens_manga": current_config.get(
                "llm_max_tokens_manga", settings.llm_max_tokens_manga
            ),
            "llm_max_tokens_analysis": current_config.get(
                "llm_max_tokens_analysis", settings.llm_max_tokens_analysis
            ),
            "llm_max_tokens_default": current_config.get(
                "llm_max_tokens_default", settings.llm_max_tokens_default
            ),
            # 编程系统
            "llm_max_tokens_coding_blueprint": current_config.get(
                "llm_max_tokens_coding_blueprint", settings.llm_max_tokens_coding_blueprint
            ),
            "llm_max_tokens_coding_system": current_config.get(
                "llm_max_tokens_coding_system", settings.llm_max_tokens_coding_system
            ),
            "llm_max_tokens_coding_module": current_config.get(
                "llm_max_tokens_coding_module", settings.llm_max_tokens_coding_module
            ),
            "llm_max_tokens_coding_feature": current_config.get(
                "llm_max_tokens_coding_feature", settings.llm_max_tokens_coding_feature
            ),
            "llm_max_tokens_coding_prompt": current_config.get(
                "llm_max_tokens_coding_prompt", settings.llm_max_tokens_coding_prompt
            ),
        }
    )


@router.post("/max-tokens-config/import", response_model=ConfigImportResult)
async def import_max_tokens_config(import_data: dict) -> ConfigImportResult:
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
            return ConfigImportResult(
                success=False,
                message="导入数据类型不匹配，期望 'max_tokens'",
                details=[]
            )

        config_data = import_data.get("config", {})
        if not config_data:
            return ConfigImportResult(
                success=False,
                message="导入数据中没有配置信息",
                details=[]
            )

        # 读取现有配置
        current_config = load_config()

        # 定义所有Max Tokens字段及其范围
        max_tokens_fields = {
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
        }

        # 更新配置（带验证）
        for field, (min_val, max_val) in max_tokens_fields.items():
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

        return ConfigImportResult(
            success=True,
            message="Max Tokens配置导入成功",
            details=details
        )

    except Exception as e:
        logger.error("导入Max Tokens配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(
            success=False,
            message=f"导入失败: {str(e)}",
            details=details
        )


# ==================== Temperature 配置 ====================

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


@router.put("/temperature-config")
async def update_temperature_config(config: TemperatureConfigUpdate) -> Dict[str, Any]:
    """
    更新Temperature配置

    将配置写入 storage/config.json 文件。

    Args:
        config: 配置更新数据

    Returns:
        更新结果
    """
    try:
        # 读取现有配置
        current_config = load_config()

        # 更新配置
        current_config['llm_temp_inspiration'] = config.llm_temp_inspiration
        current_config['llm_temp_blueprint'] = config.llm_temp_blueprint
        current_config['llm_temp_outline'] = config.llm_temp_outline
        current_config['llm_temp_writing'] = config.llm_temp_writing
        current_config['llm_temp_evaluation'] = config.llm_temp_evaluation
        current_config['llm_temp_summary'] = config.llm_temp_summary

        # 保存配置
        save_config(current_config)
        logger.info("Temperature配置已保存到配置文件")

        # 更新运行时配置
        try:
            settings.llm_temp_inspiration = config.llm_temp_inspiration
            settings.llm_temp_blueprint = config.llm_temp_blueprint
            settings.llm_temp_outline = config.llm_temp_outline
            settings.llm_temp_writing = config.llm_temp_writing
            settings.llm_temp_evaluation = config.llm_temp_evaluation
            settings.llm_temp_summary = config.llm_temp_summary

            logger.info("运行时Temperature配置已更新")
            hot_reload_success = True
        except Exception as reload_error:
            logger.warning("运行时配置更新失败: %s", str(reload_error), exc_info=True)
            hot_reload_success = False

        return {
            "success": True,
            "message": "配置已保存并立即生效" if hot_reload_success else "配置已保存，重启应用后生效",
            "hot_reload": hot_reload_success,
            "updated_config": config.dict()
        }

    except Exception as e:
        logger.error("保存Temperature配置失败：%s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"保存配置失败：{str(e)}"
        )


# ==================== Temperature 配置导入导出 ====================

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
        config={
            "llm_temp_inspiration": current_config.get(
                "llm_temp_inspiration", settings.llm_temp_inspiration
            ),
            "llm_temp_blueprint": current_config.get(
                "llm_temp_blueprint", settings.llm_temp_blueprint
            ),
            "llm_temp_outline": current_config.get(
                "llm_temp_outline", settings.llm_temp_outline
            ),
            "llm_temp_writing": current_config.get(
                "llm_temp_writing", settings.llm_temp_writing
            ),
            "llm_temp_evaluation": current_config.get(
                "llm_temp_evaluation", settings.llm_temp_evaluation
            ),
            "llm_temp_summary": current_config.get(
                "llm_temp_summary", settings.llm_temp_summary
            ),
        }
    )


@router.post("/temperature-config/import", response_model=ConfigImportResult)
async def import_temperature_config(import_data: dict) -> ConfigImportResult:
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
            return ConfigImportResult(
                success=False,
                message="导入数据类型不匹配，期望 'temperature'",
                details=[]
            )

        config_data = import_data.get("config", {})
        if not config_data:
            return ConfigImportResult(
                success=False,
                message="导入数据中没有配置信息",
                details=[]
            )

        # 读取现有配置
        current_config = load_config()

        # 定义所有Temperature字段及其范围
        temperature_fields = [
            "llm_temp_inspiration",
            "llm_temp_blueprint",
            "llm_temp_outline",
            "llm_temp_writing",
            "llm_temp_evaluation",
            "llm_temp_summary",
        ]

        # 更新配置（带验证）
        for field in temperature_fields:
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

        return ConfigImportResult(
            success=True,
            message="Temperature配置导入成功",
            details=details
        )

    except Exception as e:
        logger.error("导入Temperature配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(
            success=False,
            message=f"导入失败: {str(e)}",
            details=details
        )


# ==================== 高级配置导入导出 ====================

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
            "part_outline_threshold": current_config.get(
                "part_outline_threshold", settings.part_outline_threshold
            ),
        }
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
            return ConfigImportResult(
                success=False,
                message="导入数据类型不匹配，期望 'advanced'",
                details=[]
            )

        config_data = import_data.get("config", {})
        if not config_data:
            return ConfigImportResult(
                success=False,
                message="导入数据中没有配置信息",
                details=[]
            )

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

        # 保存配置
        save_config(current_config)

        return ConfigImportResult(
            success=True,
            message="高级配置导入成功",
            details=details
        )

    except Exception as e:
        logger.error("导入高级配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(
            success=False,
            message=f"导入失败: {str(e)}",
            details=details
        )


# ==================== 队列配置导入导出 ====================

@router.get("/queue-config/export")
async def export_queue_config() -> QueueConfigExportData:
    """
    导出队列配置

    Returns:
        包含队列配置的JSON数据
    """
    from ...services.queue import LLMRequestQueue, ImageRequestQueue

    llm_queue = LLMRequestQueue.get_instance()
    image_queue = ImageRequestQueue.get_instance()

    return QueueConfigExportData(
        export_time=datetime.now(timezone.utc).isoformat(),
        config={
            "llm_max_concurrent": llm_queue.max_concurrent,
            "image_max_concurrent": image_queue.max_concurrent,
        }
    )


@router.post("/queue-config/import", response_model=ConfigImportResult)
async def import_queue_config(import_data: dict) -> ConfigImportResult:
    """
    导入队列配置

    Args:
        import_data: 导入的配置数据

    Returns:
        导入结果
    """
    from ...services.queue import LLMRequestQueue, ImageRequestQueue

    details = []

    try:
        # 验证导入数据格式
        if import_data.get("export_type") != "queue":
            return ConfigImportResult(
                success=False,
                message="导入数据类型不匹配，期望 'queue'",
                details=[]
            )

        config_data = import_data.get("config", {})
        if not config_data:
            return ConfigImportResult(
                success=False,
                message="导入数据中没有配置信息",
                details=[]
            )

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

        return ConfigImportResult(
            success=True,
            message="队列配置导入成功",
            details=details
        )

    except Exception as e:
        logger.error("导入队列配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(
            success=False,
            message=f"导入失败: {str(e)}",
            details=details
        )


# ==================== 全局配置导入导出 ====================

@router.get("/export/all")
async def export_all_configs(
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> AllConfigExportData:
    """
    导出所有配置（LLM、嵌入、图片、高级、队列、提示词、主题）

    Returns:
        包含所有配置的JSON数据
    """
    from ...services.llm_config_service import LLMConfigService
    from ...services.embedding_config_service import EmbeddingConfigService
    from ...services.image_generation import ImageConfigService
    from ...services.queue import LLMRequestQueue, ImageRequestQueue
    from ...services.prompt_service import PromptService
    from ...services.theme_config_service import ThemeConfigService

    # 获取LLM配置（使用service的export方法获取完整数据）
    llm_service = LLMConfigService(session)
    try:
        llm_export = await llm_service.export_all_configs(desktop_user.id)
        llm_configs_data = llm_export.get("configs", [])
    except Exception:
        # 用户没有LLM配置时，返回空列表
        llm_configs_data = []

    # 获取嵌入配置（使用service的export方法获取完整数据）
    embedding_service = EmbeddingConfigService(session)
    try:
        embedding_export = await embedding_service.export_all_configs(desktop_user.id)
        embedding_configs_data = embedding_export.get("configs", [])
    except Exception:
        # 用户没有嵌入配置时，返回空列表
        embedding_configs_data = []

    # 获取图片配置（使用service的export方法获取完整数据）
    image_service = ImageConfigService(session)
    try:
        image_export = await image_service.export_all_configs(desktop_user.id)
        image_configs_data = image_export.get("configs", [])
    except Exception:
        # 用户没有图片配置时，返回空列表
        image_configs_data = []

    # 获取高级配置
    current_config = load_config()
    advanced_config = {
        "writer_chapter_version_count": current_config.get(
            "writer_chapter_version_count", settings.writer_chapter_versions
        ),
        "writer_parallel_generation": current_config.get(
            "writer_parallel_generation", settings.writer_parallel_generation
        ),
        "part_outline_threshold": current_config.get(
            "part_outline_threshold", settings.part_outline_threshold
        ),
    }

    # 获取队列配置
    llm_queue = LLMRequestQueue.get_instance()
    image_queue = ImageRequestQueue.get_instance()
    queue_config = {
        "llm_max_concurrent": llm_queue.max_concurrent,
        "image_max_concurrent": image_queue.max_concurrent,
    }

    # 获取Max Tokens配置
    max_tokens_config = {
        # 小说系统
        "llm_max_tokens_blueprint": current_config.get(
            "llm_max_tokens_blueprint", settings.llm_max_tokens_blueprint
        ),
        "llm_max_tokens_chapter": current_config.get(
            "llm_max_tokens_chapter", settings.llm_max_tokens_chapter
        ),
        "llm_max_tokens_outline": current_config.get(
            "llm_max_tokens_outline", settings.llm_max_tokens_outline
        ),
        "llm_max_tokens_manga": current_config.get(
            "llm_max_tokens_manga", settings.llm_max_tokens_manga
        ),
        "llm_max_tokens_analysis": current_config.get(
            "llm_max_tokens_analysis", settings.llm_max_tokens_analysis
        ),
        "llm_max_tokens_default": current_config.get(
            "llm_max_tokens_default", settings.llm_max_tokens_default
        ),
        # 编程系统
        "llm_max_tokens_coding_blueprint": current_config.get(
            "llm_max_tokens_coding_blueprint", settings.llm_max_tokens_coding_blueprint
        ),
        "llm_max_tokens_coding_system": current_config.get(
            "llm_max_tokens_coding_system", settings.llm_max_tokens_coding_system
        ),
        "llm_max_tokens_coding_module": current_config.get(
            "llm_max_tokens_coding_module", settings.llm_max_tokens_coding_module
        ),
        "llm_max_tokens_coding_feature": current_config.get(
            "llm_max_tokens_coding_feature", settings.llm_max_tokens_coding_feature
        ),
        "llm_max_tokens_coding_prompt": current_config.get(
            "llm_max_tokens_coding_prompt", settings.llm_max_tokens_coding_prompt
        ),
    }

    # 获取Temperature配置
    temperature_config = {
        "llm_temp_inspiration": current_config.get(
            "llm_temp_inspiration", settings.llm_temp_inspiration
        ),
        "llm_temp_blueprint": current_config.get(
            "llm_temp_blueprint", settings.llm_temp_blueprint
        ),
        "llm_temp_outline": current_config.get(
            "llm_temp_outline", settings.llm_temp_outline
        ),
        "llm_temp_writing": current_config.get(
            "llm_temp_writing", settings.llm_temp_writing
        ),
        "llm_temp_evaluation": current_config.get(
            "llm_temp_evaluation", settings.llm_temp_evaluation
        ),
        "llm_temp_summary": current_config.get(
            "llm_temp_summary", settings.llm_temp_summary
        ),
    }

    # 获取提示词配置（只导出用户已修改的）
    prompt_service = PromptService(session)
    try:
        prompt_export = await prompt_service.export_prompts()
        prompt_configs_data = prompt_export
    except Exception:
        prompt_configs_data = {"count": 0, "prompts": []}

    # 获取主题配置
    theme_service = ThemeConfigService(session)
    try:
        theme_export = await theme_service.export_all_configs(desktop_user.id)
        # 转换为字典
        theme_configs_data = theme_export.model_dump()
    except Exception:
        theme_configs_data = {"count": 0, "configs": []}

    return AllConfigExportData(
        export_time=datetime.now(timezone.utc).isoformat(),
        llm_configs=llm_configs_data,
        embedding_configs=embedding_configs_data,
        image_configs=image_configs_data,
        advanced_config=advanced_config,
        queue_config=queue_config,
        max_tokens_config=max_tokens_config,
        temperature_config=temperature_config,
        prompt_configs=prompt_configs_data,
        theme_configs=theme_configs_data,
    )


@router.post("/import/all", response_model=ConfigImportResult)
async def import_all_configs(
    import_data: dict,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ConfigImportResult:
    """
    导入所有配置（LLM、嵌入、图片、高级、队列、提示词、主题）

    支持选择性导入：只导入import_data中存在的配置类型

    Args:
        import_data: 导入的配置数据

    Returns:
        导入结果
    """
    from ...services.llm_config_service import LLMConfigService
    from ...services.embedding_config_service import EmbeddingConfigService
    from ...services.image_generation import ImageConfigService
    from ...services.queue import LLMRequestQueue, ImageRequestQueue
    from ...services.prompt_service import PromptService
    from ...services.theme_config_service import ThemeConfigService

    details = []
    has_error = False

    try:
        # 验证导入数据格式
        if import_data.get("export_type") != "all":
            return ConfigImportResult(
                success=False,
                message="导入数据类型不匹配，期望 'all'",
                details=[]
            )

        # 获取导出时间，用于重建导入数据结构
        export_time = import_data.get("export_time", datetime.now(timezone.utc).isoformat())

        # 导入LLM配置
        if import_data.get("llm_configs"):
            try:
                llm_service = LLMConfigService(session)
                llm_import_data = {
                    "version": "1.0",
                    "export_time": export_time,
                    "export_type": "batch",
                    "configs": import_data["llm_configs"]
                }
                result = await llm_service.import_configs(desktop_user.id, llm_import_data)
                details.append(f"LLM配置: {result.get('message', '导入完成')}")
            except Exception as e:
                details.append(f"LLM配置导入失败: {str(e)}")
                has_error = True

        # 导入嵌入配置
        if import_data.get("embedding_configs"):
            try:
                embedding_service = EmbeddingConfigService(session)
                embedding_import_data = {
                    "version": "1.0",
                    "export_time": export_time,
                    "export_type": "batch",
                    "configs": import_data["embedding_configs"]
                }
                result = await embedding_service.import_configs(desktop_user.id, embedding_import_data)
                details.append(f"嵌入配置: {result.get('message', '导入完成')}")
            except Exception as e:
                details.append(f"嵌入配置导入失败: {str(e)}")
                has_error = True

        # 导入图片配置
        if import_data.get("image_configs"):
            try:
                image_service = ImageConfigService(session)
                image_import_data = {
                    "version": "1.0",
                    "export_time": export_time,
                    "export_type": "batch",
                    "configs": import_data["image_configs"]
                }
                result = await image_service.import_configs(desktop_user.id, image_import_data)
                details.append(f"图片配置: {result.get('message', '导入完成')}")
            except Exception as e:
                details.append(f"图片配置导入失败: {str(e)}")
                has_error = True

        # 导入高级配置
        if import_data.get("advanced_config"):
            try:
                advanced_import_data = {
                    "export_type": "advanced",
                    "config": import_data["advanced_config"]
                }
                result = await import_advanced_config(advanced_import_data)
                details.append(f"高级配置: {result.message}")
                if not result.success:
                    has_error = True
            except Exception as e:
                details.append(f"高级配置导入失败: {str(e)}")
                has_error = True

        # 导入队列配置
        if import_data.get("queue_config"):
            try:
                queue_import_data = {
                    "export_type": "queue",
                    "config": import_data["queue_config"]
                }
                result = await import_queue_config(queue_import_data)
                details.append(f"队列配置: {result.message}")
                if not result.success:
                    has_error = True
            except Exception as e:
                details.append(f"队列配置导入失败: {str(e)}")
                has_error = True

        # 导入Max Tokens配置
        if import_data.get("max_tokens_config"):
            try:
                max_tokens_data = import_data["max_tokens_config"]
                current_config = load_config()
                updated_fields = []

                # 定义所有Max Tokens字段及其范围
                max_tokens_fields = {
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
                }

                for field, (min_val, max_val) in max_tokens_fields.items():
                    if field in max_tokens_data:
                        value = max_tokens_data[field]
                        if min_val <= value <= max_val:
                            current_config[field] = value
                            setattr(settings, field, value)
                            updated_fields.append(field)

                save_config(current_config)
                details.append(f"Max Tokens配置: 已更新 {len(updated_fields)} 项")
            except Exception as e:
                details.append(f"Max Tokens配置导入失败: {str(e)}")
                has_error = True

        # 导入Temperature配置
        if import_data.get("temperature_config"):
            try:
                temperature_data = import_data["temperature_config"]
                current_config = load_config()
                updated_fields = []

                # 定义所有Temperature字段
                temperature_fields = [
                    "llm_temp_inspiration",
                    "llm_temp_blueprint",
                    "llm_temp_outline",
                    "llm_temp_writing",
                    "llm_temp_evaluation",
                    "llm_temp_summary",
                ]

                for field in temperature_fields:
                    if field in temperature_data:
                        value = temperature_data[field]
                        if 0.0 <= value <= 2.0:
                            current_config[field] = value
                            setattr(settings, field, value)
                            updated_fields.append(field)

                save_config(current_config)
                details.append(f"Temperature配置: 已更新 {len(updated_fields)} 项")
            except Exception as e:
                details.append(f"Temperature配置导入失败: {str(e)}")
                has_error = True

        # 导入提示词配置
        if import_data.get("prompt_configs"):
            try:
                prompt_service = PromptService(session)
                result = await prompt_service.import_prompts(import_data["prompt_configs"])
                details.append(f"提示词配置: {result.get('message', '导入完成')}")
                if not result.get("success", True):
                    has_error = True
            except Exception as e:
                details.append(f"提示词配置导入失败: {str(e)}")
                has_error = True

        # 导入主题配置
        if import_data.get("theme_configs"):
            try:
                from ...schemas.theme_config import ThemeConfigExportData as ThemeExportData
                theme_service = ThemeConfigService(session)
                # 将字典转换为 ThemeConfigExportData 对象
                theme_import_data = ThemeExportData(**import_data["theme_configs"])
                result = await theme_service.import_configs(desktop_user.id, theme_import_data)
                imported = result.imported_count
                skipped = result.skipped_count
                msg = f"导入 {imported} 个"
                if skipped > 0:
                    msg += f"，跳过 {skipped} 个同名"
                details.append(f"主题配置: {msg}")
            except Exception as e:
                details.append(f"主题配置导入失败: {str(e)}")
                has_error = True

        await session.commit()

        return ConfigImportResult(
            success=not has_error,
            message="全局配置导入完成" if not has_error else "部分配置导入失败",
            details=details
        )

    except Exception as e:
        logger.error("导入全局配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(
            success=False,
            message=f"导入失败: {str(e)}",
            details=details
        )
