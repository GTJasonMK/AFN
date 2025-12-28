"""
提示词编辑对话框 - 书籍风格

用于编辑单个提示词的内容。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QFrame
)
from PyQt6.QtCore import Qt
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from utils.error_handler import handle_errors


class PromptEditDialog(QDialog):
    """提示词编辑对话框 - 书籍风格"""

    def __init__(self, prompt_data: dict, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.prompt_data = prompt_data
        self.prompt_name = prompt_data.get('name', '')

        self.setWindowTitle("编辑提示词")
        self.setMinimumSize(dp(700), dp(500))
        self.resize(dp(800), dp(600))

        self._create_ui_structure()
        self._apply_styles()

        # 填充数据
        self._populate_data()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel()
        self.title_label.setObjectName("dialog_title")
        layout.addWidget(self.title_label)

        # 描述（只读）
        self.description_frame = QFrame()
        self.description_frame.setObjectName("description_frame")
        desc_layout = QVBoxLayout(self.description_frame)
        desc_layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        desc_layout.setSpacing(dp(4))

        desc_header = QLabel("使用场景")
        desc_header.setObjectName("desc_header")
        desc_layout.addWidget(desc_header)

        self.description_label = QLabel()
        self.description_label.setObjectName("desc_content")
        self.description_label.setWordWrap(True)
        desc_layout.addWidget(self.description_label)

        layout.addWidget(self.description_frame)

        # 内容编辑区
        content_header = QLabel("提示词内容")
        content_header.setObjectName("content_header")
        layout.addWidget(content_header)

        self.content_edit = QPlainTextEdit()
        self.content_edit.setObjectName("content_edit")
        self.content_edit.setPlaceholderText("在此输入提示词内容...")
        layout.addWidget(self.content_edit, stretch=1)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def _apply_styles(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 对话框背景
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {palette.bg_primary};
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            QLabel#dialog_title {{
                font-family: {palette.serif_font};
                font-size: {sp(20)}px;
                font-weight: 700;
                color: {palette.text_primary};
            }}
        """)

        # 描述框样式
        self.description_frame.setStyleSheet(f"""
            QFrame#description_frame {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
            }}
        """)

        # 描述标题
        for widget in self.description_frame.findChildren(QLabel):
            if widget.objectName() == "desc_header":
                widget.setStyleSheet(f"""
                    QLabel {{
                        font-family: {palette.ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {palette.text_tertiary};
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        background: transparent;
                    }}
                """)
            elif widget.objectName() == "desc_content":
                widget.setStyleSheet(f"""
                    QLabel {{
                        font-family: {palette.ui_font};
                        font-size: {sp(14)}px;
                        color: {palette.text_secondary};
                        background: transparent;
                    }}
                """)

        # 内容标题
        for widget in self.findChildren(QLabel):
            if widget.objectName() == "content_header":
                widget.setStyleSheet(f"""
                    QLabel {{
                        font-family: {palette.ui_font};
                        font-size: {sp(14)}px;
                        font-weight: 600;
                        color: {palette.text_primary};
                        background: transparent;
                    }}
                """)

        # 编辑框样式
        self.content_edit.setStyleSheet(f"""
            QPlainTextEdit#content_edit {{
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: {sp(13)}px;
                color: {palette.text_primary};
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
                padding: {dp(12)}px;
                line-height: 1.6;
            }}
            QPlainTextEdit#content_edit:focus {{
                border-color: {palette.accent_color};
            }}
        """)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
        """)

        # 保存按钮样式
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(24)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {palette.text_primary};
            }}
        """)

    def _populate_data(self):
        """填充数据"""
        title = self.prompt_data.get('title') or self.prompt_data.get('name', '未命名')
        description = self.prompt_data.get('description', '暂无描述')
        content = self.prompt_data.get('content', '')

        self.title_label.setText(title)
        self.description_label.setText(description)
        self.content_edit.setPlainText(content)

    def _on_save(self):
        """保存提示词"""
        content = self.content_edit.toPlainText().strip()

        if not content:
            MessageService.show_warning(self, "提示词内容不能为空", "输入错误")
            return

        self._do_save(content)

    @handle_errors("保存提示词")
    def _do_save(self, content: str):
        """执行保存"""
        self.api_client.update_prompt(self.prompt_name, content)
        MessageService.show_success(self, "提示词已保存")
        self.accept()
