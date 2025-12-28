"""
透明度感知Mixin

为组件提供透明度控制能力，与ThemeAwareMixin配合使用。
支持自动获取配置、生成透明样式、处理子组件透明度。
"""

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QScrollArea

from themes.transparency_tokens import OpacityTokens


class TransparencyAwareMixin:
    """透明度感知Mixin

    提供透明度控制的核心能力：
    - 自动获取组件透明度配置
    - 生成带透明度的背景样式
    - 支持透明度动态切换
    - 处理子组件透明背景

    使用方法：
    1. 在组件类中混入此Mixin（放在ThemeAware系列类之前）
    2. 设置 _transparency_component_id 类属性
    3. 在 __init__ 中调用 self._init_transparency_state()
    4. 在 _apply_theme() 中调用 self._apply_transparency()

    示例：
        class MySidebar(TransparencyAwareMixin, ThemeAwareWidget):
            _transparency_component_id = "sidebar"

            def __init__(self, parent=None):
                super().__init__(parent)
                self._init_transparency_state()
                self.setupUI()

            def _apply_theme(self):
                self._apply_transparency()

                if self._transparency_enabled:
                    bg_style = self._get_transparent_bg(
                        theme_manager.BG_SECONDARY,
                        border_color=theme_manager.BORDER_LIGHT
                    )
                    # 注意：不使用Python类名选择器，Qt不识别Python类名
                    # 直接设置样式
                    self.setStyleSheet(bg_style)
                    self._make_children_transparent()
                else:
                    self.setStyleSheet("background: transparent;")
    """

    # === 类属性（子类必须覆盖） ===

    # 组件透明度标识符，对应 OpacityTokens 中的组件名称
    # 例如: "sidebar", "header", "dialog", "card" 等
    _transparency_component_id: str = ""

    # === 实例属性（由 _init_transparency_state 初始化） ===

    # 透明效果是否启用
    _transparency_enabled: bool = False

    # 当前透明度值 (0.0-1.0)
    _current_opacity: float = 1.0

    # 透明度配置缓存（避免重复读取）
    _transparency_config_cache: Optional[dict] = None

    def _init_transparency_state(self):
        """初始化透明度状态

        必须在组件 __init__ 中调用，在 super().__init__() 之后。
        """
        self._transparency_enabled = False
        self._current_opacity = self._get_default_opacity()
        self._transparency_config_cache = None

    def _get_default_opacity(self) -> float:
        """获取组件默认透明度

        Returns:
            组件的默认透明度值
        """
        if not self._transparency_component_id:
            return OpacityTokens.FULL

        return OpacityTokens.get_component_opacity(self._transparency_component_id)

    def _get_theme_manager(self):
        """获取主题管理器实例

        延迟导入以避免循环引用。
        """
        from themes.theme_manager import theme_manager
        return theme_manager

    def _get_transparency_config(self) -> dict:
        """获取透明度配置

        直接从theme_manager获取最新配置，不使用本地缓存。
        这确保了透明度设置修改后立即生效。

        Returns:
            透明度配置字典
        """
        # 直接从theme_manager获取，不使用本地缓存
        # 这确保了热更新时总是读取最新配置
        theme_manager = self._get_theme_manager()
        return theme_manager.get_transparency_config()

    def _invalidate_transparency_cache(self):
        """使透明度配置缓存失效

        在配置变更后调用，下次访问时会重新读取。
        """
        self._transparency_config_cache = None

    def _is_transparency_enabled(self) -> bool:
        """检查透明效果是否启用

        透明效果启用条件：
        1. 全局透明效果开关打开
        2. 组件ID已设置

        Returns:
            透明效果是否启用
        """
        if not self._transparency_component_id:
            return False

        config = self._get_transparency_config()
        return config.get("enabled", False)

    def _is_system_blur_enabled(self) -> bool:
        """检查系统级模糊是否启用

        系统级模糊需要：
        1. 透明效果启用
        2. system_blur 开关打开

        Returns:
            系统级模糊是否启用
        """
        config = self._get_transparency_config()
        return config.get("enabled", False) and config.get("system_blur", False)

    def _get_current_opacity(self) -> float:
        """获取当前透明度值

        优先从配置中获取组件特定透明度，
        如果没有则使用组件默认透明度。

        Returns:
            当前透明度值 (0.0-1.0)
        """
        if not self._transparency_component_id:
            return OpacityTokens.FULL

        config = self._get_transparency_config()

        # 尝试获取组件特定配置
        config_key = f"{self._transparency_component_id}_opacity"
        if config_key in config:
            return config[config_key]

        # 回退到默认值
        return self._get_default_opacity()

    def _apply_transparency(self):
        """应用透明效果

        在 _apply_theme() 中调用此方法。
        会更新 _transparency_enabled 和 _current_opacity 状态。
        """
        # 使缓存失效，确保读取最新配置
        self._invalidate_transparency_cache()

        self._transparency_enabled = self._is_transparency_enabled()
        self._current_opacity = self._get_current_opacity()

        if self._transparency_enabled:
            self._enable_transparency()
        else:
            self._disable_transparency()

    def _enable_transparency(self):
        """启用透明效果

        只有在系统级模糊启用时才设置 WA_TranslucentBackground。
        否则，仅使用RGBA背景色实现半透明效果。
        """
        # 只有在系统级模糊启用时才设置Qt透明背景属性
        # 否则，仅使用RGBA背景色（不需要WA_TranslucentBackground）
        if self._is_system_blur_enabled() and hasattr(self, 'setAttribute'):
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def _disable_transparency(self):
        """禁用透明效果

        移除Qt透明背景属性。
        """
        if hasattr(self, 'setAttribute'):
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

    def _hex_to_rgba(self, hex_color: str, opacity: float) -> str:
        """将十六进制颜色转换为rgba格式

        Args:
            hex_color: 十六进制颜色（如 "#FFFFFF"）
            opacity: 透明度 (0.0-1.0)

        Returns:
            rgba颜色字符串
        """
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c * 2 for c in hex_color])

        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        return f"rgba({r}, {g}, {b}, {opacity})"

    def _get_transparent_bg(
        self,
        base_color: str,
        opacity: Optional[float] = None,
        border_color: Optional[str] = None,
        border_opacity: Optional[float] = None
    ) -> str:
        """生成透明背景样式

        Args:
            base_color: 基础背景色（十六进制，如 "#FFFFFF"）
            opacity: 透明度（None时使用组件配置值）
            border_color: 边框颜色（可选）
            border_opacity: 边框透明度（None时使用 BORDER_DEFAULT）

        Returns:
            CSS样式字符串（background-color 和可选的 border）

        示例：
            style = self._get_transparent_bg(
                theme_manager.BG_SECONDARY,
                border_color=theme_manager.BORDER_LIGHT
            )
            # 返回: "background-color: rgba(255, 255, 255, 0.85); border: 1px solid rgba(200, 200, 200, 0.3);"
        """
        # 确定透明度
        if opacity is None:
            opacity = self._current_opacity if self._transparency_enabled else 1.0

        # 生成背景色
        bg_rgba = self._hex_to_rgba(base_color, opacity)
        style = f"background-color: {bg_rgba};"

        # 生成边框（如果指定）
        if border_color:
            if border_opacity is None:
                border_opacity = OpacityTokens.BORDER_DEFAULT
            border_rgba = self._hex_to_rgba(border_color, border_opacity)
            style += f" border: 1px solid {border_rgba};"

        return style

    def _get_transparent_border(
        self,
        border_color: str,
        opacity: Optional[float] = None,
        width: str = "1px",
        style: str = "solid"
    ) -> str:
        """生成透明边框样式

        Args:
            border_color: 边框颜色（十六进制）
            opacity: 边框透明度（None时使用 BORDER_DEFAULT）
            width: 边框宽度
            style: 边框样式（solid, dashed, dotted等）

        Returns:
            CSS边框样式字符串
        """
        if opacity is None:
            opacity = OpacityTokens.BORDER_DEFAULT

        border_rgba = self._hex_to_rgba(border_color, opacity)
        return f"border: {width} {style} {border_rgba};"

    def _make_children_transparent(self):
        """使子组件背景透明

        处理滚动区域、容器等需要透明背景的子组件。
        在启用透明效果时调用。
        """
        if not hasattr(self, 'findChildren'):
            return

        # 是否启用系统级模糊
        use_system_blur = self._is_system_blur_enabled()

        # 处理滚动区域
        scroll_areas = self.findChildren(QScrollArea)
        for scroll_area in scroll_areas:
            scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: transparent;
                    border: none;
                }
                QScrollArea > QWidget > QWidget {
                    background-color: transparent;
                }
            """)

            # viewport 需要特殊处理
            if scroll_area.viewport():
                scroll_area.viewport().setStyleSheet("background-color: transparent;")
                # 只有系统级模糊启用时才设置WA_TranslucentBackground
                if use_system_blur:
                    scroll_area.viewport().setAttribute(
                        Qt.WidgetAttribute.WA_TranslucentBackground, True
                    )

    def _make_widget_transparent(self, widget: QWidget):
        """使单个组件背景透明

        Args:
            widget: 要设置透明的组件
        """
        if widget is None:
            return

        widget.setStyleSheet("background-color: transparent;")
        # 只有系统级模糊启用时才设置WA_TranslucentBackground
        if self._is_system_blur_enabled():
            widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def _get_overlay_bg(self, is_dark: bool = None) -> str:
        """获取遮罩层背景样式

        Args:
            is_dark: 是否深色模式（None时自动检测）

        Returns:
            CSS背景色样式字符串
        """
        if is_dark is None:
            theme_manager = self._get_theme_manager()
            is_dark = theme_manager.is_dark_mode()

        opacity = self._current_opacity if self._transparency_enabled else OpacityTokens.OVERLAY

        if is_dark:
            return f"background-color: rgba(0, 0, 0, {opacity});"
        else:
            return f"background-color: rgba(255, 255, 255, {opacity});"

    def _get_glass_effect_style(
        self,
        base_color: str,
        opacity: Optional[float] = None,
        border_radius: str = "8px"
    ) -> str:
        """获取毛玻璃效果样式

        Args:
            base_color: 基础背景色
            opacity: 透明度（None时使用 CARD_GLASS）
            border_radius: 圆角大小

        Returns:
            CSS样式字符串（包含背景、边框、圆角）
        """
        if opacity is None:
            opacity = OpacityTokens.CARD_GLASS if self._transparency_enabled else 1.0

        bg_rgba = self._hex_to_rgba(base_color, opacity)
        border_rgba = self._hex_to_rgba("#FFFFFF", OpacityTokens.BORDER_LIGHT)

        return f"""
            background-color: {bg_rgba};
            border: 1px solid {border_rgba};
            border-radius: {border_radius};
        """
