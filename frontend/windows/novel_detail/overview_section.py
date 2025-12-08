"""
项目概览 Section - 现代化设计

展示项目的核心摘要和基本信息，采用卡片式布局
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes import ModernEffects
from utils.dpi_utils import dp, sp


class OverviewSection(ThemeAwareWidget):
    """项目概览组件 - 现代化卡片设计"""

    editRequested = pyqtSignal(str, str, object)

    def __init__(self, data=None, editable=True, parent=None):
        self.data = data or {}
        self.editable = editable

        # 保存组件引用
        self.summary_card = None
        self.summary_content = None
        self.field_cards = {}
        self.synopsis_card = None
        self.synopsis_content = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(20))

        # 顶部：核心摘要卡片（突出显示）
        self.summary_card = self._createSummaryCard()
        layout.addWidget(self.summary_card)

        # 中间：元信息网格（2x2布局）
        meta_grid = self._createMetaGrid()
        layout.addWidget(meta_grid)

        # 底部：完整剧情梗概
        self.synopsis_card = self._createSynopsisCard()
        layout.addWidget(self.synopsis_card)

        layout.addStretch()

    def _createSummaryCard(self):
        """创建核心摘要卡片 - 带渐变边框"""
        card = QFrame()
        card.setObjectName("summary_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(24), dp(20), dp(24), dp(20))
        layout.setSpacing(dp(12))

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        # 图标
        icon = QLabel("\u2728")  # 星星图标
        icon.setStyleSheet(f"font-size: {sp(18)}px;")
        header.addWidget(icon)

        title = QLabel("核心摘要")
        title.setObjectName("summary_title")
        header.addWidget(title)

        header.addStretch()

        if self.editable:
            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("edit_btn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda: self.editRequested.emit(
                'one_sentence_summary', '核心摘要', self.data.get('one_sentence_summary')
            ))
            header.addWidget(edit_btn)

        layout.addLayout(header)

        # 摘要内容
        self.summary_content = QLabel(self.data.get('one_sentence_summary') or '暂无核心摘要，点击编辑添加')
        self.summary_content.setObjectName("summary_content")
        self.summary_content.setWordWrap(True)
        layout.addWidget(self.summary_content)

        return card

    def _createMetaGrid(self):
        """创建元信息网格"""
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(dp(16))

        # 定义字段
        fields = [
            ('genre', '类型', '*'),      # 书本图标
            ('target_audience', '目标读者', '*'),  # 人群图标
            ('style', '写作风格', '*'),   # 写字图标
            ('tone', '情感基调', '*')     # 面具图标
        ]

        for idx, (field_key, field_label, icon) in enumerate(fields):
            row = idx // 2
            col = idx % 2

            card = self._createFieldCard(field_key, field_label, icon)
            grid.addWidget(card, row, col)
            self.field_cards[field_key] = card

        return container

    def _createFieldCard(self, field_key, field_label, icon):
        """创建字段卡片"""
        card = QFrame()
        card.setObjectName(f"field_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(20), dp(16), dp(20), dp(16))
        layout.setSpacing(dp(8))

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: {sp(16)}px;")
        header.addWidget(icon_label)

        label = QLabel(field_label)
        label.setObjectName("field_label")
        header.addWidget(label)

        header.addStretch()

        if self.editable:
            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("field_edit_btn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setFixedSize(dp(48), dp(24))
            edit_btn.clicked.connect(lambda: self.editRequested.emit(
                field_key, field_label, self.data.get(field_key)
            ))
            header.addWidget(edit_btn)

        layout.addLayout(header)

        # 字段值
        value = QLabel(self.data.get(field_key) or '暂无')
        value.setObjectName("field_value")
        value.setWordWrap(True)
        layout.addWidget(value)

        # 存储value引用
        card.value_label = value

        return card

    def _createSynopsisCard(self):
        """创建剧情梗概卡片"""
        card = QFrame()
        card.setObjectName("synopsis_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(24), dp(20), dp(24), dp(20))
        layout.setSpacing(dp(12))

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        icon = QLabel("*")  # 备忘录图标
        icon.setStyleSheet(f"font-size: {sp(18)}px;")
        header.addWidget(icon)

        title = QLabel("完整剧情梗概")
        title.setObjectName("synopsis_title")
        header.addWidget(title)

        header.addStretch()

        if self.editable:
            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("edit_btn")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda: self.editRequested.emit(
                'full_synopsis', '完整剧情梗概', self.data.get('full_synopsis')
            ))
            header.addWidget(edit_btn)

        layout.addLayout(header)

        # 梗概内容
        self.synopsis_content = QLabel(self.data.get('full_synopsis') or '暂无完整剧情梗概，点击编辑添加')
        self.synopsis_content.setObjectName("synopsis_content")
        self.synopsis_content.setWordWrap(True)
        layout.addWidget(self.synopsis_content)

        return card

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格"""
        # 使用 theme_manager 的书香风格便捷方法
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        text_tertiary = theme_manager.book_text_tertiary()  # 使用 theme_manager 的三级文字色
        border_color = theme_manager.book_border_color()
        highlight_color = theme_manager.book_accent_color()
        bg_card = "transparent"
        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        # 核心摘要卡片 - 简约风格
        if self.summary_card:
            self.summary_card.setStyleSheet(f"""
                #summary_card {{
                    background-color: {bg_card};
                    border: none;
                    border-bottom: 1px solid {border_color};
                }}
                #summary_title {{
                    font-family: {ui_font};
                    font-size: {sp(18)}px;
                    font-weight: bold;
                    color: {highlight_color};
                }}
                #summary_content {{
                    font-family: {serif_font};
                    font-size: {sp(20)}px;
                    color: {text_primary};
                    line-height: 1.6;
                    min-height: {dp(48)}px;
                    font-style: italic;
                }}
                #edit_btn {{
                    background: transparent;
                    border: none;
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                    color: {text_tertiary};
                    text-decoration: underline;
                }}
                #edit_btn:hover {{
                    color: {highlight_color};
                }}
            """)

        # 字段卡片样式
        field_card_style = f"""
            #field_card {{
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
            }}
            #field_label {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                font-weight: bold;
                color: {text_secondary};
            }}
            #field_value {{
                font-family: {ui_font};
                font-size: {sp(15)}px;
                color: {text_primary};
                min-height: {dp(24)}px;
            }}
            #field_edit_btn {{
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(11)}px;
                color: {text_tertiary};
                text-decoration: underline;
            }}
            #field_edit_btn:hover {{
                color: {highlight_color};
            }}
        """

        for field_key, card in self.field_cards.items():
            card.setStyleSheet(field_card_style)

        # 剧情梗概卡片
        if self.synopsis_card:
            self.synopsis_card.setStyleSheet(f"""
                #synopsis_card {{
                    background-color: {bg_card};
                    border: none;
                    border-top: 1px solid {border_color};
                }}
                #synopsis_title {{
                    font-family: {ui_font};
                    font-size: {sp(18)}px;
                    font-weight: bold;
                    color: {text_primary};
                }}
                #synopsis_content {{
                    font-family: {serif_font};
                    font-size: {sp(16)}px;
                    color: {text_secondary};
                    line-height: 1.8;
                }}
                #edit_btn {{
                    background: transparent;
                    border: none;
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                    color: {text_tertiary};
                    text-decoration: underline;
                }}
                #edit_btn:hover {{
                    color: {highlight_color};
                }}
            """)

    def updateData(self, new_data):
        """更新数据并刷新显示（避免重建组件）"""
        self.data = new_data

        # 更新核心摘要
        if self.summary_content:
            summary = new_data.get('one_sentence_summary') or '暂无核心摘要，点击编辑添加'
            self.summary_content.setText(summary)

        # 更新字段卡片
        for field_key, card in self.field_cards.items():
            if hasattr(card, 'value_label'):
                field_value = new_data.get(field_key) or '暂无'
                card.value_label.setText(field_value)

        # 更新完整剧情梗概
        if self.synopsis_content:
            synopsis = new_data.get('full_synopsis') or '暂无完整剧情梗概，点击编辑添加'
            self.synopsis_content.setText(synopsis)