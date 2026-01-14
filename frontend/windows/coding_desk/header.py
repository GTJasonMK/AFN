"""
编程项目工作台Header

显示项目信息和操作按钮。
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal

from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class CodingDeskHeader(ThemeAwareFrame):
    """编程项目工作台Header

    布局：
    - 返回按钮
    - 项目标题（可点击进入详情页）
    - 当前文件路径
    - 项目详情按钮
    - RAG助手切换按钮
    """

    goBackClicked = pyqtSignal()  # 返回信号
    goToDetailClicked = pyqtSignal()  # 进入详情页信号
    toggleAssistantClicked = pyqtSignal(bool)  # 切换助手面板信号

    def __init__(self, parent=None):
        self._project_title = "加载中..."
        self._current_file_path = ""
        self._assistant_visible = True

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setFixedHeight(dp(56))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(8), dp(16), dp(8))
        layout.setSpacing(dp(12))

        # 返回按钮
        self.back_btn = QPushButton("< 返回")
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(lambda: self.goBackClicked.emit())
        layout.addWidget(self.back_btn)

        # 分隔线
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedWidth(1)
        sep1.setObjectName("separator")
        layout.addWidget(sep1)

        # 项目标题
        self.title_label = QLabel(self._project_title)
        self.title_label.setObjectName("title_label")
        layout.addWidget(self.title_label)

        # 分隔线
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedWidth(1)
        sep2.setObjectName("separator")
        layout.addWidget(sep2)

        # 当前文件路径
        self.file_path_label = QLabel("")
        self.file_path_label.setObjectName("file_path_label")
        self.file_path_label.setVisible(False)
        layout.addWidget(self.file_path_label)

        layout.addStretch()

        # 项目详情按钮
        self.detail_btn = QPushButton("项目详情")
        self.detail_btn.setObjectName("detail_btn")
        self.detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_btn.clicked.connect(lambda: self.goToDetailClicked.emit())
        layout.addWidget(self.detail_btn)

        # RAG助手切换按钮
        self.toggle_assistant_btn = QPushButton("RAG助手")
        self.toggle_assistant_btn.setObjectName("toggle_btn")
        self.toggle_assistant_btn.setCheckable(True)
        self.toggle_assistant_btn.setChecked(True)
        self.toggle_assistant_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_assistant_btn.clicked.connect(self._on_toggle_assistant)
        layout.addWidget(self.toggle_assistant_btn)

    def _apply_theme(self):
        """应用主题"""
        self.setStyleSheet(f"""
            CodingDeskHeader {{
                background-color: {theme_manager.book_bg_secondary()};
                border-bottom: 1px solid {theme_manager.BORDER_DEFAULT};
            }}
        """)

        # 返回按钮
        if hasattr(self, 'back_btn'):
            self.back_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme_manager.PRIMARY};
                    border: none;
                    font-size: {dp(13)}px;
                    padding: {dp(6)}px {dp(12)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.PRIMARY}10;
                    border-radius: {dp(4)}px;
                }}
            """)

        # 分隔线
        for sep in self.findChildren(QFrame, "separator"):
            sep.setStyleSheet(f"background-color: {theme_manager.BORDER_DEFAULT};")

        # 标题
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"""
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(15)}px;
                font-weight: 600;
            """)

        # 文件路径
        if hasattr(self, 'file_path_label'):
            self.file_path_label.setStyleSheet(f"""
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
                font-family: Consolas, monospace;
            """)

        # 详情按钮
        if hasattr(self, 'detail_btn'):
            self.detail_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme_manager.TEXT_SECONDARY};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-size: {dp(12)}px;
                }}
                QPushButton:hover {{
                    color: {theme_manager.PRIMARY};
                    border-color: {theme_manager.PRIMARY};
                    background-color: {theme_manager.PRIMARY}10;
                }}
            """)

        # 切换按钮
        if hasattr(self, 'toggle_assistant_btn'):
            self.toggle_assistant_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme_manager.PRIMARY};
                    border: 1px solid {theme_manager.PRIMARY};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-size: {dp(12)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.PRIMARY}10;
                }}
                QPushButton:checked {{
                    background-color: {theme_manager.PRIMARY};
                    color: white;
                }}
            """)

    def set_project_title(self, title: str):
        """设置项目标题"""
        self._project_title = title
        self.title_label.setText(title)

    def set_current_file(self, file_path: str):
        """设置当前文件路径"""
        self._current_file_path = file_path
        self.file_path_label.setText(file_path)
        self.file_path_label.setVisible(bool(file_path))

    def clear_current_file(self):
        """清除当前文件"""
        self._current_file_path = ""
        self.file_path_label.setText("")
        self.file_path_label.setVisible(False)

    def _on_toggle_assistant(self, checked: bool):
        """切换助手面板"""
        self._assistant_visible = checked
        self.toggleAssistantClicked.emit(checked)


__all__ = ["CodingDeskHeader"]
