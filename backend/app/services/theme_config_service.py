"""
主题配置服务

提供主题配置的CRUD操作，支持获取默认值、激活配置、导入导出等功能。
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..exceptions import ResourceNotFoundError, ConflictError, InvalidParameterError
from ..models import ThemeConfig
from ..repositories.theme_config_repository import ThemeConfigRepository
from ..schemas.theme_config import (
    ThemeConfigCreate,
    ThemeConfigUpdate,
    ThemeConfigRead,
    ThemeConfigListItem,
    ThemeDefaultsResponse,
    ThemeConfigExport,
    ThemeConfigExportData,
    ThemeConfigImportResult,
    ThemeConfigV2Create,
    ThemeConfigV2Update,
    ThemeConfigV2Read,
    ThemeV2DefaultsResponse,
    ThemeConfigUnifiedRead,
)

# 从拆分后的模块导入主题默认值
from .theme_defaults import (
    LIGHT_THEME_DEFAULTS,
    DARK_THEME_DEFAULTS,
    LIGHT_THEME_V2_DEFAULTS,
    DARK_THEME_V2_DEFAULTS,
    get_theme_defaults,
    get_theme_v2_defaults,
)

logger = logging.getLogger(__name__)


class ThemeConfigService:
    """
    主题配置服务，支持多配置管理和切换。

    架构说明：
    - 每个parent_mode（light/dark）下可有多个子主题
    - 每个parent_mode下只能有一个激活的子主题
    - 配置CRUD操作是独立的原子操作，每个方法内部commit
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ThemeConfigRepository(session)

    async def list_configs(self, user_id: int) -> list[ThemeConfigListItem]:
        """获取用户的所有主题配置列表。"""
        configs = await self.repo.list_by_user(user_id)
        return [ThemeConfigListItem.model_validate(config) for config in configs]

    async def get_config(self, config_id: int, user_id: int) -> ThemeConfigRead:
        """获取指定ID的配置详情。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")
        return ThemeConfigRead.model_validate(config)

    async def get_active_config(self, user_id: int, parent_mode: str) -> Optional[ThemeConfigRead]:
        """获取用户指定模式下当前激活的配置。"""
        config = await self.repo.get_active_config(user_id, parent_mode)
        return ThemeConfigRead.model_validate(config) if config else None

    async def get_defaults(self, mode: str) -> ThemeDefaultsResponse:
        """获取指定模式的默认主题值。"""
        if mode not in ("light", "dark"):
            raise InvalidParameterError(f"无效的主题模式: {mode}，应为 'light' 或 'dark'")

        defaults = get_theme_defaults(mode)
        return ThemeDefaultsResponse(mode=mode, **defaults)

    async def create_config(self, user_id: int, payload: ThemeConfigCreate) -> ThemeConfigRead:
        """创建新的主题配置。"""
        # 验证parent_mode
        if payload.parent_mode not in ("light", "dark"):
            raise InvalidParameterError(f"无效的主题模式: {payload.parent_mode}")

        # 检查配置名称是否重复（同模式下）
        existing = await self.repo.get_by_name(user_id, payload.config_name, payload.parent_mode)
        if existing:
            raise ConflictError(f"配置名称 '{payload.config_name}' 已存在于 {payload.parent_mode} 模式下")

        # 合并默认值和用户提供的值
        defaults = get_theme_defaults(payload.parent_mode)
        data = payload.model_dump(exclude_unset=True)

        # 对于未提供的配置组，使用默认值
        config_groups = [
            "primary_colors",
            "accent_colors",
            "semantic_colors",
            "text_colors",
            "background_colors",
            "border_effects",
            "button_colors",
            "typography",
            "border_radius",
            "spacing",
            "animation",
            "button_sizes",
        ]
        for group in config_groups:
            if group not in data or data[group] is None:
                data[group] = defaults.get(group)

        # 如果该模式下没有任何配置，则将新配置设为激活
        count = await self.repo.count_by_mode(user_id, payload.parent_mode)
        is_first_config = count == 0

        instance = ThemeConfig(
            user_id=user_id,
            is_active=is_first_config,
            **data,
        )
        await self.repo.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return ThemeConfigRead.model_validate(instance)

    async def update_config(
        self, config_id: int, user_id: int, payload: ThemeConfigUpdate
    ) -> ThemeConfigRead:
        """更新主题配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        data = payload.model_dump(exclude_unset=True)

        # 检查配置名称是否与其他配置重复
        if "config_name" in data and data["config_name"]:
            existing = await self.repo.get_by_name(user_id, data["config_name"], config.parent_mode)
            if existing and existing.id != config_id:
                raise ConflictError(f"配置名称 '{data['config_name']}' 已存在")

        # 更新字段
        for key, value in data.items():
            if value is not None:
                setattr(config, key, value)

        await self.session.commit()
        await self.session.refresh(config)
        return ThemeConfigRead.model_validate(config)

    async def delete_config(self, config_id: int, user_id: int) -> None:
        """删除主题配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        # 不允许删除激活的配置（除非是该模式下唯一的配置）
        if config.is_active:
            count = await self.repo.count_by_mode(user_id, config.parent_mode)
            if count > 1:
                raise InvalidParameterError("不能删除激活中的配置，请先激活其他配置")

        await self.repo.delete(config)
        await self.session.commit()

    async def activate_config(self, config_id: int, user_id: int) -> ThemeConfigUnifiedRead:
        """激活指定配置。

        返回统一格式的配置（包含V1和V2所有字段），确保前端能够正确
        读取 effects 字段以应用透明效果等V2配置。
        """
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        await self.repo.activate_config(config_id, user_id, config.parent_mode)
        await self.session.commit()
        await self.session.refresh(config)
        return ThemeConfigUnifiedRead.model_validate(config)

    async def duplicate_config(self, config_id: int, user_id: int) -> ThemeConfigRead:
        """复制配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        # 生成新名称
        base_name = config.config_name
        new_name = f"{base_name} (副本)"
        counter = 1
        while await self.repo.get_by_name(user_id, new_name, config.parent_mode):
            counter += 1
            new_name = f"{base_name} (副本 {counter})"

        # 创建副本
        new_config = ThemeConfig(
            user_id=user_id,
            config_name=new_name,
            parent_mode=config.parent_mode,
            is_active=False,
            primary_colors=config.primary_colors,
            accent_colors=config.accent_colors,
            semantic_colors=config.semantic_colors,
            text_colors=config.text_colors,
            background_colors=config.background_colors,
            border_effects=config.border_effects,
            button_colors=config.button_colors,
            typography=config.typography,
            border_radius=config.border_radius,
            spacing=config.spacing,
            animation=config.animation,
            button_sizes=config.button_sizes,
        )
        await self.repo.add(new_config)
        await self.session.commit()
        await self.session.refresh(new_config)
        return ThemeConfigRead.model_validate(new_config)

    async def reset_config(self, config_id: int, user_id: int) -> ThemeConfigRead:
        """重置配置为默认值。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        defaults = get_theme_defaults(config.parent_mode)

        # 重置所有配置组
        config.primary_colors = defaults["primary_colors"]
        config.accent_colors = defaults["accent_colors"]
        config.semantic_colors = defaults["semantic_colors"]
        config.text_colors = defaults["text_colors"]
        config.background_colors = defaults["background_colors"]
        config.border_effects = defaults["border_effects"]
        config.button_colors = defaults["button_colors"]
        config.typography = defaults["typography"]
        config.border_radius = defaults["border_radius"]
        config.spacing = defaults["spacing"]
        config.animation = defaults["animation"]
        config.button_sizes = defaults["button_sizes"]

        await self.session.commit()
        await self.session.refresh(config)
        return ThemeConfigRead.model_validate(config)

    async def export_config(self, config_id: int, user_id: int) -> ThemeConfigExport:
        """导出单个配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        return ThemeConfigExport(
            config_name=config.config_name,
            parent_mode=config.parent_mode,
            primary_colors=config.primary_colors,
            accent_colors=config.accent_colors,
            semantic_colors=config.semantic_colors,
            text_colors=config.text_colors,
            background_colors=config.background_colors,
            border_effects=config.border_effects,
            button_colors=config.button_colors,
            typography=config.typography,
            border_radius=config.border_radius,
            spacing=config.spacing,
            animation=config.animation,
            button_sizes=config.button_sizes,
        )

    async def export_all_configs(self, user_id: int) -> ThemeConfigExportData:
        """导出用户所有配置。"""
        configs = await self.repo.list_by_user(user_id)
        export_configs = [
            ThemeConfigExport(
                config_name=c.config_name,
                parent_mode=c.parent_mode,
                primary_colors=c.primary_colors,
                accent_colors=c.accent_colors,
                semantic_colors=c.semantic_colors,
                text_colors=c.text_colors,
                background_colors=c.background_colors,
                border_effects=c.border_effects,
                button_colors=c.button_colors,
                typography=c.typography,
                border_radius=c.border_radius,
                spacing=c.spacing,
                animation=c.animation,
                button_sizes=c.button_sizes,
            )
            for c in configs
        ]
        return ThemeConfigExportData(
            export_time=datetime.now(timezone.utc).isoformat(),
            configs=export_configs,
        )

    async def import_configs(
        self, user_id: int, import_data: ThemeConfigExportData
    ) -> ThemeConfigImportResult:
        """导入配置。"""
        imported_count = 0
        skipped_count = 0
        failed_count = 0
        details = []

        for export_config in import_data.configs:
            try:
                # 检查名称是否已存在
                existing = await self.repo.get_by_name(
                    user_id, export_config.config_name, export_config.parent_mode
                )
                if existing:
                    skipped_count += 1
                    details.append(f"跳过: '{export_config.config_name}' 已存在")
                    continue

                # 合并默认值
                defaults = get_theme_defaults(export_config.parent_mode)
                data = export_config.model_dump()

                for group in [
                    "primary_colors",
                    "accent_colors",
                    "semantic_colors",
                    "text_colors",
                    "background_colors",
                    "border_effects",
                    "button_colors",
                    "typography",
                    "border_radius",
                    "spacing",
                    "animation",
                    "button_sizes",
                ]:
                    if group not in data or data[group] is None:
                        data[group] = defaults.get(group)

                instance = ThemeConfig(
                    user_id=user_id,
                    is_active=False,
                    **data,
                )
                await self.repo.add(instance)
                imported_count += 1
                details.append(f"导入成功: '{export_config.config_name}'")

            except Exception as e:
                failed_count += 1
                details.append(f"导入失败: '{export_config.config_name}' - {str(e)}")
                logger.exception(f"导入主题配置失败: {export_config.config_name}")

        await self.session.commit()

        return ThemeConfigImportResult(
            success=failed_count == 0,
            message=f"导入完成: 成功 {imported_count}, 跳过 {skipped_count}, 失败 {failed_count}",
            imported_count=imported_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            details=details,
        )

    # ==================== V2: 面向组件的配置方法 ====================

    async def get_v2_defaults(self, mode: str) -> ThemeV2DefaultsResponse:
        """获取指定模式的V2默认主题值。"""
        if mode not in ("light", "dark"):
            raise InvalidParameterError(f"无效的主题模式: {mode}，应为 'light' 或 'dark'")

        defaults = get_theme_v2_defaults(mode)
        return ThemeV2DefaultsResponse(mode=mode, **defaults)

    async def create_v2_config(
        self, user_id: int, payload: ThemeConfigV2Create
    ) -> ThemeConfigV2Read:
        """创建V2格式的主题配置。"""
        # 验证parent_mode
        if payload.parent_mode not in ("light", "dark"):
            raise InvalidParameterError(f"无效的主题模式: {payload.parent_mode}")

        # 检查配置名称是否重复（同模式下）
        existing = await self.repo.get_by_name(
            user_id, payload.config_name, payload.parent_mode
        )
        if existing:
            raise ConflictError(
                f"配置名称 '{payload.config_name}' 已存在于 {payload.parent_mode} 模式下"
            )

        # 合并默认值和用户提供的值
        defaults = get_theme_v2_defaults(payload.parent_mode)
        data = payload.model_dump(exclude_unset=True)

        # V2配置组列表
        v2_config_groups = [
            "token_colors",
            "token_typography",
            "token_spacing",
            "token_radius",
            "comp_button",
            "comp_card",
            "comp_input",
            "comp_sidebar",
            "comp_header",
            "comp_dialog",
            "comp_scrollbar",
            "comp_tooltip",
            "comp_tabs",
            "comp_text",
            "comp_semantic",
            "effects",
        ]

        # 对于未提供的配置组，使用默认值
        for group in v2_config_groups:
            if group not in data or data[group] is None:
                data[group] = defaults.get(group)

        # 如果该模式下没有任何配置，则将新配置设为激活
        count = await self.repo.count_by_mode(user_id, payload.parent_mode)
        is_first_config = count == 0

        instance = ThemeConfig(
            user_id=user_id,
            is_active=is_first_config,
            config_version=2,
            **data,
        )
        await self.repo.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return ThemeConfigV2Read.model_validate(instance)

    async def update_v2_config(
        self, config_id: int, user_id: int, payload: ThemeConfigV2Update
    ) -> ThemeConfigV2Read:
        """更新V2格式的主题配置。

        如果配置是V1版本，会自动迁移到V2格式再更新。
        这确保了用户在V2编辑器中编辑任何配置都能正常保存。
        """
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        # 如果是V1配置，先填充V2默认值再更新
        if config.config_version != 2:
            defaults = get_theme_v2_defaults(config.parent_mode)
            # 填充V2默认值（仅当字段为空时）
            if config.token_colors is None:
                config.token_colors = defaults["token_colors"]
            if config.token_typography is None:
                config.token_typography = defaults["token_typography"]
            if config.token_spacing is None:
                config.token_spacing = defaults["token_spacing"]
            if config.token_radius is None:
                config.token_radius = defaults["token_radius"]
            if config.comp_button is None:
                config.comp_button = defaults["comp_button"]
            if config.comp_card is None:
                config.comp_card = defaults["comp_card"]
            if config.comp_input is None:
                config.comp_input = defaults["comp_input"]
            if config.comp_sidebar is None:
                config.comp_sidebar = defaults["comp_sidebar"]
            if config.comp_header is None:
                config.comp_header = defaults["comp_header"]
            if config.comp_dialog is None:
                config.comp_dialog = defaults["comp_dialog"]
            if config.comp_scrollbar is None:
                config.comp_scrollbar = defaults["comp_scrollbar"]
            if config.comp_tooltip is None:
                config.comp_tooltip = defaults["comp_tooltip"]
            if config.comp_tabs is None:
                config.comp_tabs = defaults["comp_tabs"]
            if config.comp_text is None:
                config.comp_text = defaults["comp_text"]
            if config.comp_semantic is None:
                config.comp_semantic = defaults["comp_semantic"]
            if config.effects is None:
                config.effects = defaults["effects"]
            # 升级版本号
            config.config_version = 2
            logger.info(f"配置 ID={config_id} 自动从V1迁移到V2格式")

        data = payload.model_dump(exclude_unset=True)

        # 检查配置名称是否与其他配置重复
        if "config_name" in data and data["config_name"]:
            existing = await self.repo.get_by_name(
                user_id, data["config_name"], config.parent_mode
            )
            if existing and existing.id != config_id:
                raise ConflictError(f"配置名称 '{data['config_name']}' 已存在")

        # 更新字段
        for key, value in data.items():
            if value is not None:
                setattr(config, key, value)

        await self.session.commit()
        await self.session.refresh(config)
        return ThemeConfigV2Read.model_validate(config)

    async def get_v2_config(
        self, config_id: int, user_id: int
    ) -> ThemeConfigV2Read:
        """获取V2格式的配置详情。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        return ThemeConfigV2Read.model_validate(config)

    async def get_unified_config(
        self, config_id: int, user_id: int
    ) -> ThemeConfigUnifiedRead:
        """获取统一格式的配置详情（支持V1和V2）。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        return ThemeConfigUnifiedRead.model_validate(config)

    async def get_active_unified_config(
        self, user_id: int, parent_mode: str
    ) -> Optional[ThemeConfigUnifiedRead]:
        """获取用户指定模式下当前激活的统一格式配置。"""
        config = await self.repo.get_active_config(user_id, parent_mode)
        return ThemeConfigUnifiedRead.model_validate(config) if config else None

    async def duplicate_v2_config(
        self, config_id: int, user_id: int
    ) -> ThemeConfigV2Read:
        """复制V2格式的配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        # 生成新名称
        base_name = config.config_name
        new_name = f"{base_name} (副本)"
        counter = 1
        while await self.repo.get_by_name(user_id, new_name, config.parent_mode):
            counter += 1
            new_name = f"{base_name} (副本 {counter})"

        # 创建副本（包含V1和V2所有字段）
        new_config = ThemeConfig(
            user_id=user_id,
            config_name=new_name,
            parent_mode=config.parent_mode,
            is_active=False,
            config_version=config.config_version,
            # V1字段
            primary_colors=config.primary_colors,
            accent_colors=config.accent_colors,
            semantic_colors=config.semantic_colors,
            text_colors=config.text_colors,
            background_colors=config.background_colors,
            border_effects=config.border_effects,
            button_colors=config.button_colors,
            typography=config.typography,
            border_radius=config.border_radius,
            spacing=config.spacing,
            animation=config.animation,
            button_sizes=config.button_sizes,
            # V2字段
            token_colors=config.token_colors,
            token_typography=config.token_typography,
            token_spacing=config.token_spacing,
            token_radius=config.token_radius,
            comp_button=config.comp_button,
            comp_card=config.comp_card,
            comp_input=config.comp_input,
            comp_sidebar=config.comp_sidebar,
            comp_header=config.comp_header,
            comp_dialog=config.comp_dialog,
            comp_scrollbar=config.comp_scrollbar,
            comp_tooltip=config.comp_tooltip,
            comp_tabs=config.comp_tabs,
            comp_text=config.comp_text,
            comp_semantic=config.comp_semantic,
            effects=config.effects,
        )
        await self.repo.add(new_config)
        await self.session.commit()
        await self.session.refresh(new_config)

        if config.config_version == 2:
            return ThemeConfigV2Read.model_validate(new_config)
        return ThemeConfigV2Read.model_validate(new_config)

    async def reset_v2_config(
        self, config_id: int, user_id: int
    ) -> ThemeConfigV2Read:
        """重置V2配置为默认值。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        defaults = get_theme_v2_defaults(config.parent_mode)

        # 重置V2配置组
        config.token_colors = defaults["token_colors"]
        config.token_typography = defaults["token_typography"]
        config.token_spacing = defaults["token_spacing"]
        config.token_radius = defaults["token_radius"]
        config.comp_button = defaults["comp_button"]
        config.comp_card = defaults["comp_card"]
        config.comp_input = defaults["comp_input"]
        config.comp_sidebar = defaults["comp_sidebar"]
        config.comp_header = defaults["comp_header"]
        config.comp_dialog = defaults["comp_dialog"]
        config.comp_scrollbar = defaults["comp_scrollbar"]
        config.comp_tooltip = defaults["comp_tooltip"]
        config.comp_tabs = defaults["comp_tabs"]
        config.comp_text = defaults["comp_text"]
        config.comp_semantic = defaults["comp_semantic"]
        config.effects = defaults["effects"]

        # 确保标记为V2版本
        config.config_version = 2

        await self.session.commit()
        await self.session.refresh(config)
        return ThemeConfigV2Read.model_validate(config)

    async def migrate_to_v2(
        self, config_id: int, user_id: int
    ) -> ThemeConfigV2Read:
        """将V1配置迁移到V2格式。

        保留V1配置数据，同时填充V2字段为默认值。
        """
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        if config.config_version == 2:
            # 已经是V2，直接返回
            return ThemeConfigV2Read.model_validate(config)

        # 获取V2默认值并填充
        defaults = get_theme_v2_defaults(config.parent_mode)

        config.config_version = 2
        config.token_colors = defaults["token_colors"]
        config.token_typography = defaults["token_typography"]
        config.token_spacing = defaults["token_spacing"]
        config.token_radius = defaults["token_radius"]
        config.comp_button = defaults["comp_button"]
        config.comp_card = defaults["comp_card"]
        config.comp_input = defaults["comp_input"]
        config.comp_sidebar = defaults["comp_sidebar"]
        config.comp_header = defaults["comp_header"]
        config.comp_dialog = defaults["comp_dialog"]
        config.comp_scrollbar = defaults["comp_scrollbar"]
        config.comp_tooltip = defaults["comp_tooltip"]
        config.comp_tabs = defaults["comp_tabs"]
        config.comp_text = defaults["comp_text"]
        config.comp_semantic = defaults["comp_semantic"]
        config.effects = defaults["effects"]

        await self.session.commit()
        await self.session.refresh(config)
        return ThemeConfigV2Read.model_validate(config)
