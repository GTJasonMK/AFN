"""
主题配置API路由

提供主题配置的CRUD接口，支持获取默认值、激活配置、导入导出等功能。
支持两种配置格式：
- V1（旧版）：面向常量的配置
- V2（新版）：面向组件的配置
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends

from ...core.dependencies import get_default_user, get_theme_config_service
from ...schemas.theme_config import (
    ThemeConfigCreate,
    ThemeConfigUpdate,
    ThemeConfigRead,
    ThemeConfigListItem,
    ThemeDefaultsResponse,
    ThemeConfigExport,
    ThemeConfigExportData,
    ThemeConfigImportRequest,
    ThemeConfigImportResult,
    ThemeConfigV2Create,
    ThemeConfigV2Update,
    ThemeConfigV2Read,
    ThemeV2DefaultsResponse,
    ThemeConfigUnifiedRead,
)
from ...schemas.user import UserInDB
from ...services.theme_config_service import ThemeConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/theme-configs", tags=["主题配置"])


# ==================== 固定路径路由（必须在动态路径之前）====================


@router.get("", response_model=list[ThemeConfigListItem])
async def list_theme_configs(
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> list[ThemeConfigListItem]:
    """获取用户的所有主题配置列表"""
    logger.info("用户 %s 查询主题配置列表", desktop_user.id)
    return await service.list_configs(desktop_user.id)


@router.get("/defaults/{mode}", response_model=ThemeDefaultsResponse)
async def get_theme_defaults(
    mode: Literal["light", "dark"],
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeDefaultsResponse:
    """获取指定模式的默认主题值"""
    logger.info("用户 %s 获取 %s 模式默认值", desktop_user.id, mode)
    return await service.get_defaults(mode)


@router.get("/export", response_model=ThemeConfigExportData)
async def export_all_theme_configs(
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigExportData:
    """导出用户所有主题配置"""
    logger.info("用户 %s 导出所有主题配置", desktop_user.id)
    return await service.export_all_configs(desktop_user.id)


@router.get("/active/{parent_mode}", response_model=ThemeConfigRead | None)
async def get_active_theme_config(
    parent_mode: Literal["light", "dark"],
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigRead | None:
    """获取指定模式下当前激活的主题配置"""
    logger.info("用户 %s 获取 %s 模式激活配置", desktop_user.id, parent_mode)
    return await service.get_active_config(desktop_user.id, parent_mode)


# ==================== 动态路径路由（{config_id}）====================


@router.get("/{config_id}", response_model=ThemeConfigRead)
async def get_theme_config(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigRead:
    """获取指定ID的主题配置详情"""
    logger.info("用户 %s 获取主题配置 ID=%s", desktop_user.id, config_id)
    return await service.get_config(config_id, desktop_user.id)


@router.get("/{config_id}/export", response_model=ThemeConfigExport)
async def export_theme_config(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigExport:
    """导出单个主题配置"""
    logger.info("用户 %s 导出主题配置 ID=%s", desktop_user.id, config_id)
    return await service.export_config(config_id, desktop_user.id)


@router.post("", response_model=ThemeConfigRead)
async def create_theme_config(
    payload: ThemeConfigCreate,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigRead:
    """创建新的主题配置"""
    logger.info("用户 %s 创建主题配置: %s (%s)", desktop_user.id, payload.config_name, payload.parent_mode)
    return await service.create_config(desktop_user.id, payload)


@router.post("/import", response_model=ThemeConfigImportResult)
async def import_theme_configs(
    request: ThemeConfigImportRequest,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigImportResult:
    """导入主题配置"""
    logger.info("用户 %s 导入主题配置", desktop_user.id)
    return await service.import_configs(desktop_user.id, request.data)


@router.post("/{config_id}/activate", response_model=ThemeConfigUnifiedRead)
async def activate_theme_config(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigUnifiedRead:
    """激活指定的主题配置

    返回统一格式的配置（包含V1和V2所有字段），确保前端能够正确
    读取 effects 字段以应用透明效果等V2配置。
    """
    logger.info("用户 %s 激活主题配置 ID=%s", desktop_user.id, config_id)
    return await service.activate_config(config_id, desktop_user.id)


@router.post("/{config_id}/duplicate", response_model=ThemeConfigRead)
async def duplicate_theme_config(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigRead:
    """复制主题配置"""
    logger.info("用户 %s 复制主题配置 ID=%s", desktop_user.id, config_id)
    return await service.duplicate_config(config_id, desktop_user.id)


@router.post("/{config_id}/reset", response_model=ThemeConfigRead)
async def reset_theme_config(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigRead:
    """重置主题配置为默认值"""
    logger.info("用户 %s 重置主题配置 ID=%s", desktop_user.id, config_id)
    return await service.reset_config(config_id, desktop_user.id)


@router.put("/{config_id}", response_model=ThemeConfigRead)
async def update_theme_config(
    config_id: int,
    payload: ThemeConfigUpdate,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigRead:
    """更新主题配置"""
    logger.info("用户 %s 更新主题配置 ID=%s", desktop_user.id, config_id)
    return await service.update_config(config_id, desktop_user.id, payload)


@router.delete("/{config_id}")
async def delete_theme_config(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除主题配置"""
    logger.info("用户 %s 删除主题配置 ID=%s", desktop_user.id, config_id)
    await service.delete_config(config_id, desktop_user.id)
    return {"success": True, "message": "配置已删除"}


# ==================== V2: 面向组件的配置API ====================


@router.get("/v2/defaults/{mode}", response_model=ThemeV2DefaultsResponse)
async def get_theme_v2_defaults(
    mode: Literal["light", "dark"],
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeV2DefaultsResponse:
    """获取V2格式指定模式的默认主题值（面向组件）"""
    logger.info("用户 %s 获取V2 %s模式默认值", desktop_user.id, mode)
    return await service.get_v2_defaults(mode)


@router.get("/v2/{config_id}", response_model=ThemeConfigV2Read)
async def get_theme_v2_config(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigV2Read:
    """获取V2格式的主题配置详情"""
    logger.info("用户 %s 获取V2主题配置 ID=%s", desktop_user.id, config_id)
    return await service.get_v2_config(config_id, desktop_user.id)


@router.get("/unified/active/{parent_mode}", response_model=ThemeConfigUnifiedRead | None)
async def get_active_unified_theme_config(
    parent_mode: Literal["light", "dark"],
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigUnifiedRead | None:
    """获取指定模式下当前激活的统一格式主题配置"""
    logger.info("用户 %s 获取 %s 模式统一格式激活配置", desktop_user.id, parent_mode)
    return await service.get_active_unified_config(desktop_user.id, parent_mode)


@router.get("/unified/{config_id}", response_model=ThemeConfigUnifiedRead)
async def get_unified_theme_config(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigUnifiedRead:
    """获取统一格式的主题配置详情（支持V1和V2）"""
    logger.info("用户 %s 获取统一格式主题配置 ID=%s", desktop_user.id, config_id)
    return await service.get_unified_config(config_id, desktop_user.id)


@router.post("/v2", response_model=ThemeConfigV2Read)
async def create_theme_v2_config(
    payload: ThemeConfigV2Create,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigV2Read:
    """创建V2格式的主题配置"""
    logger.info(
        "用户 %s 创建V2主题配置: %s (%s)",
        desktop_user.id, payload.config_name, payload.parent_mode
    )
    return await service.create_v2_config(desktop_user.id, payload)


@router.put("/v2/{config_id}", response_model=ThemeConfigV2Read)
async def update_theme_v2_config(
    config_id: int,
    payload: ThemeConfigV2Update,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigV2Read:
    """更新V2格式的主题配置"""
    logger.info("用户 %s 更新V2主题配置 ID=%s", desktop_user.id, config_id)
    return await service.update_v2_config(config_id, desktop_user.id, payload)


@router.post("/v2/{config_id}/reset", response_model=ThemeConfigV2Read)
async def reset_theme_v2_config(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigV2Read:
    """重置V2主题配置为默认值"""
    logger.info("用户 %s 重置V2主题配置 ID=%s", desktop_user.id, config_id)
    return await service.reset_v2_config(config_id, desktop_user.id)


@router.post("/{config_id}/migrate-to-v2", response_model=ThemeConfigV2Read)
async def migrate_theme_config_to_v2(
    config_id: int,
    service: ThemeConfigService = Depends(get_theme_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ThemeConfigV2Read:
    """将V1配置迁移到V2格式

    保留V1配置数据，同时填充V2字段为默认值。
    """
    logger.info("用户 %s 将配置 ID=%s 迁移到V2格式", desktop_user.id, config_id)
    return await service.migrate_to_v2(config_id, desktop_user.id)
