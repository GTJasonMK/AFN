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
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...core.config import settings, reload_settings

logger = logging.getLogger(__name__)
router = APIRouter()


def get_config_file() -> Path:
    """获取配置文件路径（适配打包环境）"""
    if getattr(sys, 'frozen', False):
        # 打包环境：配置保存到 exe 所在目录的 storage 文件夹
        work_dir = Path(sys.executable).parent
    else:
        # 开发环境：配置保存到 backend/storage 文件夹
        work_dir = Path(__file__).resolve().parents[3]

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
