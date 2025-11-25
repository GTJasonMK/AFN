"""
部分大纲详情对话框

显示单个部分大纲的完整信息，包括主题、事件、角色发展等
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class PartOutlineDetailDialog(QDialog):
    """部分大纲详情对话框"""

    def __init__(self, part_data: dict, parent=None):
        super().__init__(parent)
        self.part_data = part_data
        self.setWindowTitle(f"部分大纲详情 - {part_data.get('title', '')}")
        self.setMinimumSize(dp(700), dp(600))
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
        self._create_basic_info(content_layout)
        self._create_theme_section(content_layout)
        self._create_summary_section(content_layout)
        self._create_events_section(content_layout)
        self._create_characters_section(content_layout)
        self._create_conflicts_section(content_layout)
        self._create_ending_hook_section(content_layout)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, stretch=1)

        # 底部按钮
        self._create_footer(layout)

    def _create_header(self, layout):
        """创建头部"""
        header = QHBoxLayout()

        # 部分编号徽章
        part_num = self.part_data.get('part_number', 1)
        badge = QLabel(f"第{part_num}部分")
        badge.setStyleSheet(f"""
            background-color: {theme_manager.PRIMARY};
            color: {theme_manager.BUTTON_TEXT};
            padding: {dp(8)}px {dp(16)}px;
            border-radius: {dp(8)}px;
            font-size: {sp(14)}px;
            font-weight: 700;
        """)
        header.addWidget(badge)

        # 章节范围
        start = self.part_data.get('start_chapter', 0)
        end = self.part_data.get('end_chapter', 0)
        range_label = QLabel(f"{start}-{end}章 · 共{end-start+1}章")
        range_label.setStyleSheet(f"""
            font-size: {sp(14)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        header.addWidget(range_label)

        header.addStretch()
        layout.addLayout(header)

        # 标题
        title = QLabel(self.part_data.get('title', ''))
        title.setWordWrap(True)
        title.setStyleSheet(f"""
            font-size: {sp(24)}px;
            font-weight: 700;
            color: {theme_manager.TEXT_PRIMARY};
            margin-bottom: {dp(8)}px;
        """)
        layout.addWidget(title)

    def _create_basic_info(self, layout):
        """创建基本信息"""
        # 生成状态和进度
        status = self.part_data.get('generation_status', 'pending')
        progress = self.part_data.get('progress', 0)

        status_map = {
            'pending': ('待生成', theme_manager.TEXT_SECONDARY),
            'generating': (f'生成中 {progress}%', theme_manager.INFO),
            'completed': ('已完成', theme_manager.SUCCESS),
            'failed': ('失败', theme_manager.ERROR),
        }

        status_text, status_color = status_map.get(status, ('未知', theme_manager.TEXT_SECONDARY))

        status_label = QLabel(f"状态：{status_text}")
        status_label.setStyleSheet(f"""
            font-size: {sp(13)}px;
            color: {status_color};
            padding: {dp(4)}px {dp(8)}px;
            background-color: {theme_manager.BG_TERTIARY};
            border-radius: {dp(4)}px;
        """)
        layout.addWidget(status_label)

    def _create_theme_section(self, layout):
        """创建主题区块"""
        theme = self.part_data.get('theme', '')
        if not theme:
            return

        card = self._create_section_card(
            "主题",
            theme,
            theme_manager.PRIMARY_PALE
        )
        layout.addWidget(card)

    def _create_summary_section(self, layout):
        """创建摘要区块"""
        summary = self.part_data.get('summary', '')
        if not summary:
            return

        card = self._create_section_card(
            "剧情摘要",
            summary,
            theme_manager.BG_CARD
        )
        layout.addWidget(card)

    def _create_events_section(self, layout):
        """创建关键事件区块"""
        events = self.part_data.get('key_events', [])
        if not events:
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
        title = QLabel("关键事件")
        title.setStyleSheet(f"""
            font-size: {sp(16)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        card_layout.addWidget(title)

        # 事件列表
        for i, event in enumerate(events, 1):
            event_label = QLabel(f"{i}. {event}")
            event_label.setWordWrap(True)
            event_label.setStyleSheet(f"""
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                padding-left: {dp(8)}px;
            """)
            card_layout.addWidget(event_label)

        layout.addWidget(card)

    def _create_characters_section(self, layout):
        """创建角色发展区块"""
        character_arcs = self.part_data.get('character_arcs', {})
        if not character_arcs:
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
        title = QLabel("角色发展")
        title.setStyleSheet(f"""
            font-size: {sp(16)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        card_layout.addWidget(title)

        # 角色列表
        for char_name, arc in character_arcs.items():
            char_card = QFrame()
            char_card.setStyleSheet(f"""
                background-color: {theme_manager.BG_TERTIARY};
                border-radius: {dp(8)}px;
                padding: {dp(12)}px;
            """)
            char_layout = QVBoxLayout(char_card)
            char_layout.setSpacing(dp(4))

            name_label = QLabel(char_name)
            name_label.setStyleSheet(f"""
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {theme_manager.PRIMARY};
            """)
            char_layout.addWidget(name_label)

            arc_label = QLabel(arc)
            arc_label.setWordWrap(True)
            arc_label.setStyleSheet(f"""
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
            """)
            char_layout.addWidget(arc_label)

            card_layout.addWidget(char_card)

        layout.addWidget(card)

    def _create_conflicts_section(self, layout):
        """创建冲突区块"""
        conflicts = self.part_data.get('conflicts', [])
        if not conflicts:
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
        title = QLabel("冲突点")
        title.setStyleSheet(f"""
            font-size: {sp(16)}px;
            font-weight: 600;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        card_layout.addWidget(title)

        # 冲突列表
        for i, conflict in enumerate(conflicts, 1):
            conflict_label = QLabel(f"{i}. {conflict}")
            conflict_label.setWordWrap(True)
            conflict_label.setStyleSheet(f"""
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                padding-left: {dp(8)}px;
            """)
            card_layout.addWidget(conflict_label)

        layout.addWidget(card)

    def _create_ending_hook_section(self, layout):
        """创建结尾钩子区块"""
        ending_hook = self.part_data.get('ending_hook', '')
        if not ending_hook:
            return

        card = self._create_section_card(
            "结尾钩子（与下一部分的衔接）",
            ending_hook,
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
