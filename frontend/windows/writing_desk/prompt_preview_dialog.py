"""
提示词预览对话框 - 用于测试RAG效果
"""

from typing import Any, Dict

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QTextEdit, QScrollArea, QFrame, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class PromptPreviewDialog(QDialog):
    """提示词预览对话框"""

    def __init__(self, preview_data: Dict[str, Any], chapter_number: int, is_retry: bool = False, parent=None):
        super().__init__(parent)
        self.preview_data = preview_data
        self.chapter_number = chapter_number
        self.is_retry = is_retry
        mode_text = "重新生成" if is_retry else "首次生成"
        self.setWindowTitle(f"第 {chapter_number} 章 - 提示词预览（{mode_text}模式）")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.setupUI()

    def setupUI(self):
        """初始化UI"""
        ui_font = theme_manager.ui_font()
        mono_font = "Consolas, 'Courier New', monospace"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))
        layout.setSpacing(dp(16))

        # 设置对话框样式
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """)

        # 顶部统计信息卡片
        stats_card = self._create_stats_card(ui_font)
        layout.addWidget(stats_card)

        # 主内容区域 - 使用TabWidget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(theme_manager.tabs())

        # Tab 1: 完整提示词
        full_prompt_tab = self._create_full_prompt_tab(mono_font)
        self.tab_widget.addTab(full_prompt_tab, "完整提示词")

        # Tab 2: 系统提示词
        system_tab = self._create_text_tab(
            self.preview_data.get('system_prompt', ''),
            mono_font,
            "系统提示词定义AI的角色和行为规范"
        )
        self.tab_widget.addTab(system_tab, "系统提示词")

        # Tab 3: 用户提示词（写作上下文）
        user_tab = self._create_text_tab(
            self.preview_data.get('user_prompt', ''),
            mono_font,
            "用户提示词包含完整的写作上下文，包括RAG检索的内容"
        )
        self.tab_widget.addTab(user_tab, "用户提示词")

        # Tab 4: 分段详情
        sections_tab = self._create_sections_tab(ui_font, mono_font)
        self.tab_widget.addTab(sections_tab, "分段详情")

        # Tab 5: RAG统计
        rag_tab = self._create_rag_stats_tab(ui_font)
        self.tab_widget.addTab(rag_tab, "RAG统计")

        layout.addWidget(self.tab_widget, stretch=1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(ButtonStyles.primary())
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(dp(100))
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _create_stats_card(self, ui_font: str) -> QFrame:
        """创建统计信息卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: {dp(16)}px;
            }}
        """)

        layout = QHBoxLayout(card)
        layout.setSpacing(dp(32))

        # 总长度
        total_length = self.preview_data.get('total_length', 0)
        layout.addWidget(self._create_stat_item(
            "总字符数",
            f"{total_length:,}",
            ui_font
        ))

        # 估算Token
        estimated_tokens = self.preview_data.get('estimated_tokens', 0)
        layout.addWidget(self._create_stat_item(
            "估算Token",
            f"{estimated_tokens:,}",
            ui_font
        ))

        # RAG片段数
        rag_stats = self.preview_data.get('rag_statistics', {})
        chunk_count = rag_stats.get('chunk_count', 0)
        layout.addWidget(self._create_stat_item(
            "RAG片段",
            str(chunk_count),
            ui_font
        ))

        # 摘要数
        summary_count = rag_stats.get('summary_count', 0)
        layout.addWidget(self._create_stat_item(
            "章节摘要",
            str(summary_count),
            ui_font
        ))

        # 上下文长度
        context_length = rag_stats.get('context_length', 0)
        layout.addWidget(self._create_stat_item(
            "上下文长度",
            f"{context_length:,}",
            ui_font
        ))

        layout.addStretch()
        return card

    def _create_stat_item(self, label: str, value: str, ui_font: str) -> QWidget:
        """创建单个统计项"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(24)}px;
            font-weight: bold;
            color: {theme_manager.PRIMARY};
        """)
        layout.addWidget(value_label)

        name_label = QLabel(label)
        name_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(name_label)

        return widget

    def _create_full_prompt_tab(self, mono_font: str) -> QWidget:
        """创建完整提示词标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # 说明
        hint = QLabel("以下是发送给LLM的完整提示词，包括系统提示词和用户提示词")
        hint.setStyleSheet(f"""
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
            padding: {dp(8)}px;
            background-color: {theme_manager.INFO_BG};
            border-radius: {dp(4)}px;
        """)
        layout.addWidget(hint)

        # 使用Splitter分割系统和用户提示词
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 系统提示词区域
        system_widget = QWidget()
        system_layout = QVBoxLayout(system_widget)
        system_layout.setContentsMargins(0, 0, 0, 0)
        system_layout.setSpacing(dp(4))

        system_label = QLabel("System Prompt")
        system_label.setStyleSheet(f"""
            font-size: {sp(13)}px;
            font-weight: bold;
            color: {theme_manager.SUCCESS};
        """)
        system_layout.addWidget(system_label)

        system_text = QTextEdit()
        system_text.setPlainText(self.preview_data.get('system_prompt', ''))
        system_text.setReadOnly(True)
        system_text.setStyleSheet(self._get_text_edit_style(mono_font))
        system_layout.addWidget(system_text)

        splitter.addWidget(system_widget)

        # 用户提示词区域
        user_widget = QWidget()
        user_layout = QVBoxLayout(user_widget)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(dp(4))

        user_label = QLabel("User Prompt (写作上下文)")
        user_label.setStyleSheet(f"""
            font-size: {sp(13)}px;
            font-weight: bold;
            color: {theme_manager.INFO};
        """)
        user_layout.addWidget(user_label)

        user_text = QTextEdit()
        user_text.setPlainText(self.preview_data.get('user_prompt', ''))
        user_text.setReadOnly(True)
        user_text.setStyleSheet(self._get_text_edit_style(mono_font))
        user_layout.addWidget(user_text)

        splitter.addWidget(user_widget)

        # 设置初始比例
        splitter.setSizes([200, 500])

        layout.addWidget(splitter, stretch=1)
        return widget

    def _create_text_tab(self, content: str, mono_font: str, description: str) -> QWidget:
        """创建文本显示标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # 说明
        hint = QLabel(description)
        hint.setStyleSheet(f"""
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
            padding: {dp(8)}px;
            background-color: {theme_manager.INFO_BG};
            border-radius: {dp(4)}px;
        """)
        layout.addWidget(hint)

        # 字数统计
        char_count = len(content)
        count_label = QLabel(f"字符数: {char_count:,}")
        count_label.setStyleSheet(f"""
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(count_label)

        # 文本编辑器
        text_edit = QTextEdit()
        text_edit.setPlainText(content)
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet(self._get_text_edit_style(mono_font))

        layout.addWidget(text_edit, stretch=1)
        return widget

    def _create_sections_tab(self, ui_font: str, mono_font: str) -> QWidget:
        """创建分段详情标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            {theme_manager.scrollbar()}
        """)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(16))

        # 说明
        hint = QLabel("提示词按功能分段展示，便于分析各部分内容")
        hint.setStyleSheet(f"""
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
            padding: {dp(8)}px;
            background-color: {theme_manager.INFO_BG};
            border-radius: {dp(4)}px;
        """)
        layout.addWidget(hint)

        # 分段内容
        sections = self.preview_data.get('prompt_sections', {})

        # 定义分段顺序和显示名称
        section_names = {
            'blueprint_core': '蓝图核心',
            'character_names': '角色名单',
            'current_outline': '当前章节大纲',
            'previous_ending': '前章结尾',
            'character_details': '角色详情',
            'foreshadowing': '伏笔信息',
            'rag_summaries': 'RAG摘要',
            'world_setting': '世界观设定',
            'rag_chunks': 'RAG检索片段',
            'writing_notes': '写作要点',
        }

        for key, display_name in section_names.items():
            content = sections.get(key, '')
            if content:
                section_card = self._create_section_card(
                    display_name,
                    content,
                    ui_font,
                    mono_font
                )
                layout.addWidget(section_card)

        # 显示未知分段
        for key, content in sections.items():
            if key not in section_names and content:
                section_card = self._create_section_card(
                    key,
                    content,
                    ui_font,
                    mono_font
                )
                layout.addWidget(section_card)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_section_card(self, title: str, content: str, ui_font: str, mono_font: str) -> QFrame:
        """创建分段卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(8))

        # 标题行
        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {theme_manager.PRIMARY};
        """)
        header.addWidget(title_label)

        char_count = len(content)
        count_label = QLabel(f"{char_count:,} 字符")
        count_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        header.addWidget(count_label)
        header.addStretch()

        layout.addLayout(header)

        # 内容
        text_edit = QTextEdit()
        text_edit.setPlainText(content)
        text_edit.setReadOnly(True)
        text_edit.setMaximumHeight(dp(200))
        text_edit.setStyleSheet(self._get_text_edit_style(mono_font))

        layout.addWidget(text_edit)
        return card

    def _create_rag_stats_tab(self, ui_font: str) -> QWidget:
        """创建RAG统计标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            {theme_manager.scrollbar()}
        """)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(16))

        rag_stats = self.preview_data.get('rag_statistics', {})

        # RAG概述卡片
        overview_card = QFrame()
        overview_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: {dp(16)}px;
            }}
        """)

        overview_layout = QVBoxLayout(overview_card)
        overview_layout.setSpacing(dp(12))

        title = QLabel("RAG检索统计")
        title.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(16)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        overview_layout.addWidget(title)

        # 统计项
        stats_items = [
            ("检索片段数", rag_stats.get('chunk_count', 0)),
            ("章节摘要数", rag_stats.get('summary_count', 0)),
            ("上下文长度", f"{rag_stats.get('context_length', 0):,} 字符"),
        ]

        for name, value in stats_items:
            item_layout = QHBoxLayout()
            name_label = QLabel(name)
            name_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
            """)
            item_layout.addWidget(name_label)

            value_label = QLabel(str(value))
            value_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(13)}px;
                font-weight: bold;
                color: {theme_manager.TEXT_PRIMARY};
            """)
            item_layout.addWidget(value_label)
            item_layout.addStretch()

            overview_layout.addLayout(item_layout)

        layout.addWidget(overview_card)

        # 查询信息卡片
        query_card = QFrame()
        query_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: {dp(16)}px;
            }}
        """)

        query_layout = QVBoxLayout(query_card)
        query_layout.setSpacing(dp(12))

        query_title = QLabel("查询构建")
        query_title.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(16)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        query_layout.addWidget(query_title)

        # 主查询
        main_query = rag_stats.get('query_main', '')
        if main_query:
            self._add_query_section(query_layout, "主查询", main_query, ui_font)

        # 角色查询
        char_queries = rag_stats.get('query_characters', [])
        if char_queries:
            self._add_query_section(query_layout, "角色查询", ", ".join(char_queries), ui_font)

        # 伏笔查询
        fs_queries = rag_stats.get('query_foreshadowing', [])
        if fs_queries:
            self._add_query_section(query_layout, "伏笔查询", ", ".join(fs_queries), ui_font)

        layout.addWidget(query_card)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _add_query_section(self, layout: QVBoxLayout, title: str, content: str, ui_font: str):
        """添加查询分区"""
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_SECONDARY};
            margin-top: {dp(8)}px;
        """)
        layout.addWidget(title_label)

        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(13)}px;
            color: {theme_manager.TEXT_PRIMARY};
            padding: {dp(8)}px;
            background-color: {theme_manager.BG_SECONDARY};
            border-radius: {dp(4)}px;
        """)
        layout.addWidget(content_label)

    def _get_text_edit_style(self, mono_font: str) -> str:
        """获取文本编辑器样式"""
        return f"""
            QTextEdit {{
                background-color: {theme_manager.BG_SECONDARY};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(4)}px;
                padding: {dp(12)}px;
                font-family: {mono_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.5;
            }}
            {theme_manager.scrollbar()}
        """
