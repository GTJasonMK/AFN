"""
CodingDesk Header组件

显示项目信息和提供导航功能。
"""

import logging
from typing import Dict, Any

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget, QMenu, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from components.base.theme_aware_widget import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class CDHeader(ThemeAwareFrame):
    """CodingDesk头部组件（主题感知）"""

    goBackClicked = pyqtSignal()
    viewDetailClicked = pyqtSignal()
    exportClicked = pyqtSignal(str)  # 导出格式

    def __init__(self, parent=None):
        self.project = None
        self.back_btn = None
        self.title_label = None
        self.subtitle_label = None
        self.detail_btn = None
        self.export_btn = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("cd_header")
        self.setFixedHeight(dp(56))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(8), dp(16), dp(8))
        layout.setSpacing(dp(12))

        # 返回按钮
        self.back_btn = QPushButton("< 返回")
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.goBackClicked.emit)
        layout.addWidget(self.back_btn)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setObjectName("header_separator")
        layout.addWidget(separator)

        # 项目信息区
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(2))

        self.title_label = QLabel("加载中...")
        self.title_label.setObjectName("project_title")
        info_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("project_subtitle")
        info_layout.addWidget(self.subtitle_label)

        layout.addWidget(info_widget)
        layout.addStretch()

        # 操作按钮区
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(dp(8))

        # 查看详情按钮
        self.detail_btn = QPushButton("项目详情")
        self.detail_btn.setObjectName("action_btn")
        self.detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_btn.clicked.connect(self.viewDetailClicked.emit)
        actions_layout.addWidget(self.detail_btn)

        # 导出按钮
        self.export_btn = QPushButton("导出")
        self.export_btn.setObjectName("action_btn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._show_export_menu)
        actions_layout.addWidget(self.export_btn)

        layout.addWidget(actions_widget)

    def _show_export_menu(self):
        """显示导出菜单"""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme_manager.book_bg_secondary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px;
            }}
            QMenu::item {{
                padding: {dp(8)}px {dp(16)}px;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            QMenu::item:selected {{
                background-color: {theme_manager.PRIMARY}15;
            }}
        """)

        md_action = menu.addAction("Markdown (.md)")
        md_action.triggered.connect(lambda: self.exportClicked.emit("md"))

        txt_action = menu.addAction("纯文本 (.txt)")
        txt_action.triggered.connect(lambda: self.exportClicked.emit("txt"))

        json_action = menu.addAction("JSON (.json)")
        json_action.triggered.connect(lambda: self.exportClicked.emit("json"))

        menu.exec(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))

    def setProject(self, project: Dict[str, Any]):
        """设置项目数据"""
        self.project = project
        if not project:
            return

        title = project.get('title', '未命名项目')
        self.title_label.setText(title)

        # 从blueprint获取信息
        blueprint = project.get('blueprint') or {}
        summary = blueprint.get('one_sentence_summary', '')
        if summary:
            self.subtitle_label.setText(summary[:50] + '...' if len(summary) > 50 else summary)
        else:
            project_type = blueprint.get('project_type_desc', '编程项目')
            self.subtitle_label.setText(project_type)

    def _apply_theme(self):
        """应用主题样式"""
        from themes.modern_effects import ModernEffects

        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        header_opacity = theme_manager.get_component_opacity("header")

        if transparency_enabled:
            header_bg = ModernEffects.hex_to_rgba(
                theme_manager.book_bg_primary(),
                header_opacity
            )
        else:
            header_bg = theme_manager.book_bg_primary()

        self.setStyleSheet(f"""
            QFrame#cd_header {{
                background-color: {header_bg};
                border-bottom: 1px solid {theme_manager.BORDER_DEFAULT};
            }}
            QPushButton#back_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: none;
                font-size: {dp(13)}px;
                padding: {dp(4)}px {dp(8)}px;
            }}
            QPushButton#back_btn:hover {{
                background-color: {theme_manager.PRIMARY}10;
                border-radius: {dp(4)}px;
            }}
            QFrame#header_separator {{
                background-color: {theme_manager.BORDER_DEFAULT};
                max-width: 1px;
            }}
            QLabel#project_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(16)}px;
                font-weight: 600;
            }}
            QLabel#project_subtitle {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(12)}px;
            }}
            QPushButton#action_btn {{
                background-color: transparent;
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                font-size: {dp(12)}px;
                padding: {dp(6)}px {dp(12)}px;
            }}
            QPushButton#action_btn:hover {{
                background-color: {theme_manager.PRIMARY}10;
                color: {theme_manager.PRIMARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """)


__all__ = ["CDHeader"]
