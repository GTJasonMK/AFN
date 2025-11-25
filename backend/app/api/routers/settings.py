"""
高级配置管理路由

提供系统配置的读取和更新接口。
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...core.config import settings, reload_settings

logger = logging.getLogger(__name__)
router = APIRouter()


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

    将配置写入.env文件，需要重启应用生效。

    Args:
        config: 配置更新数据

    Returns:
        更新结果
    """
    try:
        # 定位.env文件
        project_root = Path(__file__).resolve().parents[4]  # 回到项目根目录
        env_file = project_root / "backend" / ".env"

        if not env_file.exists():
            raise HTTPException(
                status_code=500,
                detail=f".env文件不存在：{env_file}"
            )

        # 读取现有内容
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 更新配置行
        config_map = {
            'WRITER_CHAPTER_VERSION_COUNT': str(config.writer_chapter_version_count),
            'WRITER_PARALLEL_GENERATION': 'true' if config.writer_parallel_generation else 'false',
            'PART_OUTLINE_THRESHOLD': str(config.part_outline_threshold),
        }

        updated_lines = []
        updated_keys = set()

        for line in lines:
            stripped = line.strip()
            # 跳过空行和注释
            if not stripped or stripped.startswith('#'):
                updated_lines.append(line)
                continue

            # 检查是否是需要更新的配置
            key = stripped.split('=')[0] if '=' in stripped else None
            if key in config_map:
                updated_lines.append(f"{key}={config_map[key]}\n")
                updated_keys.add(key)
                logger.info("更新配置：%s=%s", key, config_map[key])
            else:
                updated_lines.append(line)

        # 添加缺失的配置项
        for key, value in config_map.items():
            if key not in updated_keys:
                updated_lines.append(f"\n# 自动添加的配置\n{key}={value}\n")
                logger.info("添加配置：%s=%s", key, value)

        # 写回文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)

        logger.info("高级配置已保存到.env文件")

        # 重新加载配置，使更改立即生效
        try:
            reload_settings()
            logger.info("配置已重新加载，立即生效")
            hot_reload_success = True
        except Exception as reload_error:
            logger.warning("配置重载失败: %s，需要重启应用", str(reload_error), exc_info=True)
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
