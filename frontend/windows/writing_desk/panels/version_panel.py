"""
版本面板构建器 - 章节版本Tab的UI构建逻辑

从 WDWorkspace 中提取，负责创建版本对比Tab的所有UI组件。
包含版本内容显示、版本选择、重新生成等功能。
"""

from typing import Callable, Optional, List
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QTextEdit, QPushButton, QTabWidget
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from themes.button_styles import ButtonStyles
from components.empty_state import EmptyStateWithIllustration
from utils.dpi_utils import dp, sp
from utils.formatters import count_chinese_characters, format_word_count
from .base import BasePanelBuilder


class VersionPanelBuilder(BasePanelBuilder):
    """版本面板构建器

    职责：创建章节版本Tab的所有UI组件
    设计模式：工厂方法模式，将复杂的UI构建逻辑封装在独立类中

    使用回调函数模式处理用户交互，避免与父组件的信号耦合。
    继承自 BasePanelBuilder，使用缓存的 styler 属性减少 theme_manager 调用。
    """

    def __init__(
        self,
        on_select_version: Optional[Callable[[int], None]] = None,
        on_retry_version: Optional[Callable[[int], None]] = None
    ):
        """初始化构建器

        Args:
            on_select_version: 选择版本回调函数，参数为版本索引
            on_retry_version: 重新生成版本回调函数，参数为版本索引
        """
        super().__init__()  # 初始化 BasePanelBuilder，获取 _styler
        self._on_select_version = on_select_version
        self._on_retry_version = on_retry_version

    def create_panel(self, data: dict) -> QWidget:
        """实现抽象方法 - 创建面板"""
        return self.create_versions_tab(data)

    def create_versions_tab(self, chapter_data: dict, parent: QWidget = None) -> QWidget:
        """创建版本对比标签页

        Args:
            chapter_data: 章节数据，包含 versions 和 selected_version 字段
            parent: 父组件（用于空状态组件）

        Returns:
            版本Tab的根Widget
        """
        s = self._styler  # 使用缓存的样式器属性
        versions = chapter_data.get('versions') or []
        selected_idx = chapter_data.get('selected_version')

        # 如果没有版本数据，使用专业空状态组件
        if not versions:
            return EmptyStateWithIllustration(
                illustration_char='V',
                title='暂无版本',
                description='生成章节后，AI会创建3个候选版本供你选择\n请点击顶部的"生成章节"按钮',
                parent=parent
            )

        # 创建版本对比容器
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {s.text_primary};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(10))

        # 版本TabWidget
        version_tabs = QTabWidget()
        version_tabs.setStyleSheet(theme_manager.tabs())

        for idx, version_content in enumerate(versions):
            # 创建单个版本widget
            version_widget = self._create_single_version_widget(
                idx, version_content, selected_idx
            )

            # Tab标题
            tab_title = f"版本 {idx + 1}"
            if idx == selected_idx:
                tab_title += " *"

            version_tabs.addTab(version_widget, tab_title)

        layout.addWidget(version_tabs, stretch=1)
        return container

    def _create_single_version_widget(
        self,
        version_index: int,
        content: str,
        selected_idx: Optional[int]
    ) -> QWidget:
        """创建单个版本的widget

        Args:
            version_index: 版本索引
            content: 版本内容
            selected_idx: 当前选中的版本索引

        Returns:
            单个版本的Widget
        """
        s = self._styler

        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))

        # 内容显示区 - 使用卡片样式
        content_card = QFrame()
        content_card.setObjectName(f"version_card_{version_index}")
        content_card.setStyleSheet(f"""
            QFrame#version_card_{version_index} {{
                background-color: {s.bg_secondary};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
                padding: {dp(2)}px;
            }}
        """)

        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 文本显示（只读）
        text_edit = QTextEdit()
        text_edit.setPlainText(content)
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {s.bg_card};
                border: none;
                padding: {dp(16)}px;
                font-family: {s.serif_font};
                font-size: {sp(15)}px;
                color: {s.text_primary};
                line-height: 1.8;
            }}
            {s.scrollbar_style()}
        """)
        content_layout.addWidget(text_edit)

        layout.addWidget(content_card, stretch=1)

        # 底部信息栏
        info_bar = self._create_info_bar(version_index, content, selected_idx)
        layout.addWidget(info_bar)

        return widget

    def _create_info_bar(
        self,
        version_index: int,
        content: str,
        selected_idx: Optional[int]
    ) -> QFrame:
        """创建版本信息栏

        Args:
            version_index: 版本索引
            content: 版本内容
            selected_idx: 当前选中的版本索引

        Returns:
            信息栏Frame
        """
        s = self._styler

        info_bar = QFrame()
        info_bar.setObjectName(f"version_info_bar_{version_index}")
        info_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
                padding: {dp(8)}px {dp(12)}px;
            }}
        """)

        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(8))

        # 字数统计
        word_count = count_chinese_characters(content)
        info_label = QLabel(f"{format_word_count(word_count)}")
        info_label.setObjectName(f"version_info_label_{version_index}")
        info_label.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        info_layout.addWidget(info_label)
        info_layout.addStretch()

        # 操作按钮
        if version_index == selected_idx:
            select_btn = QPushButton("已选择")
            select_btn.setObjectName(f"version_select_btn_{version_index}")
            select_btn.setEnabled(False)
            select_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {s.serif_font};
                    background: {s.success};
                    color: {s.button_text};
                    border: none;
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-size: {sp(12)}px;
                }}
            """)
        else:
            select_btn = QPushButton("选择")
            select_btn.setObjectName(f"version_select_btn_{version_index}")
            select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            select_btn.setStyleSheet(ButtonStyles.primary('SM'))
            if self._on_select_version:
                select_btn.clicked.connect(
                    lambda checked, idx=version_index: self._on_select_version(idx)
                )

        info_layout.addWidget(select_btn)

        # 重新生成按钮
        retry_btn = QPushButton("重新生成")
        retry_btn.setObjectName(f"version_retry_btn_{version_index}")
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.setStyleSheet(ButtonStyles.secondary('SM'))
        if self._on_retry_version:
            retry_btn.clicked.connect(
                lambda checked, idx=version_index: self._on_retry_version(idx)
            )
        info_layout.addWidget(retry_btn)

        return info_bar
