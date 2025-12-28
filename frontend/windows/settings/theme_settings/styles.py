"""
主题设置样式Mixin

负责应用主题样式到各UI组件。
"""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QGroupBox, QScrollArea, QLineEdit, QWidget

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

from .config_groups import CONFIG_GROUPS

if TYPE_CHECKING:
    from .widget import ThemeSettingsWidget


class ThemeStylesMixin:
    """
    主题样式Mixin

    负责：
    - 应用主题样式到各UI组件
    - 处理样式变化响应
    """

    def _apply_theme(self: "ThemeSettingsWidget"):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # 工具提示样式（全局）
        self.setStyleSheet(f"""
            QToolTip {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_primary};
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(10)}px;
            }}
        """)

        # Tab样式
        self.mode_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
            }}
            QTabBar::tab {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                padding: {dp(12)}px {dp(24)}px;
                margin-right: {dp(8)}px;
            }}
            QTabBar::tab:hover {{
                color: {palette.text_primary};
            }}
            QTabBar::tab:selected {{
                color: {palette.accent_color};
                border-bottom: 2px solid {palette.accent_color};
            }}
        """)

        # 提示横幅样式
        if hasattr(self, 'hint_banner') and self.hint_banner:
            self.hint_banner.setStyleSheet(f"""
                QFrame#hint_banner {{
                    background-color: {theme_manager.INFO_BG};
                    border: 1px solid {theme_manager.INFO};
                    border-radius: {dp(6)}px;
                }}
                QLabel#hint_icon {{
                    font-family: {palette.ui_font};
                    font-size: {sp(12)}px;
                    font-weight: bold;
                    color: {theme_manager.INFO};
                    background-color: transparent;
                    border: 1px solid {theme_manager.INFO};
                    border-radius: {dp(10)}px;
                }}
                QLabel#hint_text {{
                    font-family: {palette.ui_font};
                    font-size: {sp(12)}px;
                    color: {palette.text_secondary};
                    background-color: transparent;
                }}
            """)

        # 左侧面板
        self.findChild(QFrame, "left_panel").setStyleSheet(f"""
            QFrame#left_panel {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
            }}
        """)

        # 新建按钮
        self.new_btn.setStyleSheet(f"""
            QPushButton#new_theme_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.accent_color};
                background-color: transparent;
                border: 1px dashed {palette.accent_color};
                border-radius: {dp(4)}px;
                padding: {dp(10)}px;
            }}
            QPushButton#new_theme_btn:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
        """)

        # 配置列表
        self.config_list.setStyleSheet(f"""
            QListWidget#config_list {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#config_list::item {{
                color: {palette.text_secondary};
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(10)}px;
                margin: {dp(2)}px 0;
            }}
            QListWidget#config_list::item:hover {{
                color: {palette.text_primary};
                background-color: {theme_manager.PRIMARY_PALE};
            }}
            QListWidget#config_list::item:selected {{
                color: {palette.accent_color};
                background-color: {palette.bg_primary};
                font-weight: 500;
            }}
        """)

        # 列表操作按钮
        list_btn_style = f"""
            QPushButton#list_action_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
            }}
            QPushButton#list_action_btn:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """
        self.duplicate_btn.setStyleSheet(list_btn_style)
        self.delete_btn.setStyleSheet(list_btn_style)

        # 右侧面板
        self.findChild(QFrame, "right_panel").setStyleSheet(f"""
            QFrame#right_panel {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
            }}
        """)

        # 滚动区域
        scroll = self.findChild(QScrollArea, "config_scroll")
        if scroll:
            scroll.setStyleSheet(f"""
                QScrollArea#config_scroll {{
                    background-color: transparent;
                    border: none;
                }}
                QScrollBar:vertical {{
                    background-color: {palette.bg_primary};
                    width: {dp(8)}px;
                    border-radius: {dp(4)}px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: {palette.border_color};
                    border-radius: {dp(4)}px;
                    min-height: {dp(30)}px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: {palette.accent_color};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0;
                }}
            """)

        # 滚动内容区域背景
        scroll_content = self.findChild(QWidget, "scroll_content")
        if scroll_content:
            scroll_content.setStyleSheet(f"""
                QWidget#scroll_content {{
                    background-color: {palette.bg_secondary};
                }}
            """)

        # 配置名称标签
        name_label = self.config_layout.itemAt(0)
        if name_label and name_label.layout():
            label_widget = name_label.layout().itemAt(0)
            if label_widget and label_widget.widget():
                label_widget.widget().setStyleSheet(f"""
                    QLabel {{
                        font-family: {palette.ui_font};
                        font-size: {sp(14)}px;
                        color: {palette.text_primary};
                        background-color: transparent;
                    }}
                """)

        # 配置名称输入
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                color: {palette.text_primary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(12)}px;
            }}
            QLineEdit:focus {{
                border-color: {palette.accent_color};
            }}
        """)

        # 配置组样式
        group_style = f"""
            QGroupBox {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {palette.text_primary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                margin-top: {dp(12)}px;
                padding-top: {dp(8)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {dp(12)}px;
                padding: 0 {dp(8)}px;
                background-color: {palette.bg_secondary};
            }}
            QLabel#field_label {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
            }}
        """
        for group_key in CONFIG_GROUPS:
            group_box = self.findChild(QGroupBox, f"group_{group_key}")
            if group_box:
                group_box.setStyleSheet(group_style)

        # 文本类型输入框样式（阴影颜色、遮罩颜色等）
        text_input_style = f"""
            QLineEdit#text_field_input {{
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: {sp(13)}px;
                color: {palette.text_primary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QLineEdit#text_field_input:focus {{
                border-color: {palette.accent_color};
            }}
        """
        for text_input in self.findChildren(QLineEdit, "text_field_input"):
            text_input.setStyleSheet(text_input_style)

        # 底部操作栏
        self.findChild(QFrame, "bottom_bar").setStyleSheet(f"""
            QFrame#bottom_bar {{
                background-color: {palette.bg_primary};
                border-top: 1px solid {palette.border_color};
            }}
        """)

        # 重置按钮
        self.reset_btn.setStyleSheet(f"""
            QPushButton#reset_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
            }}
            QPushButton#reset_btn:hover {{
                color: {theme_manager.WARNING};
                border-color: {theme_manager.WARNING};
            }}
        """)

        # 导入导出按钮样式
        io_btn_style = f"""
            QPushButton {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """
        self.import_btn.setStyleSheet(io_btn_style)
        self.export_btn.setStyleSheet(io_btn_style)

        # 保存按钮
        self.save_btn.setStyleSheet(f"""
            QPushButton#save_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.accent_color};
                background-color: transparent;
                border: 1px solid {palette.accent_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(20)}px;
            }}
            QPushButton#save_btn:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
        """)

        # 激活按钮
        self.activate_btn.setStyleSheet(f"""
            QPushButton#activate_btn {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.BUTTON_TEXT};
                background-color: {palette.accent_color};
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(20)}px;
            }}
            QPushButton#activate_btn:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)


__all__ = [
    "ThemeStylesMixin",
]
