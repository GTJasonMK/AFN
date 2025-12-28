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


# ==================== V2: 面向组件的默认主题值 ====================
# 新版配置结构：设计令牌 + 组件配置 + 效果配置

LIGHT_THEME_V2_DEFAULTS = {
    # 设计令牌 - 颜色
    "token_colors": {
        # 品牌色
        "brand": "#8B4513",
        "brand_light": "#A0522D",
        "brand_dark": "#6B3410",
        "accent": "#A0522D",
        "accent_light": "#B8653D",
        # 背景色
        "background": "#F9F5F0",
        "surface": "#FFFBF0",
        "surface_alt": "#F0EBE5",
        "surface_hover": "#F5F0EA",
        # 文本色
        "text": "#2C1810",
        "text_muted": "#5D4037",
        "text_subtle": "#6D6560",
        "text_disabled": "#B0A8A0",
        "text_placeholder": "#8D8580",
        # 边框色
        "border": "#D7CCC8",
        "border_light": "#E8E4DF",
        "border_dark": "#C4C0BC",
        # 语义色
        "success": "#4a9f6e",
        "success_light": "#6db88a",
        "success_bg": "#f0f9f4",
        "error": "#A85448",
        "error_light": "#C4706A",
        "error_bg": "#fdf3f2",
        "warning": "#d4923a",
        "warning_light": "#e5ad5c",
        "warning_bg": "#fdf8f0",
        "info": "#4a8db3",
        "info_light": "#6da8c9",
        "info_bg": "#f0f6fa",
        # 阴影色
        "shadow": "rgba(44, 24, 16, 0.08)",
        "overlay": "rgba(44, 24, 16, 0.25)",
    },
    # 设计令牌 - 排版
    "token_typography": {
        "font_heading": "'Noto Serif SC', 'Source Han Serif SC', serif",
        "font_body": "'Noto Sans SC', 'Source Han Sans SC', sans-serif",
        "font_ui": "'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', sans-serif",
        "size_xs": "12px",
        "size_sm": "12px",
        "size_base": "14px",
        "size_md": "16px",
        "size_lg": "18px",
        "size_xl": "20px",
        "size_2xl": "24px",
        "size_3xl": "32px",
        "weight_normal": "400",
        "weight_medium": "500",
        "weight_semibold": "600",
        "weight_bold": "700",
        "line_height_tight": "1.4",
        "line_height_normal": "1.5",
        "line_height_relaxed": "1.6",
    },
    # 设计令牌 - 间距
    "token_spacing": {
        "xs": "8px",
        "sm": "16px",
        "md": "24px",
        "lg": "32px",
        "xl": "40px",
        "xxl": "48px",
    },
    # 设计令牌 - 圆角
    "token_radius": {
        "xs": "2px",
        "sm": "4px",
        "md": "6px",
        "lg": "8px",
        "xl": "16px",
        "2xl": "24px",
        "pill": "9999px",
        "round": "50%",
    },
    # 组件配置 - 按钮
    "comp_button": {
        "primary": {
            "bg": "#8B4513",
            "bg_hover": "#A0522D",
            "bg_pressed": "#6B3410",
            "text": "#FFFBF0",
            "border": "none",
            "radius": "24px",
            "shadow": "none",
        },
        "secondary": {
            "bg": "transparent",
            "bg_hover": "#8B4513",
            "text": "#8B4513",
            "text_hover": "#FFFBF0",
            "border": "2px solid #8B4513",
            "radius": "24px",
        },
        "ghost": {
            "bg": "transparent",
            "bg_hover": "#F0EBE5",
            "text": "#2C1810",
            "border": "none",
            "radius": "6px",
        },
        "danger": {
            "bg": "#A85448",
            "bg_hover": "#C4706A",
            "bg_pressed": "#8B3F35",
            "text": "#FFFBF0",
            "border": "none",
            "radius": "24px",
        },
        "sizes": {
            "sm": {"height": "40px", "padding": "24px"},
            "default": {"height": "48px", "padding": "32px"},
            "lg": {"height": "56px", "padding": "40px"},
        },
    },
    # 组件配置 - 卡片
    "comp_card": {
        "bg": "#FFFBF0",
        "bg_hover": "#F5F0EA",
        "border": "1px solid #E8E4DF",
        "radius": "8px",
        "shadow": "0 4px 20px -2px rgba(139,69,19,0.10)",
        "shadow_hover": "0 20px 40px -10px rgba(139,69,19,0.15)",
        "padding": "24px",
    },
    # 组件配置 - 输入框
    "comp_input": {
        "bg": "#FFFBF0",
        "bg_focus": "#FFFFFF",
        "border": "1px solid #D7CCC8",
        "border_focus": "1px solid #8B4513",
        "text": "#2C1810",
        "placeholder": "#8D8580",
        "radius": "6px",
        "height": "40px",
        "padding": "12px 16px",
    },
    # 组件配置 - 侧边栏（含透明效果）
    "comp_sidebar": {
        "bg": "#F9F5F0",
        "border": "1px solid #E8E4DF",
        "item_bg_hover": "#F0EBE5",
        "item_bg_active": "#FFFBF0",
        "item_text": "#5D4037",
        "item_text_active": "#8B4513",
        "item_radius": "6px",
        # 透明效果配置
        "opacity": 0.85,
        "blur_radius": 20,
        "use_transparency": False,
    },
    # 组件配置 - 顶部栏（含透明效果）
    "comp_header": {
        "bg": "#F9F5F0",
        "border": "1px solid #E8E4DF",
        "text": "#2C1810",
        "height": "56px",
        # 透明效果配置
        "opacity": 0.90,
        "blur_radius": 20,
        "use_transparency": False,
    },
    # 组件配置 - 对话框（含透明效果）
    "comp_dialog": {
        "bg": "#FFFBF0",
        "border": "1px solid #E8E4DF",
        "radius": "16px",
        "shadow": "0 20px 40px -10px rgba(139,69,19,0.20)",
        "overlay": "rgba(44, 24, 16, 0.25)",
        "header_bg": "#F9F5F0",
        "footer_bg": "#F9F5F0",
        # 透明效果配置
        "opacity": 0.95,
        "blur_radius": 20,
        "use_transparency": False,
    },
    # 组件配置 - 滚动条
    "comp_scrollbar": {
        "width": "8px",
        "track_bg": "transparent",
        "thumb_bg": "#D7CCC8",
        "thumb_bg_hover": "#C4C0BC",
        "radius": "4px",
    },
    # 组件配置 - 工具提示
    "comp_tooltip": {
        "bg": "#2C1810",
        "text": "#FFFBF0",
        "border": "none",
        "radius": "6px",
        "padding": "8px 12px",
        "shadow": "0 4px 12px rgba(44, 24, 16, 0.15)",
    },
    # 组件配置 - 标签页
    "comp_tabs": {
        "bg": "transparent",
        "tab_bg": "transparent",
        "tab_bg_active": "#FFFBF0",
        "tab_text": "#5D4037",
        "tab_text_active": "#8B4513",
        "indicator": "#8B4513",
        "border": "1px solid #E8E4DF",
        "radius": "6px",
    },
    # 组件配置 - 文本样式
    "comp_text": {
        "heading": {
            "color": "#2C1810",
            "font": "'Noto Serif SC', serif",
            "weight": "600",
        },
        "body": {
            "color": "#2C1810",
            "font": "'Noto Sans SC', sans-serif",
            "weight": "400",
        },
        "muted": {
            "color": "#5D4037",
        },
        "link": {
            "color": "#8B4513",
            "color_hover": "#A0522D",
            "decoration": "none",
            "decoration_hover": "underline",
        },
    },
    # 组件配置 - 语义反馈
    "comp_semantic": {
        "success": {
            "bg": "#f0f9f4",
            "border": "1px solid #6db88a",
            "text": "#3a8558",
            "icon": "#4a9f6e",
        },
        "error": {
            "bg": "#fdf3f2",
            "border": "1px solid #C4706A",
            "text": "#8B3F35",
            "icon": "#A85448",
        },
        "warning": {
            "bg": "#fdf8f0",
            "border": "1px solid #e5ad5c",
            "text": "#b87a2a",
            "icon": "#d4923a",
        },
        "info": {
            "bg": "#f0f6fa",
            "border": "1px solid #6da8c9",
            "text": "#3a7499",
            "icon": "#4a8db3",
        },
    },
    # 效果配置
    "effects": {
        "transparency_enabled": False,
        "blur_enabled": False,
        "system_blur": False,
        "animation_speed": "normal",  # "none" | "slow" | "normal" | "fast"
        "hover_effects": True,
        "focus_ring": True,
        "transition_fast": "150ms",
        "transition_base": "300ms",
        "transition_slow": "500ms",
        "easing": "ease-out",
    },
}


DARK_THEME_V2_DEFAULTS = {
    # 设计令牌 - 颜色（深色主题）
    "token_colors": {
        # 品牌色
        "brand": "#E89B6C",
        "brand_light": "#F0B088",
        "brand_dark": "#D4845A",
        "accent": "#D4845A",
        "accent_light": "#E89B6C",
        # 背景色
        "background": "#1C1714",
        "surface": "#251E19",
        "surface_alt": "#3D332B",
        "surface_hover": "#2D2520",
        # 文本色
        "text": "#E8DFD4",
        "text_muted": "#9C8B7A",
        "text_subtle": "#7A6B5A",
        "text_disabled": "#4A3F35",
        "text_placeholder": "#5A4D40",
        # 边框色
        "border": "#4A3F35",
        "border_light": "#3D332B",
        "border_dark": "#5A4D40",
        # 语义色
        "success": "#4a9f6e",
        "success_light": "#6db88a",
        "success_bg": "#1a2f22",
        "error": "#A85448",
        "error_light": "#C4706A",
        "error_bg": "#2D1F1C",
        "warning": "#D4923A",
        "warning_light": "#E5AD5C",
        "warning_bg": "#2D2518",
        "info": "#4A8DB3",
        "info_light": "#6DA8C9",
        "info_bg": "#1A2530",
        # 阴影色
        "shadow": "rgba(0, 0, 0, 0.3)",
        "overlay": "rgba(28, 23, 20, 0.4)",
    },
    # 设计令牌 - 排版（与亮色主题相同）
    "token_typography": LIGHT_THEME_V2_DEFAULTS["token_typography"].copy(),
    # 设计令牌 - 间距（与亮色主题相同）
    "token_spacing": LIGHT_THEME_V2_DEFAULTS["token_spacing"].copy(),
    # 设计令牌 - 圆角（与亮色主题相同）
    "token_radius": LIGHT_THEME_V2_DEFAULTS["token_radius"].copy(),
    # 组件配置 - 按钮（深色主题）
    "comp_button": {
        "primary": {
            "bg": "#E89B6C",
            "bg_hover": "#F0B088",
            "bg_pressed": "#D4845A",
            "text": "#1C1714",
            "border": "none",
            "radius": "24px",
            "shadow": "none",
        },
        "secondary": {
            "bg": "transparent",
            "bg_hover": "#E89B6C",
            "text": "#E89B6C",
            "text_hover": "#1C1714",
            "border": "2px solid #E89B6C",
            "radius": "24px",
        },
        "ghost": {
            "bg": "transparent",
            "bg_hover": "#3D332B",
            "text": "#E8DFD4",
            "border": "none",
            "radius": "6px",
        },
        "danger": {
            "bg": "#A85448",
            "bg_hover": "#C4706A",
            "bg_pressed": "#8B3F35",
            "text": "#E8DFD4",
            "border": "none",
            "radius": "24px",
        },
        "sizes": LIGHT_THEME_V2_DEFAULTS["comp_button"]["sizes"].copy(),
    },
    # 组件配置 - 卡片（深色主题）
    "comp_card": {
        "bg": "#251E19",
        "bg_hover": "#2D2520",
        "border": "1px solid #3D332B",
        "radius": "8px",
        "shadow": "0 4px 20px -2px rgba(232,155,108,0.10)",
        "shadow_hover": "0 20px 40px -10px rgba(232,155,108,0.15)",
        "padding": "24px",
    },
    # 组件配置 - 输入框（深色主题）
    "comp_input": {
        "bg": "#251E19",
        "bg_focus": "#2D2520",
        "border": "1px solid #4A3F35",
        "border_focus": "1px solid #E89B6C",
        "text": "#E8DFD4",
        "placeholder": "#5A4D40",
        "radius": "6px",
        "height": "40px",
        "padding": "12px 16px",
    },
    # 组件配置 - 侧边栏（深色主题，含透明效果）
    "comp_sidebar": {
        "bg": "#1C1714",
        "border": "1px solid #3D332B",
        "item_bg_hover": "#3D332B",
        "item_bg_active": "#251E19",
        "item_text": "#9C8B7A",
        "item_text_active": "#E89B6C",
        "item_radius": "6px",
        # 透明效果配置
        "opacity": 0.85,
        "blur_radius": 20,
        "use_transparency": False,
    },
    # 组件配置 - 顶部栏（深色主题，含透明效果）
    "comp_header": {
        "bg": "#1C1714",
        "border": "1px solid #3D332B",
        "text": "#E8DFD4",
        "height": "56px",
        # 透明效果配置
        "opacity": 0.90,
        "blur_radius": 20,
        "use_transparency": False,
    },
    # 组件配置 - 对话框（深色主题，含透明效果）
    "comp_dialog": {
        "bg": "#251E19",
        "border": "1px solid #3D332B",
        "radius": "16px",
        "shadow": "0 20px 40px -10px rgba(0,0,0,0.40)",
        "overlay": "rgba(28, 23, 20, 0.4)",
        "header_bg": "#1C1714",
        "footer_bg": "#1C1714",
        # 透明效果配置
        "opacity": 0.95,
        "blur_radius": 20,
        "use_transparency": False,
    },
    # 组件配置 - 滚动条（深色主题）
    "comp_scrollbar": {
        "width": "8px",
        "track_bg": "transparent",
        "thumb_bg": "#4A3F35",
        "thumb_bg_hover": "#5A4D40",
        "radius": "4px",
    },
    # 组件配置 - 工具提示（深色主题）
    "comp_tooltip": {
        "bg": "#E8DFD4",
        "text": "#1C1714",
        "border": "none",
        "radius": "6px",
        "padding": "8px 12px",
        "shadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
    },
    # 组件配置 - 标签页（深色主题）
    "comp_tabs": {
        "bg": "transparent",
        "tab_bg": "transparent",
        "tab_bg_active": "#251E19",
        "tab_text": "#9C8B7A",
        "tab_text_active": "#E89B6C",
        "indicator": "#E89B6C",
        "border": "1px solid #3D332B",
        "radius": "6px",
    },
    # 组件配置 - 文本样式（深色主题）
    "comp_text": {
        "heading": {
            "color": "#E8DFD4",
            "font": "'Noto Serif SC', serif",
            "weight": "600",
        },
        "body": {
            "color": "#E8DFD4",
            "font": "'Noto Sans SC', sans-serif",
            "weight": "400",
        },
        "muted": {
            "color": "#9C8B7A",
        },
        "link": {
            "color": "#E89B6C",
            "color_hover": "#F0B088",
            "decoration": "none",
            "decoration_hover": "underline",
        },
    },
    # 组件配置 - 语义反馈（深色主题）
    "comp_semantic": {
        "success": {
            "bg": "#1a2f22",
            "border": "1px solid #6db88a",
            "text": "#6db88a",
            "icon": "#4a9f6e",
        },
        "error": {
            "bg": "#2D1F1C",
            "border": "1px solid #C4706A",
            "text": "#C4706A",
            "icon": "#A85448",
        },
        "warning": {
            "bg": "#2D2518",
            "border": "1px solid #E5AD5C",
            "text": "#E5AD5C",
            "icon": "#D4923A",
        },
        "info": {
            "bg": "#1A2530",
            "border": "1px solid #6DA8C9",
            "text": "#6DA8C9",
            "icon": "#4A8DB3",
        },
    },
    # 效果配置（与亮色主题相同）
    "effects": LIGHT_THEME_V2_DEFAULTS["effects"].copy(),
}


def get_theme_defaults(mode: str, version: int = 1) -> dict[str, Any]:
    """获取指定模式的默认主题值

    Args:
        mode: 主题模式 ("light" 或 "dark")
        version: 配置版本 (1 = V1面向常量, 2 = V2面向组件)

    Returns:
        dict: 默认主题配置
    """
    if version == 2:
        return DARK_THEME_V2_DEFAULTS if mode == "dark" else LIGHT_THEME_V2_DEFAULTS
    return DARK_THEME_DEFAULTS if mode == "dark" else LIGHT_THEME_DEFAULTS


def get_theme_v2_defaults(mode: str) -> dict[str, Any]:
    """获取指定模式的V2默认主题值（面向组件）"""
    return DARK_THEME_V2_DEFAULTS if mode == "dark" else LIGHT_THEME_V2_DEFAULTS


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
