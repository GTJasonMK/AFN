"""
重新生成确认对话框 - 带偏好输入

在重新生成时显示确认提示，并允许用户输入偏好指导。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit, QDialog
)
from PyQt6.QtCore import Qt
from utils.dpi_utils import dp
from typing import Tuple, Optional

from ..base import BaseDialog
from ..styles import DialogStyles


class RegenerateDialog(BaseDialog):
    """重新生成确认对话框

    用于在重新生成时：
    1. 显示确认提示
    2. 允许用户输入偏好指导（可选）

    使用方式：
        preference, ok = RegenerateDialog.getPreference(
            parent=self,
            title="重新生成系统划分",
            message="当前已有 3 个系统划分。重新生成将覆盖现有数据。",
            placeholder="例如：希望更细粒度划分、合并某些系统等"
        )
        if ok:
            # 用户确认，preference可能为空字符串（不提供偏好）或有内容
            do_regenerate(preference=preference if preference else None)
    """

    def __init__(
        self,
        parent=None,
        title: str = "重新生成",
        message: str = "",
        placeholder: str = "输入偏好指导（可选）..."
    ):
        self.title_text = title
        self.message_text = message
        self.placeholder_text = placeholder

        # UI组件引用
        self.container = None
        self.title_label = None
        self.message_label = None
        self.preference_label = None
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
        self.container.setObjectName("regenerate_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("regenerate_title")
        container_layout.addWidget(self.title_label)

        # 确认消息
        if self.message_text:
            self.message_label = QLabel(self.message_text)
            self.message_label.setObjectName("regenerate_message")
            self.message_label.setWordWrap(True)
            container_layout.addWidget(self.message_label)

        # 偏好输入区域
        self.preference_label = QLabel("偏好指导（可选）：")
        self.preference_label.setObjectName("regenerate_preference_label")
        container_layout.addWidget(self.preference_label)

        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("regenerate_text_field")
        self.text_edit.setPlaceholderText(self.placeholder_text)
        self.text_edit.setMinimumHeight(dp(80))
        self.text_edit.setMaximumHeight(dp(120))
        container_layout.addWidget(self.text_edit)

        # 提示文字
        hint_label = QLabel("提供偏好指导可以帮助AI更好地理解你的需求，生成更符合预期的结果。")
        hint_label.setObjectName("regenerate_hint")
        hint_label.setWordWrap(True)
        container_layout.addWidget(hint_label)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("regenerate_cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确认重新生成")
        self.ok_btn.setObjectName("regenerate_ok_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(120))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)
        layout.addWidget(self.container)

        self.setFixedWidth(dp(500))

    def _apply_theme(self):
        """应用主题样式"""
        from themes.theme_manager import theme_manager

        self.container.setStyleSheet(DialogStyles.container("regenerate_container"))
        self.title_label.setStyleSheet(DialogStyles.title("regenerate_title"))

        if self.message_label:
            self.message_label.setStyleSheet(f"""
                QLabel#regenerate_message {{
                    color: {theme_manager.TEXT_PRIMARY};
                    font-size: {dp(14)}px;
                    line-height: 1.5;
                    padding: {dp(8)}px {dp(12)}px;
                    background-color: {theme_manager.WARNING}15;
                    border: 1px solid {theme_manager.WARNING}30;
                    border-radius: {dp(6)}px;
                }}
            """)

        self.preference_label.setStyleSheet(f"""
            QLabel#regenerate_preference_label {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(13)}px;
                font-weight: 500;
            }}
        """)

        self.text_edit.setStyleSheet(DialogStyles.text_edit("regenerate_text_field"))

        # 提示文字样式
        for child in self.container.findChildren(QLabel):
            if child.objectName() == "regenerate_hint":
                child.setStyleSheet(f"""
                    QLabel#regenerate_hint {{
                        color: {theme_manager.TEXT_TERTIARY};
                        font-size: {dp(12)}px;
                        font-style: italic;
                    }}
                """)

        self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("regenerate_cancel_btn"))
        self.ok_btn.setStyleSheet(DialogStyles.button_primary("regenerate_ok_btn"))

    def getPreference(self) -> str:
        """获取输入的偏好"""
        return self.text_edit.toPlainText().strip()

    @staticmethod
    def getPreferenceStatic(
        parent=None,
        title: str = "重新生成",
        message: str = "",
        placeholder: str = "输入偏好指导（可选）..."
    ) -> Tuple[Optional[str], bool]:
        """静态方法：显示对话框并获取偏好

        Returns:
            (preference, ok): 偏好文本（可能为空字符串）和用户是否确认
        """
        dialog = RegenerateDialog(parent, title, message, placeholder)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            preference = dialog.getPreference()
            return preference if preference else None, True
        return None, False


# 便捷函数
def get_regenerate_preference(
    parent=None,
    title: str = "重新生成",
    message: str = "",
    placeholder: str = "输入偏好指导（可选）..."
) -> Tuple[Optional[str], bool]:
    """便捷函数：获取重新生成偏好

    Returns:
        (preference, ok): 偏好文本（None表示不提供）和用户是否确认
    """
    return RegenerateDialog.getPreferenceStatic(parent, title, message, placeholder)
