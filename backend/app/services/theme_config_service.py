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
)

logger = logging.getLogger(__name__)


# ==================== 默认主题值定义 ====================
# 这些值与前端的LightTheme/DarkTheme类保持同步

LIGHT_THEME_DEFAULTS = {
    "primary_colors": {
        "PRIMARY": "#8B4513",
        "PRIMARY_LIGHT": "#A0522D",
        "PRIMARY_DARK": "#6B3410",
        "PRIMARY_PALE": "#FDF5ED",
        "PRIMARY_GRADIENT": ["#A0522D", "#8B4513", "#6B3410"],
    },
    "accent_colors": {
        "ACCENT": "#A0522D",
        "ACCENT_LIGHT": "#B8653D",
        "ACCENT_DARK": "#8B4513",
        "ACCENT_PALE": "#FAF5F0",
        "ACCENT_GRADIENT": ["#B8653D", "#A0522D", "#8B4513"],
    },
    "semantic_colors": {
        "SUCCESS": "#4a9f6e",
        "SUCCESS_LIGHT": "#6db88a",
        "SUCCESS_DARK": "#3a8558",
        "SUCCESS_BG": "#f0f9f4",
        "SUCCESS_GRADIENT": ["#8fcca6", "#6db88a", "#4a9f6e"],
        "ERROR": "#A85448",
        "ERROR_LIGHT": "#C4706A",
        "ERROR_DARK": "#8B3F35",
        "ERROR_BG": "#fdf3f2",
        "ERROR_GRADIENT": ["#C4706A", "#A85448", "#8B3F35"],
        "WARNING": "#d4923a",
        "WARNING_LIGHT": "#e5ad5c",
        "WARNING_DARK": "#b87a2a",
        "WARNING_BG": "#fdf8f0",
        "WARNING_GRADIENT": ["#f0c67d", "#e5ad5c", "#d4923a"],
        "INFO": "#4a8db3",
        "INFO_LIGHT": "#6da8c9",
        "INFO_DARK": "#3a7499",
        "INFO_BG": "#f0f6fa",
        "INFO_GRADIENT": ["#90c5dd", "#6da8c9", "#4a8db3"],
    },
    "text_colors": {
        "TEXT_PRIMARY": "#2C1810",
        "TEXT_SECONDARY": "#5D4037",
        "TEXT_TERTIARY": "#6D6560",
        "TEXT_PLACEHOLDER": "#8D8580",
        "TEXT_DISABLED": "#B0A8A0",
    },
    "background_colors": {
        "BG_PRIMARY": "#F9F5F0",
        "BG_SECONDARY": "#FFFBF0",
        "BG_TERTIARY": "#F0EBE5",
        "BG_CARD": "#FFFBF0",
        "BG_CARD_HOVER": "#F5F0EA",
        "BG_GRADIENT": ["#F9F5F0", "#FFFBF0", "#F0EBE5"],
        "BG_MUTED": "#F0EBE5",
        "BG_ACCENT": "#E6DCCD",
        "GLASS_BG": "rgba(249, 245, 240, 0.85)",
    },
    "border_effects": {
        "BORDER_DEFAULT": "#D7CCC8",
        "BORDER_LIGHT": "#E8E4DF",
        "BORDER_DARK": "#C4C0BC",
        "SHADOW_COLOR": "rgba(44, 24, 16, 0.08)",
        "OVERLAY_COLOR": "rgba(44, 24, 16, 0.25)",
        "SHADOW_CARD": "0 4px 20px -2px rgba(139,69,19,0.10)",
        "SHADOW_CARD_HOVER": "0 20px 40px -10px rgba(139,69,19,0.15)",
        "SHADOW_SIENNA": "0 4px 20px -2px rgba(139,69,19,0.15)",
        "SHADOW_SIENNA_HOVER": "0 6px 24px -4px rgba(139,69,19,0.25)",
    },
    "button_colors": {
        "BUTTON_TEXT": "#FFFBF0",
        "BUTTON_TEXT_SECONDARY": "#2C1810",
    },
    "typography": {
        "FONT_HEADING": "'Noto Serif SC', 'Source Han Serif SC', serif",
        "FONT_BODY": "'Noto Sans SC', 'Source Han Sans SC', sans-serif",
        "FONT_DISPLAY": "'Noto Serif SC', 'Source Han Serif SC', serif",
        "FONT_UI": "'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', sans-serif",
        "FONT_SIZE_XS": "12px",
        "FONT_SIZE_SM": "12px",
        "FONT_SIZE_BASE": "14px",
        "FONT_SIZE_MD": "16px",
        "FONT_SIZE_LG": "18px",
        "FONT_SIZE_XL": "20px",
        "FONT_SIZE_2XL": "24px",
        "FONT_SIZE_3XL": "32px",
        "FONT_WEIGHT_NORMAL": "400",
        "FONT_WEIGHT_MEDIUM": "500",
        "FONT_WEIGHT_SEMIBOLD": "600",
        "FONT_WEIGHT_BOLD": "700",
        "LINE_HEIGHT_TIGHT": "1.4",
        "LINE_HEIGHT_NORMAL": "1.5",
        "LINE_HEIGHT_RELAXED": "1.6",
        "LINE_HEIGHT_LOOSE": "1.8",
        "LETTER_SPACING_TIGHT": "-0.02em",
        "LETTER_SPACING_NORMAL": "0",
        "LETTER_SPACING_WIDE": "0.05em",
        "LETTER_SPACING_WIDER": "0.1em",
        "LETTER_SPACING_WIDEST": "0.15em",
    },
    "border_radius": {
        "RADIUS_XS": "2px",
        "RADIUS_SM": "4px",
        "RADIUS_MD": "6px",
        "RADIUS_LG": "8px",
        "RADIUS_XL": "16px",
        "RADIUS_2XL": "24px",
        "RADIUS_3XL": "32px",
        "RADIUS_ROUND": "50%",
        "RADIUS_ORGANIC": "60% 40% 30% 70% / 60% 30% 70% 40%",
        "RADIUS_ORGANIC_ALT": "30% 70% 70% 30% / 30% 30% 70% 70%",
        "RADIUS_PILL": "9999px",
    },
    "spacing": {
        "SPACING_XS": "8px",
        "SPACING_SM": "16px",
        "SPACING_MD": "24px",
        "SPACING_LG": "32px",
        "SPACING_XL": "40px",
        "SPACING_XXL": "48px",
    },
    "animation": {
        "TRANSITION_FAST": "150ms",
        "TRANSITION_BASE": "300ms",
        "TRANSITION_SLOW": "500ms",
        "TRANSITION_DRAMATIC": "700ms",
        "EASING_DEFAULT": "ease-out",
    },
    "button_sizes": {
        "BUTTON_HEIGHT_SM": "40px",
        "BUTTON_HEIGHT_DEFAULT": "48px",
        "BUTTON_HEIGHT_LG": "56px",
        "BUTTON_PADDING_SM": "24px",
        "BUTTON_PADDING_DEFAULT": "32px",
        "BUTTON_PADDING_LG": "40px",
    },
}

DARK_THEME_DEFAULTS = {
    "primary_colors": {
        "PRIMARY": "#E89B6C",
        "PRIMARY_LIGHT": "#F0B088",
        "PRIMARY_DARK": "#D4845A",
        "PRIMARY_PALE": "#2A2520",
        "PRIMARY_GRADIENT": ["#F0B088", "#E89B6C", "#D4845A"],
    },
    "accent_colors": {
        "ACCENT": "#D4845A",
        "ACCENT_LIGHT": "#E89B6C",
        "ACCENT_DARK": "#B86E48",
        "ACCENT_PALE": "#2D2118",
        "ACCENT_GRADIENT": ["#E89B6C", "#D4845A", "#B86E48"],
    },
    "semantic_colors": {
        "SUCCESS": "#4a9f6e",
        "SUCCESS_LIGHT": "#6db88a",
        "SUCCESS_DARK": "#3a8558",
        "SUCCESS_BG": "#1a2f22",
        "SUCCESS_GRADIENT": ["#8fcca6", "#6db88a", "#4a9f6e"],
        "ERROR": "#A85448",
        "ERROR_LIGHT": "#C4706A",
        "ERROR_DARK": "#8B3F35",
        "ERROR_BG": "#2D1F1C",
        "ERROR_GRADIENT": ["#C4706A", "#A85448", "#8B3F35"],
        "WARNING": "#D4923A",
        "WARNING_LIGHT": "#E5AD5C",
        "WARNING_DARK": "#B87A2A",
        "WARNING_BG": "#2D2518",
        "WARNING_GRADIENT": ["#E5AD5C", "#D4923A", "#B87A2A"],
        "INFO": "#4A8DB3",
        "INFO_LIGHT": "#6DA8C9",
        "INFO_DARK": "#3A7499",
        "INFO_BG": "#1A2530",
        "INFO_GRADIENT": ["#6DA8C9", "#4A8DB3", "#3A7499"],
    },
    "text_colors": {
        "TEXT_PRIMARY": "#E8DFD4",
        "TEXT_SECONDARY": "#9C8B7A",
        "TEXT_TERTIARY": "#7A6B5A",
        "TEXT_PLACEHOLDER": "#5A4D40",
        "TEXT_DISABLED": "#4A3F35",
    },
    "background_colors": {
        "BG_PRIMARY": "#1C1714",
        "BG_SECONDARY": "#251E19",
        "BG_TERTIARY": "#3D332B",
        "BG_CARD": "#251E19",
        "BG_CARD_HOVER": "#2D2520",
        "BG_GRADIENT": ["#1C1714", "#251E19", "#3D332B"],
        "BG_MUTED": "#3D332B",
        "BG_ACCENT": "#3D332B",
        "GLASS_BG": "rgba(37, 30, 25, 0.85)",
    },
    "border_effects": {
        "BORDER_DEFAULT": "#4A3F35",
        "BORDER_LIGHT": "#3D332B",
        "BORDER_DARK": "#5A4D40",
        "SHADOW_COLOR": "rgba(0, 0, 0, 0.3)",
        "OVERLAY_COLOR": "rgba(28, 23, 20, 0.4)",
        "SHADOW_CARD": "0 4px 20px -2px rgba(232,155,108,0.10)",
        "SHADOW_CARD_HOVER": "0 20px 40px -10px rgba(232,155,108,0.15)",
        "SHADOW_SIENNA": "0 4px 20px -2px rgba(232,155,108,0.15)",
        "SHADOW_SIENNA_HOVER": "0 6px 24px -4px rgba(232,155,108,0.25)",
        "SHADOW_AMBER_GLOW": "0 4px 12px rgba(232,155,108,0.3)",
    },
    "button_colors": {
        "BUTTON_TEXT": "#1C1714",
        "BUTTON_TEXT_SECONDARY": "#E8DFD4",
    },
    "typography": LIGHT_THEME_DEFAULTS["typography"].copy(),  # 字体配置与亮色主题相同
    "border_radius": LIGHT_THEME_DEFAULTS["border_radius"].copy(),  # 圆角配置与亮色主题相同
    "spacing": LIGHT_THEME_DEFAULTS["spacing"].copy(),  # 间距配置与亮色主题相同
    "animation": LIGHT_THEME_DEFAULTS["animation"].copy(),  # 动画配置与亮色主题相同
    "button_sizes": LIGHT_THEME_DEFAULTS["button_sizes"].copy(),  # 按钮尺寸与亮色主题相同
}


def get_theme_defaults(mode: str) -> dict[str, Any]:
    """获取指定模式的默认主题值"""
    if mode == "dark":
        return DARK_THEME_DEFAULTS
    return LIGHT_THEME_DEFAULTS


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

    async def activate_config(self, config_id: int, user_id: int) -> ThemeConfigRead:
        """激活指定配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("主题配置", f"ID={config_id}")

        await self.repo.activate_config(config_id, user_id, config.parent_mode)
        await self.session.commit()
        await self.session.refresh(config)
        return ThemeConfigRead.model_validate(config)

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
