"""
嵌入模型配置对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager


class EmbeddingConfigDialog(QDialog):
    """嵌入模型配置创建/编辑对话框"""

    def __init__(self, config=None, providers=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.providers = providers or []
        self.is_create = config is None
        self.ui_font = theme_manager.ui_font()
        self.setWindowTitle("新增嵌入模型配置" if self.is_create else "编辑嵌入模型配置")
        self.setMinimumSize(600, 550)
        self.setupUI()

    def setupUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 表单
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        input_style = f"""
            QLineEdit, QComboBox, QSpinBox {{
                font-family: {self.ui_font};
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_PRIMARY};
                padding: 8px 12px;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {theme_manager.ACCENT_PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
        """

        # 配置名称
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：OpenAI Embedding、本地 Ollama 等")
        self.name_input.setStyleSheet(input_style)
        if self.config:
            self.name_input.setText(self.config.get('config_name', ''))
        form_layout.addRow("配置名称 *", self.name_input)

        # 提供方选择
        self.provider_combo = QComboBox()
        self.provider_combo.setStyleSheet(input_style)
        self.provider_combo.addItem("OpenAI / 兼容 API", "openai")
        self.provider_combo.addItem("Ollama 本地模型", "ollama")
        if self.config:
            provider = self.config.get('provider', 'openai')
            index = self.provider_combo.findData(provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        form_layout.addRow("提供方", self.provider_combo)

        # API Base URL
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.openai.com/v1")
        self.url_input.setStyleSheet(input_style)
        if self.config:
            self.url_input.setText(self.config.get('api_base_url', ''))
        form_layout.addRow("API Base URL", self.url_input)

        # API Key
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-..." if self.is_create else "留空表示不修改")
        self.key_input.setStyleSheet(input_style)
        form_layout.addRow("API Key", self.key_input)

        # API Key 提示
        self.key_hint = QLabel("Ollama 本地模型无需 API Key")
        self.key_hint.setStyleSheet(f"font-family: {self.ui_font}; font-size: 11px; color: {theme_manager.TEXT_SECONDARY};")
        form_layout.addRow("", self.key_hint)

        # 模型名称
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("text-embedding-3-small")
        self.model_input.setStyleSheet(input_style)
        if self.config:
            self.model_input.setText(self.config.get('model_name', ''))
        form_layout.addRow("模型名称", self.model_input)

        # 向量维度（可选）
        self.vector_size_input = QSpinBox()
        self.vector_size_input.setStyleSheet(input_style)
        self.vector_size_input.setRange(0, 10000)
        self.vector_size_input.setSpecialValueText("自动检测")
        if self.config and self.config.get('vector_size'):
            self.vector_size_input.setValue(self.config.get('vector_size'))
        form_layout.addRow("向量维度", self.vector_size_input)

        # 向量维度提示
        dim_hint = QLabel("留空或设为0将在测试时自动检测")
        dim_hint.setStyleSheet(f"font-family: {self.ui_font}; font-size: 11px; color: {theme_manager.TEXT_SECONDARY};")
        form_layout.addRow("", dim_hint)

        layout.addLayout(form_layout)

        # 常用模型提示
        hint_label = QLabel("常用嵌入模型：\n- OpenAI: text-embedding-3-small, text-embedding-3-large\n- Ollama: nomic-embed-text, mxbai-embed-large")
        hint_label.setStyleSheet(f"""
            font-family: {self.ui_font};
            font-size: 12px;
            color: {theme_manager.TEXT_SECONDARY};
            background-color: {theme_manager.BG_SECONDARY};
            padding: 12px;
            border-radius: {theme_manager.RADIUS_SM};
        """)
        layout.addWidget(hint_label)

        layout.addStretch()

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
                font-family: {self.ui_font};
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

        # 初始化提供方相关的UI状态
        self._on_provider_changed()

    def _on_provider_changed(self):
        """提供方切换时更新UI"""
        provider = self.provider_combo.currentData()

        if provider == "ollama":
            self.url_input.setPlaceholderText("http://localhost:11434")
            self.model_input.setPlaceholderText("nomic-embed-text:latest")
            self.key_input.setEnabled(False)
            self.key_hint.setText("Ollama 本地模型无需 API Key")
        else:
            self.url_input.setPlaceholderText("https://api.openai.com/v1")
            self.model_input.setPlaceholderText("text-embedding-3-small")
            self.key_input.setEnabled(True)
            if self.is_create:
                self.key_hint.setText("使用中转站时请填写对应的 API Key")
            else:
                self.key_hint.setText("留空表示保持原有 API Key 不变")

    def getData(self):
        """获取表单数据"""
        data = {
            'config_name': self.name_input.text().strip(),
            'provider': self.provider_combo.currentData(),
        }

        if self.url_input.text().strip():
            data['api_base_url'] = self.url_input.text().strip()

        if self.key_input.text().strip():
            data['api_key'] = self.key_input.text().strip()

        if self.model_input.text().strip():
            data['model_name'] = self.model_input.text().strip()

        if self.vector_size_input.value() > 0:
            data['vector_size'] = self.vector_size_input.value()

        return data
