"""
嵌入模型配置对话框 - 书籍风格
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class EmbeddingConfigDialog(QDialog):
    """嵌入模型配置创建/编辑对话框 - 书籍风格"""

    def __init__(self, config=None, providers=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.providers = providers or []
        self.is_create = config is None
        self.setWindowTitle("新增嵌入模型配置" if self.is_create else "编辑嵌入模型配置")
        self.setMinimumSize(500, 500)
        self._create_ui_structure()
        self._apply_theme()
        theme_manager.theme_changed.connect(lambda _: self._apply_theme())

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        # 标题
        self.title_label = QLabel("新增嵌入模型配置" if self.is_create else "编辑嵌入模型配置")
        layout.addWidget(self.title_label)

        # 表单区域
        form_layout = QFormLayout()
        form_layout.setSpacing(dp(16))
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # 配置名称
        self.name_label = QLabel("配置名称 *")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：OpenAI Embedding、本地 Ollama 等")
        self.name_input.setMinimumHeight(dp(40))
        if self.config:
            self.name_input.setText(self.config.get('config_name', ''))
        form_layout.addRow(self.name_label, self.name_input)

        # 提供方选择
        self.provider_label = QLabel("提供方")
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumHeight(dp(40))
        self.provider_combo.addItem("OpenAI / 兼容 API", "openai")
        self.provider_combo.addItem("Ollama 本地模型", "ollama")
        if self.config:
            provider = self.config.get('provider', 'openai')
            index = self.provider_combo.findData(provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        form_layout.addRow(self.provider_label, self.provider_combo)

        # API Base URL
        self.url_label = QLabel("API Base URL")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.openai.com/v1")
        self.url_input.setMinimumHeight(dp(40))
        if self.config:
            self.url_input.setText(self.config.get('api_base_url', ''))
        form_layout.addRow(self.url_label, self.url_input)

        # API Key
        self.key_label = QLabel("API Key")
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-..." if self.is_create else "留空表示不修改")
        self.key_input.setMinimumHeight(dp(40))
        form_layout.addRow(self.key_label, self.key_input)

        # API Key 提示
        self.key_hint = QLabel("Ollama 本地模型无需 API Key")
        form_layout.addRow("", self.key_hint)

        # 模型名称
        self.model_label = QLabel("模型名称")
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("text-embedding-3-small")
        self.model_input.setMinimumHeight(dp(40))
        if self.config:
            self.model_input.setText(self.config.get('model_name', ''))
        form_layout.addRow(self.model_label, self.model_input)

        # 向量维度（可选）
        self.dim_label = QLabel("向量维度")
        self.vector_size_input = QSpinBox()
        self.vector_size_input.setMinimumHeight(dp(40))
        self.vector_size_input.setRange(0, 10000)
        self.vector_size_input.setSpecialValueText("自动检测")
        if self.config and self.config.get('vector_size'):
            self.vector_size_input.setValue(self.config.get('vector_size'))
        form_layout.addRow(self.dim_label, self.vector_size_input)

        # 向量维度提示
        self.dim_hint = QLabel("留空或设为0将在测试时自动检测")
        form_layout.addRow("", self.dim_hint)

        layout.addLayout(form_layout)

        # 常用模型提示
        self.hint_label = QLabel(
            "常用嵌入模型：\n"
            "- OpenAI: text-embedding-3-small, text-embedding-3-large\n"
            "- Ollama: nomic-embed-text, mxbai-embed-large"
        )
        layout.addWidget(self.hint_label)

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

        # 初始化提供方相关的UI状态
        self._on_provider_changed()

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
        self.provider_label.setStyleSheet(label_style)
        self.url_label.setStyleSheet(label_style)
        self.key_label.setStyleSheet(label_style)
        self.model_label.setStyleSheet(label_style)
        self.dim_label.setStyleSheet(label_style)

        # 提示文字样式
        hint_style = f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {sp(11)}px;
                color: {text_secondary};
                font-style: italic;
            }}
        """
        self.key_hint.setStyleSheet(hint_style)
        self.dim_hint.setStyleSheet(hint_style)

        # 常用模型提示样式
        self.hint_label.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
                background-color: {bg_secondary};
                padding: {dp(12)}px;
                border-radius: {dp(6)}px;
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

        # ComboBox样式
        self.provider_combo.setStyleSheet(f"""
            QComboBox {{
                font-family: {ui_font};
                background-color: {bg_secondary};
                color: {text_primary};
                padding: {dp(10)}px {dp(14)}px;
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                font-size: {sp(13)}px;
            }}
            QComboBox:focus {{
                border-color: {accent_color};
                border-width: 2px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {dp(8)}px;
            }}
            QComboBox::down-arrow {{
                width: {dp(12)}px;
                height: {dp(12)}px;
            }}
            QComboBox QAbstractItemView {{
                font-family: {ui_font};
                background-color: {bg_primary};
                color: {text_primary};
                border: 1px solid {border_color};
                selection-background-color: {accent_color};
                selection-color: {bg_primary};
            }}
        """)

        # SpinBox样式
        self.vector_size_input.setStyleSheet(f"""
            QSpinBox {{
                font-family: {ui_font};
                background-color: {bg_secondary};
                color: {text_primary};
                padding: {dp(10)}px {dp(14)}px;
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                font-size: {sp(13)}px;
            }}
            QSpinBox:focus {{
                border-color: {accent_color};
                border-width: 2px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: {dp(20)}px;
                background-color: {bg_secondary};
                border: none;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {accent_color};
            }}
        """)

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
