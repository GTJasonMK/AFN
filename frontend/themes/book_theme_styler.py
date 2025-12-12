"""
书香风格样式器 - 统一管理书香主题的样式生成

解决问题：
- 减少各组件中重复调用 theme_manager.book_* 方法
- 缓存主题值，避免频繁查询
- 提供统一的样式生成接口

职责边界：
- BookThemeStyler: 书香风格系统（本模块）
  - 小说写作界面专用，缓存主题值以提高性能
  - 提供章节编辑器、版本卡片等专业样式
  - 使用 object_name 参数以支持复杂布局

- ComponentStyles (themes/component_styles.py): 通用 UI 组件样式
  - 使用 QWidget 类选择器，适用于全局样式
  - 提供卡片、标签、徽章等基础组件样式

- DialogStyles (components/dialogs/styles.py): 对话框组件专用
  - 使用 object_name 参数生成精确的 CSS 选择器
  - 关注对话框的容器、标题、按钮、输入框等元素

用法示例：
    from themes.book_theme_styler import BookThemeStyler

    class MyComponent(ThemeAwareWidget):
        def __init__(self):
            self._styler = BookThemeStyler()
            super().__init__()

        def _apply_theme(self):
            self._styler.refresh()  # 刷新缓存的主题值
            self.card.setStyleSheet(self._styler.card_style("my_card"))
            self.label.setStyleSheet(self._styler.text_style("my_label"))
"""

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class BookThemeStyler:
    """书香风格样式器

    缓存书香主题的所有颜色值，并提供常用样式的生成方法。
    在主题切换时调用 refresh() 更新缓存。

    设计原则：
    - 单一职责：只负责书香风格的样式生成
    - 缓存优化：减少重复的 theme_manager 调用
    - 统一接口：提供一致的样式生成方法
    """

    def __init__(self):
        """初始化样式器并加载当前主题值"""
        self.refresh()

    def refresh(self):
        """刷新缓存的主题值

        在主题切换时调用此方法更新所有缓存的颜色值。
        """
        # 背景色
        self.bg_primary = theme_manager.book_bg_primary()
        self.bg_secondary = theme_manager.book_bg_secondary()
        self.bg_card = theme_manager.BG_CARD

        # 文本色
        self.text_primary = theme_manager.book_text_primary()
        self.text_secondary = theme_manager.book_text_secondary()
        self.text_tertiary = theme_manager.book_text_tertiary()

        # 边框和强调色
        self.border_color = theme_manager.book_border_color()
        self.accent_color = theme_manager.book_accent_color()

        # 字体
        self.ui_font = theme_manager.ui_font()
        self.serif_font = theme_manager.serif_font()

        # 语义色
        self.success = theme_manager.SUCCESS
        self.error = theme_manager.ERROR
        self.warning = theme_manager.WARNING
        self.info = theme_manager.INFO

        # 语义色文本
        self.text_success = theme_manager.text_success()
        self.text_error = theme_manager.text_error()
        self.text_warning = theme_manager.text_warning()
        self.text_info = theme_manager.text_info()

        # 语义色背景
        self.success_bg = theme_manager.SUCCESS_BG
        self.error_bg = theme_manager.ERROR_BG
        self.warning_bg = theme_manager.WARNING_BG
        self.info_bg = theme_manager.INFO_BG

        # 主题色
        self.primary = theme_manager.PRIMARY
        self.primary_pale = theme_manager.PRIMARY_PALE
        self.button_text = theme_manager.BUTTON_TEXT

        # 其他常用值
        self.border_default = theme_manager.BORDER_DEFAULT
        self.border_light = theme_manager.BORDER_LIGHT

    # ==================== 卡片样式 ====================

    def card_style(self, object_name: str, with_hover: bool = False) -> str:
        """生成卡片样式

        Args:
            object_name: QSS对象名称
            with_hover: 是否包含hover效果

        Returns:
            QSS样式字符串
        """
        base = f"""
            QFrame#{object_name} {{
                background-color: {self.bg_secondary};
                border: 1px solid {self.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(12)}px;
            }}
        """
        if with_hover:
            base += f"""
            QFrame#{object_name}:hover {{
                border-color: {self.accent_color};
            }}
            """
        return base

    def card_style_flat(self, object_name: str) -> str:
        """生成扁平卡片样式（无边框）"""
        return f"""
            QFrame#{object_name} {{
                background-color: {self.bg_secondary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(12)}px;
            }}
        """

    def card_style_accent(self, object_name: str, border_width: int = 3) -> str:
        """生成带强调边框的卡片样式"""
        return f"""
            QFrame#{object_name} {{
                background-color: {self.bg_secondary};
                border-left: {dp(border_width)}px solid {self.accent_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
            }}
        """

    # ==================== 文本样式 ====================

    def text_style(self, object_name: str, size: int = 14, weight: str = "normal",
                   color: str = None, use_serif: bool = False) -> str:
        """生成文本样式

        Args:
            object_name: QSS对象名称
            size: 字体大小（sp单位）
            weight: 字重 (normal/bold/600等)
            color: 颜色（默认使用text_primary）
            use_serif: 是否使用衬线字体

        Returns:
            QSS样式字符串
        """
        font = self.serif_font if use_serif else self.ui_font
        text_color = color or self.text_primary
        return f"""
            #{object_name} {{
                font-family: {font};
                font-size: {sp(size)}px;
                font-weight: {weight};
                color: {text_color};
            }}
        """

    def title_style(self, object_name: str, size: int = 16) -> str:
        """生成标题样式"""
        return self.text_style(object_name, size=size, weight="600", use_serif=True)

    def subtitle_style(self, object_name: str, size: int = 14) -> str:
        """生成副标题样式"""
        return self.text_style(object_name, size=size, weight="500",
                               color=self.text_secondary)

    def label_style(self, object_name: str, size: int = 12) -> str:
        """生成标签样式（小字体）"""
        return self.text_style(object_name, size=size, weight="600",
                               color=self.text_secondary)

    def hint_style(self, object_name: str, size: int = 11) -> str:
        """生成提示文本样式"""
        return self.text_style(object_name, size=size, weight="normal",
                               color=self.text_tertiary)

    # ==================== 信息卡片样式 ====================

    def info_card_style(self, object_name: str, card_type: str = "info") -> str:
        """生成信息卡片样式（带左边框）

        Args:
            object_name: QSS对象名称
            card_type: 卡片类型 (info/success/warning/error)

        Returns:
            QSS样式字符串
        """
        type_colors = {
            "info": (self.info, self.info_bg),
            "success": (self.success, self.success_bg),
            "warning": (self.warning, self.warning_bg),
            "error": (self.error, self.error_bg),
        }
        border_color, bg_color = type_colors.get(card_type, (self.info, self.info_bg))

        return f"""
            QFrame#{object_name} {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-left: 4px solid {border_color};
                border-radius: {dp(4)}px;
                padding: {dp(12)}px;
            }}
        """

    # ==================== 标签/徽章样式 ====================

    def tag_style(self, tag_type: str = "default") -> str:
        """生成标签样式（无object_name，用于动态创建的标签）

        Args:
            tag_type: 标签类型 (default/character/location/item/keyword/tag)

        Returns:
            QSS样式字符串
        """
        type_colors = {
            "character": self.success,
            "location": self.info,
            "item": self.warning,
            "keyword": self.accent_color,
            "tag": self.primary,
            "default": self.border_color,
        }
        tag_border = type_colors.get(tag_type, self.border_color)

        return f"""
            font-family: {self.ui_font};
            font-size: {sp(12)}px;
            color: {self.text_secondary};
            background-color: transparent;
            border: 1px solid {tag_border};
            border-radius: {dp(4)}px;
            padding: {dp(4)}px {dp(8)}px;
        """

    # ==================== 按钮样式 ====================

    def button_primary_style(self, object_name: str) -> str:
        """生成主要按钮样式"""
        return f"""
            QPushButton#{object_name} {{
                font-family: {self.ui_font};
                background-color: {self.accent_color};
                color: {self.button_text};
                border: 1px solid {self.accent_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(16)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            QPushButton#{object_name}:hover {{
                background-color: {self.text_primary};
                border-color: {self.text_primary};
            }}
            QPushButton#{object_name}:disabled {{
                background-color: {self.border_color};
                color: {self.text_tertiary};
            }}
        """

    def button_secondary_style(self, object_name: str) -> str:
        """生成次要按钮样式"""
        return f"""
            QPushButton#{object_name} {{
                font-family: {self.ui_font};
                background-color: transparent;
                color: {self.text_primary};
                border: 1px solid {self.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(16)}px;
                font-size: {sp(14)}px;
            }}
            QPushButton#{object_name}:hover {{
                color: {self.accent_color};
                border-color: {self.accent_color};
                background-color: rgba(0,0,0,0.05);
            }}
        """

    # ==================== 滚动条样式 ====================

    def scrollbar_style(self) -> str:
        """获取滚动条样式"""
        return theme_manager.scrollbar()

    # ==================== 输入框样式 ====================

    def input_style(self, object_name: str) -> str:
        """生成输入框样式"""
        return f"""
            #{object_name} {{
                font-family: {self.ui_font};
                background-color: {self.bg_secondary};
                color: {self.text_primary};
                border: 1px solid {self.border_default};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(12)}px;
                font-size: {sp(14)}px;
            }}
            #{object_name}:focus {{
                border-color: {self.accent_color};
                background-color: {self.bg_primary};
            }}
        """

    def text_edit_style(self, object_name: str) -> str:
        """生成多行文本框样式"""
        return f"""
            QTextEdit#{object_name} {{
                font-family: {self.serif_font};
                background-color: {self.bg_secondary};
                color: {self.text_primary};
                border: 1px solid {self.border_default};
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(12)}px;
                font-size: {sp(14)}px;
                line-height: 1.6;
            }}
            QTextEdit#{object_name}:focus {{
                border-color: {self.accent_color};
            }}
            {self.scrollbar_style()}
        """

    # ==================== 复合样式（组合多个组件） ====================

    def section_header_style(self, icon_name: str, title_name: str) -> tuple:
        """生成分区头部样式（图标+标题）

        Returns:
            (icon_style, title_style) 元组
        """
        icon_style = f"""
            #{icon_name} {{
                font-size: {sp(16)}px;
                color: {self.accent_color};
            }}
        """
        title_style = f"""
            #{title_name} {{
                font-family: {self.ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {self.text_primary};
            }}
        """
        return icon_style, title_style


# 全局单例（可选使用）
_global_styler = None


def get_book_styler() -> BookThemeStyler:
    """获取全局BookThemeStyler单例

    注意：使用全局单例时，需要在主题切换时调用 refresh()。
    建议在组件中创建自己的实例，或在 _apply_theme 中调用 get_book_styler().refresh()。
    """
    global _global_styler
    if _global_styler is None:
        _global_styler = BookThemeStyler()
    return _global_styler
