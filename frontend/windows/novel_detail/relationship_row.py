"""
关系横条组件

用于显示单个人物关系的横条形式
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget, QDialog,
    QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class RelationshipDetailDialog(QDialog):
    """关系详情对话框"""

    def __init__(self, relationship: dict, parent=None):
        super().__init__(parent)
        self.relationship = relationship
        # 使用书香风格字体
        self.serif_font = theme_manager.serif_font()
        char_from = relationship.get('character_from', '')
        char_to = relationship.get('character_to', '')
        self.setWindowTitle(f"关系详情 - {char_from} & {char_to}")
        self.setMinimumSize(dp(450), dp(350))
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        # 头部：关系可视化
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(16))

        # 角色A
        char_from = self.relationship.get('character_from', '')
        from_widget = self._create_character_badge(char_from, is_large=True)
        header_layout.addWidget(from_widget)

        # 箭头和关系类型
        arrow_container = QWidget()
        arrow_layout = QVBoxLayout(arrow_container)
        arrow_layout.setContentsMargins(0, 0, 0, 0)
        arrow_layout.setSpacing(dp(4))
        arrow_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        arrow = QLabel("\u2192")
        arrow.setObjectName("arrow_large")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_layout.addWidget(arrow)

        rel_type = self.relationship.get('relationship_type', '')
        if rel_type:
            type_label = QLabel(rel_type)
            type_label.setObjectName("rel_type_large")
            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow_layout.addWidget(type_label)

        header_layout.addWidget(arrow_container)

        # 角色B
        char_to = self.relationship.get('character_to', '')
        to_widget = self._create_character_badge(char_to, is_large=True)
        header_layout.addWidget(to_widget)

        header_layout.addStretch()
        layout.addWidget(header)

        # 滚动内容区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(dp(16))

        # 关系描述
        description = self.relationship.get('description', '')
        if description:
            desc_card = self._create_field_card("关系描述", description)
            content_layout.addWidget(desc_card)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        # 底部按钮
        footer = QHBoxLayout()
        footer.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(ButtonStyles.primary())
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

    def _create_character_badge(self, name: str, is_large: bool = False) -> QWidget:
        """创建角色徽章"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 圆形头像
        avatar = QLabel()
        avatar.setObjectName("avatar_large" if is_large else "avatar")
        size = dp(56) if is_large else dp(36)
        avatar.setFixedSize(size, size)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        first_char = name[0] if name else '?'
        avatar.setText(first_char)
        layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignCenter)

        # 名字
        name_label = QLabel(name or '未知')
        name_label.setObjectName("char_name_large" if is_large else "char_name")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        return widget

    def _create_field_card(self, label: str, value: str) -> QFrame:
        """创建字段卡片"""
        card = QFrame()
        card.setObjectName("field_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        card_layout.setSpacing(dp(8))

        label_widget = QLabel(label)
        label_widget.setObjectName("field_label")
        card_layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setObjectName("field_value")
        value_widget.setWordWrap(True)
        card_layout.addWidget(value_widget)

        return card

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
            #avatar_large {{
                font-family: {self.serif_font};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme_manager.ACCENT_LIGHT}, stop:1 {theme_manager.ACCENT});
                color: {theme_manager.BUTTON_TEXT};
                font-size: {sp(22)}px;
                font-weight: 700;
                border-radius: {dp(28)}px;
            }}
            #char_name_large {{
                font-family: {self.serif_font};
                font-size: {sp(16)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #arrow_large {{
                font-size: {sp(28)}px;
                color: {theme_manager.PRIMARY};
            }}
            #rel_type_large {{
                font-family: {self.serif_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
                background-color: {theme_manager.PRIMARY_PALE};
                padding: {dp(6)}px {dp(16)}px;
                border-radius: {dp(12)}px;
            }}
            #field_card {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(8)}px;
            }}
            #field_label {{
                font-family: {self.serif_font};
                font-size: {sp(13)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_TERTIARY};
            }}
            #field_value {{
                font-family: {self.serif_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.5;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)


class RelationshipRow(QFrame):
    """关系横条 - 支持自动换行"""

    detailClicked = pyqtSignal(dict)

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        # 使用书香风格字体
        self.serif_font = theme_manager.serif_font()
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI结构"""
        # 不设置固定高度，让内容自适应
        self.setMinimumHeight(dp(64))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 关系指示区域（角色A -> 角色B）
        relation_widget = QWidget()
        relation_layout = QHBoxLayout(relation_widget)
        relation_layout.setContentsMargins(0, 0, 0, 0)
        relation_layout.setSpacing(dp(8))

        # 角色A头像
        char_from = self.data.get('character_from', '')
        self.from_avatar = QLabel(char_from[0] if char_from else '?')
        self.from_avatar.setObjectName("from_avatar")
        self.from_avatar.setFixedSize(dp(32), dp(32))
        self.from_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        relation_layout.addWidget(self.from_avatar)

        # 角色A名字
        self.from_name = QLabel(char_from or '未知')
        self.from_name.setObjectName("from_name")
        relation_layout.addWidget(self.from_name)

        # 箭头
        arrow = QLabel("\u2192")
        arrow.setObjectName("arrow")
        relation_layout.addWidget(arrow)

        # 角色B头像
        char_to = self.data.get('character_to', '')
        self.to_avatar = QLabel(char_to[0] if char_to else '?')
        self.to_avatar.setObjectName("to_avatar")
        self.to_avatar.setFixedSize(dp(32), dp(32))
        self.to_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        relation_layout.addWidget(self.to_avatar)

        # 角色B名字
        self.to_name = QLabel(char_to or '未知')
        self.to_name.setObjectName("to_name")
        relation_layout.addWidget(self.to_name)

        layout.addWidget(relation_widget, alignment=Qt.AlignmentFlag.AlignTop)

        # 内容区域（关系类型和描述）
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(dp(4))

        # 关系类型标签
        rel_type = self.data.get('relationship_type', '')
        if rel_type:
            self.type_label = QLabel(rel_type)
            self.type_label.setObjectName("type_label")
            content_layout.addWidget(self.type_label)

        # 描述（限制显示2行，超出省略）
        description = self.data.get('description', '')
        if description:
            # 截断显示，约2行（约60字符）
            display_desc = description[:60] + "..." if len(description) > 60 else description
            self.desc_label = QLabel(display_desc)
            self.desc_label.setObjectName("desc_label")
            self.desc_label.setWordWrap(True)
            self.desc_label.setMaximumHeight(dp(40))  # 限制最大高度约2行
            content_layout.addWidget(self.desc_label)

        layout.addWidget(content_widget, stretch=1)

        # 查看详情按钮
        self.detail_btn = QPushButton("详情")
        self.detail_btn.setFixedSize(dp(60), dp(32))
        self.detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_btn.clicked.connect(self._show_detail)
        layout.addWidget(self.detail_btn, alignment=Qt.AlignmentFlag.AlignTop)

    def _show_detail(self):
        """显示详情对话框"""
        dialog = RelationshipDetailDialog(self.data, parent=self)
        dialog.exec()

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet(f"""
            RelationshipRow {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(8)}px;
            }}
            RelationshipRow:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """)

        # 头像样式
        avatar_style = f"""
            font-family: {self.serif_font};
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme_manager.ACCENT_LIGHT}, stop:1 {theme_manager.ACCENT});
            color: {theme_manager.BUTTON_TEXT};
            font-size: {sp(12)}px;
            font-weight: 700;
            border-radius: {dp(16)}px;
        """
        self.from_avatar.setStyleSheet(avatar_style)
        self.to_avatar.setStyleSheet(avatar_style)

        # 名字样式
        name_style = f"font-family: {self.serif_font}; font-size: {sp(14)}px; font-weight: 600; color: {theme_manager.TEXT_PRIMARY}; background: transparent;"
        self.from_name.setStyleSheet(name_style)
        self.to_name.setStyleSheet(name_style)

        # 关系类型样式
        if hasattr(self, 'type_label'):
            self.type_label.setStyleSheet(
                f"font-family: {self.serif_font}; font-size: {sp(12)}px; font-weight: 600; color: {theme_manager.PRIMARY}; "
                f"background-color: {theme_manager.PRIMARY_PALE}; "
                f"padding: {dp(2)}px {dp(10)}px; border-radius: {dp(10)}px;"
            )

        # 描述样式
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(
                f"font-family: {self.serif_font}; font-size: {sp(13)}px; color: {theme_manager.TEXT_SECONDARY}; background: transparent;"
            )

        # 按钮样式
        self.detail_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {self.serif_font};
                background-color: transparent;
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                color: {theme_manager.PRIMARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """)

    def update_theme(self):
        """更新主题"""
        self._apply_style()

    def update_data(self, data: dict):
        """更新数据"""
        self.data = data

        char_from = data.get('character_from', '')
        self.from_avatar.setText(char_from[0] if char_from else '?')
        self.from_name.setText(char_from or '未知')

        char_to = data.get('character_to', '')
        self.to_avatar.setText(char_to[0] if char_to else '?')
        self.to_name.setText(char_to or '未知')

        if hasattr(self, 'type_label'):
            self.type_label.setText(data.get('relationship_type', ''))

        if hasattr(self, 'desc_label'):
            description = data.get('description', '')
            display_desc = description[:60] + "..." if len(description) > 60 else description
            self.desc_label.setText(display_desc)
