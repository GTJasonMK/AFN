"""
对话框样式辅助类

提供统一的对话框样式生成方法，减少代码重复。
所有方法都接受 object_name 参数以支持 Qt 的 object name selector。

职责边界：
- DialogStyles: 对话框组件专用（确认框、输入框、加载框等）
  - 使用 object_name 参数生成精确的 CSS 选择器
  - 关注对话框的容器、标题、按钮、输入框等元素

- ComponentStyles (themes/component_styles.py): 通用 UI 组件样式
  - 使用 QWidget 类选择器，适用于全局样式
  - 提供卡片、标签、徽章等基础组件样式

- BookThemeStyler (themes/book_theme_styler.py): 书香风格系统
  - 小说写作界面专用，缓存主题值以提高性能
  - 提供章节编辑器、版本卡片等专业样式
"""

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class DialogStyles:
    """对话框样式辅助类

    提供统一的对话框样式生成方法，减少代码重复。
    所有方法都接受 object_name 参数以支持 Qt 的 object name selector。
    """

    @staticmethod
    def container(object_name: str) -> str:
        """对话框容器样式"""
        return f"""
            #{object_name} {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(16)}px;
            }}
        """

    @staticmethod
    def title(object_name: str) -> str:
        """标题样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                font-size: {sp(17)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """

    @staticmethod
    def label(object_name: str) -> str:
        """提示文本样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
            }}
        """

    @staticmethod
    def message(object_name: str, padding_left: int = 0) -> str:
        """消息文本样式"""
        ui_font = theme_manager.ui_font()
        padding = f"padding-left: {dp(padding_left)}px;" if padding_left else ""
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                {padding}
                line-height: 1.5;
            }}
        """

    @staticmethod
    def input_field(object_name: str) -> str:
        """输入框样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(12)}px;
                font-size: {sp(14)}px;
            }}
            #{object_name}:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """

    @staticmethod
    def text_edit(object_name: str) -> str:
        """多行文本框样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: {dp(10)}px {dp(12)}px;
                font-size: {sp(14)}px;
            }}
            #{object_name}:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """

    @staticmethod
    def button_primary(object_name: str) -> str:
        """主要按钮样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            #{object_name}:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
            }}
            #{object_name}:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            #{object_name}:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def button_secondary(object_name: str) -> str:
        """次要按钮样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 500;
            }}
            #{object_name}:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.BORDER_DARK};
            }}
            #{object_name}:pressed {{
                background-color: {theme_manager.BORDER_LIGHT};
            }}
        """

    @staticmethod
    def button_danger(object_name: str) -> str:
        """危险按钮样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                background-color: {theme_manager.ERROR};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            #{object_name}:hover {{
                background-color: {theme_manager.ERROR_DARK};
            }}
            #{object_name}:pressed {{
                background-color: {theme_manager.ERROR_DARK};
            }}
        """

    @staticmethod
    def button_warning(object_name: str) -> str:
        """警告按钮样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                background-color: {theme_manager.WARNING};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            #{object_name}:hover {{
                background-color: {theme_manager.WARNING_DARK};
            }}
            #{object_name}:pressed {{
                background-color: {theme_manager.WARNING_DARK};
            }}
        """

    @staticmethod
    def icon(object_name: str, color: str, bg_color: str) -> str:
        """图标样式"""
        return f"""
            #{object_name} {{
                font-size: {sp(20)}px;
                font-weight: 700;
                color: {color};
                background-color: {bg_color};
                border-radius: {dp(16)}px;
            }}
        """

    @staticmethod
    def spin_box(object_name: str) -> str:
        """数字输入框样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(12)}px;
                font-size: {sp(14)}px;
            }}
            #{object_name}:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
            }}
            #{object_name}::up-button, #{object_name}::down-button {{
                width: {dp(24)}px;
                border: none;
                background-color: {theme_manager.BG_TERTIARY};
            }}
            #{object_name}::up-button:hover, #{object_name}::down-button:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
            #{object_name}::up-arrow {{
                image: none;
                border-left: {dp(5)}px solid transparent;
                border-right: {dp(5)}px solid transparent;
                border-bottom: {dp(6)}px solid {theme_manager.TEXT_SECONDARY};
            }}
            #{object_name}::down-arrow {{
                image: none;
                border-left: {dp(5)}px solid transparent;
                border-right: {dp(5)}px solid transparent;
                border-top: {dp(6)}px solid {theme_manager.TEXT_SECONDARY};
            }}
        """

    @staticmethod
    def spin_box_generic() -> str:
        """通用数字输入框样式（无object_name选择器）"""
        ui_font = theme_manager.ui_font()
        return f"""
            QSpinBox {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: 0 {dp(8)}px;
                font-size: {sp(14)}px;
            }}
            QSpinBox:focus {{
                border-color: {theme_manager.PRIMARY};
            }}
            QSpinBox:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_TERTIARY};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: {dp(20)}px;
                border: none;
                background-color: {theme_manager.BG_TERTIARY};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
        """

    @staticmethod
    def radio_button() -> str:
        """单选按钮样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            QRadioButton {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
                spacing: {dp(8)}px;
            }}
            QRadioButton::indicator {{
                width: {dp(18)}px;
                height: {dp(18)}px;
                border: 2px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(9)}px;
                background-color: {theme_manager.BG_SECONDARY};
            }}
            QRadioButton::indicator:checked {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY};
            }}
        """

    @staticmethod
    def hint_label(object_name: str) -> str:
        """提示标签样式（小字体）"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_TERTIARY};
                padding-left: {dp(4)}px;
            }}
        """

    @staticmethod
    def separator(object_name: str) -> str:
        """分隔线样式"""
        return f"""
            #{object_name} {{
                background-color: {theme_manager.BORDER_LIGHT};
            }}
        """

    @staticmethod
    def quick_button() -> str:
        """快捷按钮样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            QPushButton#quick_btn {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
            }}
            QPushButton#quick_btn:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                color: {theme_manager.PRIMARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """

    @staticmethod
    def preview_container(object_name: str) -> str:
        """预览区域容器样式"""
        return f"""
            #{object_name} {{
                background-color: {theme_manager.PRIMARY_PALE};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(8)}px;
            }}
        """

    @staticmethod
    def preview_label(object_name: str) -> str:
        """预览标签样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.PRIMARY};
                font-weight: 500;
            }}
        """

    @staticmethod
    def locked_label(object_name: str) -> str:
        """锁定标签样式"""
        ui_font = theme_manager.ui_font()
        return f"""
            #{object_name} {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                padding: {dp(8)}px {dp(12)}px;
                background-color: {theme_manager.BG_TERTIARY};
                border-radius: {dp(6)}px;
            }}
        """

    @staticmethod
    def scrollbar() -> str:
        """滚动条样式"""
        return theme_manager.scrollbar()

    # ==================== 书籍风格样式 ====================
    # 用于设置页面等需要书籍风格的对话框

    @staticmethod
    def book_dialog_background() -> str:
        """书籍风格对话框背景"""
        palette = theme_manager.get_book_palette()
        return f"""
            QDialog {{
                background-color: {palette.bg_primary};
            }}
        """

    @staticmethod
    def book_title(object_name: str) -> str:
        """书籍风格标题"""
        palette = theme_manager.get_book_palette()
        return f"""
            #{object_name} {{
                font-family: {palette.serif_font};
                font-size: {sp(24)}px;
                font-weight: 700;
                color: {palette.text_primary};
                padding-bottom: {dp(12)}px;
                border-bottom: 1px solid {palette.border_color};
            }}
        """

    @staticmethod
    def book_label(object_name: str) -> str:
        """书籍风格标签"""
        palette = theme_manager.get_book_palette()
        return f"""
            #{object_name} {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                color: {palette.text_secondary};
                font-weight: 500;
            }}
        """

    @staticmethod
    def book_hint(object_name: str) -> str:
        """书籍风格提示文字"""
        palette = theme_manager.get_book_palette()
        return f"""
            #{object_name} {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_tertiary};
                font-style: italic;
                margin-top: {dp(4)}px;
            }}
        """

    @staticmethod
    def book_input() -> str:
        """书籍风格输入框（通用）"""
        palette = theme_manager.get_book_palette()
        return f"""
            QLineEdit {{
                font-family: {palette.ui_font};
                background-color: {palette.bg_secondary};
                color: {palette.text_primary};
                padding: {dp(10)}px {dp(14)}px;
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                font-size: {sp(14)}px;
            }}
            QLineEdit:focus {{
                border: 1px solid {palette.accent_color};
                background-color: {palette.bg_primary};
            }}
            QLineEdit::placeholder {{
                color: {palette.text_tertiary};
            }}
            QLineEdit:disabled {{
                background-color: {palette.bg_primary};
                color: {palette.text_tertiary};
            }}
        """

    @staticmethod
    def book_combobox() -> str:
        """书籍风格下拉框"""
        palette = theme_manager.get_book_palette()
        return f"""
            QComboBox {{
                font-family: {palette.ui_font};
                background-color: {palette.bg_secondary};
                color: {palette.text_primary};
                padding: {dp(10)}px {dp(14)}px;
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                font-size: {sp(14)}px;
            }}
            QComboBox:focus {{
                border: 1px solid {palette.accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {dp(8)}px;
            }}
            QComboBox::down-arrow {{
                width: {dp(12)}px;
                height: {dp(12)}px;
            }}
            QComboBox QAbstractItemView {{
                font-family: {palette.ui_font};
                background-color: {palette.bg_primary};
                color: {palette.text_primary};
                border: 1px solid {palette.border_color};
                selection-background-color: {palette.accent_color};
                selection-color: {palette.bg_primary};
            }}
        """

    @staticmethod
    def book_spinbox() -> str:
        """书籍风格数字输入框"""
        palette = theme_manager.get_book_palette()
        return f"""
            QSpinBox {{
                font-family: {palette.ui_font};
                background-color: {palette.bg_secondary};
                color: {palette.text_primary};
                padding: {dp(10)}px {dp(14)}px;
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                font-size: {sp(14)}px;
            }}
            QSpinBox:focus {{
                border: 1px solid {palette.accent_color};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: {dp(20)}px;
                background-color: transparent;
                border: none;
                border-radius: {dp(4)}px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {palette.border_color};
            }}
        """

    @staticmethod
    def book_button_cancel() -> str:
        """书籍风格取消按钮"""
        palette = theme_manager.get_book_palette()
        return f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14)}px;
                min-width: {dp(80)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
                background-color: {palette.bg_secondary};
            }}
        """

    @staticmethod
    def book_button_save() -> str:
        """书籍风格保存按钮"""
        palette = theme_manager.get_book_palette()
        return f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
                min-width: {dp(80)}px;
            }}
            QPushButton:hover {{
                background-color: {palette.text_primary};
            }}
            QPushButton:pressed {{
                background-color: {palette.accent_light};
            }}
        """

    @staticmethod
    def book_info_card() -> str:
        """书籍风格信息卡片"""
        palette = theme_manager.get_book_palette()
        return f"""
            QLabel {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_secondary};
                background-color: {palette.bg_secondary};
                padding: {dp(12)}px;
                border-radius: {dp(8)}px;
                border: 1px dashed {palette.border_color};
            }}
        """
