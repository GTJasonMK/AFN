"""
保存/不保存/取消 三按钮对话框

用于处理未保存修改时的用户选择。
"""

from enum import IntEnum
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

from .base import BaseDialog
from .styles import DialogStyles


class SaveDiscardResult(IntEnum):
    """三按钮对话框返回值"""
    CANCEL = 0   # 取消操作
    DISCARD = 1  # 不保存，继续
    SAVE = 2     # 保存后继续


class SaveDiscardDialog(BaseDialog):
    """保存/不保存/取消 三按钮对话框

    用于处理未保存修改时的用户选择。

    使用方式：
        dialog = SaveDiscardDialog(
            parent=self,
            title="确认离开",
            message="有未保存的修改（3处）",
            detail="是否保存修改？",
            save_text="保存",
            discard_text="不保存",
            cancel_text="取消"
        )
        result = dialog.exec()
        if result == SaveDiscardResult.SAVE:
            # 保存后继续
            pass
        elif result == SaveDiscardResult.DISCARD:
            # 不保存，继续
            pass
        else:
            # 取消操作
            pass
    """

    def __init__(
        self,
        parent=None,
        title: str = "确认",
        message: str = "",
        detail: str = "",
        save_text: str = "保存",
        discard_text: str = "不保存",
        cancel_text: str = "取消"
    ):
        self.title_text = title
        self.message_text = message
        self.detail_text = detail
        self.save_text = save_text
        self.discard_text = discard_text
        self.cancel_text = cancel_text

        # 返回值
        self._result = SaveDiscardResult.CANCEL

        # UI组件引用
        self.container = None
        self.icon_label = None
        self.title_label = None
        self.message_label = None
        self.detail_label = None
        self.save_btn = None
        self.discard_btn = None
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
        self.icon_label = QLabel("!")
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

        # 详细信息（如果有）
        if self.detail_text:
            self.detail_label = QLabel(self.detail_text)
            self.detail_label.setObjectName("dialog_detail")
            self.detail_label.setWordWrap(True)
            self.detail_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            container_layout.addWidget(self.detail_label)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))

        # 取消按钮（左侧）
        self.cancel_btn = QPushButton(self.cancel_text)
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)

        button_layout.addStretch()

        # 不保存按钮（右侧）
        self.discard_btn = QPushButton(self.discard_text)
        self.discard_btn.setObjectName("discard_btn")
        self.discard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.discard_btn.setFixedHeight(dp(38))
        self.discard_btn.setMinimumWidth(dp(80))
        self.discard_btn.clicked.connect(self._on_discard)
        button_layout.addWidget(self.discard_btn)

        # 保存按钮（主按钮）
        self.save_btn = QPushButton(self.save_text)
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFixedHeight(dp(38))
        self.save_btn.setMinimumWidth(dp(80))
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setDefault(True)
        button_layout.addWidget(self.save_btn)

        container_layout.addLayout(button_layout)

        layout.addWidget(self.container)

        # 设置对话框大小
        self.setFixedWidth(dp(420))

    def _on_save(self):
        """保存按钮点击"""
        self._result = SaveDiscardResult.SAVE
        self.done(int(SaveDiscardResult.SAVE))

    def _on_discard(self):
        """不保存按钮点击"""
        self._result = SaveDiscardResult.DISCARD
        self.done(int(SaveDiscardResult.DISCARD))

    def _on_cancel(self):
        """取消按钮点击"""
        self._result = SaveDiscardResult.CANCEL
        self.done(int(SaveDiscardResult.CANCEL))

    def result(self) -> SaveDiscardResult:
        """获取用户选择结果"""
        return self._result

    def _apply_theme(self):
        """应用主题样式"""
        accent_color = theme_manager.WARNING
        accent_bg = theme_manager.WARNING_BG if hasattr(theme_manager, 'WARNING_BG') else theme_manager.PRIMARY_PALE

        # 使用 DialogStyles 辅助类
        self.container.setStyleSheet(DialogStyles.container("dialog_container"))
        self.icon_label.setStyleSheet(DialogStyles.icon("dialog_icon", accent_color, accent_bg))
        self.title_label.setStyleSheet(DialogStyles.title("dialog_title"))
        self.message_label.setStyleSheet(DialogStyles.message("dialog_message", padding_left=44))

        if self.detail_label:
            self.detail_label.setStyleSheet(f"""
                QLabel#dialog_detail {{
                    font-family: {theme_manager.FONT_UI};
                    font-size: {sp(13)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                    padding-left: {dp(44)}px;
                }}
            """)

        self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("cancel_btn"))
        self.discard_btn.setStyleSheet(DialogStyles.button_secondary("discard_btn"))
        self.save_btn.setStyleSheet(DialogStyles.button_primary("save_btn"))
