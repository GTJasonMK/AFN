"""
字体选择器组件

提供常用字体族选择功能，支持手动输入自定义字体。
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox
)
from PyQt6.QtCore import pyqtSignal

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class FontFamilySelector(QWidget):
    """字体选择器组件

    布局：
    ┌─────────────────────────────────────┐
    │ [Georgia, Times New Roman ▼]       │
    └─────────────────────────────────────┘

    - 下拉选择常用字体族
    - 支持手动输入自定义字体
    """

    # 值变更信号
    value_changed = pyqtSignal(str)

    # 预设字体族选项
    FONT_PRESETS = {
        "衬线字体（中文）": "'Noto Serif SC', 'Source Han Serif SC', serif",
        "无衬线字体（中文）": "'Noto Sans SC', 'Source Han Sans SC', sans-serif",
        "UI字体（中文）": "'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', sans-serif",
        "衬线字体（英文）": "Georgia, 'Times New Roman', serif",
        "无衬线字体（英文）": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
        "等宽字体": "'Consolas', 'Monaco', 'Courier New', monospace",
        "展示字体": "'Noto Serif SC', 'Source Han Serif SC', serif",
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_value: str = ""
    ):
        """初始化字体选择器

        Args:
            parent: 父组件
            initial_value: 初始字体值
        """
        super().__init__(parent)
        self._create_ui()
        self._apply_theme()

        if initial_value:
            self.set_value(initial_value)

        # 监听主题变化
        theme_manager.theme_changed.connect(self._apply_theme)

    def _create_ui(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 字体选择下拉框（支持编辑）
        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        # 添加预设选项
        for name, value in self.FONT_PRESETS.items():
            self.font_combo.addItem(name, value)

        # 信号连接
        self.font_combo.currentIndexChanged.connect(self._on_selection_changed)
        self.font_combo.lineEdit().textChanged.connect(self._on_text_changed)

        layout.addWidget(self.font_combo)

    def _apply_theme(self):
        """应用主题样式"""
        palette = theme_manager.get_book_palette()

        self.font_combo.setStyleSheet(f"""
            QComboBox {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_primary};
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
                min-height: {dp(32)}px;
            }}
            QComboBox:hover {{
                border-color: {palette.accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                width: {dp(24)}px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid {palette.text_secondary};
                margin-right: {dp(8)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                selection-background-color: {theme_manager.PRIMARY_PALE};
                selection-color: {palette.accent_color};
                padding: {dp(4)}px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: {dp(8)}px;
                min-height: {dp(32)}px;
            }}
            QComboBox QLineEdit {{
                background-color: transparent;
                border: none;
                padding: 0;
                font-size: {sp(13)}px;
            }}
        """)

    def _on_selection_changed(self, index: int):
        """选择变更处理"""
        if index >= 0:
            # 获取选中项的数据值
            value = self.font_combo.itemData(index)
            if value:
                # 更新编辑框显示实际值
                self.font_combo.lineEdit().setText(value)
                self.value_changed.emit(value)

    def _on_text_changed(self, text: str):
        """文本变更处理（手动输入）"""
        # 检查是否与预设匹配
        text = text.strip()
        for name, value in self.FONT_PRESETS.items():
            if text == value:
                # 找到匹配的预设，不重复发信号
                return

        # 自定义输入，发送信号
        if text:
            self.value_changed.emit(text)

    def get_value(self) -> str:
        """获取当前字体值"""
        return self.font_combo.lineEdit().text().strip()

    def set_value(self, value: str):
        """设置字体值

        Args:
            value: 字体族值，如"'Georgia', serif"
        """
        if not value:
            return

        # 检查是否匹配预设
        for i in range(self.font_combo.count()):
            if self.font_combo.itemData(i) == value:
                self.font_combo.setCurrentIndex(i)
                self.font_combo.lineEdit().setText(value)
                return

        # 自定义值，直接设置文本
        self.font_combo.setCurrentIndex(-1)
        self.font_combo.lineEdit().setText(value)

    # 属性接口
    value = property(get_value, set_value)
