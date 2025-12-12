"""
主题管理器 - 支持亮色和深色主题切换

提供统一的主题切换接口，让用户可以在不同主题间自由切换
集成现代美学效果（渐变、玻璃态、新拟态）
"""

from PyQt6.QtCore import QObject, pyqtSignal
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple
from .modern_effects import ModernEffects

if TYPE_CHECKING:
    from utils.config_manager import ConfigManager


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


class DesignSystemConstants:
    """设计系统共享常量基类

    包含所有主题共享的设计规范，确保亮色/深色主题间的一致性。
    子类只需定义颜色相关属性。
    """

    # ==================== 圆角规范 - 方正风格（微圆角设计）====================
    RADIUS_XS = "2px"    # 超小元素（几乎直角）
    RADIUS_SM = "4px"    # 小元素：按钮、标签、小卡片
    RADIUS_MD = "6px"    # 中等元素：卡片、输入框
    RADIUS_LG = "8px"    # 大元素：大型容器
    RADIUS_XL = "10px"   # 超大元素：模态框
    RADIUS_ROUND = "50%"  # 圆形：头像、图标按钮

    # ==================== 间距规范 - 8px网格系统 ====================
    SPACING_XS = "8px"
    SPACING_SM = "16px"
    SPACING_MD = "24px"
    SPACING_LG = "32px"
    SPACING_XL = "40px"
    SPACING_XXL = "48px"

    # ==================== 字体大小规范 ====================
    FONT_SIZE_XS = "12px"
    FONT_SIZE_SM = "13px"
    FONT_SIZE_BASE = "14px"
    FONT_SIZE_MD = "16px"
    FONT_SIZE_LG = "18px"
    FONT_SIZE_XL = "20px"
    FONT_SIZE_2XL = "24px"
    FONT_SIZE_3XL = "32px"

    # ==================== 字体粗细规范 ====================
    FONT_WEIGHT_NORMAL = "400"
    FONT_WEIGHT_MEDIUM = "500"
    FONT_WEIGHT_SEMIBOLD = "600"
    FONT_WEIGHT_BOLD = "700"

    # ==================== 行高规范 ====================
    LINE_HEIGHT_TIGHT = "1.2"
    LINE_HEIGHT_NORMAL = "1.5"
    LINE_HEIGHT_RELAXED = "1.6"
    LINE_HEIGHT_LOOSE = "1.8"

    # ==================== 字母间距规范 ====================
    LETTER_SPACING_TIGHT = "-0.02em"
    LETTER_SPACING_NORMAL = "0"
    LETTER_SPACING_WIDE = "0.05em"
    LETTER_SPACING_WIDER = "0.1em"


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


class ThemeManager(QObject):
    """主题管理器 - 单例模式"""
    
    theme_changed = pyqtSignal(str)  # 主题切换信号
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 必须在__new__中调用QObject的__init__
            QObject.__init__(cls._instance)
            cls._instance._current_mode = ThemeMode.LIGHT
            cls._instance._current_theme = LightTheme
            cls._instance._config_manager = None
            cls._initialized = True
        return cls._instance
    
    def __init__(self):
        # 由于在__new__中已经初始化，这里不需要再做任何事
        pass
    
    @property
    def current_mode(self):
        """获取当前主题模式"""
        return self._current_mode
    
    @property
    def current_theme(self):
        """获取当前主题类"""
        return self._current_theme
    
    def set_config_manager(self, config_manager: 'ConfigManager'):
        """设置配置管理器

        Args:
            config_manager: ConfigManager实例
        """
        self._config_manager = config_manager

    def load_theme_from_config(self):
        """从配置文件加载主题"""
        if self._config_manager is None:
            return

        theme_mode = self._config_manager.get_theme_mode()
        if theme_mode == "dark":
            self.switch_theme(ThemeMode.DARK, save_config=False)
        else:
            self.switch_theme(ThemeMode.LIGHT, save_config=False)

    def save_theme_to_config(self):
        """保存主题到配置文件"""
        if self._config_manager is None:
            return

        mode_str = self._current_mode.value
        self._config_manager.set_theme_mode(mode_str)

    def switch_theme(self, mode: ThemeMode = None, save_config: bool = True):
        """切换主题
        
        Args:
            mode: 目标主题模式，如果为None则切换到另一个主题
            save_config: 是否保存到配置文件
        """
        if mode is None:
            # 如果没有指定模式，则切换到另一个主题
            mode = ThemeMode.DARK if self._current_mode == ThemeMode.LIGHT else ThemeMode.LIGHT
        
        self._current_mode = mode
        self._current_theme = DarkTheme if mode == ThemeMode.DARK else LightTheme
        
        # 保存到配置
        if save_config:
            self.save_theme_to_config()
        
        # 发射主题切换信号
        self.theme_changed.emit(mode.value)
    
    def is_dark_mode(self):
        """判断是否为深色模式"""
        return self._current_mode == ThemeMode.DARK
    
    def is_light_mode(self):
        """判断是否为亮色模式"""
        return self._current_mode == ThemeMode.LIGHT
    
    # ==================== 便捷访问属性 ====================
    @property
    def PRIMARY(self):
        return self._current_theme.PRIMARY

    @property
    def PRIMARY_LIGHT(self):
        return self._current_theme.PRIMARY_LIGHT

    @property
    def PRIMARY_DARK(self):
        return self._current_theme.PRIMARY_DARK

    @property
    def PRIMARY_PALE(self):
        return self._current_theme.PRIMARY_PALE

    @property
    def PRIMARY_GRADIENT(self):
        return getattr(self._current_theme, 'PRIMARY_GRADIENT', [self.PRIMARY, self.PRIMARY_DARK])

    @property
    def ACCENT(self):
        return getattr(self._current_theme, 'ACCENT', self.PRIMARY)

    @property
    def ACCENT_LIGHT(self):
        return getattr(self._current_theme, 'ACCENT_LIGHT', self.PRIMARY_LIGHT)

    @property
    def ACCENT_DARK(self):
        return getattr(self._current_theme, 'ACCENT_DARK', self.PRIMARY_DARK)

    @property
    def ACCENT_PALE(self):
        return getattr(self._current_theme, 'ACCENT_PALE', self.PRIMARY_PALE)

    @property
    def ACCENT_GRADIENT(self):
        return getattr(self._current_theme, 'ACCENT_GRADIENT', [self.ACCENT, self.ACCENT_DARK])

    # 保留旧的强调色属性以兼容
    @property
    def ACCENT_PRIMARY(self):
        return self.SUCCESS

    @property
    def ACCENT_SECONDARY(self):
        return self.INFO

    @property
    def ACCENT_TERTIARY(self):
        return self.WARNING
    
    @property
    def TEXT_PRIMARY(self):
        return self._current_theme.TEXT_PRIMARY
    
    @property
    def TEXT_SECONDARY(self):
        return self._current_theme.TEXT_SECONDARY
    
    @property
    def TEXT_TERTIARY(self):
        return self._current_theme.TEXT_TERTIARY
    
    @property
    def TEXT_PLACEHOLDER(self):
        return self._current_theme.TEXT_PLACEHOLDER
    
    @property
    def TEXT_DISABLED(self):
        return self._current_theme.TEXT_DISABLED
    
    @property
    def BG_PRIMARY(self):
        return self._current_theme.BG_PRIMARY
    
    @property
    def BG_SECONDARY(self):
        return self._current_theme.BG_SECONDARY
    
    @property
    def BG_TERTIARY(self):
        return self._current_theme.BG_TERTIARY
    
    @property
    def BG_CARD(self):
        return self._current_theme.BG_CARD
    
    @property
    def BG_CARD_HOVER(self):
        return self._current_theme.BG_CARD_HOVER
    
    @property
    def BORDER_DEFAULT(self):
        return self._current_theme.BORDER_DEFAULT
    
    @property
    def BORDER_LIGHT(self):
        return self._current_theme.BORDER_LIGHT
    
    @property
    def BORDER_DARK(self):
        return self._current_theme.BORDER_DARK

    @property
    def BUTTON_TEXT(self):
        """按钮文字颜色"""
        return self._current_theme.BUTTON_TEXT

    @property
    def BUTTON_TEXT_SECONDARY(self):
        """次要按钮文字颜色"""
        return self._current_theme.BUTTON_TEXT_SECONDARY

    @property
    def OVERLAY_COLOR(self):
        """遮罩层颜色"""
        return self._current_theme.OVERLAY_COLOR

    @property
    def SHADOW_COLOR(self):
        """阴影颜色"""
        return self._current_theme.SHADOW_COLOR

    @property
    def SUCCESS(self):
        return self._current_theme.SUCCESS

    @property
    def SUCCESS_LIGHT(self):
        return self._current_theme.SUCCESS_LIGHT

    @property
    def SUCCESS_DARK(self):
        return self._current_theme.SUCCESS_DARK

    @property
    def SUCCESS_BG(self):
        return self._current_theme.SUCCESS_BG
    
    @property
    def ERROR(self):
        return self._current_theme.ERROR

    @property
    def ERROR_LIGHT(self):
        return self._current_theme.ERROR_LIGHT

    @property
    def ERROR_DARK(self):
        return self._current_theme.ERROR_DARK

    @property
    def ERROR_BG(self):
        return self._current_theme.ERROR_BG
    
    @property
    def WARNING(self):
        return self._current_theme.WARNING

    @property
    def WARNING_LIGHT(self):
        return self._current_theme.WARNING_LIGHT

    @property
    def WARNING_DARK(self):
        return self._current_theme.WARNING_DARK

    @property
    def WARNING_BG(self):
        return self._current_theme.WARNING_BG
    
    @property
    def INFO(self):
        return self._current_theme.INFO

    @property
    def INFO_LIGHT(self):
        return self._current_theme.INFO_LIGHT

    @property
    def INFO_DARK(self):
        return self._current_theme.INFO_DARK

    @property
    def INFO_BG(self):
        return self._current_theme.INFO_BG

    # ==================== 渐变属性 ====================
    @property
    def SUCCESS_GRADIENT(self):
        return self._current_theme.SUCCESS_GRADIENT

    @property
    def ERROR_GRADIENT(self):
        return self._current_theme.ERROR_GRADIENT

    @property
    def WARNING_GRADIENT(self):
        return self._current_theme.WARNING_GRADIENT

    @property
    def INFO_GRADIENT(self):
        return self._current_theme.INFO_GRADIENT
    
    # ==================== 设计系统常量 ====================
    @property
    def RADIUS_XS(self):
        return self._current_theme.RADIUS_XS
    
    @property
    def RADIUS_SM(self):
        return self._current_theme.RADIUS_SM
    
    @property
    def RADIUS_MD(self):
        return self._current_theme.RADIUS_MD
    
    @property
    def RADIUS_LG(self):
        return self._current_theme.RADIUS_LG
    
    @property
    def RADIUS_ROUND(self):
        return self._current_theme.RADIUS_ROUND
    
    @property
    def SPACING_XS(self):
        return self._current_theme.SPACING_XS
    
    @property
    def SPACING_SM(self):
        return self._current_theme.SPACING_SM
    
    @property
    def SPACING_MD(self):
        return self._current_theme.SPACING_MD
    
    @property
    def SPACING_LG(self):
        return self._current_theme.SPACING_LG
    
    @property
    def SPACING_XL(self):
        return self._current_theme.SPACING_XL
    
    @property
    def SPACING_XXL(self):
        return self._current_theme.SPACING_XXL
    
    # ==================== 字体系统常量 ====================
    @property
    def FONT_SIZE_XS(self):
        return self._current_theme.FONT_SIZE_XS
    
    @property
    def FONT_SIZE_SM(self):
        return self._current_theme.FONT_SIZE_SM
    
    @property
    def FONT_SIZE_BASE(self):
        return self._current_theme.FONT_SIZE_BASE
    
    @property
    def FONT_SIZE_MD(self):
        return self._current_theme.FONT_SIZE_MD
    
    @property
    def FONT_SIZE_LG(self):
        return self._current_theme.FONT_SIZE_LG
    
    @property
    def FONT_SIZE_XL(self):
        return self._current_theme.FONT_SIZE_XL
    
    @property
    def FONT_SIZE_2XL(self):
        return self._current_theme.FONT_SIZE_2XL
    
    @property
    def FONT_SIZE_3XL(self):
        return self._current_theme.FONT_SIZE_3XL
    
    @property
    def FONT_WEIGHT_NORMAL(self):
        return self._current_theme.FONT_WEIGHT_NORMAL
    
    @property
    def FONT_WEIGHT_MEDIUM(self):
        return self._current_theme.FONT_WEIGHT_MEDIUM
    
    @property
    def FONT_WEIGHT_SEMIBOLD(self):
        return self._current_theme.FONT_WEIGHT_SEMIBOLD
    
    @property
    def FONT_WEIGHT_BOLD(self):
        return self._current_theme.FONT_WEIGHT_BOLD
    
    @property
    def LINE_HEIGHT_TIGHT(self):
        return self._current_theme.LINE_HEIGHT_TIGHT
    
    @property
    def LINE_HEIGHT_NORMAL(self):
        return self._current_theme.LINE_HEIGHT_NORMAL
    
    @property
    def LINE_HEIGHT_RELAXED(self):
        return self._current_theme.LINE_HEIGHT_RELAXED
    
    @property
    def LINE_HEIGHT_LOOSE(self):
        return self._current_theme.LINE_HEIGHT_LOOSE

    @property
    def LETTER_SPACING_TIGHT(self):
        return self._current_theme.LETTER_SPACING_TIGHT

    @property
    def LETTER_SPACING_NORMAL(self):
        return self._current_theme.LETTER_SPACING_NORMAL

    @property
    def LETTER_SPACING_WIDE(self):
        return self._current_theme.LETTER_SPACING_WIDE

    @property
    def LETTER_SPACING_WIDER(self):
        return self._current_theme.LETTER_SPACING_WIDER

    # ==================== 按钮样式工厂方法 ====================

    def _solid_button_style(
        self,
        bg_color: str,
        bg_hover: str,
        bg_pressed: str,
        text_color: str = None,
        border: str = "none",
        padding: str = "10px 24px",
        min_height: str = "36px"
    ) -> str:
        """实心按钮样式工厂方法

        Args:
            bg_color: 背景颜色
            bg_hover: 悬停时背景颜色
            bg_pressed: 按下时背景颜色
            text_color: 文字颜色（默认为 BUTTON_TEXT）
            border: 边框样式（默认为 none）
            padding: 内边距
            min_height: 最小高度

        Returns:
            QPushButton 样式表字符串
        """
        ui_font = self.ui_font()
        text = text_color or self.BUTTON_TEXT
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text};
                border: {border};
                border-radius: {self.RADIUS_SM};
                padding: {padding};
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: {min_height};
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
            }}
            QPushButton:pressed {{
                background-color: {bg_pressed};
            }}
            QPushButton:disabled {{
                background-color: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
            }}
        """

    def button_primary(self):
        """主要按钮样式 - 渐变背景"""
        gradient_colors = self.PRIMARY_GRADIENT
        gradient_style = ModernEffects.linear_gradient(gradient_colors, 135)
        hover_gradient = ModernEffects.linear_gradient([self.PRIMARY_LIGHT, self.PRIMARY], 135)
        ui_font = self.ui_font()

        # 注意：Qt StyleSheet 不支持 box-shadow、transform 等 CSS3 属性
        # 渐变按钮需要特殊处理，不能使用工厂方法
        return f"""
            QPushButton {{
                background: {gradient_style};
                color: {self.BUTTON_TEXT};
                border: none;
                border-radius: {self.RADIUS_SM};
                padding: 10px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: {hover_gradient};
            }}
            QPushButton:pressed {{
                background: {self.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                background: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
            }}
        """

    def button_secondary(self):
        """次要按钮样式 - 玻璃态效果"""
        glass_style = ModernEffects.glassmorphism_card(self.is_dark_mode())
        ui_font = self.ui_font()

        return f"""
            QPushButton {{
                {glass_style}
                color: {self.TEXT_PRIMARY};
                border: 1px solid {self.BORDER_DEFAULT};
                border-radius: {self.RADIUS_SM};
                padding: 10px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.PRIMARY_PALE};
                border-color: {self.PRIMARY};
                color: {self.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {self.BG_SECONDARY};
            }}
            QPushButton:disabled {{
                color: {self.TEXT_DISABLED};
                border-color: {self.BORDER_LIGHT};
                background: transparent;
            }}
        """

    def button_accent(self):
        """强调按钮样式 - 活力渐变"""
        gradient_colors = self.ACCENT_GRADIENT
        gradient_style = ModernEffects.linear_gradient(gradient_colors, 135)
        hover_gradient = ModernEffects.linear_gradient([self.ACCENT_LIGHT, self.ACCENT], 135)
        accent_dark = self.ACCENT_DARK if hasattr(self, 'ACCENT_DARK') else self.ACCENT
        ui_font = self.ui_font()

        return f"""
            QPushButton {{
                background: {gradient_style};
                color: {self.BUTTON_TEXT};
                border: none;
                border-radius: {self.RADIUS_SM};
                padding: 10px 24px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_SEMIBOLD};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: {hover_gradient};
            }}
            QPushButton:pressed {{
                background: {accent_dark};
            }}
            QPushButton:disabled {{
                background: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
            }}
        """

    def button_text(self):
        """文本按钮样式 - 纯文本无边框"""
        ui_font = self.ui_font()
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {self.TEXT_SECONDARY};
                border: none;
                border-radius: {self.RADIUS_SM};
                padding: 8px 16px;
                font-family: {ui_font};
                font-size: {self.FONT_SIZE_SM};
                font-weight: {self.FONT_WEIGHT_MEDIUM};
                min-height: 32px;
            }}
            QPushButton:hover {{
                background-color: {self.BG_TERTIARY};
                color: {self.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {self.BG_SECONDARY};
            }}
            QPushButton:disabled {{
                color: {self.TEXT_DISABLED};
            }}
        """

    def button_danger(self):
        """危险按钮样式 - 红色警告"""
        return self._solid_button_style(
            bg_color=self.ERROR,
            bg_hover=self.ERROR_DARK,
            bg_pressed=self.ERROR_DARK
        )

    def button_warning(self):
        """警告按钮样式 - 橙色提醒"""
        return self._solid_button_style(
            bg_color=self.WARNING,
            bg_hover=self.WARNING_DARK,
            bg_pressed=self.WARNING_DARK
        )

    def button_success(self):
        """成功按钮样式 - 绿色确认"""
        return self._solid_button_style(
            bg_color=self.SUCCESS,
            bg_hover=self.SUCCESS_DARK,
            bg_pressed=self.SUCCESS_DARK
        )

    # ==================== 现代化样式方法 ====================

    def card_style(self, elevated: bool = False) -> str:
        """卡片样式 - 支持普通和浮起效果

        注意：Qt StyleSheet 不支持 box-shadow。
        阴影效果应通过 QGraphicsDropShadowEffect 实现。
        """
        if elevated:
            # 浮起卡片 - 新拟态效果（移除不支持的shadow transition）
            return f"""
                background-color: {self.BG_CARD};
                border-radius: {self.RADIUS_LG};
                border: 1px solid {self.BORDER_LIGHT};
            """
        else:
            # 普通卡片
            return f"""
                background-color: {self.BG_CARD};
                border: 1px solid {self.BORDER_LIGHT};
                border-radius: {self.RADIUS_MD};
            """

    def glass_card_style(self) -> str:
        """玻璃卡片样式

        注意：Qt StyleSheet 不支持 box-shadow。
        阴影效果应通过 QGraphicsDropShadowEffect 实现。
        """
        return f"""
            {ModernEffects.glassmorphism_card(self.is_dark_mode())}
            border-radius: {self.RADIUS_LG};
        """

    def input_style(self) -> str:
        """输入框样式 - 现代化设计

        注意：Qt StyleSheet 不支持 box-shadow（glow_effect）。
        发光效果应通过 QGraphicsDropShadowEffect 实现。
        """
        return f"""
            QLineEdit, QTextEdit {{
                background-color: {self.BG_CARD};
                border: 2px solid {self.BORDER_DEFAULT};
                border-radius: {self.RADIUS_SM};
                padding: 10px 12px;
                font-size: {self.FONT_SIZE_BASE};
                color: {self.TEXT_PRIMARY};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {self.PRIMARY};
                background-color: {self.BG_CARD};
            }}
            QLineEdit:hover, QTextEdit:hover {{
                border-color: {self.PRIMARY_LIGHT};
            }}
            QLineEdit:disabled, QTextEdit:disabled {{
                background-color: {self.BG_TERTIARY};
                color: {self.TEXT_DISABLED};
                border-color: {self.BORDER_LIGHT};
            }}
        """

    def gradient_background(self, colors: list = None) -> str:
        """渐变背景样式"""
        if colors is None:
            colors = getattr(self._current_theme, 'BG_GRADIENT', [self.BG_PRIMARY, self.BG_SECONDARY])
        return ModernEffects.linear_gradient(colors, 180)

    def aurora_background(self) -> str:
        """极光背景效果"""
        return ModernEffects.aurora_bg(self.is_dark_mode())

    def loading_style(self) -> str:
        """加载动画样式"""
        # 注意：Qt StyleSheet 对 CSS animations 支持有限
        return """
            QLabel {
                color: palette(text);
            }
        """

    def hover_lift_effect(self) -> str:
        """悬停上浮效果

        注意：Qt StyleSheet 不支持 transform 和 box-shadow。
        实际的悬停效果应通过 QPropertyAnimation 实现。
        这里返回空字符串，仅作为占位。
        """
        return ""

    def theme_transition(self, duration: str = "0.3s") -> str:
        """主题切换过渡动画

        注意：Qt StyleSheet 对 transition 的支持有限，
        仅支持部分属性。box-shadow 不被支持。

        Args:
            duration: 过渡时长，默认0.3秒

        Returns:
            CSS过渡样式字符串（仅包含Qt支持的属性）
        """
        return f"""
            transition: background-color {duration} ease,
                        color {duration} ease,
                        border-color {duration} ease;
        """

    def tabs(self):
        """标签页样式 - 支持主题切换"""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {self.BORDER_LIGHT};
                border-radius: {self.RADIUS_SM};
                background-color: {self.BG_CARD};
                top: -1px;
            }}
            QTabBar::tab {{
                padding: 10px 20px;
                font-size: {self.FONT_SIZE_BASE};
                font-weight: {self.FONT_WEIGHT_NORMAL};
                color: {self.TEXT_SECONDARY};
                background-color: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                color: {self.PRIMARY};
                border-bottom: 2px solid {self.PRIMARY};
                font-weight: {self.FONT_WEIGHT_MEDIUM};
            }}
            QTabBar::tab:hover:!selected {{
                color: {self.TEXT_PRIMARY};
                background-color: {self.BG_SECONDARY};
            }}
        """

    def scrollbar(self):
        """返回滚动条样式 - 极简设计，符合中国风美学"""
        return f"""
            QScrollBar:vertical {{
                background-color: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.BORDER_DEFAULT};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.TEXT_TERTIARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                background-color: transparent;
                height: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {self.BORDER_DEFAULT};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {self.TEXT_TERTIARY};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """

    # ==================== 书香风格专用方法 ====================

    def ui_font(self) -> str:
        """获取UI字体族 - 现代无衬线字体"""
        return "'Segoe UI', 'Microsoft YaHei', 'PingFang SC', 'Roboto', sans-serif"

    def serif_font(self) -> str:
        """获取衬线字体族 - 书香风格核心字体"""
        return "Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif"

    def book_accent_color(self) -> str:
        """获取书香风格强调色 - 赭石(亮)/暖琥珀(暗)"""
        return "#8B4513" if self.is_light_mode() else "#E89B6C"

    def book_accent_light(self) -> str:
        """获取书香风格浅强调色"""
        return "#A0522D" if self.is_light_mode() else "#F2B896"

    def book_text_primary(self) -> str:
        """获取书香风格主文字色 - 深褐(亮)/暖白(暗)"""
        return "#2C1810" if self.is_light_mode() else "#F5F0EB"

    def book_text_secondary(self) -> str:
        """获取书香风格次要文字色"""
        return "#5D4037" if self.is_light_mode() else "#D4CCC4"

    def book_bg_primary(self) -> str:
        """获取书香风格主背景色 - 米色(亮)/深暖褐(暗)"""
        return "#F9F5F0" if self.is_light_mode() else "#171412"

    def book_bg_secondary(self) -> str:
        """获取书香风格次要背景色 - 亮米色(亮)/中暖褐(暗)"""
        return "#FFFBF0" if self.is_light_mode() else "#1F1B18"

    def book_border_color(self) -> str:
        """获取书香风格边框色"""
        return "#D7CCC8" if self.is_light_mode() else "#3D3835"

    def book_text_tertiary(self) -> str:
        """获取书香风格三级文字色 - 确保在对应背景上有足够对比度"""
        # 亮色模式使用更深的灰色，深色模式使用暖浅灰
        return "#6D6560" if self.is_light_mode() else "#C4BAB0"

    def text_success(self) -> str:
        """获取用于文字的成功色 - 确保在背景上有足够对比度"""
        # 亮色模式使用更深的绿色，深色模式使用标准成功色
        return "#2E7D4A" if self.is_light_mode() else "#4ade80"

    def text_warning(self) -> str:
        """获取用于文字的警告色 - 确保在背景上有足够对比度"""
        # 亮色模式使用更深的琥珀棕色（对比度 > 5:1），深色模式使用标准警告色
        return "#8B5A00" if self.is_light_mode() else "#fbbf24"

    def text_error(self) -> str:
        """获取用于文字的错误色 - 确保在背景上有足够对比度"""
        # 亮色模式使用更深的红色，深色模式使用标准错误色
        return "#B8433C" if self.is_light_mode() else "#fb7185"

    def text_info(self) -> str:
        """获取用于文字的信息色 - 确保在背景上有足够对比度"""
        # 亮色模式使用更深的蓝色，深色模式使用标准信息色
        return "#2A6B8F" if self.is_light_mode() else "#38bdf8"

    def glassmorphism_bg(self, opacity: float = 0.85) -> str:
        """获取玻璃态背景色

        Args:
            opacity: 透明度 (0.0-1.0)

        Returns:
            rgba颜色字符串
        """
        if self.is_dark_mode():
            # 深色模式 - 暖褐玻璃效果（与暖夜书香主题一致）
            return f"rgba(26, 23, 20, {opacity})"
        else:
            # 亮色模式 - 暖米色玻璃
            return f"rgba(255, 251, 240, {opacity})"

    def book_card_style(self, hover: bool = False) -> str:
        """书香风格卡片样式

        Args:
            hover: 是否为悬停状态

        Returns:
            CSS样式字符串
        """
        bg = self.book_bg_secondary()
        border = self.book_border_color()
        accent = self.book_accent_color()

        if hover:
            return f"""
                background-color: {bg};
                border: 1px solid {accent};
                border-radius: 4px;
            """
        return f"""
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 4px;
        """

    def book_title_style(self, size: int = 28) -> str:
        """书香风格标题样式

        Args:
            size: 字体大小 (px)

        Returns:
            CSS样式字符串
        """
        return f"""
            font-family: {self.serif_font()};
            font-size: {size}px;
            font-weight: bold;
            color: {self.book_text_primary()};
            letter-spacing: 2px;
        """

    def book_body_style(self, size: int = 15) -> str:
        """书香风格正文样式

        Args:
            size: 字体大小 (px)

        Returns:
            CSS样式字符串
        """
        return f"""
            font-family: {self.serif_font()};
            font-size: {size}px;
            color: {self.book_text_primary()};
            line-height: 1.8;
        """

    def book_button_style(self, primary: bool = False) -> str:
        """书香风格按钮样式

        Args:
            primary: 是否为主要按钮

        Returns:
            CSS样式字符串
        """
        accent = self.book_accent_color()
        text_secondary = self.book_text_secondary()
        border = self.book_border_color()
        serif = self.serif_font()

        if primary:
            return f"""
                QPushButton {{
                    background-color: {accent};
                    color: #FFFFFF;
                    border: 1px solid {accent};
                    border-radius: 4px;
                    font-family: {serif};
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.book_text_primary()};
                    border-color: {self.book_text_primary()};
                }}
                QPushButton:pressed {{
                    background-color: {self.book_accent_light()};
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: 1px solid {border};
                    border-radius: 4px;
                    font-family: {serif};
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    color: {accent};
                    border-color: {accent};
                    background-color: rgba(0,0,0,0.03);
                }}
                QPushButton:pressed {{
                    background-color: rgba(0,0,0,0.05);
                }}
            """

    def book_tag_style(self, accent: bool = False) -> str:
        """书香风格标签样式

        Args:
            accent: 是否使用强调色

        Returns:
            CSS样式字符串
        """
        border = self.book_border_color()
        text = self.book_text_secondary()
        bg = "transparent"
        serif = self.serif_font()

        if accent:
            color = self.book_accent_color()
            return f"""
                background-color: {bg};
                color: {color};
                border: 1px solid {color};
                padding: 4px 12px;
                border-radius: 4px;
                font-family: {serif};
                font-size: 12px;
                font-weight: bold;
            """
        return f"""
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            padding: 4px 12px;
            border-radius: 4px;
            font-family: {serif};
            font-size: 12px;
        """

    def book_input_style(self) -> str:
        """书香风格输入框样式"""
        bg = self.book_bg_secondary()
        border = self.book_border_color()
        text = self.book_text_primary()
        accent = self.book_accent_color()
        serif = self.serif_font()

        return f"""
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 12px 16px;
                font-family: {serif};
                font-size: 15px;
                color: {text};
                line-height: 1.8;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {accent};
            }}
        """

    def book_separator(self, vertical: bool = False) -> str:
        """书香风格分隔线样式

        Args:
            vertical: 是否为垂直分隔线

        Returns:
            CSS样式字符串
        """
        border = self.book_border_color()
        if vertical:
            return f"border-left: 1px solid {border};"
        return f"border-top: 1px solid {border};"

    def get_book_palette(self) -> BookPalette:
        """获取书香风格完整调色板

        返回一个命名元组，包含所有常用的书香风格颜色和字体，
        用于在组件的 _apply_theme 方法中一次性获取所有颜色，
        减少重复代码。

        Returns:
            BookPalette: 包含所有常用颜色和字体的命名元组

        Example:
            def _apply_theme(self):
                palette = theme_manager.get_book_palette()
                self.title_label.setStyleSheet(f"color: {palette.text_primary};")
                self.content.setStyleSheet(f"background: {palette.bg_primary};")
        """
        return BookPalette(
            bg_primary=self.book_bg_primary(),
            bg_secondary=self.book_bg_secondary(),
            text_primary=self.book_text_primary(),
            text_secondary=self.book_text_secondary(),
            text_tertiary=self.book_text_tertiary(),
            accent_color=self.book_accent_color(),
            accent_light=self.book_accent_light(),
            border_color=self.book_border_color(),
            serif_font=self.serif_font(),
            ui_font=self.ui_font(),
        )


# 全局主题管理器实例
theme_manager = ThemeManager()