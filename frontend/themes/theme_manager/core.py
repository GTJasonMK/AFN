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
    """主题管理器 - 单例模式

    组合多个 Mixin 提供完整的主题管理功能：
    - ThemePropertiesMixin: 颜色和设计常量属性代理
    - ButtonStylesMixin: 按钮样式工厂方法
    - ComponentStylesMixin: 通用组件样式方法
    - BookStylesMixin: 书香风格专用方法
    """

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


# 全局主题管理器实例
theme_manager = ThemeManager()
