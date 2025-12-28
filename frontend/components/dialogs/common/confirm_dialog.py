"""
确认对话框 - 主题适配

提供与主题系统完美适配的确认对话框。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

from ..base import BaseDialog
from ..styles import DialogStyles


class ConfirmDialog(BaseDialog):
    """确认对话框 - 主题适配

    使用方式：
        dialog = ConfirmDialog(
            parent=self,
            title="确认删除",
            message="确定要删除这个项目吗？",
            confirm_text="删除",
            cancel_text="取消",
            dialog_type="danger"  # normal, danger, warning
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 用户点击了确认
            pass
    """

    def __init__(
        self,
        parent=None,
        title: str = "确认",
        message: str = "",
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        dialog_type: str = "normal"  # normal, danger, warning
    ):
        self.title_text = title
        self.message_text = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.dialog_type = dialog_type

        # UI组件引用
        self.container = None
        self.icon_label = None
        self.title_label = None
        self.message_label = None
        self.confirm_btn = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器（用于圆角和阴影）
        self.container = QFrame()
        self.container.setObjectName("dialog_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 图标和标题行
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(12))

        # 图标
        self.icon_label = QLabel(self._get_icon())
        self.icon_label.setObjectName("dialog_icon")
        self.icon_label.setFixedSize(dp(32), dp(32))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icon_label)

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("dialog_title")
        header_layout.addWidget(self.title_label, stretch=1)

        container_layout.addLayout(header_layout)

        # 消息内容
        self.message_label = QLabel(self.message_text)
        self.message_label.setObjectName("dialog_message")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        container_layout.addWidget(self.message_label)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        # 取消按钮
        self.cancel_btn = QPushButton(self.cancel_text)
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        # 确认按钮
        self.confirm_btn = QPushButton(self.confirm_text)
        self.confirm_btn.setObjectName("confirm_btn")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setFixedHeight(dp(38))
        self.confirm_btn.setMinimumWidth(dp(80))
        self.confirm_btn.clicked.connect(self.accept)
        self.confirm_btn.setDefault(True)
        button_layout.addWidget(self.confirm_btn)

        container_layout.addLayout(button_layout)

        layout.addWidget(self.container)

        # 设置对话框大小
        self.setFixedWidth(dp(400))

    def _get_icon(self) -> str:
        """获取图标"""
        icons = {
            "normal": "?",
            "danger": "!",
            "warning": "!"
        }
        return icons.get(self.dialog_type, "?")

    def _apply_theme(self):
        """应用主题样式"""
        # 获取类型对应的颜色
        if self.dialog_type == "danger":
            accent_color = theme_manager.ERROR
            accent_bg = theme_manager.ERROR_BG if hasattr(theme_manager, 'ERROR_BG') else theme_manager.PRIMARY_PALE
        elif self.dialog_type == "warning":
            accent_color = theme_manager.WARNING
            accent_bg = theme_manager.WARNING_BG if hasattr(theme_manager, 'WARNING_BG') else theme_manager.PRIMARY_PALE
        else:
            accent_color = theme_manager.PRIMARY
            accent_bg = theme_manager.PRIMARY_PALE

        # 使用 DialogStyles 辅助类
        self.container.setStyleSheet(DialogStyles.container("dialog_container"))
        self.icon_label.setStyleSheet(DialogStyles.icon("dialog_icon", accent_color, accent_bg))
        self.title_label.setStyleSheet(DialogStyles.title("dialog_title"))
        self.message_label.setStyleSheet(DialogStyles.message("dialog_message", padding_left=44))
        self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("cancel_btn"))

        # 确认按钮样式（根据类型）
        if self.dialog_type == "danger":
            self.confirm_btn.setStyleSheet(DialogStyles.button_danger("confirm_btn"))
        elif self.dialog_type == "warning":
            self.confirm_btn.setStyleSheet(DialogStyles.button_warning("confirm_btn"))
        else:
            self.confirm_btn.setStyleSheet(DialogStyles.button_primary("confirm_btn"))
