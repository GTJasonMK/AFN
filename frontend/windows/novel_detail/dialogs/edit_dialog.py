"""
编辑对话框组件

支持不同类型字段的编辑
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QWidget
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from typing import Any


class EditDialog(QDialog):
    """通用编辑对话框"""

    def __init__(self, field_label, current_value, multiline=True, parent=None):
        super().__init__(parent)
        self.field_label = field_label
        self.current_value = current_value
        self.multiline = multiline
        self.new_value = None
        # 使用现代UI字体
        self.ui_font = theme_manager.ui_font()

        self.setupUI()
        self.setWindowTitle(f"编辑 - {field_label}")
        self.resize(600, 400 if multiline else 200)

    def setupUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title = QLabel(f"编辑{self.field_label}")
        title.setStyleSheet(f"""
            font-family: {self.ui_font};
            font-size: 16px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        layout.addWidget(title)

        # 输入框
        if self.multiline:
            self.input_widget = QTextEdit()
            self.input_widget.setPlaceholderText(f"请输入{self.field_label}...")
            self.input_widget.setMinimumHeight(200)
            # 设置纯文本
            if self.current_value:
                self.input_widget.setPlainText(str(self.current_value))
        else:
            self.input_widget = QLineEdit()
            self.input_widget.setPlaceholderText(f"请输入{self.field_label}...")
            if self.current_value:
                self.input_widget.setText(str(self.current_value))

        self.input_widget.setStyleSheet(f"""
            QTextEdit, QLineEdit {{
                font-family: {self.ui_font};
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_MD};
                padding: 12px;
                font-size: {theme_manager.FONT_SIZE_BASE};
                color: {theme_manager.TEXT_PRIMARY};
            }}
            QTextEdit:focus, QLineEdit:focus {{
                border-color: {theme_manager.ACCENT_PRIMARY};
            }}
        """)
        layout.addWidget(self.input_widget)

        # 提示文字
        hint = QLabel("提示：修改后点击保存按钮")
        hint.setStyleSheet(f"""
            font-family: {self.ui_font};
            font-size: {theme_manager.FONT_SIZE_XS};
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(hint)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {self.ui_font};
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: 10px 20px;
                font-size: {theme_manager.FONT_SIZE_SM};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
            }}
            QPushButton:hover {{
                background-color: {theme_manager.BG_CARD};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedWidth(100)
        save_btn.setStyleSheet(ButtonStyles.primary())
        save_btn.clicked.connect(self.onSave)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        # 对话框样式
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """)

    def onSave(self):
        """保存修改"""
        if self.multiline:
            self.new_value = self.input_widget.toPlainText().strip()
        else:
            self.new_value = self.input_widget.text().strip()

        if not self.new_value:
            from utils.message_service import MessageService
            MessageService.show_warning(self, "内容不能为空", "提示")
            return

        self.accept()

    def getValue(self):
        """获取新值"""
        return self.new_value