"""
LLM配置测试结果对话框 - 书籍风格
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class TestResultDialog(QDialog):
    """测试结果对话框 - 书籍风格"""

    def __init__(self, success, message, details=None, parent=None):
        super().__init__(parent)
        self.success = success
        self.message = message
        self.details = details or {}
        self._theme_connected = False
        self.setWindowTitle("测试结果")
        self.setMinimumSize(400, 300)
        self._create_ui_structure()
        self._apply_theme()
        self._connect_theme_signal()

    def _connect_theme_signal(self):
        """连接主题信号"""
        if not self._theme_connected:
            theme_manager.theme_changed.connect(self._on_theme_changed)
            self._theme_connected = True

    def _disconnect_theme_signal(self):
        """断开主题信号"""
        if self._theme_connected:
            try:
                theme_manager.theme_changed.disconnect(self._on_theme_changed)
            except TypeError:
                pass
            self._theme_connected = False

    def _on_theme_changed(self, mode: str):
        """主题改变回调"""
        self._apply_theme()

    def closeEvent(self, event):
        """关闭时断开信号"""
        self._disconnect_theme_signal()
        super().closeEvent(event)

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(dp(16))
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))

        # 图标
        self.icon_label = QLabel("Y" if self.success else "X")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(dp(64), dp(64))
        layout.addWidget(self.icon_label)

        # 标题
        self.title_label = QLabel("连接成功" if self.success else "连接失败")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 消息
        self.message_label = QLabel(self.message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        # 详细信息
        if self.success and self.details:
            self.details_frame = QFrame()
            details_layout = QVBoxLayout(self.details_frame)
            details_layout.setSpacing(dp(8))
            details_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))

            if 'response_time_ms' in self.details:
                time_row = QHBoxLayout()
                self.time_label = QLabel("响应时间:")
                time_row.addWidget(self.time_label)
                time_row.addStretch()
                self.time_value = QLabel(f"{self.details['response_time_ms']:.2f} ms")
                time_row.addWidget(self.time_value)
                details_layout.addLayout(time_row)

            if 'model_info' in self.details:
                model_row = QHBoxLayout()
                self.model_label = QLabel("模型:")
                model_row.addWidget(self.model_label)
                model_row.addStretch()
                self.model_value = QLabel(str(self.details['model_info']))
                model_row.addWidget(self.model_value)
                details_layout.addLayout(model_row)

            if 'vector_dimension' in self.details and self.details['vector_dimension']:
                dim_row = QHBoxLayout()
                self.dim_label = QLabel("向量维度:")
                dim_row.addWidget(self.dim_label)
                dim_row.addStretch()
                self.dim_value = QLabel(str(self.details['vector_dimension']))
                dim_row.addWidget(self.dim_value)
                details_layout.addLayout(dim_row)

            layout.addWidget(self.details_frame)
        else:
            self.details_frame = None

        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_theme(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 成功/失败颜色 - 使用主题定义的颜色
        success_color = theme_manager.SUCCESS
        success_bg = theme_manager.SUCCESS_BG
        error_color = theme_manager.ERROR
        error_bg = theme_manager.ERROR_BG

        # 对话框背景
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {palette.bg_primary};
            }}
        """)

        # 图标样式
        icon_bg = success_bg if self.success else error_bg
        icon_color = success_color if self.success else error_color
        self.icon_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.ui_font};
                background-color: {icon_bg};
                color: {icon_color};
                border-radius: {dp(32)}px;
                font-size: {sp(32)}px;
                font-weight: bold;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.serif_font};
                font-size: {sp(20)}px;
                font-weight: 700;
                color: {palette.text_primary};
            }}
        """)

        # 消息样式
        self.message_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                color: {palette.text_secondary};
            }}
        """)

        # 详细信息框样式
        if self.details_frame:
            self.details_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {palette.bg_secondary};
                    border: 1px solid {palette.border_color};
                    border-radius: {dp(8)}px;
                }}
            """)

            # 标签样式
            label_style = f"""
                QLabel {{
                    font-family: {palette.ui_font};
                    font-size: {sp(13)}px;
                    color: {palette.text_secondary};
                }}
            """
            value_style = f"""
                QLabel {{
                    font-family: {palette.ui_font};
                    font-size: {sp(13)}px;
                    font-weight: 600;
                    color: {palette.text_primary};
                }}
            """

            if hasattr(self, 'time_label'):
                self.time_label.setStyleSheet(label_style)
                self.time_value.setStyleSheet(value_style)
            if hasattr(self, 'model_label'):
                self.model_label.setStyleSheet(label_style)
                self.model_value.setStyleSheet(value_style)
            if hasattr(self, 'dim_label'):
                self.dim_label.setStyleSheet(label_style)
                self.dim_value.setStyleSheet(value_style)

        # 关闭按钮样式
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(32)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
                min-width: {dp(100)}px;
            }}
            QPushButton:hover {{
                background-color: {palette.text_primary};
            }}
            QPushButton:pressed {{
                background-color: {palette.accent_light};
            }}
        """)
