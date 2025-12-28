"""
LLM配置创建/编辑对话框 - 书籍风格

使用 BookStyleDialog 基类和 DialogStyles 统一样式。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt
from components.dialogs import BookStyleDialog, DialogStyles
from utils.dpi_utils import dp


class LLMConfigDialog(BookStyleDialog):
    """LLM配置创建/编辑对话框 - 书籍风格"""

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.is_create = config is None
        self.setWindowTitle("新增 LLM 配置" if self.is_create else "编辑 LLM 配置")
        self.setMinimumSize(500, 400)
        self._create_ui_structure()
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        # 标题
        self.title_label = QLabel("新增 LLM 配置" if self.is_create else "编辑 LLM 配置")
        self.title_label.setObjectName("config_title")
        layout.addWidget(self.title_label)

        # 表单区域
        form_layout = QFormLayout()
        form_layout.setSpacing(dp(16))
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # 配置名称
        self.name_label = QLabel("配置名称 *")
        self.name_label.setObjectName("config_label")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：GPT-4 配置、Claude 配置等")
        self.name_input.setMinimumHeight(dp(40))
        if self.config:
            self.name_input.setText(self.config.get('config_name', ''))
        form_layout.addRow(self.name_label, self.name_input)

        # API Base URL
        self.url_label = QLabel("API Base URL")
        self.url_label.setObjectName("config_label")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.openai.com/v1")
        self.url_input.setMinimumHeight(dp(40))
        if self.config:
            self.url_input.setText(self.config.get('llm_provider_url', ''))
        form_layout.addRow(self.url_label, self.url_input)

        # API Key
        self.key_label = QLabel("API Key")
        self.key_label.setObjectName("config_label")
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-..." if self.is_create else "留空表示不修改")
        self.key_input.setMinimumHeight(dp(40))
        form_layout.addRow(self.key_label, self.key_input)

        if not self.is_create:
            self.key_hint = QLabel("留空表示保持原有 API Key 不变")
            self.key_hint.setObjectName("config_hint")
            form_layout.addRow("", self.key_hint)

        # 模型名称
        self.model_label = QLabel("模型名称")
        self.model_label.setObjectName("config_label")
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
        # 使用 DialogStyles 的统一样式方法
        self.setStyleSheet(DialogStyles.book_dialog_background())
        self.title_label.setStyleSheet(DialogStyles.book_title("config_title"))

        # 标签样式
        label_style = DialogStyles.book_label("config_label")
        self.name_label.setStyleSheet(label_style)
        self.url_label.setStyleSheet(label_style)
        self.key_label.setStyleSheet(label_style)
        self.model_label.setStyleSheet(label_style)

        # 提示文字样式
        if hasattr(self, 'key_hint'):
            self.key_hint.setStyleSheet(DialogStyles.book_hint("config_hint"))

        # 输入框样式
        input_style = DialogStyles.book_input()
        self.name_input.setStyleSheet(input_style)
        self.url_input.setStyleSheet(input_style)
        self.key_input.setStyleSheet(input_style)
        self.model_input.setStyleSheet(input_style)

        # 按钮样式
        self.cancel_btn.setStyleSheet(DialogStyles.book_button_cancel())
        self.save_btn.setStyleSheet(DialogStyles.book_button_save())

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
