"""
嵌入模型配置路由

提供嵌入模型配置的 CRUD 和测试接口。
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_default_user, get_embedding_config_service
from ...db.session import get_session
from ...exceptions import ResourceNotFoundError
from ...schemas.embedding_config import (
    EmbeddingConfigCreate,
    EmbeddingConfigRead,
    EmbeddingConfigUpdate,
    EmbeddingConfigTestResponse,
    EMBEDDING_PROVIDERS,
)
from ...schemas.user import UserInDB
from ...services.embedding_config_service import EmbeddingConfigService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/embedding-configs", tags=["Embedding Configuration"])


# ========== 嵌入模型配置管理API ==========


@router.get("/providers")
async def list_providers():
    """获取支持的嵌入模型提供方列表。"""
    return [provider.model_dump() for provider in EMBEDDING_PROVIDERS]


@router.get("", response_model=list[EmbeddingConfigRead])
async def list_embedding_configs(
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> list[EmbeddingConfigRead]:
    """获取用户的所有嵌入模型配置列表。"""
    logger.debug("用户 %s 查询嵌入模型配置列表", desktop_user.id)
    return await service.list_configs(desktop_user.id)


@router.get("/active", response_model=EmbeddingConfigRead)
async def get_active_config(
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """获取用户当前激活的嵌入模型配置。"""
    config = await service.get_active_config(desktop_user.id)
    if not config:
        logger.warning("用户 %s 没有激活的嵌入模型配置", desktop_user.id)
        raise ResourceNotFoundError("激活的嵌入模型配置", f"用户 {desktop_user.id}")
    logger.debug("用户 %s 获取激活的嵌入模型配置: %s", desktop_user.id, config.config_name)
    return config


@router.get("/{config_id}", response_model=EmbeddingConfigRead)
async def get_embedding_config_by_id(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """获取指定ID的嵌入模型配置。"""
    logger.debug("用户 %s 查询嵌入模型配置 ID=%s", desktop_user.id, config_id)
    return await service.get_config(config_id, desktop_user.id)


@router.post("", response_model=EmbeddingConfigRead, status_code=status.HTTP_201_CREATED)
async def create_embedding_config(
    payload: EmbeddingConfigCreate,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """创建新的嵌入模型配置。"""
    logger.info("用户 %s 创建嵌入模型配置: %s", desktop_user.id, payload.config_name)
    return await service.create_config(desktop_user.id, payload)


@router.put("/{config_id}", response_model=EmbeddingConfigRead)
async def update_embedding_config(
    config_id: int,
    payload: EmbeddingConfigUpdate,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """更新指定ID的嵌入模型配置。"""
    logger.info("用户 %s 更新嵌入模型配置 ID=%s", desktop_user.id, config_id)
    return await service.update_config(config_id, desktop_user.id, payload)


@router.post("/{config_id}/activate", response_model=EmbeddingConfigRead)
async def activate_embedding_config(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """激活指定ID的嵌入模型配置。"""
    logger.info("用户 %s 激活嵌入模型配置 ID=%s", desktop_user.id, config_id)
    return await service.activate_config(config_id, desktop_user.id)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_embedding_config_by_id(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> None:
    """删除指定ID的嵌入模型配置。"""
    logger.info("用户 %s 删除嵌入模型配置 ID=%s", desktop_user.id, config_id)
    await service.delete_config(config_id, desktop_user.id)


@router.post("/{config_id}/test", response_model=EmbeddingConfigTestResponse)
async def test_embedding_config(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigTestResponse:
    """测试指定ID的嵌入模型配置是否可用。"""
    logger.info("用户 %s 测试嵌入模型配置 ID=%s", desktop_user.id, config_id)
    return await service.test_config(config_id, desktop_user.id)


# ========== 导入导出API ==========


@router.get("/{config_id}/export")
async def export_embedding_config(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """导出单个嵌入模型配置。"""
    logger.debug("用户 %s 导出嵌入模型配置 ID=%s", desktop_user.id, config_id)
    export_data = await service.export_config(config_id, desktop_user.id)
    return export_data


@router.get("/export/all")
async def export_all_embedding_configs(
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """导出用户的所有嵌入模型配置。"""
    logger.debug("用户 %s 导出所有嵌入模型配置", desktop_user.id)
    export_data = await service.export_all_configs(desktop_user.id)
    return export_data


@router.post("/import")
async def import_embedding_configs(
    import_data: dict,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """导入嵌入模型配置。"""
    logger.info("用户 %s 导入嵌入模型配置", desktop_user.id)
    result = await service.import_configs(desktop_user.id, import_data)
    return result
