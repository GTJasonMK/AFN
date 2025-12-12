"""
单行文本输入对话框 - 主题适配

替代 QInputDialog.getText()
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit, QDialog
)
from PyQt6.QtCore import Qt
from utils.dpi_utils import dp
from typing import Tuple

from .base import BaseDialog
from .styles import DialogStyles


class InputDialog(BaseDialog):
    """单行文本输入对话框 - 主题适配

    替代 QInputDialog.getText()

    使用方式：
        text, ok = InputDialog.getText(
            parent=self,
            title="编辑标题",
            label="请输入新标题：",
            text="默认值"
        )
        if ok and text:
            # 用户输入了内容
            pass
    """

    def __init__(
        self,
        parent=None,
        title: str = "输入",
        label: str = "",
        text: str = "",
        placeholder: str = ""
    ):
        self.title_text = title
        self.label_text = label
        self.default_text = text
        self.placeholder_text = placeholder

        # UI组件引用
        self.container = None
        self.title_label = None
        self.label_widget = None
        self.input_field = None
        self.ok_btn = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("input_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("input_title")
        container_layout.addWidget(self.title_label)

        # 提示文本
        if self.label_text:
            self.label_widget = QLabel(self.label_text)
            self.label_widget.setObjectName("input_label")
            self.label_widget.setWordWrap(True)
            container_layout.addWidget(self.label_widget)

        # 输入框
        self.input_field = QLineEdit()
        self.input_field.setObjectName("input_field")
        self.input_field.setText(self.default_text)
        if self.placeholder_text:
            self.input_field.setPlaceholderText(self.placeholder_text)
        self.input_field.setFixedHeight(dp(40))
        container_layout.addWidget(self.input_field)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("input_cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setObjectName("input_ok_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(80))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)
        layout.addWidget(self.container)

        self.setFixedWidth(dp(400))

    def _apply_theme(self):
        """应用主题样式"""
        # 使用 DialogStyles 辅助类
        self.container.setStyleSheet(DialogStyles.container("input_container"))
        self.title_label.setStyleSheet(DialogStyles.title("input_title"))

        if self.label_widget:
            self.label_widget.setStyleSheet(DialogStyles.label("input_label"))

        self.input_field.setStyleSheet(DialogStyles.input_field("input_field"))
        self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("input_cancel_btn"))
        self.ok_btn.setStyleSheet(DialogStyles.button_primary("input_ok_btn"))

    def getText(self) -> str:
        """获取输入的文本"""
        return self.input_field.text()

    @staticmethod
    def getTextStatic(
        parent=None,
        title: str = "输入",
        label: str = "",
        text: str = "",
        placeholder: str = ""
    ) -> Tuple[str, bool]:
        """静态方法：显示对话框并获取输入

        Returns:
            (text, ok): 输入的文本和用户是否确认
        """
        dialog = InputDialog(parent, title, label, text, placeholder)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.getText(), True
        return "", False
