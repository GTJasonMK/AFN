"""
章节大纲编辑对话框

用于在写作台直接修改章节标题和摘要
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QTextEdit, QDialog
)
from PyQt6.QtCore import Qt
from components.dialogs import BaseDialog
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from typing import Tuple


class OutlineEditDialog(BaseDialog):
    """章节大纲编辑对话框"""

    def __init__(
        self,
        parent=None,
        chapter_number: int = 1,
        title: str = "",
        summary: str = ""
    ):
        self.chapter_number = chapter_number
        self.current_title = title
        self.current_summary = summary

        # UI组件引用
        self.container = None
        self.title_edit = None
        self.summary_edit = None
        self.ok_btn = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("outline_edit_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题行
        header_label = QLabel(f"编辑第 {self.chapter_number} 章大纲")
        header_label.setObjectName("dialog_header")
        container_layout.addWidget(header_label)

        # 章节标题输入
        title_label = QLabel("章节标题")
        title_label.setObjectName("field_label")
        container_layout.addWidget(title_label)

        self.title_edit = QLineEdit(self.current_title)
        self.title_edit.setObjectName("title_input")
        self.title_edit.setFixedHeight(dp(40))
        self.title_edit.setPlaceholderText("请输入章节标题")
        container_layout.addWidget(self.title_edit)

        # 章节摘要输入
        summary_label = QLabel("章节摘要")
        summary_label.setObjectName("field_label")
        container_layout.addWidget(summary_label)

        self.summary_edit = QTextEdit()
        self.summary_edit.setPlainText(self.current_summary)
        self.summary_edit.setObjectName("summary_input")
        self.summary_edit.setMinimumHeight(dp(160))
        self.summary_edit.setPlaceholderText("请输入章节摘要...")
        container_layout.addWidget(self.summary_edit)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("保存")
        self.ok_btn.setObjectName("ok_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(80))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)
        layout.addWidget(self.container)

        # 设置对话框大小
        self.setFixedWidth(dp(500))

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 容器样式
        self.container.setStyleSheet(f"""
            #outline_edit_container {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(16)}px;
            }}
        """)

        # 标题样式
        if header := self.findChild(QLabel, "dialog_header"):
            header.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(18)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
                margin-bottom: {dp(8)}px;
            """)

        # 字段标签样式
        for label in self.findChildren(QLabel, "field_label"):
            label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: 500;
                color: {theme_manager.TEXT_SECONDARY};
            """)

        # 输入框通用样式
        input_style = f"""
            font-family: {ui_font};
            background-color: {theme_manager.BG_SECONDARY};
            color: {theme_manager.TEXT_PRIMARY};
            border: 1px solid {theme_manager.BORDER_DEFAULT};
            border-radius: {dp(8)}px;
            padding: {dp(8)}px {dp(12)}px;
            font-size: {sp(14)}px;
        """

        # 标题输入框
        self.title_edit.setStyleSheet(f"""
            #title_input {{
                {input_style}
            }}
            #title_input:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """)

        # 摘要输入框
        self.summary_edit.setStyleSheet(f"""
            #summary_input {{
                {input_style}
            }}
            #summary_input:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
            }}
            {theme_manager.scrollbar()}
        """)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(f"""
            #cancel_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 500;
            }}
            #cancel_btn:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.BORDER_DARK};
            }}
            #cancel_btn:pressed {{
                background-color: {theme_manager.BORDER_LIGHT};
            }}
        """)

        # 确定按钮样式
        self.ok_btn.setStyleSheet(f"""
            #ok_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            #ok_btn:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
            }}
            #ok_btn:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)

    def getValues(self) -> Tuple[str, str]:
        """获取输入值 (title, summary)"""
        return self.title_edit.text().strip(), self.summary_edit.toPlainText().strip()

    @staticmethod
    def getOutlineStatic(
        parent=None,
        chapter_number: int = 1,
        title: str = "",
        summary: str = ""
    ) -> Tuple[str, str, bool]:
        """静态方法：显示对话框并获取结果"""
        dialog = OutlineEditDialog(parent, chapter_number, title, summary)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            t, s = dialog.getValues()
            return t, s, True
        return "", "", False
