"""
全局配置导入导出路由

包含：
- /export/all 导出所有配置
- /import/all 导入所有配置（支持选择性导入）
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.dependencies import get_default_user
from ...db.session import get_session
from ...schemas.user import UserInDB
from .settings_advanced import import_advanced_config
from .settings_max_tokens import MAX_TOKENS_FIELDS
from .settings_models import ConfigImportResult
from .settings_queue import import_queue_config
from .settings_temperature import TEMPERATURE_FIELDS
from .settings_utils import load_config, save_config

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.get("/export/all")
async def export_all_configs(
    session: AsyncSession = Depends(get_session),
    current_user: UserInDB = Depends(get_default_user),
) -> AllConfigExportData:
    """
    导出所有配置（LLM、嵌入、图片、高级、队列、提示词、主题）

    Returns:
        包含所有配置的JSON数据
    """
    from ...services.embedding_config_service import EmbeddingConfigService
    from ...services.image_generation import ImageConfigService
    from ...services.llm_config_service import LLMConfigService
    from ...services.prompt_service import PromptService
    from ...services.queue import ImageRequestQueue, LLMRequestQueue
    from ...services.theme_config_service import ThemeConfigService

    is_admin = bool(getattr(current_user, "is_admin", False))

    # 获取LLM配置（使用service的export方法获取完整数据）
    llm_service = LLMConfigService(session)
    try:
        llm_export = await llm_service.export_all_configs(current_user.id)
        llm_configs_data = llm_export.get("configs", [])
    except Exception:
        # 用户没有LLM配置时，返回空列表
        llm_configs_data = []

    # 获取嵌入配置（使用service的export方法获取完整数据）
    embedding_service = EmbeddingConfigService(session)
    try:
        embedding_export = await embedding_service.export_all_configs(current_user.id)
        embedding_configs_data = embedding_export.get("configs", [])
    except Exception:
        # 用户没有嵌入配置时，返回空列表
        embedding_configs_data = []

    # 获取图片配置（使用service的export方法获取完整数据）
    image_service = ImageConfigService(session)
    try:
        image_export = await image_service.export_all_configs(current_user.id)
        image_configs_data = image_export.get("configs", [])
    except Exception:
        # 用户没有图片配置时，返回空列表
        image_configs_data = []

    # 全局配置（仅管理员可导出）
    advanced_config = None
    queue_config = None
    max_tokens_config = None
    temperature_config = None
    prompt_configs_data = None

    if is_admin:
        current_config = load_config()
        advanced_config = {
            "coding_project_enabled": current_config.get("coding_project_enabled", settings.coding_project_enabled),
            "writer_chapter_version_count": current_config.get(
                "writer_chapter_version_count", settings.writer_chapter_versions
            ),
            "writer_parallel_generation": current_config.get(
                "writer_parallel_generation", settings.writer_parallel_generation
            ),
            "part_outline_threshold": current_config.get("part_outline_threshold", settings.part_outline_threshold),
            "agent_context_max_chars": current_config.get("agent_context_max_chars", settings.agent_context_max_chars),
        }

        # 获取队列配置
        llm_queue = LLMRequestQueue.get_instance()
        image_queue = ImageRequestQueue.get_instance()
        queue_config = {
            "llm_max_concurrent": llm_queue.max_concurrent,
            "image_max_concurrent": image_queue.max_concurrent,
        }

        # 获取Max Tokens配置
        max_tokens_config = {key: current_config.get(key, getattr(settings, key)) for key in MAX_TOKENS_FIELDS}

        # 获取Temperature配置
        temperature_config = {key: current_config.get(key, getattr(settings, key)) for key in TEMPERATURE_FIELDS}

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
        theme_export = await theme_service.export_all_configs(current_user.id)
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
    current_user: UserInDB = Depends(get_default_user),
) -> ConfigImportResult:
    """
    导入所有配置（LLM、嵌入、图片、高级、队列、提示词、主题）

    支持选择性导入：只导入import_data中存在的配置类型

    Args:
        import_data: 导入的配置数据

    Returns:
        导入结果
    """
    from ...services.embedding_config_service import EmbeddingConfigService
    from ...services.image_generation import ImageConfigService
    from ...services.llm_config_service import LLMConfigService
    from ...services.prompt_service import PromptService
    from ...services.theme_config_service import ThemeConfigService

    details = []
    has_error = False

    try:
        is_admin = bool(getattr(current_user, "is_admin", False))

        # 验证导入数据格式
        if import_data.get("export_type") != "all":
            return ConfigImportResult(success=False, message="导入数据类型不匹配，期望 'all'", details=[])

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
                    "configs": import_data["llm_configs"],
                }
                result = await llm_service.import_configs(current_user.id, llm_import_data)
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
                    "configs": import_data["embedding_configs"],
                }
                result = await embedding_service.import_configs(current_user.id, embedding_import_data)
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
                    "configs": import_data["image_configs"],
                }
                result = await image_service.import_configs(current_user.id, image_import_data)
                details.append(f"图片配置: {result.get('message', '导入完成')}")
            except Exception as e:
                details.append(f"图片配置导入失败: {str(e)}")
                has_error = True

        # 导入高级配置
        if import_data.get("advanced_config"):
            if not is_admin:
                details.append("高级配置: 需要管理员权限，已跳过")
                has_error = True
            else:
                try:
                    advanced_import_data = {"export_type": "advanced", "config": import_data["advanced_config"]}
                    result = await import_advanced_config(advanced_import_data)
                    details.append(f"高级配置: {result.message}")
                    if not result.success:
                        has_error = True
                except Exception as e:
                    details.append(f"高级配置导入失败: {str(e)}")
                    has_error = True

        # 导入队列配置
        if import_data.get("queue_config"):
            if not is_admin:
                details.append("队列配置: 需要管理员权限，已跳过")
                has_error = True
            else:
                try:
                    queue_import_data = {"export_type": "queue", "config": import_data["queue_config"]}
                    result = await import_queue_config(queue_import_data)
                    details.append(f"队列配置: {result.message}")
                    if not result.success:
                        has_error = True
                except Exception as e:
                    details.append(f"队列配置导入失败: {str(e)}")
                    has_error = True

        # 导入Max Tokens配置
        if import_data.get("max_tokens_config"):
            if not is_admin:
                details.append("Max Tokens配置: 需要管理员权限，已跳过")
                has_error = True
            else:
                try:
                    max_tokens_data = import_data["max_tokens_config"]
                    current_config = load_config()
                    updated_fields = []

                    for field, (min_val, max_val) in MAX_TOKENS_FIELDS.items():
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
            if not is_admin:
                details.append("Temperature配置: 需要管理员权限，已跳过")
                has_error = True
            else:
                try:
                    temperature_data = import_data["temperature_config"]
                    current_config = load_config()
                    updated_fields = []

                    for field in TEMPERATURE_FIELDS:
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
            if not is_admin:
                details.append("提示词配置: 需要管理员权限，已跳过")
                has_error = True
            else:
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
                result = await theme_service.import_configs(current_user.id, theme_import_data)
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
            details=details,
        )

    except Exception as e:
        logger.error("导入全局配置失败: %s", str(e), exc_info=True)
        return ConfigImportResult(success=False, message=f"导入失败: {str(e)}", details=details)


__all__ = ["router", "AllConfigExportData"]
