"""
多行文本输入对话框 - 主题适配

替代 QInputDialog.getMultiLineText()
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit, QDialog
)
from PyQt6.QtCore import Qt
from utils.dpi_utils import dp
from typing import Tuple

from ..base import BaseDialog
from ..styles import DialogStyles


class TextInputDialog(BaseDialog):
    """多行文本输入对话框 - 主题适配

    替代 QInputDialog.getMultiLineText()

    使用方式：
        text, ok = TextInputDialog.getText(
            parent=self,
            title="输入内容",
            label="请输入详细描述：",
            text="默认内容"
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
        self.text_edit = None
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
        self.container.setObjectName("text_input_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("text_input_title")
        container_layout.addWidget(self.title_label)

        # 提示文本
        if self.label_text:
            self.label_widget = QLabel(self.label_text)
            self.label_widget.setObjectName("text_input_label")
            self.label_widget.setWordWrap(True)
            container_layout.addWidget(self.label_widget)

        # 多行输入框
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("text_input_field")
        self.text_edit.setPlainText(self.default_text)
        if self.placeholder_text:
            self.text_edit.setPlaceholderText(self.placeholder_text)
        self.text_edit.setMinimumHeight(dp(120))
        self.text_edit.setMaximumHeight(dp(200))
        container_layout.addWidget(self.text_edit)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("text_input_cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setObjectName("text_input_ok_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(80))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)
        layout.addWidget(self.container)

        self.setFixedWidth(dp(480))

    def _apply_theme(self):
        """应用主题样式"""
        # 使用 DialogStyles 辅助类
        self.container.setStyleSheet(DialogStyles.container("text_input_container"))
        self.title_label.setStyleSheet(DialogStyles.title("text_input_title"))

        if self.label_widget:
            self.label_widget.setStyleSheet(DialogStyles.label("text_input_label"))

        self.text_edit.setStyleSheet(DialogStyles.text_edit("text_input_field"))
        self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("text_input_cancel_btn"))
        self.ok_btn.setStyleSheet(DialogStyles.button_primary("text_input_ok_btn"))

    def getText(self) -> str:
        """获取输入的文本"""
        return self.text_edit.toPlainText()

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
        dialog = TextInputDialog(parent, title, label, text, placeholder)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.getText(), True
        return "", False
