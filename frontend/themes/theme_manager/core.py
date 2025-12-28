"""
ThemeManager 核心类

主题管理器的核心实现，组合所有 Mixin 类。
支持两种配置格式：
- V1（旧版）：面向常量的配置
- V2（新版）：面向组件的配置

性能优化：
- 信号防抖：多次连续调用只发射一次信号
- 静默模式：允许批量更新配置后一次性刷新
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .themes import ThemeMode, LightTheme, DarkTheme
from .properties_mixin import ThemePropertiesMixin
from .button_styles_mixin import ButtonStylesMixin
from .component_styles_mixin import ComponentStylesMixin
from .book_styles_mixin import BookStylesMixin
from .v2_config_mixin import V2ConfigMixin

if TYPE_CHECKING:
    from utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ThemeManager(
    ThemePropertiesMixin,
    ButtonStylesMixin,
    ComponentStylesMixin,
    BookStylesMixin,
    V2ConfigMixin,
    QObject
):
    """主题管理器

    组合多个 Mixin 提供完整的主题管理功能：
    - ThemePropertiesMixin: 颜色和设计常量属性代理（V1兼容）
    - ButtonStylesMixin: 按钮样式工厂方法
    - ComponentStylesMixin: 通用组件样式方法
    - BookStylesMixin: 书香风格专用方法
    - V2ConfigMixin: V2面向组件的配置访问（新增）

    使用模块级单例模式，通过 theme_manager 变量访问全局实例。

    支持自定义主题：
    - apply_custom_theme(): 应用V1格式用户自定义配置
    - apply_v2_config(): 应用V2格式用户自定义配置（新增）
    - reset_to_default(): 重置为内置默认主题
    """

    theme_changed = pyqtSignal(str)  # 主题切换信号

    def __init__(self):
        """初始化主题管理器"""
        # 使用协作式多重继承，super().__init__() 会按 MRO 顺序调用所有父类的 __init__
        super().__init__()

        self._current_mode = ThemeMode.LIGHT
        self._current_theme = LightTheme
        self._config_manager = None
        # 自定义主题支持（V1）
        self._custom_theme_config = None  # 自定义配置字典
        self._use_custom = False          # 是否使用V1自定义主题
        # 透明度配置缓存
        self._transparency_config_cache = None

        # 信号防抖机制：避免短时间内多次发射信号导致UI重复刷新
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(50)  # 50ms防抖间隔
        self._debounce_timer.timeout.connect(self._do_emit_theme_changed)
        self._pending_theme_signal = None  # 待发射的主题模式值
        self._silent_mode = False  # 静默模式：批量更新时不发射信号

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
        # 使透明度缓存失效，确保下次读取时从config_manager加载
        self._invalidate_transparency_cache()

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

        # 发射主题切换信号（使用防抖）
        self._emit_theme_changed(mode.value)

    def is_dark_mode(self):
        """判断是否为深色模式"""
        return self._current_mode == ThemeMode.DARK

    def is_light_mode(self):
        """判断是否为亮色模式"""
        return self._current_mode == ThemeMode.LIGHT

    # ==================== 信号防抖机制 ====================

    def _emit_theme_changed(self, mode_value: str = None):
        """发射主题切换信号（带防抖）

        多次连续调用只会在防抖间隔后发射一次信号。

        Args:
            mode_value: 主题模式值，默认使用当前模式
        """
        if self._silent_mode:
            return

        self._pending_theme_signal = mode_value or self._current_mode.value
        # 重启防抖计时器（如果已在计时，会重置）
        self._debounce_timer.start()

    def _do_emit_theme_changed(self):
        """实际发射主题切换信号（由防抖计时器调用）"""
        if self._pending_theme_signal is not None:
            self.theme_changed.emit(self._pending_theme_signal)
            self._pending_theme_signal = None

    def begin_batch_update(self):
        """开始批量更新（进入静默模式）

        在批量更新期间，所有主题变更都不会立即发射信号。
        调用 end_batch_update() 后统一刷新一次。

        用法:
            theme_manager.begin_batch_update()
            try:
                theme_manager.apply_custom_theme(config)
                theme_manager.set_transparency_config(config)
            finally:
                theme_manager.end_batch_update()
        """
        self._silent_mode = True
        # 停止任何待处理的防抖计时器
        self._debounce_timer.stop()
        self._pending_theme_signal = None

    def end_batch_update(self):
        """结束批量更新（退出静默模式并发射一次信号）"""
        self._silent_mode = False
        # 立即发射一次信号刷新UI
        self.theme_changed.emit(self._current_mode.value)

    def apply_custom_theme(self, config: dict, save: bool = True):
        """应用自定义主题配置（V1格式）

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
        # 重置V2配置（V1/V2互斥）
        self._v2_config = None
        self._use_v2 = False

        # 应用V1配置
        self._custom_theme_config = config
        self._use_custom = True

        # 创建动态主题类
        self._current_theme = self._create_theme_from_config(config)

        # 发射主题切换信号（使用防抖）
        self._emit_theme_changed()

    def reset_to_default(self):
        """重置为默认主题（同时清除 V1 和 V2 自定义配置）"""
        # 重置 V1 自定义配置
        self._use_custom = False
        self._custom_theme_config = None

        # 重置 V2 配置
        self.reset_v2_config()

        # 恢复为内置主题
        self._current_theme = DarkTheme if self._current_mode == ThemeMode.DARK else LightTheme

        # 发射主题切换信号（使用防抖）
        self._emit_theme_changed()

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

    # ==================== 透明效果配置 ====================

    # 组件透明度默认值（与OpacityTokens保持一致）
    _DEFAULT_OPACITY_CONFIG = {
        "enabled": False,
        "system_blur": False,
        "master_opacity": 1.0,  # 主控透明度系数，与所有组件透明度相乘
        # 布局组件
        "sidebar_opacity": 0.85,
        "header_opacity": 0.90,
        "content_opacity": 0.95,
        # 浮层组件
        "dialog_opacity": 0.95,
        "modal_opacity": 0.92,
        "dropdown_opacity": 0.95,
        "tooltip_opacity": 0.90,
        "popover_opacity": 0.92,
        # 卡片组件
        "card_opacity": 0.95,
        "card_glass_opacity": 0.85,
        # 反馈组件
        "overlay_opacity": 0.50,
        "loading_opacity": 0.85,
        "toast_opacity": 0.95,
        # 输入组件
        "input_opacity": 0.98,
        "button_opacity": 1.00,
    }

    def get_transparency_config(self) -> dict:
        """获取透明效果配置（统一处理V1和V2）

        使用缓存避免重复读取配置。如果使用V2配置，从组件配置中提取透明设置；
        否则从ConfigManager中获取。

        Returns:
            dict: 透明效果配置字典，包含:
                - enabled: 是否启用透明效果
                - system_blur: 是否启用系统级模糊（仅Windows）
                - {component_id}_opacity: 各组件的透明度值（15个组件）
        """
        # 使用缓存
        if self._transparency_config_cache is not None:
            return self._transparency_config_cache

        # 透明度配置始终从本地ConfigManager读取，不使用V2配置
        # （透明度是本地设置，不同步到后端）
        if self._config_manager is None:
            # 返回默认配置
            config = self._DEFAULT_OPACITY_CONFIG.copy()
        else:
            config = self._config_manager.get_transparency_config()

        # 缓存配置
        self._transparency_config_cache = config
        return config

    def _invalidate_transparency_cache(self):
        """使透明度配置缓存失效"""
        self._transparency_config_cache = None

    def set_transparency_config(self, config: dict):
        """保存透明效果配置（仅持久化，不刷新UI）

        只负责将配置保存到本地存储，不发射信号。
        如需刷新UI，请调用 apply_transparency()。

        Args:
            config: 透明效果配置字典
        """
        # 更新缓存
        self._transparency_config_cache = config.copy()

        # 持久化到本地存储
        if self._config_manager is not None:
            self._config_manager.set_transparency_config(config)

    def apply_transparency(self):
        """应用透明效果（刷新UI）

        发射主题切换信号，触发所有组件刷新透明效果。
        """
        # 发射主题切换信号以刷新UI（使用防抖）
        self._emit_theme_changed()

    def is_transparency_enabled(self) -> bool:
        """检查透明效果是否启用"""
        return self.get_transparency_config().get("enabled", False)

    def reset_transparency_config(self):
        """重置透明效果配置为默认值"""
        # 使缓存失效
        self._invalidate_transparency_cache()

        if self._config_manager is not None:
            self._config_manager.reset_transparency_config()

        # 发射主题切换信号以刷新UI（使用防抖）
        self._emit_theme_changed()


# 全局主题管理器实例
theme_manager = ThemeManager()
