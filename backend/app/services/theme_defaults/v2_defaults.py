"""
V2版本主题默认配置

面向组件的主题配置结构：设计令牌 + 组件配置 + 效果配置。
"""

from typing import Any, Dict


# ==================== V2: 亮色主题默认值 ====================

LIGHT_THEME_V2_DEFAULTS: Dict[str, Any] = {
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


# ==================== V2: 暗色主题默认值 ====================

DARK_THEME_V2_DEFAULTS: Dict[str, Any] = {
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
