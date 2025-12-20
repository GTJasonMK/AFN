"""
正文面板构建器 - 章节正文Tab的UI构建逻辑

从 WDWorkspace 中提取，负责创建章节正文Tab的所有UI组件。
包含章节内容编辑器、字数统计、保存功能等。
"""

from typing import Callable, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame,
    QTextEdit, QPushButton
)
from PyQt6.QtCore import Qt
from themes.button_styles import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.formatters import count_chinese_characters, format_word_count
from .base import BasePanelBuilder


class ContentPanelBuilder(BasePanelBuilder):
    """正文面板构建器

    职责：创建章节正文Tab的所有UI组件
    设计模式：工厂方法模式，将复杂的UI构建逻辑封装在独立类中

    使用回调函数模式处理用户交互，避免与父组件的信号耦合。
    继承自 BasePanelBuilder，使用缓存的 styler 属性减少 theme_manager 调用。
    """

    def __init__(
        self,
        on_save_content: Optional[Callable[[], None]] = None,
        on_rag_ingest: Optional[Callable[[], None]] = None
    ):
        """初始化构建器

        Args:
            on_save_content: 保存内容回调函数（仅保存，不触发RAG处理）
            on_rag_ingest: RAG入库回调函数（执行摘要生成、分析、索引、向量入库）
        """
        super().__init__()  # 初始化 BasePanelBuilder，获取 _styler
        self._on_save_content = on_save_content
        self._on_rag_ingest = on_rag_ingest
        self._content_text: Optional[QTextEdit] = None

    @property
    def content_text(self) -> Optional[QTextEdit]:
        """获取内容编辑器引用，用于外部读取内容"""
        return self._content_text

    def create_panel(self, data: dict) -> QWidget:
        """实现抽象方法 - 创建面板"""
        return self.create_content_tab(data)

    def create_content_tab(self, chapter_data: dict, parent: QWidget = None) -> QWidget:
        """创建正文标签页 - 现代化设计（内容优先）

        Args:
            chapter_data: 章节数据，包含 content 字段
            parent: 父组件

        Returns:
            正文Tab的根Widget
        """
        s = self._styler  # 使用缓存的样式器属性

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

        content = chapter_data.get('content', '')

        # 工具栏
        toolbar = self._create_toolbar(content)
        layout.addWidget(toolbar)

        # 章节内容编辑器
        editor_container = self._create_editor_container(content)
        layout.addWidget(editor_container, stretch=1)

        return container

    def _create_toolbar(self, content: str) -> QFrame:
        """创建工具栏

        Args:
            content: 章节内容

        Returns:
            工具栏Frame
        """
        s = self._styler

        toolbar = QFrame()
        toolbar.setObjectName("content_toolbar")
        toolbar.setStyleSheet(f"""
            QFrame#content_toolbar {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
                padding: {dp(6)}px {dp(10)}px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setSpacing(dp(10))
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # 字数统计
        word_count = count_chinese_characters(content) if content else 0
        word_count_label = QLabel(f"字数：{format_word_count(word_count)}")
        word_count_label.setObjectName("word_count_label")
        word_count_label.setStyleSheet(f"""
            font-family: {s.serif_font};
            font-size: {sp(13)}px;
            color: {s.text_secondary};
            font-weight: 500;
        """)
        toolbar_layout.addWidget(word_count_label)

        # 状态提示
        if not content:
            status_label = QLabel("* 尚未生成")
            status_label.setObjectName("status_label")
            status_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(13)}px;
                color: {s.text_warning};
            """)
            toolbar_layout.addWidget(status_label)

        toolbar_layout.addStretch()

        # 保存按钮（仅保存内容，不触发RAG处理）
        save_btn = QPushButton("保存内容")
        save_btn.setObjectName("save_btn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(ButtonStyles.primary('SM'))
        save_btn.setToolTip("保存章节内容（不执行RAG处理）")
        if self._on_save_content:
            save_btn.clicked.connect(self._on_save_content)
        toolbar_layout.addWidget(save_btn)

        # RAG入库按钮（执行完整RAG处理：摘要、分析、索引、向量入库）
        rag_btn = QPushButton("RAG入库")
        rag_btn.setObjectName("rag_btn")
        rag_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rag_btn.setStyleSheet(ButtonStyles.secondary('SM'))
        rag_btn.setToolTip("保存并执行RAG处理：生成摘要、分析角色状态和伏笔、更新索引、向量入库")
        if self._on_rag_ingest:
            rag_btn.clicked.connect(self._on_rag_ingest)
        toolbar_layout.addWidget(rag_btn)

        return toolbar

    def _create_editor_container(self, content: str) -> QFrame:
        """创建编辑器容器

        Args:
            content: 章节内容

        Returns:
            编辑器容器Frame
        """
        s = self._styler

        editor_container = QFrame()
        editor_container.setObjectName("editor_container")
        editor_container.setStyleSheet(f"""
            QFrame#editor_container {{
                background-color: {s.bg_secondary};
                border: 1px solid {s.border_light};
                border-radius: {dp(8)}px;
                padding: {dp(2)}px;
            }}
        """)

        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        # 文本编辑器
        self._content_text = QTextEdit()
        self._content_text.setPlainText(
            content if content else '暂无内容，请点击"生成章节"按钮'
        )
        self._content_text.setReadOnly(False)
        self._content_text.setStyleSheet(f"""
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
        editor_layout.addWidget(self._content_text)

        return editor_container

    def get_content(self) -> str:
        """获取当前编辑器中的内容

        Returns:
            编辑器中的文本内容
        """
        if self._content_text:
            return self._content_text.toPlainText()
        return ''

    def set_content(self, content: str):
        """设置编辑器内容

        Args:
            content: 要设置的文本内容
        """
        if self._content_text:
            self._content_text.setPlainText(content)
