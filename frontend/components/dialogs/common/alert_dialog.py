"""
警告/信息对话框 - 主题适配

单按钮对话框，用于显示需要用户确认的信息。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget, QScrollArea
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

from ..base import BaseDialog
from ..styles import DialogStyles


class AlertDialog(BaseDialog):
    """警告/信息对话框 - 主题适配

    单按钮对话框，用于显示需要用户确认的信息

    使用方式：
        dialog = AlertDialog(
            parent=self,
            title="操作失败",
            message="网络连接失败，请检查网络设置",
            button_text="知道了",
            dialog_type="error"  # info, success, warning, error
        )
        dialog.exec()
    """

    def __init__(
        self,
        parent=None,
        title: str = "提示",
        message: str = "",
        button_text: str = "确定",
        dialog_type: str = "info"  # info, success, warning, error
    ):
        self.title_text = title
        self.message_text = message
        self.button_text = button_text
        self.dialog_type = dialog_type

        # UI组件引用
        self.container = None
        self.icon_label = None
        self.title_label = None
        self.message_label = None
        self.message_scroll = None
        self.ok_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("alert_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 图标和标题行
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(12))

        # 图标
        self.icon_label = QLabel(self._get_icon())
        self.icon_label.setObjectName("alert_icon")
        self.icon_label.setFixedSize(dp(32), dp(32))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icon_label)

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("alert_title")
        header_layout.addWidget(self.title_label, stretch=1)

        container_layout.addLayout(header_layout)

        # 消息内容 - 使用滚动区域防止内容过长
        self.message_scroll = QScrollArea()
        self.message_scroll.setObjectName("alert_message_scroll")
        self.message_scroll.setWidgetResizable(True)
        self.message_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.message_scroll.setMaximumHeight(dp(300))  # 最大高度限制

        message_container = QWidget()
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)

        self.message_label = QLabel(self.message_text)
        self.message_label.setObjectName("alert_message")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        message_layout.addWidget(self.message_label)

        self.message_scroll.setWidget(message_container)
        container_layout.addWidget(self.message_scroll)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton(self.button_text)
        self.ok_btn.setObjectName("alert_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(100))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)

        layout.addWidget(self.container)

        # 设置对话框大小
        self.setFixedWidth(dp(400))

    def _get_icon(self) -> str:
        """获取图标"""
        icons = {
            "info": "i",
            "success": "*",
            "warning": "!",
            "error": "x"
        }
        return icons.get(self.dialog_type, "i")

    def _apply_theme(self):
        """应用主题样式"""
        # 获取类型对应的颜色
        colors = {
            "info": (theme_manager.INFO, getattr(theme_manager, 'INFO_BG', theme_manager.PRIMARY_PALE)),
            "success": (theme_manager.SUCCESS, getattr(theme_manager, 'SUCCESS_BG', theme_manager.PRIMARY_PALE)),
            "warning": (theme_manager.WARNING, getattr(theme_manager, 'WARNING_BG', theme_manager.PRIMARY_PALE)),
            "error": (theme_manager.ERROR, getattr(theme_manager, 'ERROR_BG', theme_manager.PRIMARY_PALE)),
        }
        accent_color, accent_bg = colors.get(self.dialog_type, colors["info"])

        # 使用 DialogStyles 辅助类
        self.container.setStyleSheet(DialogStyles.container("alert_container"))
        self.icon_label.setStyleSheet(DialogStyles.icon("alert_icon", accent_color, accent_bg))
        self.title_label.setStyleSheet(DialogStyles.title("alert_title"))
        self.message_label.setStyleSheet(DialogStyles.message("alert_message", padding_left=44))

        # 滚动区域样式
        if hasattr(self, 'message_scroll'):
            self.message_scroll.setStyleSheet(f"""
                QScrollArea#alert_message_scroll {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea#alert_message_scroll > QWidget > QWidget {{
                    background: transparent;
                }}
                {DialogStyles.scrollbar()}
            """)

        # 按钮样式
        self.ok_btn.setStyleSheet(DialogStyles.button_primary("alert_btn"))
