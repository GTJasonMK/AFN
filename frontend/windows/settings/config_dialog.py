"""
LLM配置创建/编辑对话框 - 书籍风格
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class LLMConfigDialog(QDialog):
    """LLM配置创建/编辑对话框 - 书籍风格"""

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.is_create = config is None
        self._theme_connected = False
        self.setWindowTitle("新增 LLM 配置" if self.is_create else "编辑 LLM 配置")
        self.setMinimumSize(500, 400)
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
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        # 标题
        self.title_label = QLabel("新增 LLM 配置" if self.is_create else "编辑 LLM 配置")
        layout.addWidget(self.title_label)

        # 表单区域
        form_layout = QFormLayout()
        form_layout.setSpacing(dp(16))
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # 配置名称
        self.name_label = QLabel("配置名称 *")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：GPT-4 配置、Claude 配置等")
        self.name_input.setMinimumHeight(dp(40))
        if self.config:
            self.name_input.setText(self.config.get('config_name', ''))
        form_layout.addRow(self.name_label, self.name_input)

        # API Base URL
        self.url_label = QLabel("API Base URL")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.openai.com/v1")
        self.url_input.setMinimumHeight(dp(40))
        if self.config:
            self.url_input.setText(self.config.get('llm_provider_url', ''))
        form_layout.addRow(self.url_label, self.url_input)

        # API Key
        self.key_label = QLabel("API Key")
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-..." if self.is_create else "留空表示不修改")
        self.key_input.setMinimumHeight(dp(40))
        form_layout.addRow(self.key_label, self.key_input)

        if not self.is_create:
            self.key_hint = QLabel("留空表示保持原有 API Key 不变")
            form_layout.addRow("", self.key_hint)

        # 模型名称
        self.model_label = QLabel("模型名称")
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("gpt-4、claude-3-opus-20240229 等")
        self.model_input.setMinimumHeight(dp(40))
        if self.config:
            self.model_input.setText(self.config.get('llm_provider_model', ''))
        form_layout.addRow(self.model_label, self.model_input)

        layout.addLayout(form_layout)
        layout.addStretch()

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(12))
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _apply_theme(self):
        """应用书籍风格主题"""
        bg_primary = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()
        serif_font = theme_manager.serif_font()
        ui_font = theme_manager.ui_font()

        # 对话框背景
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_primary};
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {serif_font};
                font-size: {sp(20)}px;
                font-weight: bold;
                color: {text_primary};
                padding-bottom: {dp(8)}px;
            }}
        """)

        # 标签样式
        label_style = f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_secondary};
            }}
        """
        self.name_label.setStyleSheet(label_style)
        self.url_label.setStyleSheet(label_style)
        self.key_label.setStyleSheet(label_style)
        self.model_label.setStyleSheet(label_style)

        if hasattr(self, 'key_hint'):
            self.key_hint.setStyleSheet(f"""
                QLabel {{
                    font-family: {ui_font};
                    font-size: {sp(11)}px;
                    color: {text_secondary};
                    font-style: italic;
                }}
            """)

        # 输入框样式
        input_style = f"""
            QLineEdit {{
                font-family: {ui_font};
                background-color: {bg_secondary};
                color: {text_primary};
                padding: {dp(10)}px {dp(14)}px;
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                font-size: {sp(13)}px;
            }}
            QLineEdit:focus {{
                border-color: {accent_color};
                border-width: 2px;
            }}
            QLineEdit::placeholder {{
                color: {text_secondary};
            }}
        """
        self.name_input.setStyleSheet(input_style)
        self.url_input.setStyleSheet(input_style)
        self.key_input.setStyleSheet(input_style)
        self.model_input.setStyleSheet(input_style)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {ui_font};
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(13)}px;
                min-width: {dp(80)}px;
            }}
            QPushButton:hover {{
                color: {accent_color};
                border-color: {accent_color};
            }}
        """)

        # 保存按钮样式
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {ui_font};
                background-color: {accent_color};
                color: {bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
                min-width: {dp(80)}px;
            }}
            QPushButton:hover {{
                background-color: {text_primary};
            }}
        """)

    def getData(self):
        """获取表单数据"""
        data = {
            'config_name': self.name_input.text().strip()
        }

        if self.url_input.text().strip():
            data['llm_provider_url'] = self.url_input.text().strip()

        if self.key_input.text().strip():
            data['llm_provider_api_key'] = self.key_input.text().strip()

        if self.model_input.text().strip():
            data['llm_provider_model'] = self.model_input.text().strip()

        return data