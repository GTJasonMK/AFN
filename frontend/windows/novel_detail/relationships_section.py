"""
人物关系 Section - 现代化设计

展示角色之间的关系网络
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class RelationshipsSection(ThemeAwareWidget):
    """人物关系组件 - 现代化卡片设计"""

    editRequested = pyqtSignal(str, str, object)

    def __init__(self, data=None, editable=True, parent=None):
        self.data = data or []
        self.editable = editable

        # 保存组件引用
        self.header_widget = None
        self.count_label = None
        self.edit_btn = None
        self.no_data_widget = None
        self.cards_container = None
        self.relationship_cards = []

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(20))

        # 顶部标题栏
        self.header_widget = QWidget()
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(12))

        # 图标
        icon = QLabel("\U0001F517")  # 链接图标
        icon.setStyleSheet(f"font-size: {sp(20)}px;")
        header_layout.addWidget(icon)

        # 标题
        title = QLabel("人物关系")
        title.setObjectName("section_title")
        header_layout.addWidget(title)

        # 数量标签
        self.count_label = QLabel(f"{len(self.data)} 条关系")
        self.count_label.setObjectName("count_label")
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        # 编辑按钮
        if self.editable:
            self.edit_btn = QPushButton("编辑关系")
            self.edit_btn.setObjectName("edit_btn")
            self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.edit_btn.clicked.connect(lambda: self.editRequested.emit('relationships', '人物关系', self.data))
            header_layout.addWidget(self.edit_btn)

        layout.addWidget(self.header_widget)

        # 关系内容区域
        if not self.data:
            self.no_data_widget = self._createEmptyState()
            layout.addWidget(self.no_data_widget)
        else:
            self.cards_container = QWidget()
            cards_layout = QVBoxLayout(self.cards_container)
            cards_layout.setContentsMargins(0, 0, 0, 0)
            cards_layout.setSpacing(dp(12))

            for relationship in self.data:
                card = self._createRelationshipCard(relationship)
                cards_layout.addWidget(card)
                self.relationship_cards.append(card)

            layout.addWidget(self.cards_container)

        layout.addStretch()

    def _createEmptyState(self):
        """创建空状态提示"""
        widget = QFrame()
        widget.setObjectName("empty_state")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(dp(12))

        icon = QLabel("\U0001F91D")  # 握手图标
        icon.setStyleSheet(f"font-size: {sp(48)}px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        text = QLabel("暂无人物关系")
        text.setObjectName("empty_text")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)

        hint = QLabel("点击\"编辑关系\"按钮添加角色之间的关系")
        hint.setObjectName("empty_hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        return widget

    def _createRelationshipCard(self, relationship):
        """创建关系卡片 - 现代化设计"""
        card = QFrame()
        card.setObjectName("relationship_card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(dp(20), dp(16), dp(20), dp(16))
        card_layout.setSpacing(dp(16))

        # 角色A（圆形头像 + 名字）
        from_widget = self._createCharacterBadge(relationship.get('character_from', ''))
        card_layout.addWidget(from_widget)

        # 关系连接线和类型
        connection = QWidget()
        connection_layout = QVBoxLayout(connection)
        connection_layout.setContentsMargins(0, 0, 0, 0)
        connection_layout.setSpacing(dp(4))

        # 箭头
        arrow = QLabel("\u2192")  # 右箭头
        arrow.setObjectName("arrow")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        connection_layout.addWidget(arrow)

        # 关系类型标签
        rel_type = relationship.get('relationship_type', '')
        if rel_type:
            type_label = QLabel(rel_type)
            type_label.setObjectName("rel_type")
            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            connection_layout.addWidget(type_label)

        card_layout.addWidget(connection)

        # 角色B
        to_widget = self._createCharacterBadge(relationship.get('character_to', ''))
        card_layout.addWidget(to_widget)

        card_layout.addStretch()

        # 关系描述（如果有）
        description = relationship.get('description', '')
        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("rel_desc")
            desc_label.setWordWrap(True)
            desc_label.setMaximumWidth(dp(250))
            card_layout.addWidget(desc_label)

        return card

    def _createCharacterBadge(self, name):
        """创建角色徽章（头像 + 名字）"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))

        # 圆形头像
        avatar = QLabel()
        avatar.setObjectName("char_avatar")
        avatar.setFixedSize(dp(36), dp(36))
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        first_char = name[0] if name else '?'
        avatar.setText(first_char)
        layout.addWidget(avatar)

        # 名字
        name_label = QLabel(name)
        name_label.setObjectName("char_badge_name")
        layout.addWidget(name_label)

        return widget

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        self.setStyleSheet(f"""
            #section_title {{
                font-size: {sp(18)}px;
                font-weight: 700;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #count_label {{
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_TERTIARY};
                background-color: {theme_manager.BG_TERTIARY};
                padding: {dp(4)}px {dp(12)}px;
                border-radius: {dp(12)}px;
            }}
            #edit_btn {{
                background: transparent;
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
            }}
            #edit_btn:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-color: {theme_manager.PRIMARY};
                color: {theme_manager.PRIMARY};
            }}
            #empty_state {{
                background-color: {theme_manager.BG_SECONDARY};
                border: 2px dashed {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(12)}px;
                padding: {dp(40)}px;
            }}
            #empty_text {{
                font-size: {sp(16)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_SECONDARY};
            }}
            #empty_hint {{
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_TERTIARY};
            }}
            #relationship_card {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(12)}px;
            }}
            #relationship_card:hover {{
                border-color: {theme_manager.PRIMARY_LIGHT};
            }}
            #char_avatar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme_manager.ACCENT_LIGHT}, stop:1 {theme_manager.ACCENT});
                color: {theme_manager.BUTTON_TEXT};
                font-size: {sp(14)}px;
                font-weight: 600;
                border-radius: {dp(18)}px;
            }}
            #char_badge_name {{
                font-size: {sp(15)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #arrow {{
                font-size: {sp(20)}px;
                color: {theme_manager.PRIMARY};
            }}
            #rel_type {{
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.PRIMARY_PALE};
                padding: {dp(4)}px {dp(12)}px;
                border-radius: {dp(10)}px;
            }}
            #rel_desc {{
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
                background-color: {theme_manager.BG_TERTIARY};
                padding: {dp(8)}px {dp(12)}px;
                border-radius: {dp(8)}px;
            }}
        """)

    def updateData(self, new_data):
        """更新数据并刷新显示"""
        self.data = new_data

        # 更新数量标签
        if self.count_label:
            self.count_label.setText(f"{len(new_data)} 条关系")

        # 获取主layout
        main_layout = self.layout()

        # 先删除所有现有的关系卡片
        for card in self.relationship_cards:
            card.deleteLater()
        self.relationship_cards.clear()

        # 情况1：从无数据 -> 有数据
        if self.no_data_widget and new_data:
            self.no_data_widget.deleteLater()
            self.no_data_widget = None

            # 创建卡片容器
            self.cards_container = QWidget()
            cards_layout = QVBoxLayout(self.cards_container)
            cards_layout.setContentsMargins(0, 0, 0, 0)
            cards_layout.setSpacing(dp(12))

            for relationship in new_data:
                card = self._createRelationshipCard(relationship)
                cards_layout.addWidget(card)
                self.relationship_cards.append(card)

            main_layout.insertWidget(main_layout.count() - 1, self.cards_container)
            self._apply_theme()

        # 情况2：从有数据 -> 无数据
        elif self.cards_container and not new_data:
            self.cards_container.deleteLater()
            self.cards_container = None

            self.no_data_widget = self._createEmptyState()
            main_layout.insertWidget(main_layout.count() - 1, self.no_data_widget)
            self._apply_theme()

        # 情况3：从有数据 -> 有数据（更新）
        elif self.cards_container and new_data:
            cards_layout = self.cards_container.layout()

            for relationship in new_data:
                card = self._createRelationshipCard(relationship)
                cards_layout.addWidget(card)
                self.relationship_cards.append(card)

            self._apply_theme()
