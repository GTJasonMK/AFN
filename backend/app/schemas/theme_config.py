"""
主题配置Schema模块

定义主题配置的请求/响应模型。
"""

from datetime import datetime
from typing import Any, Optional, Literal

from pydantic import BaseModel, Field


# ==================== 常量分组定义 ====================

class PrimaryColorsSchema(BaseModel):
    """主色调组"""
    PRIMARY: Optional[str] = None
    PRIMARY_LIGHT: Optional[str] = None
    PRIMARY_DARK: Optional[str] = None
    PRIMARY_PALE: Optional[str] = None
    PRIMARY_GRADIENT: Optional[list[str]] = None


class AccentColorsSchema(BaseModel):
    """强调色组"""
    ACCENT: Optional[str] = None
    ACCENT_LIGHT: Optional[str] = None
    ACCENT_DARK: Optional[str] = None
    ACCENT_PALE: Optional[str] = None
    ACCENT_GRADIENT: Optional[list[str]] = None


class SemanticColorsSchema(BaseModel):
    """语义色组（成功、错误、警告、信息）"""
    # 成功色系
    SUCCESS: Optional[str] = None
    SUCCESS_LIGHT: Optional[str] = None
    SUCCESS_DARK: Optional[str] = None
    SUCCESS_BG: Optional[str] = None
    SUCCESS_GRADIENT: Optional[list[str]] = None
    # 错误色系
    ERROR: Optional[str] = None
    ERROR_LIGHT: Optional[str] = None
    ERROR_DARK: Optional[str] = None
    ERROR_BG: Optional[str] = None
    ERROR_GRADIENT: Optional[list[str]] = None
    # 警告色系
    WARNING: Optional[str] = None
    WARNING_LIGHT: Optional[str] = None
    WARNING_DARK: Optional[str] = None
    WARNING_BG: Optional[str] = None
    WARNING_GRADIENT: Optional[list[str]] = None
    # 信息色系
    INFO: Optional[str] = None
    INFO_LIGHT: Optional[str] = None
    INFO_DARK: Optional[str] = None
    INFO_BG: Optional[str] = None
    INFO_GRADIENT: Optional[list[str]] = None


class TextColorsSchema(BaseModel):
    """文字色组"""
    TEXT_PRIMARY: Optional[str] = None
    TEXT_SECONDARY: Optional[str] = None
    TEXT_TERTIARY: Optional[str] = None
    TEXT_PLACEHOLDER: Optional[str] = None
    TEXT_DISABLED: Optional[str] = None


class BackgroundColorsSchema(BaseModel):
    """背景色组"""
    BG_PRIMARY: Optional[str] = None
    BG_SECONDARY: Optional[str] = None
    BG_TERTIARY: Optional[str] = None
    BG_CARD: Optional[str] = None
    BG_CARD_HOVER: Optional[str] = None
    BG_GRADIENT: Optional[list[str]] = None
    BG_MUTED: Optional[str] = None
    BG_ACCENT: Optional[str] = None
    GLASS_BG: Optional[str] = None


class BorderEffectsSchema(BaseModel):
    """边框与特效组"""
    BORDER_DEFAULT: Optional[str] = None
    BORDER_LIGHT: Optional[str] = None
    BORDER_DARK: Optional[str] = None
    SHADOW_COLOR: Optional[str] = None
    OVERLAY_COLOR: Optional[str] = None
    SHADOW_CARD: Optional[str] = None
    SHADOW_CARD_HOVER: Optional[str] = None
    SHADOW_SIENNA: Optional[str] = None
    SHADOW_SIENNA_HOVER: Optional[str] = None
    SHADOW_AMBER_GLOW: Optional[str] = None  # 仅深色主题


class ButtonColorsSchema(BaseModel):
    """按钮文字色组"""
    BUTTON_TEXT: Optional[str] = None
    BUTTON_TEXT_SECONDARY: Optional[str] = None


class TypographySchema(BaseModel):
    """字体配置组"""
    # 字体族
    FONT_HEADING: Optional[str] = None
    FONT_BODY: Optional[str] = None
    FONT_DISPLAY: Optional[str] = None
    FONT_UI: Optional[str] = None
    # 字体大小
    FONT_SIZE_XS: Optional[str] = None
    FONT_SIZE_SM: Optional[str] = None
    FONT_SIZE_BASE: Optional[str] = None
    FONT_SIZE_MD: Optional[str] = None
    FONT_SIZE_LG: Optional[str] = None
    FONT_SIZE_XL: Optional[str] = None
    FONT_SIZE_2XL: Optional[str] = None
    FONT_SIZE_3XL: Optional[str] = None
    # 字体粗细
    FONT_WEIGHT_NORMAL: Optional[str] = None
    FONT_WEIGHT_MEDIUM: Optional[str] = None
    FONT_WEIGHT_SEMIBOLD: Optional[str] = None
    FONT_WEIGHT_BOLD: Optional[str] = None
    # 行高
    LINE_HEIGHT_TIGHT: Optional[str] = None
    LINE_HEIGHT_NORMAL: Optional[str] = None
    LINE_HEIGHT_RELAXED: Optional[str] = None
    LINE_HEIGHT_LOOSE: Optional[str] = None
    # 字间距
    LETTER_SPACING_TIGHT: Optional[str] = None
    LETTER_SPACING_NORMAL: Optional[str] = None
    LETTER_SPACING_WIDE: Optional[str] = None
    LETTER_SPACING_WIDER: Optional[str] = None
    LETTER_SPACING_WIDEST: Optional[str] = None


class BorderRadiusSchema(BaseModel):
    """圆角配置组"""
    RADIUS_XS: Optional[str] = None
    RADIUS_SM: Optional[str] = None
    RADIUS_MD: Optional[str] = None
    RADIUS_LG: Optional[str] = None
    RADIUS_XL: Optional[str] = None
    RADIUS_2XL: Optional[str] = None
    RADIUS_3XL: Optional[str] = None
    RADIUS_ROUND: Optional[str] = None
    RADIUS_ORGANIC: Optional[str] = None
    RADIUS_ORGANIC_ALT: Optional[str] = None
    RADIUS_PILL: Optional[str] = None


class SpacingSchema(BaseModel):
    """间距配置组"""
    SPACING_XS: Optional[str] = None
    SPACING_SM: Optional[str] = None
    SPACING_MD: Optional[str] = None
    SPACING_LG: Optional[str] = None
    SPACING_XL: Optional[str] = None
    SPACING_XXL: Optional[str] = None


class AnimationSchema(BaseModel):
    """动画配置组"""
    TRANSITION_FAST: Optional[str] = None
    TRANSITION_BASE: Optional[str] = None
    TRANSITION_SLOW: Optional[str] = None
    TRANSITION_DRAMATIC: Optional[str] = None
    EASING_DEFAULT: Optional[str] = None


class ButtonSizesSchema(BaseModel):
    """按钮尺寸配置组"""
    BUTTON_HEIGHT_SM: Optional[str] = None
    BUTTON_HEIGHT_DEFAULT: Optional[str] = None
    BUTTON_HEIGHT_LG: Optional[str] = None
    BUTTON_PADDING_SM: Optional[str] = None
    BUTTON_PADDING_DEFAULT: Optional[str] = None
    BUTTON_PADDING_LG: Optional[str] = None


# ==================== 请求/响应模型 ====================

class ThemeConfigBase(BaseModel):
    """主题配置基础模型"""
    config_name: str = Field(default="自定义主题", description="配置名称", max_length=100)
    parent_mode: Literal["light", "dark"] = Field(..., description="顶级主题模式")


class ThemeConfigCreate(ThemeConfigBase):
    """创建主题配置的请求模型"""
    # 各组配置（可选，不提供则使用默认值）
    primary_colors: Optional[dict[str, Any]] = None
    accent_colors: Optional[dict[str, Any]] = None
    semantic_colors: Optional[dict[str, Any]] = None
    text_colors: Optional[dict[str, Any]] = None
    background_colors: Optional[dict[str, Any]] = None
    border_effects: Optional[dict[str, Any]] = None
    button_colors: Optional[dict[str, Any]] = None
    typography: Optional[dict[str, Any]] = None
    border_radius: Optional[dict[str, Any]] = None
    spacing: Optional[dict[str, Any]] = None
    animation: Optional[dict[str, Any]] = None
    button_sizes: Optional[dict[str, Any]] = None


class ThemeConfigUpdate(BaseModel):
    """更新主题配置的请求模型（所有字段可选）"""
    config_name: Optional[str] = Field(default=None, max_length=100)
    primary_colors: Optional[dict[str, Any]] = None
    accent_colors: Optional[dict[str, Any]] = None
    semantic_colors: Optional[dict[str, Any]] = None
    text_colors: Optional[dict[str, Any]] = None
    background_colors: Optional[dict[str, Any]] = None
    border_effects: Optional[dict[str, Any]] = None
    button_colors: Optional[dict[str, Any]] = None
    typography: Optional[dict[str, Any]] = None
    border_radius: Optional[dict[str, Any]] = None
    spacing: Optional[dict[str, Any]] = None
    animation: Optional[dict[str, Any]] = None
    button_sizes: Optional[dict[str, Any]] = None


class ThemeConfigRead(BaseModel):
    """主题配置的响应模型"""
    id: int
    user_id: int
    config_name: str
    parent_mode: str
    is_active: bool
    primary_colors: Optional[dict[str, Any]] = None
    accent_colors: Optional[dict[str, Any]] = None
    semantic_colors: Optional[dict[str, Any]] = None
    text_colors: Optional[dict[str, Any]] = None
    background_colors: Optional[dict[str, Any]] = None
    border_effects: Optional[dict[str, Any]] = None
    button_colors: Optional[dict[str, Any]] = None
    typography: Optional[dict[str, Any]] = None
    border_radius: Optional[dict[str, Any]] = None
    spacing: Optional[dict[str, Any]] = None
    animation: Optional[dict[str, Any]] = None
    button_sizes: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThemeConfigListItem(BaseModel):
    """主题配置列表项（简化版，用于列表显示）"""
    id: int
    config_name: str
    parent_mode: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThemeDefaultsResponse(BaseModel):
    """获取默认主题值的响应"""
    mode: str
    primary_colors: dict[str, Any]
    accent_colors: dict[str, Any]
    semantic_colors: dict[str, Any]
    text_colors: dict[str, Any]
    background_colors: dict[str, Any]
    border_effects: dict[str, Any]
    button_colors: dict[str, Any]
    typography: dict[str, Any]
    border_radius: dict[str, Any]
    spacing: dict[str, Any]
    animation: dict[str, Any]
    button_sizes: dict[str, Any]


class ThemeConfigExport(BaseModel):
    """导出的主题配置数据"""
    config_name: str
    parent_mode: str
    primary_colors: Optional[dict[str, Any]] = None
    accent_colors: Optional[dict[str, Any]] = None
    semantic_colors: Optional[dict[str, Any]] = None
    text_colors: Optional[dict[str, Any]] = None
    background_colors: Optional[dict[str, Any]] = None
    border_effects: Optional[dict[str, Any]] = None
    button_colors: Optional[dict[str, Any]] = None
    typography: Optional[dict[str, Any]] = None
    border_radius: Optional[dict[str, Any]] = None
    spacing: Optional[dict[str, Any]] = None
    animation: Optional[dict[str, Any]] = None
    button_sizes: Optional[dict[str, Any]] = None


class ThemeConfigExportData(BaseModel):
    """导出文件的完整数据结构"""
    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    configs: list[ThemeConfigExport] = Field(..., description="配置列表")


class ThemeConfigImportRequest(BaseModel):
    """导入主题配置的请求模型"""
    data: ThemeConfigExportData


class ThemeConfigImportResult(BaseModel):
    """导入结果"""
    success: bool
    message: str
    imported_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    details: list[str] = []
