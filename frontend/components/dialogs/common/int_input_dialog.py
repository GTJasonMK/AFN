"""
整数输入对话框 - 主题适配

替代 QInputDialog.getInt()
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSpinBox, QDialog
)
from PyQt6.QtCore import Qt
from utils.dpi_utils import dp
from typing import Tuple

from ..base import BaseDialog
from ..styles import DialogStyles


class IntInputDialog(BaseDialog):
    """整数输入对话框 - 主题适配

    替代 QInputDialog.getInt()

    使用方式：
        value, ok = IntInputDialog.getInt(
            parent=self,
            title="设置数量",
            label="请输入章节数量：",
            value=10,
            min_value=1,
            max_value=100
        )
        if ok:
            # 用户输入了数值
            pass
    """

    def __init__(
        self,
        parent=None,
        title: str = "输入",
        label: str = "",
        value: int = 0,
        min_value: int = 0,
        max_value: int = 100,
        step: int = 1
    ):
        self.title_text = title
        self.label_text = label
        self.default_value = value
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

        # UI组件引用
        self.container = None
        self.title_label = None
        self.label_widget = None
        self.spin_box = None
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
        self.container.setObjectName("int_input_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("int_input_title")
        container_layout.addWidget(self.title_label)

        # 提示文本
        if self.label_text:
            self.label_widget = QLabel(self.label_text)
            self.label_widget.setObjectName("int_input_label")
            self.label_widget.setWordWrap(True)
            container_layout.addWidget(self.label_widget)

        # 数字输入框
        self.spin_box = QSpinBox()
        self.spin_box.setObjectName("int_input_field")
        self.spin_box.setRange(self.min_value, self.max_value)
        self.spin_box.setValue(self.default_value)
        self.spin_box.setSingleStep(self.step)
        self.spin_box.setFixedHeight(dp(40))
        container_layout.addWidget(self.spin_box)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("int_input_cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setObjectName("int_input_ok_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(80))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)
        layout.addWidget(self.container)

        self.setFixedWidth(dp(360))

    def _apply_theme(self):
        """应用主题样式"""
        # 使用 DialogStyles 辅助类
        self.container.setStyleSheet(DialogStyles.container("int_input_container"))
        self.title_label.setStyleSheet(DialogStyles.title("int_input_title"))

        if self.label_widget:
            self.label_widget.setStyleSheet(DialogStyles.label("int_input_label"))

        self.spin_box.setStyleSheet(DialogStyles.spin_box("int_input_field"))
        self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("int_input_cancel_btn"))
        self.ok_btn.setStyleSheet(DialogStyles.button_primary("int_input_ok_btn"))

    def getValue(self) -> int:
        """获取输入的数值"""
        return self.spin_box.value()

    @staticmethod
    def getIntStatic(
        parent=None,
        title: str = "输入",
        label: str = "",
        value: int = 0,
        min_value: int = 0,
        max_value: int = 100,
        step: int = 1
    ) -> Tuple[int, bool]:
        """静态方法：显示对话框并获取输入

        Returns:
            (value, ok): 输入的数值和用户是否确认
        """
        dialog = IntInputDialog(parent, title, label, value, min_value, max_value, step)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.getValue(), True
        return 0, False
