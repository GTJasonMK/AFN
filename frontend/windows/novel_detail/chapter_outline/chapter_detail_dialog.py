"""
章节大纲详情对话框

显示单个章节大纲的完整信息
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class ChapterOutlineDetailDialog(QDialog):
    """章节大纲详情对话框"""

    def __init__(self, chapter_data: dict, parent=None):
        super().__init__(parent)
        self.chapter_data = chapter_data
        chapter_num = chapter_data.get('chapter_number', 0)
        title = chapter_data.get('title', f'第{chapter_num}章')
        self.setWindowTitle(f"章节大纲详情 - {title}")
        self.setMinimumSize(dp(600), dp(500))
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        # 标题区域
        self._create_header(layout)

        # 滚动内容区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(dp(20))

        # 各个信息区块
        self._create_summary_section(content_layout)
        self._create_key_points_section(content_layout)
        self._create_characters_section(content_layout)
        self._create_notes_section(content_layout)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, stretch=1)

        # 底部按钮
        self._create_footer(layout)

    def _create_header(self, layout):
        """创建头部"""
        header = QHBoxLayout()

        # 章节编号徽章
        chapter_num = self.chapter_data.get('chapter_number', 1)
        badge = QLabel(f"第{chapter_num}章")
        badge.setStyleSheet(f"""
            background-color: {theme_manager.PRIMARY};
            color: {theme_manager.BUTTON_TEXT};
            padding: {dp(8)}px {dp(16)}px;
            border-radius: {dp(8)}px;
            font-size: {sp(14)}px;
            font-weight: 700;
        """)
        header.addWidget(badge)

        header.addStretch()
        layout.addLayout(header)

        # 标题
        title = QLabel(self.chapter_data.get('title', f'第{chapter_num}章'))
        title.setWordWrap(True)
        title.setStyleSheet(f"""
            font-size: {sp(24)}px;
            font-weight: 700;
            color: {theme_manager.TEXT_PRIMARY};
            margin-bottom: {dp(8)}px;
        """)
        layout.addWidget(title)

    def _create_summary_section(self, layout):
        """创建摘要区块"""
        summary = self.chapter_data.get('summary', '')
        if not summary:
            return

        card = self._create_section_card(
            "章节摘要",
            summary,
            theme_manager.BG_CARD
        )
        layout.addWidget(card)

    def _create_key_points_section(self, layout):
        """创建关键情节点区块"""
        key_points = self.chapter_data.get('key_points', [])
        if not key_points:
            return

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(12)}px;
                padding: {dp(16)}px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(dp(12))

        # 标题
        title = QLabel("关键情节点")
        title.setStyleSheet(f"""
            font-size: {sp(16)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        card_layout.addWidget(title)

        # 情节点列表
        for i, point in enumerate(key_points, 1):
            point_label = QLabel(f"{i}. {point}")
            point_label.setWordWrap(True)
            point_label.setStyleSheet(f"""
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                padding-left: {dp(8)}px;
            """)
            card_layout.addWidget(point_label)

        layout.addWidget(card)

    def _create_characters_section(self, layout):
        """创建出场角色区块"""
        characters = self.chapter_data.get('characters', [])
        if not characters:
            return

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(12)}px;
                padding: {dp(16)}px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(dp(12))

        # 标题
        title = QLabel("出场角色")
        title.setStyleSheet(f"""
            font-size: {sp(16)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        card_layout.addWidget(title)

        # 角色列表（横向显示）
        chars_layout = QHBoxLayout()
        chars_layout.setSpacing(dp(8))

        for char in characters:
            char_name = char if isinstance(char, str) else char.get('name', '')
            char_label = QLabel(char_name)
            char_label.setStyleSheet(f"""
                background-color: {theme_manager.PRIMARY_PALE};
                color: {theme_manager.PRIMARY};
                padding: {dp(4)}px {dp(12)}px;
                border-radius: {dp(12)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
            """)
            chars_layout.addWidget(char_label)

        chars_layout.addStretch()
        card_layout.addLayout(chars_layout)

        layout.addWidget(card)

    def _create_notes_section(self, layout):
        """创建备注区块"""
        notes = self.chapter_data.get('notes', '')
        if not notes:
            return

        card = self._create_section_card(
            "备注",
            notes,
            theme_manager.WARNING_BG
        )
        layout.addWidget(card)

    def _create_section_card(self, title_text: str, content_text: str, bg_color: str):
        """创建通用区块卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(12)}px;
                padding: {dp(16)}px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(dp(8))

        # 标题
        title = QLabel(title_text)
        title.setStyleSheet(f"""
            font-size: {sp(16)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        card_layout.addWidget(title)

        # 内容
        content = QLabel(content_text)
        content.setWordWrap(True)
        content.setStyleSheet(f"""
            font-size: {sp(14)}px;
            color: {theme_manager.TEXT_SECONDARY};
            line-height: 1.6;
        """)
        card_layout.addWidget(content)

        return card

    def _create_footer(self, layout):
        """创建底部按钮"""
        footer = QHBoxLayout()
        footer.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(ButtonStyles.primary())
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

    def _apply_style(self):
        """应用对话框样式"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)
