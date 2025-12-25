"""
尺寸输入组件

提供数值+单位的输入功能，支持px/em/%/ms等单位。
"""

import re
from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QComboBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QDoubleValidator

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class SizeInputWidget(QWidget):
    """尺寸输入组件

    布局：
    ┌─────────────────────────┐
    │ [24      ] [px ▼]       │
    └─────────────────────────┘

    - 数值输入框（支持小数）
    - 单位选择下拉框
    """

    # 值变更信号
    value_changed = pyqtSignal(str)

    # 支持的单位列表
    UNITS = ["px", "em", "rem", "%", "ms", "s", "vw", "vh"]

    # 解析尺寸值正则
    SIZE_PATTERN = re.compile(r'^(-?\d+(?:\.\d+)?)\s*(px|em|rem|%|ms|s|vw|vh)?$', re.IGNORECASE)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_value: str = "",
        allowed_units: Optional[list] = None
    ):
        """初始化尺寸输入组件

        Args:
            parent: 父组件
            initial_value: 初始值，如"24px"
            allowed_units: 允许的单位列表，None表示使用默认所有单位
        """
        super().__init__(parent)
        self._allowed_units = allowed_units or self.UNITS
        self._create_ui()
        self._apply_theme()

        if initial_value:
            self.set_value(initial_value)

        # 监听主题变化
        theme_manager.theme_changed.connect(self._apply_theme)

    def _create_ui(self):
        """创建UI结构"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        # 数值输入框
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("0")

        # 设置数值验证器（允许负数和小数）
        validator = QDoubleValidator(-9999.0, 9999.0, 2)
        self.value_input.setValidator(validator)
        self.value_input.textChanged.connect(self._on_value_changed)
        layout.addWidget(self.value_input, stretch=1)

        # 单位选择下拉框
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(self._allowed_units)
        self.unit_combo.setFixedWidth(dp(64))
        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        layout.addWidget(self.unit_combo)

    def _apply_theme(self):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        # 输入框样式
        self.value_input.setStyleSheet(f"""
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
        """)

        # 下拉框样式
        self.unit_combo.setStyleSheet(f"""
            QComboBox {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_primary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QComboBox:hover {{
                border-color: {palette.accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                width: {dp(20)}px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {palette.text_secondary};
                margin-right: {dp(8)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                selection-background-color: {theme_manager.PRIMARY_PALE};
                selection-color: {palette.accent_color};
            }}
            QComboBox QAbstractItemView::item {{
                color: {palette.text_primary};
                padding: {dp(4)}px;
            }}
        """)

    def _on_value_changed(self, text: str):
        """数值变更处理"""
        self._emit_value()

    def _on_unit_changed(self, index: int):
        """单位变更处理"""
        self._emit_value()

    def _emit_value(self):
        """发射值变更信号"""
        value = self.get_value()
        if value:
            self.value_changed.emit(value)

    def get_value(self) -> str:
        """获取当前值（如"24px"）"""
        num = self.value_input.text().strip()
        if not num:
            return ""
        unit = self.unit_combo.currentText()
        return f"{num}{unit}"

    def set_value(self, value: str):
        """设置值

        Args:
            value: 尺寸值，如"24px"、"1.5em"、"50%"
        """
        if not value:
            self.value_input.clear()
            return

        # 解析值
        match = self.SIZE_PATTERN.match(value.strip())
        if match:
            num, unit = match.groups()
            self.value_input.setText(num)
            if unit:
                unit_lower = unit.lower()
                # 查找单位在列表中的位置
                for i, u in enumerate(self._allowed_units):
                    if u.lower() == unit_lower:
                        self.unit_combo.setCurrentIndex(i)
                        break
        else:
            # 尝试作为纯数字处理
            try:
                float(value)
                self.value_input.setText(value)
            except ValueError:
                # 无法解析，直接设置文本
                self.value_input.setText(value)

    def get_numeric_value(self) -> Tuple[Optional[float], str]:
        """获取数值和单位

        Returns:
            (数值, 单位) 元组，数值无效时为None
        """
        try:
            num = float(self.value_input.text().strip())
            unit = self.unit_combo.currentText()
            return (num, unit)
        except (ValueError, TypeError):
            return (None, "")

    # 属性接口
    value = property(get_value, set_value)
