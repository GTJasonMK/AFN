"""
颜色选择器组件

提供16进制颜色输入和可视化选择功能。
"""

import re
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QColorDialog
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class ColorPickerWidget(QWidget):
    """颜色选择器组件

    布局：
    ┌─────────────────────────────────────┐
    │ [████] [#8B4513        ] [选择...]  │
    └─────────────────────────────────────┘

    - 左侧颜色预览块
    - 中间16进制颜色输入框
    - 右侧选择按钮弹出QColorDialog
    """

    # 颜色变更信号
    color_changed = pyqtSignal(str)

    # 16进制颜色正则（支持3/6/8位）
    HEX_COLOR_PATTERN = re.compile(r'^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$')

    def __init__(self, parent: Optional[QWidget] = None, initial_color: str = "#000000"):
        super().__init__(parent)
        self._color = initial_color
        self._is_valid = True
        self._create_ui()
        self._apply_theme()
        self._update_preview()

        # 监听主题变化
        theme_manager.theme_changed.connect(self._apply_theme)

    def _create_ui(self):
        """创建UI结构"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))

        # 颜色预览块
        self.preview_btn = QPushButton()
        self.preview_btn.setFixedSize(dp(32), dp(32))
        self.preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_btn.clicked.connect(self._open_color_dialog)
        layout.addWidget(self.preview_btn)

        # 颜色输入框
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("#RRGGBB")
        self.color_input.setMaxLength(9)  # 最多#RRGGBBAA
        self.color_input.setText(self._color)
        self.color_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.color_input, stretch=1)

        # 选择按钮
        self.pick_btn = QPushButton("选择")
        self.pick_btn.setFixedWidth(dp(56))
        self.pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick_btn.clicked.connect(self._open_color_dialog)
        layout.addWidget(self.pick_btn)

    def _apply_theme(self):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # 输入框样式
        self.color_input.setStyleSheet(f"""
            QLineEdit {{
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: {sp(13)}px;
                color: {palette.text_primary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QLineEdit:focus {{
                border-color: {palette.accent_color};
            }}
            QLineEdit[valid="false"] {{
                border-color: {theme_manager.ERROR};
                background-color: {theme_manager.ERROR_BG};
            }}
        """)

        # 选择按钮样式
        self.pick_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_secondary};
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """)

        self._update_preview()

    def _update_preview(self):
        """更新颜色预览块"""
        color = self._color if self._is_valid else "#CCCCCC"
        palette = theme_manager.get_book_palette()

        self.preview_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
            }}
            QPushButton:hover {{
                border-color: {palette.accent_color};
            }}
        """)

    def _on_text_changed(self, text: str):
        """输入框文本变更处理"""
        # 验证格式
        text = text.strip()
        if not text.startswith('#'):
            text = '#' + text

        self._is_valid = bool(self.HEX_COLOR_PATTERN.match(text))

        # 更新属性（用于样式选择器）
        self.color_input.setProperty("valid", "true" if self._is_valid else "false")
        self.color_input.style().unpolish(self.color_input)
        self.color_input.style().polish(self.color_input)

        if self._is_valid:
            self._color = text
            self._update_preview()
            self.color_changed.emit(self._color)

    def _open_color_dialog(self):
        """打开颜色选择对话框"""
        initial = QColor(self._color) if self._is_valid else QColor("#000000")

        # 支持Alpha通道
        color = QColorDialog.getColor(
            initial,
            self,
            "选择颜色",
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )

        if color.isValid():
            # 如果有Alpha值且不是255，使用8位格式
            if color.alpha() < 255:
                hex_color = color.name(QColor.NameFormat.HexArgb)
            else:
                hex_color = color.name(QColor.NameFormat.HexRgb)

            self.color_input.setText(hex_color.upper())

    def get_color(self) -> str:
        """获取当前颜色值"""
        return self._color if self._is_valid else ""

    def set_color(self, color: str):
        """设置颜色值"""
        if color:
            self.color_input.setText(color)

    def is_valid(self) -> bool:
        """检查颜色值是否有效"""
        return self._is_valid

    # 属性接口
    color = property(get_color, set_color)
