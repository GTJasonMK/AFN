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
    """亮色主题 - Claude晨曦风格 (Morning Theme)

    设计理念：
    - 温暖舒适的暖色调（适合长时间创作）
    - 赭红色主色调（Claude品牌色，温暖亲切）
    - 米色背景（护眼柔和，减少蓝光）
    - 棕色系文字（自然阅读体验）

    灵感来源：Claude AI品牌色彩体系
    """

    # ==================== 色彩系统 - Claude晨曦风格 ====================
    # 主色调 - 温暖赭红色（Claude品牌色）
    PRIMARY = "#c6613f"  # 赭红色（温暖亲切）
    PRIMARY_LIGHT = "#d4826a"  # 浅赭红
    PRIMARY_DARK = "#a8502f"   # 深赭红
    PRIMARY_PALE = "#faf5f0"   # 极浅暖色（hover/focus状态）
    PRIMARY_GRADIENT = ["#d4826a", "#c6613f", "#a8502f"]  # 赭红渐变

    # 强调色 - 暖调鼠尾草绿（自然舒适）
    ACCENT = "#7c9a76"    # 鼠尾草绿
    ACCENT_LIGHT = "#9db897"
    ACCENT_DARK = "#5f7d59"
    ACCENT_PALE = "#f0f5ee"
    ACCENT_GRADIENT = ["#9db897", "#7c9a76", "#5f7d59"]  # 鼠尾草渐变

    # 成功色 - 暖调翠绿（自然舒适）
    SUCCESS = "#4a9f6e"
    SUCCESS_LIGHT = "#6db88a"
    SUCCESS_DARK = "#3a8558"
    SUCCESS_BG = "#f0f9f4"
    SUCCESS_GRADIENT = ["#8fcca6", "#6db88a", "#4a9f6e"]  # 暖翠绿渐变

    # 错误色 - 暖调砖红（柔和警示）
    ERROR = "#d4564e"
    ERROR_LIGHT = "#e07a74"
    ERROR_DARK = "#b8433c"
    ERROR_BG = "#fdf3f2"
    ERROR_GRADIENT = ["#eba09b", "#e07a74", "#d4564e"]  # 砖红渐变

    # 警告色 - 暖调琥珀（温暖提醒）
    WARNING = "#d4923a"
    WARNING_LIGHT = "#e5ad5c"
    WARNING_DARK = "#b87a2a"
    WARNING_BG = "#fdf8f0"
    WARNING_GRADIENT = ["#f0c67d", "#e5ad5c", "#d4923a"]  # 琥珀渐变

    # 信息色 - 暖调青石蓝（沉稳资讯）
    INFO = "#4a8db3"
    INFO_LIGHT = "#6da8c9"
    INFO_DARK = "#3a7499"
    INFO_BG = "#f0f6fa"
    INFO_GRADIENT = ["#90c5dd", "#6da8c9", "#4a8db3"]  # 青石蓝渐变

    # 文字颜色 - 暖棕色调（自然阅读）
    TEXT_PRIMARY = "#2c2621"     # 深棕色（主文本）
    TEXT_SECONDARY = "#615e5a"    # 中棕灰
    TEXT_TERTIARY = "#8a8580"     # 浅棕灰
    TEXT_PLACEHOLDER = "#a39e99"  # 占位符
    TEXT_DISABLED = "#c4c0bc"     # 禁用

    # 背景颜色 - 温暖米色（护眼舒适）
    BG_PRIMARY = "#f1ede6"       # 温暖米色（主背景）
    BG_SECONDARY = "#f7f3ee"     # 浅米白（次级背景）
    BG_TERTIARY = "#ebe4db"      # 浅棕色（输入框/代码块）
    BG_CARD = "#f7f3ee"          # 卡片背景（与次级背景统一）
    BG_CARD_HOVER = "#e8e4df"    # 悬浮状态
    BG_GRADIENT = ["#f7f3ee", "#f1ede6", "#ebe4db"]  # 温暖渐变背景

    # 边框颜色 - 暖灰色调（柔和分隔）
    BORDER_DEFAULT = "#ddd9d3"   # 适中边框
    BORDER_LIGHT = "#e8e4df"     # 浅边框
    BORDER_DARK = "#c4c0bc"      # 深边框

    # 特殊效果色
    GLASS_BG = "rgba(247, 243, 238, 0.85)"  # 暖色玻璃态背景
    SHADOW_COLOR = "rgba(44, 38, 33, 0.08)"  # 暖色阴影
    OVERLAY_COLOR = "rgba(44, 38, 33, 0.25)"  # 暖色遮罩层

    # 按钮文字颜色（在有色按钮上）
    BUTTON_TEXT = "#ffffff"      # 白色文字（在PRIMARY/ACCENT等深色按钮上）
    BUTTON_TEXT_SECONDARY = "#2c2621"  # 深棕文字（在浅色按钮上）


class DarkTheme(DesignSystemConstants):
    """深色主题 - 暖夜书香风格 (2025 Modern Design)

    设计理念：
    - 深邃温暖的背景（护眼舒适，带褐色调）
    - 暖琥珀金色主调（与亮色主题赭红呼应）
    - 高亮度文字（清晰可读）
    - 温暖典雅的文学气质
    """

    # ==================== 色彩系统 - 暖夜书香风格 ====================
    # 主色调 - 暖琥珀金（与亮色主题赭红呼应，温暖典雅）
    PRIMARY = "#E89B6C"      # 暖橙琥珀
    PRIMARY_LIGHT = "#F2B896"
    PRIMARY_DARK = "#D4784F"
    PRIMARY_PALE = "#3D2A1F"  # 深褐色背景tint
    PRIMARY_GRADIENT = ["#F2B896", "#E89B6C", "#D4784F"]  # 暖琥珀渐变

    # 强调色 - 温润青玉（与主色形成优雅对比）
    ACCENT = "#5AB8A8"       # 青玉色
    ACCENT_LIGHT = "#7DCCC0"
    ACCENT_DARK = "#3D9C8C"
    ACCENT_PALE = "#1F3D38"
    ACCENT_GRADIENT = ["#9DDCD2", "#7DCCC0", "#5AB8A8"]  # 青玉渐变

    # 成功色 - 翠绿（舒适自然）
    SUCCESS = "#22c55e"
    SUCCESS_LIGHT = "#4ade80"
    SUCCESS_DARK = "#16a34a"
    SUCCESS_BG = "#14532d"
    SUCCESS_GRADIENT = ["#86efac", "#4ade80", "#22c55e"]

    # 错误色 - 玫瑰红（温和警示）
    ERROR = "#f43f5e"
    ERROR_LIGHT = "#fb7185"
    ERROR_DARK = "#e11d48"
    ERROR_BG = "#881337"
    ERROR_GRADIENT = ["#fda4af", "#fb7185", "#f43f5e"]

    # 警告色 - 琥珀色（温暖提醒）
    WARNING = "#f59e0b"
    WARNING_LIGHT = "#fbbf24"
    WARNING_DARK = "#d97706"
    WARNING_BG = "#78350f"
    WARNING_GRADIENT = ["#fcd34d", "#fbbf24", "#f59e0b"]

    # 信息色 - 天空蓝（清新资讯）
    INFO = "#0ea5e9"
    INFO_LIGHT = "#38bdf8"
    INFO_DARK = "#0284c7"
    INFO_BG = "#0c4a6e"
    INFO_GRADIENT = ["#7dd3fc", "#38bdf8", "#0ea5e9"]

    # 文字颜色 - 暖调高亮度（护眼清晰）
    TEXT_PRIMARY = "#F5F0EB"     # 暖白色
    TEXT_SECONDARY = "#D4CCC4"   # 暖浅灰
    TEXT_TERTIARY = "#A89E94"    # 暖中灰
    TEXT_PLACEHOLDER = "#6D635A" # 暖暗灰
    TEXT_DISABLED = "#4A433D"    # 暖深灰

    # 背景颜色 - 深邃暖褐（温暖护眼）
    BG_PRIMARY = "#0F0D0B"       # 深暖黑
    BG_SECONDARY = "#171412"     # 暗褐灰
    BG_TERTIARY = "#1F1B18"      # 中褐灰
    BG_CARD = "#1A1714"          # 卡片深褐
    BG_CARD_HOVER = "#252220"    # 悬浮亮褐
    BG_GRADIENT = ["#0F0D0B", "#171412", "#1F1B18"]  # 暖夜渐变背景

    # 边框颜色 - 暖灰色调
    BORDER_DEFAULT = "#3D3835"   # 暖灰边框
    BORDER_LIGHT = "#2D2926"
    BORDER_DARK = "#4D4845"

    # 特殊效果色
    GLASS_BG = "rgba(26, 23, 20, 0.75)"   # 暖色玻璃态
    SHADOW_COLOR = "rgba(0, 0, 0, 0.5)"   # 深色阴影
    OVERLAY_COLOR = "rgba(0, 0, 0, 0.45)" # 遮罩层颜色

    # 按钮文字颜色（在有色按钮上）
    BUTTON_TEXT = "#ffffff"          # 白色文字
    BUTTON_TEXT_SECONDARY = "#F5F0EB"  # 暖白文字
