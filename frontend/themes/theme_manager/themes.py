"""
主题定义模块

包含亮色主题和深色主题的颜色定义，以及辅助类型。
"""

from enum import Enum
from typing import NamedTuple

from .constants import DesignSystemConstants


class BookPalette(NamedTuple):
    """书香风格调色板 - 用于减少组件中重复的颜色获取代码"""
    bg_primary: str
    bg_secondary: str
    text_primary: str
    text_secondary: str
    text_tertiary: str
    accent_color: str
    accent_light: str
    border_color: str
    serif_font: str
    ui_font: str


class ThemeMode(Enum):
    """主题模式枚举"""
    LIGHT = "light"  # 亮色主题
    DARK = "dark"    # 深色主题


class LightTheme(DesignSystemConstants):
    """亮色主题 - 书香风格（Book Style）

    设计理念：
    - 温暖的书香氛围（古旧书页、羊皮纸、赭石墨水）
    - 材质感参考（米色纸张、皮革书脊、陈旧羊皮纸）
    - 统一的赭石/琥珀色系

    视觉DNA：
    - 温暖的米色背景
    - 赭石色强调
    - 深褐色文字
    """

    # ==================== 色彩系统 - 书香风格 ====================
    # 主色调 - 赭石色（Sienna）- 书香、温暖、经典
    PRIMARY = "#8B4513"          # 赭石色（与book_accent_color一致）
    PRIMARY_LIGHT = "#A0522D"    # 浅赭石
    PRIMARY_DARK = "#6B3410"     # 深赭石
    PRIMARY_PALE = "#FDF5ED"     # 极浅赭石（hover/focus状态）
    PRIMARY_GRADIENT = ["#A0522D", "#8B4513", "#6B3410"]  # 赭石渐变

    # 强调色 - 陶土色（Terracotta）- 温暖、手工质感
    ACCENT = "#A0522D"           # 陶土色
    ACCENT_LIGHT = "#B8653D"     # 浅陶土
    ACCENT_DARK = "#8B4513"      # 深陶土（与PRIMARY相同）
    ACCENT_PALE = "#FAF5F0"      # 极浅陶土
    ACCENT_GRADIENT = ["#B8653D", "#A0522D", "#8B4513"]  # 陶土渐变

    # 成功色 - 翠绿（自然舒适）
    SUCCESS = "#4a9f6e"
    SUCCESS_LIGHT = "#6db88a"
    SUCCESS_DARK = "#3a8558"
    SUCCESS_BG = "#f0f9f4"
    SUCCESS_GRADIENT = ["#8fcca6", "#6db88a", "#4a9f6e"]

    # 错误色 - 烧焦赭色（柔和警示）
    ERROR = "#A85448"
    ERROR_LIGHT = "#C4706A"
    ERROR_DARK = "#8B3F35"
    ERROR_BG = "#fdf3f2"
    ERROR_GRADIENT = ["#C4706A", "#A85448", "#8B3F35"]

    # 警告色 - 暖琥珀（温暖提醒）
    WARNING = "#d4923a"
    WARNING_LIGHT = "#e5ad5c"
    WARNING_DARK = "#b87a2a"
    WARNING_BG = "#fdf8f0"
    WARNING_GRADIENT = ["#f0c67d", "#e5ad5c", "#d4923a"]

    # 信息色 - 青石蓝（沉稳资讯）
    INFO = "#4a8db3"
    INFO_LIGHT = "#6da8c9"
    INFO_DARK = "#3a7499"
    INFO_BG = "#f0f6fa"
    INFO_GRADIENT = ["#90c5dd", "#6da8c9", "#4a8db3"]

    # 文字颜色 - 书香深褐色调
    TEXT_PRIMARY = "#2C1810"     # 深褐（主文本，与book_text_primary一致）
    TEXT_SECONDARY = "#5D4037"   # 中褐（次级文本，与book_text_secondary一致）
    TEXT_TERTIARY = "#6D6560"    # 浅褐
    TEXT_PLACEHOLDER = "#8D8580" # 占位符
    TEXT_DISABLED = "#B0A8A0"    # 禁用

    # 背景颜色 - 书香米色纸张
    BG_PRIMARY = "#F9F5F0"       # 米色（主背景，与book_bg_primary一致）
    BG_SECONDARY = "#FFFBF0"     # 浅米色（卡片背景，与book_bg_secondary一致）
    BG_TERTIARY = "#F0EBE5"      # 石材色（输入框/代码块）
    BG_CARD = "#FFFBF0"          # 卡片背景
    BG_CARD_HOVER = "#F5F0EA"    # 悬浮状态
    BG_GRADIENT = ["#F9F5F0", "#FFFBF0", "#F0EBE5"]  # 自然渐变背景
    BG_MUTED = "#F0EBE5"         # 柔和背景
    BG_ACCENT = "#E6DCCD"        # 沙色强调背景

    # 边框颜色 - 书香边框（与book_border_color一致）
    BORDER_DEFAULT = "#D7CCC8"   # 默认边框
    BORDER_LIGHT = "#E8E4DF"     # 浅边框
    BORDER_DARK = "#C4C0BC"      # 深边框

    # 特殊效果色
    GLASS_BG = "rgba(249, 245, 240, 0.85)"  # 米白玻璃态
    SHADOW_COLOR = "rgba(44, 24, 16, 0.08)" # 书香色阴影
    OVERLAY_COLOR = "rgba(44, 24, 16, 0.25)" # 书香遮罩层

    # 按钮文字颜色
    BUTTON_TEXT = "#FFFBF0"      # 浅米色（在赭石按钮上）
    BUTTON_TEXT_SECONDARY = "#2C1810"  # 深褐（在浅色按钮上）

    # ==================== 书香风格特有效果 ====================
    # 赭石色阴影
    SHADOW_SIENNA = "0 4px 20px -2px rgba(139,69,19,0.15)"
    SHADOW_SIENNA_HOVER = "0 6px 24px -4px rgba(139,69,19,0.25)"

    # 卡片阴影
    SHADOW_CARD = "0 4px 20px -2px rgba(139,69,19,0.10)"
    SHADOW_CARD_HOVER = "0 20px 40px -10px rgba(139,69,19,0.15)"

    # 有机圆角（blob形状）
    RADIUS_ORGANIC = "60% 40% 30% 70% / 60% 30% 70% 40%"
    RADIUS_ORGANIC_ALT = "30% 70% 70% 30% / 30% 30% 70% 70%"

    # 药丸形按钮圆角
    RADIUS_PILL = "9999px"


class DarkTheme(DesignSystemConstants):
    """深色主题 - 书香风格（Book Style Dark）

    设计理念：
    - 与亮色主题统一的书香氛围
    - 温暖的琥珀色调（夜间阅读的温馨感）
    - 深色背景配合暖色强调

    视觉DNA：
    - 深褐色背景（古旧书房）
    - 琥珀色强调（烛光温暖）
    - 羊皮纸色文字
    """

    # ==================== 色彩系统 - 书香风格（暗色版） ====================
    # 主色调 - 琥珀色（Amber）- 与亮色主题的赭石色呼应
    PRIMARY = "#E89B6C"          # 琥珀色（与book_accent_color dark一致）
    PRIMARY_LIGHT = "#F0B088"    # 浅琥珀
    PRIMARY_DARK = "#D4845A"     # 深琥珀
    PRIMARY_PALE = "#2A2520"     # 琥珀背景tint
    PRIMARY_GRADIENT = ["#F0B088", "#E89B6C", "#D4845A"]  # 琥珀渐变

    # 强调色 - 暖陶土色（Warm Terracotta）- 与亮色主题统一
    ACCENT = "#D4845A"           # 暖陶土
    ACCENT_LIGHT = "#E89B6C"     # 浅陶土（与PRIMARY相同）
    ACCENT_DARK = "#B86E48"      # 深陶土
    ACCENT_PALE = "#2D2118"      # 陶土背景tint
    ACCENT_GRADIENT = ["#E89B6C", "#D4845A", "#B86E48"]  # 陶土渐变

    # 成功色 - 暖调翠绿
    SUCCESS = "#4a9f6e"
    SUCCESS_LIGHT = "#6db88a"
    SUCCESS_DARK = "#3a8558"
    SUCCESS_BG = "#1a2f22"
    SUCCESS_GRADIENT = ["#8fcca6", "#6db88a", "#4a9f6e"]

    # 错误色 - 烧焦赭色（Burnt Sienna）
    ERROR = "#A85448"
    ERROR_LIGHT = "#C4706A"
    ERROR_DARK = "#8B3F35"
    ERROR_BG = "#2D1F1C"
    ERROR_GRADIENT = ["#C4706A", "#A85448", "#8B3F35"]

    # 警告色 - 暖琥珀
    WARNING = "#D4923A"
    WARNING_LIGHT = "#E5AD5C"
    WARNING_DARK = "#B87A2A"
    WARNING_BG = "#2D2518"
    WARNING_GRADIENT = ["#E5AD5C", "#D4923A", "#B87A2A"]

    # 信息色 - 青石蓝
    INFO = "#4A8DB3"
    INFO_LIGHT = "#6DA8C9"
    INFO_DARK = "#3A7499"
    INFO_BG = "#1A2530"
    INFO_GRADIENT = ["#6DA8C9", "#4A8DB3", "#3A7499"]

    # 文字颜色 - 古董羊皮纸色调（Antique Parchment）
    TEXT_PRIMARY = "#E8DFD4"     # 古董羊皮纸（主文本）
    TEXT_SECONDARY = "#9C8B7A"   # 褪色墨水（次级文本）
    TEXT_TERTIARY = "#7A6B5A"    # 暗褪色墨水
    TEXT_PLACEHOLDER = "#5A4D40" # 占位符
    TEXT_DISABLED = "#4A3F35"    # 禁用（与边框同色）

    # 背景颜色 - 深色木质（Mahogany Wood）
    BG_PRIMARY = "#1C1714"       # 深桃花心木（主背景）
    BG_SECONDARY = "#251E19"     # 古老橡木（卡片/面板背景）
    BG_TERTIARY = "#3D332B"      # 磨损皮革（三级背景）
    BG_CARD = "#251E19"          # 卡片背景（与次级背景统一）
    BG_CARD_HOVER = "#2D2520"    # 悬浮状态
    BG_GRADIENT = ["#1C1714", "#251E19", "#3D332B"]  # 木质渐变背景
    BG_MUTED = "#3D332B"         # 柔和背景（Worn Leather）

    # 边框颜色 - 木纹色调（Wood Grain）
    BORDER_DEFAULT = "#4A3F35"   # 木纹边框
    BORDER_LIGHT = "#3D332B"     # 浅木纹
    BORDER_DARK = "#5A4D40"      # 深木纹

    # 特殊效果色
    GLASS_BG = "rgba(37, 30, 25, 0.85)"    # 橡木玻璃态
    SHADOW_COLOR = "rgba(0, 0, 0, 0.3)"    # 深色阴影
    OVERLAY_COLOR = "rgba(28, 23, 20, 0.4)" # 桃花心木遮罩

    # 按钮文字颜色
    BUTTON_TEXT = "#1C1714"          # 深色文字（在琥珀按钮上）
    BUTTON_TEXT_SECONDARY = "#E8DFD4"  # 羊皮纸文字（在深色按钮上）

    # ==================== 书香风格特有效果（暗色版） ====================
    # 琥珀色阴影（与亮色主题的赭石阴影呼应）
    SHADOW_SIENNA = "0 4px 20px -2px rgba(232,155,108,0.15)"
    SHADOW_SIENNA_HOVER = "0 6px 24px -4px rgba(232,155,108,0.25)"

    # 卡片阴影
    SHADOW_CARD = "0 4px 20px -2px rgba(232,155,108,0.10)"
    SHADOW_CARD_HOVER = "0 20px 40px -10px rgba(232,155,108,0.15)"

    # 琥珀光晕（hover状态）
    SHADOW_AMBER_GLOW = "0 4px 12px rgba(232,155,108,0.3)"

    # 有机圆角（blob形状）- 与亮色主题统一
    RADIUS_ORGANIC = "60% 40% 30% 70% / 60% 30% 70% 40%"
    RADIUS_ORGANIC_ALT = "30% 70% 70% 30% / 30% 30% 70% 70%"

    # 药丸形按钮圆角
    RADIUS_PILL = "9999px"
