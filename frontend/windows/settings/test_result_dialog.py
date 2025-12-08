"""
LLM配置测试结果对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles


class TestResultDialog(QDialog):
    """测试结果对话框 - 禅意风格"""

    def __init__(self, success, message, details=None, parent=None):
        super().__init__(parent)
        self.success = success
        self.message = message
        self.details = details or {}
        # 使用现代UI字体
        self.ui_font = theme_manager.ui_font()
        self.setWindowTitle("测试结果")
        self.setMinimumSize(400, 300)
        self.setupUI()

    def setupUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # 图标
        icon = QLabel("Y" if self.success else "X")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(64, 64)
        icon.setStyleSheet(f"""
            font-family: {self.ui_font};
            background-color: {theme_manager.SUCCESS_BG if self.success else theme_manager.ERROR_BG};
            color: {theme_manager.SUCCESS if self.success else theme_manager.ERROR};
            border-radius: 32px;
            font-size: 32px;
            font-weight: bold;
        """)
        layout.addWidget(icon)

        # 标题
        title = QLabel("连接成功" if self.success else "连接失败")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-family: {self.ui_font}; font-size: 18px; font-weight: 700; color: {theme_manager.TEXT_PRIMARY};")
        layout.addWidget(title)

        # 消息
        message = QLabel(self.message)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        message.setStyleSheet(f"font-family: {self.ui_font}; font-size: 14px; color: {theme_manager.TEXT_SECONDARY};")
        layout.addWidget(message)

        # 详细信息
        if self.success and self.details:
            details_frame = QFrame()
            details_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme_manager.BG_SECONDARY};
                    border-radius: {theme_manager.RADIUS_SM};
                    padding: 16px;
                }}
            """)
            details_layout = QVBoxLayout(details_frame)
            details_layout.setSpacing(8)

            if 'response_time_ms' in self.details:
                time_row = QHBoxLayout()
                time_label = QLabel("响应时间:")
                time_label.setStyleSheet(f"font-family: {self.ui_font}; font-size: 13px; color: {theme_manager.TEXT_SECONDARY};")
                time_row.addWidget(time_label)
                time_row.addStretch()
                time_value = QLabel(f"{self.details['response_time_ms']:.2f} ms")
                time_value.setStyleSheet(f"font-family: {self.ui_font}; font-size: 13px; font-weight: 600; color: {theme_manager.TEXT_PRIMARY};")
                time_row.addWidget(time_value)
                details_layout.addLayout(time_row)

            if 'model_info' in self.details:
                model_row = QHBoxLayout()
                model_label = QLabel("模型:")
                model_label.setStyleSheet(f"font-family: {self.ui_font}; font-size: 13px; color: {theme_manager.TEXT_SECONDARY};")
                model_row.addWidget(model_label)
                model_row.addStretch()
                model_value = QLabel(str(self.details['model_info']))
                model_value.setStyleSheet(f"font-family: {self.ui_font}; font-size: 13px; font-weight: 600; color: {theme_manager.TEXT_PRIMARY};")
                model_row.addWidget(model_value)
                details_layout.addLayout(model_row)

            layout.addWidget(details_frame)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(ButtonStyles.primary())
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)