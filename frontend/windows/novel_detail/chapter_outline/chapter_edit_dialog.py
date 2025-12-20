"""
章节大纲编辑对话框

允许用户编辑章节大纲的标题和摘要。
支持新增和编辑两种模式。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class ChapterOutlineEditDialog(QDialog):
    """章节大纲编辑对话框

    使用方式：
        # 编辑现有章节
        dialog = ChapterOutlineEditDialog(
            chapter_number=1,
            title="第一章 开端",
            summary="这是第一章的摘要...",
            parent=self
        )

        # 新增章节
        dialog = ChapterOutlineEditDialog(
            chapter_number=5,
            is_new=True,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            title, summary = dialog.get_values()
            # 处理保存...
    """

    def __init__(
        self,
        chapter_number: int,
        title: str = "",
        summary: str = "",
        is_new: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.chapter_number = chapter_number
        self._title = title
        self._summary = summary
        self._is_new = is_new

        # UI组件
        self.title_input = None
        self.summary_input = None

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI"""
        dialog_title = "新增章节大纲" if self._is_new else "编辑章节大纲"
        self.setWindowTitle(f"{dialog_title} - 第{self.chapter_number}章")
        self.setMinimumSize(dp(500), dp(400))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        # 章节编号标签
        chapter_badge = QLabel(f"第 {self.chapter_number} 章")
        chapter_badge.setObjectName("chapter_badge")
        layout.addWidget(chapter_badge)

        # 标题输入
        title_label = QLabel("章节标题")
        title_label.setObjectName("field_label")
        layout.addWidget(title_label)

        self.title_input = QLineEdit()
        self.title_input.setObjectName("title_input")
        self.title_input.setPlaceholderText("请输入章节标题...")
        self.title_input.setText(self._title)
        layout.addWidget(self.title_input)

        # 摘要输入
        summary_label = QLabel("章节摘要")
        summary_label.setObjectName("field_label")
        layout.addWidget(summary_label)

        self.summary_input = QTextEdit()
        self.summary_input.setObjectName("summary_input")
        self.summary_input.setPlaceholderText("请输入章节摘要，描述本章的主要内容和情节发展...")
        self.summary_input.setText(self._summary)
        layout.addWidget(self.summary_input, stretch=1)

        # 字数统计
        self.char_count_label = QLabel("0 字")
        self.char_count_label.setObjectName("char_count")
        self.summary_input.textChanged.connect(self._update_char_count)
        layout.addWidget(self.char_count_label)

        # 初始更新字数
        self._update_char_count()

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(12))
        btn_layout.addStretch()

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(dp(38))
        cancel_btn.setMinimumWidth(dp(80))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        # 确认按钮
        confirm_text = "新增" if self._is_new else "保存"
        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setObjectName("confirm_btn")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setFixedHeight(dp(38))
        confirm_btn.setMinimumWidth(dp(80))
        confirm_btn.clicked.connect(self._on_confirm)
        confirm_btn.setDefault(True)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _update_char_count(self):
        """更新字数统计"""
        text = self.summary_input.toPlainText()
        count = len(text)
        self.char_count_label.setText(f"{count} 字")

    def _on_confirm(self):
        """确认按钮点击"""
        title = self.title_input.text().strip()
        summary = self.summary_input.toPlainText().strip()

        # 验证
        if not title:
            self.title_input.setFocus()
            return

        self.accept()

    def get_values(self) -> tuple:
        """获取编辑后的值

        Returns:
            (title, summary) 元组
        """
        return (
            self.title_input.text().strip(),
            self.summary_input.toPlainText().strip()
        )

    def _apply_style(self):
        """应用样式"""
        ui_font = theme_manager.ui_font()
        bg_color = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        text_tertiary = theme_manager.book_text_tertiary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel#chapter_badge {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: 700;
                color: {accent_color};
                background-color: {bg_secondary};
                padding: {dp(6)}px {dp(12)}px;
                border-radius: {dp(4)}px;
                border: 1px solid {border_color};
            }}
            QLabel#field_label {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {text_primary};
            }}
            QLineEdit#title_input {{
                font-family: {ui_font};
                font-size: {sp(15)}px;
                color: {text_primary};
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(14)}px;
            }}
            QLineEdit#title_input:focus {{
                border-color: {accent_color};
            }}
            QTextEdit#summary_input {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {text_primary};
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(14)}px;
                line-height: 1.6;
            }}
            QTextEdit#summary_input:focus {{
                border-color: {accent_color};
            }}
            QLabel#char_count {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_tertiary};
            }}
            QPushButton#cancel_btn {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {text_secondary};
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
            }}
            QPushButton#cancel_btn:hover {{
                color: {accent_color};
                border-color: {accent_color};
            }}
            QPushButton#confirm_btn {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: #FFFFFF;
                background-color: {accent_color};
                border: none;
                border-radius: {dp(6)}px;
            }}
            QPushButton#confirm_btn:hover {{
                background-color: {text_primary};
            }}
        """)
