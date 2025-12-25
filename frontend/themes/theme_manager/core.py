"""
ThemeManager 核心类

主题管理器的核心实现，组合所有 Mixin 类。
"""

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from .themes import ThemeMode, LightTheme, DarkTheme
from .properties_mixin import ThemePropertiesMixin
from .button_styles_mixin import ButtonStylesMixin
from .component_styles_mixin import ComponentStylesMixin
from .book_styles_mixin import BookStylesMixin

if TYPE_CHECKING:
    from utils.config_manager import ConfigManager


class ThemeManager(
    ThemePropertiesMixin,
    ButtonStylesMixin,
    ComponentStylesMixin,
    BookStylesMixin,
    QObject
):
    """主题管理器

    组合多个 Mixin 提供完整的主题管理功能：
    - ThemePropertiesMixin: 颜色和设计常量属性代理
    - ButtonStylesMixin: 按钮样式工厂方法
    - ComponentStylesMixin: 通用组件样式方法
    - BookStylesMixin: 书香风格专用方法

    使用模块级单例模式，通过 theme_manager 变量访问全局实例。

    支持自定义主题：
    - apply_custom_theme(): 应用用户自定义配置
    - reset_to_default(): 重置为内置默认主题
    """

    theme_changed = pyqtSignal(str)  # 主题切换信号

    def __init__(self):
        """初始化主题管理器"""
        super().__init__()
        self._current_mode = ThemeMode.LIGHT
        self._current_theme = LightTheme
        self._config_manager = None
        # 自定义主题支持
        self._custom_theme_config = None  # 自定义配置字典
        self._use_custom = False          # 是否使用自定义主题

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
        import logging
        logger = logging.getLogger(__name__)

        if mode is None:
            # 如果没有指定模式，则切换到另一个主题
            mode = ThemeMode.DARK if self._current_mode == ThemeMode.LIGHT else ThemeMode.LIGHT

        logger.info(f"=== ThemeManager.switch_theme() ===")
        logger.info(f"Switching from {self._current_mode} to {mode}")

        self._current_mode = mode
        self._current_theme = DarkTheme if mode == ThemeMode.DARK else LightTheme

        # 保存到配置
        if save_config:
            self.save_theme_to_config()

        # 发射主题切换信号
        logger.info(f"Emitting theme_changed signal with mode: {mode.value}")
        self.theme_changed.emit(mode.value)

    def is_dark_mode(self):
        """判断是否为深色模式"""
        return self._current_mode == ThemeMode.DARK

    def is_light_mode(self):
        """判断是否为亮色模式"""
        return self._current_mode == ThemeMode.LIGHT

    def apply_custom_theme(self, config: dict, save: bool = True):
        """应用自定义主题配置

        Args:
            config: 配置字典，包含主题常量的自定义值
            save: 是否保存配置（预留，暂未实现）

        配置字典示例:
            {
                "PRIMARY": "#8B4513",
                "TEXT_PRIMARY": "#2C1810",
                "BG_PRIMARY": "#F9F5F0",
                ...
            }
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== ThemeManager.apply_custom_theme() ===")
        logger.info(f"Applying custom theme with {len(config)} properties")

        self._custom_theme_config = config
        self._use_custom = True

        # 创建动态主题类
        self._current_theme = self._create_theme_from_config(config)

        # 发射主题切换信号
        self.theme_changed.emit(self._current_mode.value)

    def reset_to_default(self):
        """重置为默认主题"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== ThemeManager.reset_to_default() ===")

        self._use_custom = False
        self._custom_theme_config = None
        self._current_theme = DarkTheme if self._current_mode == ThemeMode.DARK else LightTheme

        # 发射主题切换信号
        self.theme_changed.emit(self._current_mode.value)

    def _create_theme_from_config(self, config: dict):
        """从配置创建动态主题类

        基于当前模式的默认主题，覆盖用户自定义的值。

        Args:
            config: 用户自定义配置字典

        Returns:
            动态创建的主题类
        """
        # 选择基础主题类
        base_theme = DarkTheme if self._current_mode == ThemeMode.DARK else LightTheme

        # 创建动态类，继承基础主题
        class CustomTheme(base_theme):
            pass

        # 覆盖用户自定义的属性
        for key, value in config.items():
            if value is not None and value != "":
                setattr(CustomTheme, key, value)

        return CustomTheme

    @property
    def is_using_custom_theme(self) -> bool:
        """检查是否正在使用自定义主题"""
        return self._use_custom

    @property
    def custom_theme_config(self) -> dict:
        """获取当前自定义主题配置"""
        return self._custom_theme_config or {}


# 全局主题管理器实例
theme_manager = ThemeManager()
