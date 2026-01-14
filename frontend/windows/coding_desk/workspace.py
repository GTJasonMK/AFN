"""
编程项目工作台工作区

提供Prompt编辑和生成功能。
"""

import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class CodingWorkspace(ThemeAwareFrame):
    """编程项目工作区

    布局：
    - 工具栏（生成/保存/审查按钮 + 状态）
    - Prompt编辑器（主体）
    - 审查Prompt区域（底部）
    """

    generateRequested = pyqtSignal()  # 生成请求
    saveRequested = pyqtSignal(str)  # 保存请求，传递内容
    generateReviewRequested = pyqtSignal()  # 生成审查Prompt请求

    def __init__(self, parent=None):
        self._current_file: Optional[Dict[str, Any]] = None
        self._is_generating = False

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(12))

        # 工具栏
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(dp(8))

        # 生成按钮
        self.generate_btn = QPushButton("生成Prompt")
        self.generate_btn.setObjectName("generate_btn")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self._on_generate)
        self.generate_btn.setEnabled(False)
        toolbar_layout.addWidget(self.generate_btn)

        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setEnabled(False)
        toolbar_layout.addWidget(self.save_btn)

        # 生成审查Prompt按钮
        self.review_btn = QPushButton("生成审查Prompt")
        self.review_btn.setObjectName("review_btn")
        self.review_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.review_btn.clicked.connect(self._on_generate_review)
        self.review_btn.setEnabled(False)
        toolbar_layout.addWidget(self.review_btn)

        toolbar_layout.addStretch()

        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setObjectName("status_label")
        toolbar_layout.addWidget(self.status_label)

        layout.addWidget(toolbar)

        # 文件信息
        self.file_info = QLabel("选择一个文件开始编辑...")
        self.file_info.setObjectName("file_info")
        self.file_info.setWordWrap(True)
        layout.addWidget(self.file_info)

        # Prompt编辑器
        self.prompt_editor = QTextEdit()
        self.prompt_editor.setObjectName("prompt_editor")
        self.prompt_editor.setPlaceholderText(
            "选择一个文件后点击「生成Prompt」开始生成...\n\n"
            "或者直接编辑内容后点击「保存」。"
        )
        layout.addWidget(self.prompt_editor, stretch=1)

        # 审查Prompt区域
        review_header = QLabel("审查Prompt")
        review_header.setObjectName("review_header")
        layout.addWidget(review_header)

        self.review_editor = QTextEdit()
        self.review_editor.setObjectName("review_editor")
        self.review_editor.setPlaceholderText("生成实现Prompt后可生成审查Prompt...")
        self.review_editor.setMaximumHeight(dp(180))
        layout.addWidget(self.review_editor)

    def _apply_theme(self):
        """应用主题"""
        bg_color = theme_manager.book_bg_primary()

        self.setStyleSheet(f"""
            CodingWorkspace {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
        """)

        # 生成按钮
        if hasattr(self, 'generate_btn'):
            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {dp(13)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.PRIMARY_DARK};
                }}
                QPushButton:disabled {{
                    background-color: {theme_manager.TEXT_TERTIARY};
                }}
            """)

        # 保存和审查按钮
        secondary_btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {dp(13)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
            QPushButton:disabled {{
                color: {theme_manager.TEXT_TERTIARY};
                border-color: {theme_manager.TEXT_TERTIARY};
            }}
        """
        if hasattr(self, 'save_btn'):
            self.save_btn.setStyleSheet(secondary_btn_style)
        if hasattr(self, 'review_btn'):
            self.review_btn.setStyleSheet(secondary_btn_style)

        # 状态标签
        if hasattr(self, 'status_label'):
            self.status_label.setStyleSheet(f"""
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
            """)

        # 文件信息
        if hasattr(self, 'file_info'):
            self.file_info.setStyleSheet(f"""
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                padding: {dp(4)}px 0;
            """)

        # 编辑器
        editor_style = f"""
            QTextEdit {{
                background-color: {bg_color};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
                font-size: {dp(13)}px;
                font-family: Consolas, monospace;
            }}
        """
        if hasattr(self, 'prompt_editor'):
            self.prompt_editor.setStyleSheet(editor_style)
        if hasattr(self, 'review_editor'):
            self.review_editor.setStyleSheet(editor_style)

        # 审查标题
        review_header = self.findChild(QLabel, "review_header")
        if review_header:
            review_header.setStyleSheet(f"""
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                margin-top: {dp(8)}px;
            """)

    def load_file(self, file_data: Dict[str, Any], content: str = "", review_prompt: str = ""):
        """加载文件

        Args:
            file_data: 文件数据
            content: 文件内容（Prompt）
            review_prompt: 审查Prompt
        """
        self._current_file = file_data

        # 更新文件信息
        filename = file_data.get('filename', '')
        file_path = file_data.get('file_path', '')
        description = file_data.get('description', '')

        info_parts = [f"文件: {file_path}"]
        if description:
            info_parts.append(f"说明: {description}")
        self.file_info.setText(" | ".join(info_parts))

        # 更新编辑器内容
        self.prompt_editor.setPlainText(content)
        self.review_editor.setPlainText(review_prompt)

        # 启用按钮
        self.generate_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.review_btn.setEnabled(bool(content))

        # 清除状态
        self.status_label.setText("")

    def clear(self):
        """清空工作区"""
        self._current_file = None
        self.file_info.setText("选择一个文件开始编辑...")
        self.prompt_editor.clear()
        self.review_editor.clear()
        self.generate_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.review_btn.setEnabled(False)
        self.status_label.setText("")

    def get_content(self) -> str:
        """获取当前编辑内容"""
        return self.prompt_editor.toPlainText()

    def get_review_content(self) -> str:
        """获取审查Prompt内容"""
        return self.review_editor.toPlainText()

    def set_content(self, content: str):
        """设置编辑内容"""
        self.prompt_editor.setPlainText(content)

    def append_content(self, text: str):
        """追加内容（用于SSE流式）"""
        cursor = self.prompt_editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.prompt_editor.setTextCursor(cursor)
        self.prompt_editor.ensureCursorVisible()

    def set_review_content(self, content: str):
        """设置审查Prompt内容"""
        self.review_editor.setPlainText(content)

    def set_status(self, text: str):
        """设置状态文本"""
        self.status_label.setText(text)

    def set_generating(self, is_generating: bool):
        """设置生成状态"""
        self._is_generating = is_generating
        self.generate_btn.setEnabled(not is_generating and self._current_file is not None)

        if is_generating:
            self.prompt_editor.clear()
            self.set_status("正在生成...")

    def set_generate_complete(self):
        """生成完成"""
        self._is_generating = False
        self.generate_btn.setEnabled(True)
        self.review_btn.setEnabled(True)
        self.set_status("生成完成")

    def _on_generate(self):
        """生成按钮点击"""
        if self._current_file and not self._is_generating:
            self.generateRequested.emit()

    def _on_save(self):
        """保存按钮点击"""
        content = self.get_content()
        if content.strip():
            self.saveRequested.emit(content)

    def _on_generate_review(self):
        """生成审查Prompt按钮点击"""
        if self._current_file:
            self.generateReviewRequested.emit()


__all__ = ["CodingWorkspace"]
