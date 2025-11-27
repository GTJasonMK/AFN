"""
角色横条组件

用于显示单个角色信息的横条形式
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget, QDialog,
    QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class CharacterDetailDialog(QDialog):
    """角色详情对话框"""

    def __init__(self, character: dict, parent=None):
        super().__init__(parent)
        self.character = character
        # 使用书香风格字体
        self.serif_font = theme_manager.serif_font()
        name = character.get('name', '未命名')
        self.setWindowTitle(f"角色详情 - {name}")
        self.setMinimumSize(dp(500), dp(400))
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        # 头部：头像 + 名字
        header = QHBoxLayout()
        header.setSpacing(dp(16))

        # 圆形头像
        name = self.character.get('name', '')
        first_char = name[0] if name else '?'
        avatar = QLabel(first_char)
        avatar.setObjectName("avatar")
        avatar.setFixedSize(dp(64), dp(64))
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(avatar)

        # 名字和身份
        name_container = QWidget()
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(dp(4))

        name_label = QLabel(name or '未命名')
        name_label.setObjectName("char_name")
        name_layout.addWidget(name_label)

        identity = self.character.get('identity', '')
        if identity:
            identity_label = QLabel(identity)
            identity_label.setObjectName("char_identity")
            name_layout.addWidget(identity_label)

        header.addWidget(name_container, stretch=1)
        layout.addLayout(header)

        # 滚动内容区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(dp(16))

        # 各个字段
        fields = [
            ('personality', '性格'),
            ('goal', '目标'),
            ('ability', '能力'),
            ('background', '背景'),
            ('relationship_with_protagonist', '与主角关系'),
        ]

        for field_key, field_label in fields:
            value = self.character.get(field_key)
            if value:
                card = self._create_field_card(field_label, value)
                content_layout.addWidget(card)

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
            #avatar {{
                font-family: {self.serif_font};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme_manager.PRIMARY_LIGHT}, stop:1 {theme_manager.PRIMARY});
                color: {theme_manager.BUTTON_TEXT};
                font-size: {sp(24)}px;
                font-weight: 700;
                border-radius: {dp(32)}px;
            }}
            #char_name {{
                font-family: {self.serif_font};
                font-size: {sp(20)}px;
                font-weight: 700;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #char_identity {{
                font-family: {self.serif_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
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


class CharacterRow(QFrame):
    """角色横条 - 支持自动换行"""

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
        self.setMinimumHeight(dp(72))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(16))

        # 圆形头像
        name = self.data.get('name', '')
        first_char = name[0] if name else '?'
        self.avatar = QLabel(first_char)
        self.avatar.setFixedSize(dp(48), dp(48))
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignTop)

        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(dp(6))

        # 名字和身份（同一行，但允许换行）
        name_widget = QWidget()
        name_layout = QHBoxLayout(name_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(dp(8))

        self.name_label = QLabel(name or '未命名')
        self.name_label.setWordWrap(True)
        name_layout.addWidget(self.name_label)

        identity = self.data.get('identity', '')
        if identity:
            self.identity_label = QLabel(identity)
            self.identity_label.setWordWrap(True)
            name_layout.addWidget(self.identity_label)

        name_layout.addStretch()
        content_layout.addWidget(name_widget)

        layout.addWidget(content_widget, stretch=1)

        # 查看详情按钮
        self.detail_btn = QPushButton("详情")
        self.detail_btn.setFixedSize(dp(60), dp(32))
        self.detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_btn.clicked.connect(self._show_detail)
        layout.addWidget(self.detail_btn, alignment=Qt.AlignmentFlag.AlignTop)

    def _show_detail(self):
        """显示详情对话框"""
        dialog = CharacterDetailDialog(self.data, parent=self)
        dialog.exec()

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet(f"""
            CharacterRow {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(8)}px;
            }}
            CharacterRow:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """)

        # 头像样式
        self.avatar.setStyleSheet(f"""
            font-family: {self.serif_font};
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme_manager.PRIMARY_LIGHT}, stop:1 {theme_manager.PRIMARY});
            color: {theme_manager.BUTTON_TEXT};
            font-size: {sp(18)}px;
            font-weight: 700;
            border-radius: {dp(24)}px;
        """)

        # 名字样式
        self.name_label.setStyleSheet(
            f"font-family: {self.serif_font}; font-size: {sp(15)}px; font-weight: 600; color: {theme_manager.TEXT_PRIMARY}; background: transparent;"
        )

        # 身份样式
        if hasattr(self, 'identity_label'):
            self.identity_label.setStyleSheet(
                f"font-family: {self.serif_font}; font-size: {sp(12)}px; color: {theme_manager.TEXT_TERTIARY}; "
                f"background-color: {theme_manager.BG_TERTIARY}; "
                f"padding: {dp(2)}px {dp(8)}px; border-radius: {dp(10)}px;"
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
        name = data.get('name', '')
        first_char = name[0] if name else '?'

        self.avatar.setText(first_char)
        self.name_label.setText(name or '未命名')

        # 更新身份标签（如果存在）
        if hasattr(self, 'identity_label'):
            identity = data.get('identity', '')
            self.identity_label.setText(identity)
