import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_default_user
from ...db.session import get_session
from ...exceptions import ResourceNotFoundError
from ...schemas.llm_config import (
    LLMConfigCreate,
    LLMConfigRead,
    LLMConfigUpdate,
    LLMConfigTestRequest,
    LLMConfigTestResponse,
)
from ...schemas.user import UserInDB
from ...services.llm_config_service import LLMConfigService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm-configs", tags=["LLM Configuration"])


def get_llm_config_service(session: AsyncSession = Depends(get_session)) -> LLMConfigService:
    return LLMConfigService(session)


# ========== LLM配置管理API ==========


@router.get("", response_model=list[LLMConfigRead])
async def list_llm_configs(
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> list[LLMConfigRead]:
    """获取用户的所有LLM配置列表。"""
    logger.info("用户 %s 查询 LLM 配置列表", desktop_user.id)
    return await service.list_configs(desktop_user.id)


@router.get("/active", response_model=LLMConfigRead)
async def get_active_config(
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """获取用户当前激活的LLM配置。"""
    config = await service.get_active_config(desktop_user.id)
    if not config:
        logger.warning("用户 %s 没有激活的 LLM 配置", desktop_user.id)
        raise ResourceNotFoundError("激活的LLM配置", f"用户 {desktop_user.id}")
    logger.info("用户 %s 获取激活的 LLM 配置: %s", desktop_user.id, config.config_name)
    return config


@router.get("/{config_id}", response_model=LLMConfigRead)
async def get_llm_config_by_id(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """获取指定ID的LLM配置。"""
    logger.info("用户 %s 查询 LLM 配置 ID=%s", desktop_user.id, config_id)
    return await service.get_config(config_id, desktop_user.id)


@router.post("", response_model=LLMConfigRead, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    payload: LLMConfigCreate,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """创建新的LLM配置。"""
    logger.info("用户 %s 创建 LLM 配置: %s", desktop_user.id, payload.config_name)
    return await service.create_config(desktop_user.id, payload)


@router.put("/{config_id}", response_model=LLMConfigRead)
async def update_llm_config(
    config_id: int,
    payload: LLMConfigUpdate,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """更新指定ID的LLM配置。"""
    logger.info("用户 %s 更新 LLM 配置 ID=%s", desktop_user.id, config_id)
    return await service.update_config(config_id, desktop_user.id, payload)


@router.post("/{config_id}/activate", response_model=LLMConfigRead)
async def activate_llm_config(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """激活指定ID的LLM配置。"""
    logger.info("用户 %s 激活 LLM 配置 ID=%s", desktop_user.id, config_id)
    return await service.activate_config(config_id, desktop_user.id)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config_by_id(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> None:
    """删除指定ID的LLM配置。"""
    logger.info("用户 %s 删除 LLM 配置 ID=%s", desktop_user.id, config_id)
    await service.delete_config(config_id, desktop_user.id)


@router.post("/{config_id}/test", response_model=LLMConfigTestResponse)
async def test_llm_config(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigTestResponse:
    """测试指定ID的LLM配置是否可用。"""
    logger.info("用户 %s 测试 LLM 配置 ID=%s", desktop_user.id, config_id)
    return await service.test_config(config_id, desktop_user.id)


# ========== 导入导出功能 ==========


@router.get("/{config_id}/export")
async def export_llm_config(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导出单个LLM配置为JSON文件。"""
    logger.info("用户 %s 导出 LLM 配置 ID=%s", desktop_user.id, config_id)
    export_data = await service.export_config(config_id, desktop_user.id)

    # 返回JSON文件下载
    from fastapi.responses import JSONResponse
    filename = f"llm_config_{config_id}.json"
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/export", response_model=list[dict])
async def export_all_llm_configs(
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导出用户的所有LLM配置为JSON列表。"""
    logger.info("用户 %s 导出所有 LLM 配置", desktop_user.id)
    export_data = await service.export_all_configs(desktop_user.id)
    return export_data


@router.post("/import")
async def import_llm_configs(
    import_data: dict,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导入LLM配置数据（需符合LLMConfigExportData格式）。"""
    logger.info("用户 %s 导入 LLM 配置", desktop_user.id)
    result = await service.import_configs(desktop_user.id, import_data)
    return result

