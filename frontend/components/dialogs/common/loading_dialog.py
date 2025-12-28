"""
加载中对话框 - 主题适配

替代 QProgressDialog，提供与主题系统完美适配的加载动画。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from utils.dpi_utils import dp

from ..base import BaseDialog
from ..styles import DialogStyles


class LoadingDialog(BaseDialog):
    """加载中对话框 - 主题适配

    替代 QProgressDialog，提供与主题系统完美适配的加载动画

    使用方式：
        # 方式1：手动控制
        dialog = LoadingDialog(
            parent=self,
            message="正在处理...",
            cancelable=True
        )
        dialog.show()
        # ... 异步操作
        dialog.close()

        # 方式2：配合异步Worker
        dialog = LoadingDialog(parent=self, message="正在生成...")
        worker.finished.connect(dialog.close)
        worker.start()
        dialog.exec()  # 阻塞直到close被调用
    """

    def __init__(
        self,
        parent=None,
        message: str = "加载中...",
        title: str = "请稍候",
        cancelable: bool = False
    ):
        self.message_text = message
        self.title_text = title
        self.cancelable = cancelable
        self._cancelled = False

        # UI组件引用
        self.container = None
        self.title_label = None
        self.message_label = None
        self.spinner = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        from components.loading_spinner import CircularSpinner

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("loading_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(32), dp(28), dp(32), dp(28))
        container_layout.setSpacing(dp(20))
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("loading_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.title_label)

        # 加载动画
        spinner_container = QHBoxLayout()
        spinner_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner = CircularSpinner(size=dp(48))
        spinner_container.addWidget(self.spinner)
        container_layout.addLayout(spinner_container)

        # 消息文本
        self.message_label = QLabel(self.message_text)
        self.message_label.setObjectName("loading_message")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        container_layout.addWidget(self.message_label)

        # 取消按钮（可选）
        if self.cancelable:
            button_layout = QHBoxLayout()
            button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.cancel_btn = QPushButton("取消")
            self.cancel_btn.setObjectName("loading_cancel_btn")
            self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.cancel_btn.setFixedHeight(dp(36))
            self.cancel_btn.setMinimumWidth(dp(100))
            self.cancel_btn.clicked.connect(self._on_cancel)
            button_layout.addWidget(self.cancel_btn)

            container_layout.addLayout(button_layout)

        layout.addWidget(self.container)

        # 设置对话框大小
        self.setFixedWidth(dp(320))

    def _apply_theme(self):
        """应用主题样式"""
        # 使用 DialogStyles 辅助类
        self.container.setStyleSheet(DialogStyles.container("loading_container"))
        self.title_label.setStyleSheet(DialogStyles.title("loading_title"))
        self.message_label.setStyleSheet(DialogStyles.label("loading_message"))

        if self.cancel_btn:
            self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("loading_cancel_btn"))

    def setMessage(self, message: str):
        """更新消息文本"""
        self.message_text = message
        if self.message_label:
            self.message_label.setText(message)

    def setTitle(self, title: str):
        """更新标题"""
        self.title_text = title
        if self.title_label:
            self.title_label.setText(title)

    def _on_cancel(self):
        """取消按钮点击"""
        self._cancelled = True
        self.reject()

    def wasCancelled(self) -> bool:
        """是否被取消"""
        return self._cancelled

    def show(self):
        """显示对话框"""
        super().show()
        if self.spinner:
            self.spinner.start()

    def close(self):
        """关闭对话框"""
        if self.spinner:
            self.spinner.stop()
        super().close()

    def accept(self):
        """接受并关闭"""
        if self.spinner:
            self.spinner.stop()
        super().accept()

    def reject(self):
        """拒绝并关闭"""
        if self.spinner:
            self.spinner.stop()
        super().reject()
