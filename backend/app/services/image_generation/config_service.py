"""
图片生成配置服务

负责图片生成配置的CRUD操作，与图片生成逻辑解耦。
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import ImageConfigCreate, ImageConfigUpdate
from .providers import ImageProviderFactory
from ...models.image_config import ImageGenerationConfig

logger = logging.getLogger(__name__)


class ImageConfigService:
    """图片生成配置管理服务

    职责：
    - 配置的CRUD操作
    - 配置激活/切换
    - 配置连接测试

    遵循单一职责原则，仅处理配置相关逻辑。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_configs(self, user_id: int) -> List[ImageGenerationConfig]:
        """获取用户的所有图片生成配置"""
        result = await self.session.execute(
            select(ImageGenerationConfig)
            .where(ImageGenerationConfig.user_id == user_id)
            .order_by(ImageGenerationConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_config(self, config_id: int, user_id: int) -> Optional[ImageGenerationConfig]:
        """获取单个配置"""
        result = await self.session.execute(
            select(ImageGenerationConfig).where(
                ImageGenerationConfig.id == config_id,
                ImageGenerationConfig.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_config(self, user_id: int) -> Optional[ImageGenerationConfig]:
        """获取用户激活的配置"""
        result = await self.session.execute(
            select(ImageGenerationConfig).where(
                ImageGenerationConfig.user_id == user_id,
                ImageGenerationConfig.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def create_config(
        self, user_id: int, data: ImageConfigCreate
    ) -> ImageGenerationConfig:
        """创建新配置"""
        config = ImageGenerationConfig(
            user_id=user_id,
            config_name=data.config_name,
            provider_type=data.provider_type.value,
            api_base_url=data.api_base_url,
            api_key=data.api_key,
            model_name=data.model_name,
            default_style=data.default_style,
            default_ratio=data.default_ratio,
            default_resolution=data.default_resolution,
            default_quality=data.default_quality,
            extra_params=data.extra_params or {},
        )
        self.session.add(config)
        await self.session.flush()
        return config

    async def update_config(
        self, config_id: int, user_id: int, data: ImageConfigUpdate
    ) -> Optional[ImageGenerationConfig]:
        """更新配置"""
        config = await self.get_config(config_id, user_id)
        if not config:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "provider_type" and value is not None:
                setattr(config, key, value.value)
            else:
                setattr(config, key, value)

        await self.session.flush()
        return config

    async def delete_config(self, config_id: int, user_id: int) -> bool:
        """删除配置"""
        config = await self.get_config(config_id, user_id)
        if not config:
            return False

        if config.is_active:
            raise ValueError("无法删除激活的配置")

        await self.session.delete(config)
        await self.session.flush()
        return True

    async def activate_config(self, config_id: int, user_id: int) -> bool:
        """激活配置"""
        # 先取消所有其他配置的激活状态
        result = await self.session.execute(
            select(ImageGenerationConfig).where(
                ImageGenerationConfig.user_id == user_id,
                ImageGenerationConfig.is_active == True,
            )
        )
        for old_config in result.scalars().all():
            old_config.is_active = False

        # 激活指定配置
        config = await self.get_config(config_id, user_id)
        if not config:
            return False

        config.is_active = True
        await self.session.flush()
        return True

    async def test_config(self, config_id: int, user_id: int) -> Dict[str, Any]:
        """测试配置连接（使用工厂模式）"""
        config = await self.get_config(config_id, user_id)
        if not config:
            return {"success": False, "message": "配置不存在"}

        try:
            # 使用工厂获取对应的供应商
            provider = ImageProviderFactory.get_provider(config.provider_type)
            if not provider:
                result = {"success": False, "message": f"不支持的提供商类型: {config.provider_type}"}
            else:
                test_result = await provider.test_connection(config)
                result = {
                    "success": test_result.success,
                    "message": test_result.message,
                    **test_result.extra_info
                }

            # 更新测试状态
            config.last_test_at = datetime.utcnow()
            config.test_status = "success" if result["success"] else "failed"
            config.test_message = result.get("message", "")
            config.is_verified = result["success"]
            await self.session.flush()

            return result

        except Exception as e:
            logger.error(f"测试配置失败: {e}")
            config.last_test_at = datetime.utcnow()
            config.test_status = "failed"
            config.test_message = str(e)
            await self.session.flush()
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # 导入导出功能
    # ------------------------------------------------------------------

    async def export_config(self, config_id: int, user_id: int) -> dict:
        """
        导出单个图片生成配置为JSON格式。

        Args:
            config_id: 配置ID
            user_id: 用户ID（权限验证）

        Returns:
            包含配置信息的字典
        """
        from datetime import timezone
        from .schemas import ImageConfigExport, ImageConfigExportData

        config = await self.get_config(config_id, user_id)
        if not config:
            raise ValueError(f"配置不存在: ID={config_id}")

        export_data = ImageConfigExportData(
            version="1.0",
            export_time=datetime.now(timezone.utc).isoformat(),
            export_type="image",
            configs=[
                ImageConfigExport(
                    config_name=config.config_name,
                    provider_type=config.provider_type,
                    api_base_url=config.api_base_url,
                    api_key=config.api_key,
                    model_name=config.model_name,
                    default_style=config.default_style,
                    default_ratio=config.default_ratio,
                    default_resolution=config.default_resolution,
                    default_quality=config.default_quality,
                    extra_params=config.extra_params,
                )
            ],
        )

        return export_data.model_dump()

    async def export_all_configs(self, user_id: int) -> dict:
        """
        导出用户的所有图片生成配置为JSON格式。

        Args:
            user_id: 用户ID

        Returns:
            包含所有配置的字典
        """
        from datetime import timezone
        from .schemas import ImageConfigExport, ImageConfigExportData

        configs = await self.get_configs(user_id)
        if not configs:
            raise ValueError(f"用户ID={user_id}无配置可导出")

        export_data = ImageConfigExportData(
            version="1.0",
            export_time=datetime.now(timezone.utc).isoformat(),
            export_type="image",
            configs=[
                ImageConfigExport(
                    config_name=config.config_name,
                    provider_type=config.provider_type,
                    api_base_url=config.api_base_url,
                    api_key=config.api_key,
                    model_name=config.model_name,
                    default_style=config.default_style,
                    default_ratio=config.default_ratio,
                    default_resolution=config.default_resolution,
                    default_quality=config.default_quality,
                    extra_params=config.extra_params,
                )
                for config in configs
            ],
        )

        return export_data.model_dump()

    async def import_configs(self, user_id: int, import_data: dict) -> dict:
        """
        导入图片生成配置。

        Args:
            user_id: 用户ID
            import_data: 导入的配置数据

        Returns:
            导入结果统计
        """
        from .schemas import ImageConfigExportData, ImageConfigImportResult

        # 验证导入数据格式
        try:
            data = ImageConfigExportData(**import_data)
        except Exception as exc:
            raise ValueError(f"导入数据格式错误: {str(exc)}")

        # 检查版本兼容性
        if data.version != "1.0":
            raise ValueError(f"不支持的导出格式版本: {data.version}，当前仅支持 1.0")

        # 获取用户现有的配置名称
        existing_configs = await self.get_configs(user_id)
        existing_names = {config.config_name for config in existing_configs}

        imported_count = 0
        skipped_count = 0
        failed_count = 0
        details = []

        for config_data in data.configs:
            try:
                # 处理重名
                original_name = config_data.config_name
                config_name = original_name
                suffix = 1

                while config_name in existing_names:
                    config_name = f"{original_name} ({suffix})"
                    suffix += 1

                if config_name != original_name:
                    details.append(
                        f"配置 '{original_name}' 已重命名为 '{config_name}'（避免重名）"
                    )

                # 创建新配置
                new_config = ImageGenerationConfig(
                    user_id=user_id,
                    config_name=config_name,
                    provider_type=config_data.provider_type,
                    api_base_url=config_data.api_base_url,
                    api_key=config_data.api_key,
                    model_name=config_data.model_name,
                    default_style=config_data.default_style,
                    default_ratio=config_data.default_ratio,
                    default_resolution=config_data.default_resolution,
                    default_quality=config_data.default_quality,
                    extra_params=config_data.extra_params or {},
                    is_active=False,
                    is_verified=False,
                )

                self.session.add(new_config)
                existing_names.add(config_name)
                imported_count += 1
                details.append(f"成功导入配置 '{config_name}'")

            except Exception as exc:
                failed_count += 1
                details.append(
                    f"导入配置 '{config_data.config_name}' 失败: {str(exc)}"
                )
                logger.error(
                    "导入图片配置失败: user_id=%s, config_name=%s, error=%s",
                    user_id,
                    config_data.config_name,
                    str(exc),
                    exc_info=True,
                )

        await self.session.flush()

        return ImageConfigImportResult(
            success=imported_count > 0,
            message=f"导入完成：成功 {imported_count} 个，失败 {failed_count} 个",
            imported_count=imported_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            details=details,
        ).model_dump()
