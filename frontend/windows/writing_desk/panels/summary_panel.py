"""
摘要面板构建器 - 章节摘要Tab的UI构建逻辑

从 WDWorkspace 中提取，负责创建章节摘要Tab的所有UI组件。
用于展示RAG上下文优化所需的章节摘要信息。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QWidget, QFrame, QTextEdit
)
from PyQt6.QtCore import Qt
from components.empty_state import EmptyStateWithIllustration
from utils.dpi_utils import dp, sp
from utils.formatters import count_chinese_characters, format_word_count
from .base import BasePanelBuilder


class SummaryPanelBuilder(BasePanelBuilder):
    """摘要面板构建器

    职责：创建章节摘要Tab的所有UI组件
    设计模式：工厂方法模式，将复杂的UI构建逻辑封装在独立类中
    继承自 BasePanelBuilder，使用缓存的 styler 属性减少 theme_manager 调用。
    """

    def __init__(self):
        """初始化构建器"""
        super().__init__()  # 初始化 BasePanelBuilder，获取 _styler

    def create_panel(self, data: dict) -> QWidget:
        """实现抽象方法 - 创建面板"""
        return self.create_summary_tab(data)

    def create_summary_tab(self, chapter_data: dict, parent: QWidget = None) -> QWidget:
        """创建章节摘要标签页 - 用于RAG上下文优化

        Args:
            chapter_data: 章节数据，包含 real_summary 字段
            parent: 父组件（用于空状态组件）

        Returns:
            摘要Tab的根Widget
        """
        real_summary = chapter_data.get('real_summary', '')

        # 如果没有摘要数据，显示空状态
        if not real_summary:
            return self._create_empty_state(
                title='暂无章节摘要',
                description='选择版本后系统会自动生成章节摘要，用于优化后续章节的生成效果',
                icon_char='S',
            )

        # 创建摘要展示容器
        return self._create_summary_content(real_summary)

    def _create_summary_content(self, real_summary: str) -> QWidget:
        """创建摘要内容Widget

        Args:
            real_summary: 章节摘要文本

        Returns:
            摘要内容Widget
        """
        s = self._styler

        container = QWidget()
        container.setObjectName("summary_container")
        container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {s.text_primary};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # 说明卡片
        info_card = self._build_info_card(
            object_name="summary_info_card",
            title="RAG上下文摘要",
            description="此摘要由AI根据章节内容自动生成，用于为后续章节生成提供上下文参考，确保故事连贯性和设定一致性。",
        )
        layout.addWidget(info_card)

        # 摘要内容卡片
        summary_card = self._create_summary_card(real_summary)
        layout.addWidget(summary_card, stretch=1)

        # 底部字数统计
        word_count = count_chinese_characters(real_summary)
        word_count_label = QLabel(f"摘要字数: {format_word_count(word_count)}")
        word_count_label.setObjectName("summary_word_count")
        word_count_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
            padding: {dp(4)}px 0;
        """)
        layout.addWidget(word_count_label)

        return container

    def _create_summary_card(self, real_summary: str) -> QFrame:
        """创建摘要内容卡片

        Args:
            real_summary: 摘要文本

        Returns:
            摘要内容卡片Frame
        """
        s = self._styler

        summary_card = QFrame()
        summary_card.setObjectName("summary_content_card")
        summary_card.setStyleSheet(f"""
            QFrame#summary_content_card {{
                background-color: {s.bg_secondary};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
                padding: {dp(2)}px;
            }}
        """)

        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(0, 0, 0, 0)

        # 摘要文本显示（只读）
        summary_text = QTextEdit()
        summary_text.setObjectName("summary_text_edit")
        summary_text.setPlainText(real_summary)
        summary_text.setReadOnly(True)
        summary_text.setStyleSheet(f"""
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
        summary_layout.addWidget(summary_text)

        return summary_card
