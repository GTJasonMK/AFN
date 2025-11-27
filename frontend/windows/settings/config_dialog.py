"""
LLM配置创建/编辑对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager


class LLMConfigDialog(QDialog):
    """LLM配置创建/编辑对话框 - 禅意风格"""

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.is_create = config is None
        # 使用书香风格字体
        self.serif_font = theme_manager.serif_font()
        self.setWindowTitle("新增 LLM 配置" if self.is_create else "编辑 LLM 配置")
        self.setMinimumSize(600, 500)
        self.setupUI()

    def setupUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 表单
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 配置名称
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：GPT-4 配置、Claude 配置等")
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                font-family: {self.serif_font};
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_PRIMARY};
                padding: 8px 12px;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {theme_manager.ACCENT_PRIMARY};
            }}
        """)
        if self.config:
            self.name_input.setText(self.config.get('config_name', ''))
        form_layout.addRow("配置名称 *", self.name_input)

        # API Base URL
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.openai.com/v1")
        self.url_input.setStyleSheet(self.name_input.styleSheet())
        if self.config:
            self.url_input.setText(self.config.get('llm_provider_url', ''))
        form_layout.addRow("API Base URL", self.url_input)

        # API Key
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-..." if self.is_create else "留空表示不修改")
        self.key_input.setStyleSheet(self.name_input.styleSheet())
        form_layout.addRow("API Key", self.key_input)

        if not self.is_create:
            hint = QLabel("留空表示保持原有 API Key 不变")
            hint.setStyleSheet(f"font-family: {self.serif_font}; font-size: 11px; color: {theme_manager.TEXT_SECONDARY};")
            form_layout.addRow("", hint)

        # 模型名称
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("gpt-4、claude-3-opus-20240229 等")
        self.model_input.setStyleSheet(self.name_input.styleSheet())
        if self.config:
            self.model_input.setText(self.config.get('llm_provider_model', ''))
        form_layout.addRow("模型名称", self.model_input)

        layout.addLayout(form_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(theme_manager.button_secondary())
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {self.serif_font};
                background-color: {theme_manager.ACCENT_PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: 8px 24px;
                font-size: {theme_manager.FONT_SIZE_SM};
                font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                min-height: 32px;
                min-width: 64px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.ACCENT_TERTIARY};
            }}
            QPushButton:focus {{
                border: 2px solid {theme_manager.ACCENT_SECONDARY};
                outline: none;
            }}
        """)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

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
