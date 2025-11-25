"""
角色列表 Section - 现代化设计

展示主要角色的信息，采用卡片式布局
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QPushButton,
    QWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class CharactersSection(ThemeAwareWidget):
    """主要角色组件 - 现代化卡片设计"""

    editRequested = pyqtSignal(str, str, object)

    def __init__(self, data=None, editable=True, parent=None):
        self.data = data or []
        self.editable = editable

        # 保存组件引用
        self.header_widget = None
        self.count_label = None
        self.edit_btn = None
        self.no_data_widget = None
        self.grid_widget = None
        self.grid_layout = None
        self.character_cards = []

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
        icon = QLabel("\U0001F465")  # 人群图标
        icon.setStyleSheet(f"font-size: {sp(20)}px;")
        header_layout.addWidget(icon)

        # 标题
        title = QLabel("主要角色")
        title.setObjectName("section_title")
        header_layout.addWidget(title)

        # 数量标签
        self.count_label = QLabel(f"{len(self.data)} 个角色")
        self.count_label.setObjectName("count_label")
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        # 编辑按钮
        if self.editable:
            self.edit_btn = QPushButton("编辑角色")
            self.edit_btn.setObjectName("edit_btn")
            self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.edit_btn.clicked.connect(lambda: self.editRequested.emit('characters', '主要角色', self.data))
            header_layout.addWidget(self.edit_btn)

        layout.addWidget(self.header_widget)

        # 角色内容区域
        if not self.data:
            self.no_data_widget = self._createEmptyState()
            layout.addWidget(self.no_data_widget)
        else:
            self.grid_widget = QWidget()
            self.grid_layout = QGridLayout(self.grid_widget)
            self.grid_layout.setContentsMargins(0, 0, 0, 0)
            self.grid_layout.setSpacing(dp(16))

            for idx, character in enumerate(self.data):
                row = idx // 2
                col = idx % 2
                card = self._createCharacterCard(character)
                self.grid_layout.addWidget(card, row, col)
                self.character_cards.append(card)

            layout.addWidget(self.grid_widget)

        layout.addStretch()

    def _createEmptyState(self):
        """创建空状态提示"""
        widget = QFrame()
        widget.setObjectName("empty_state")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(dp(12))

        icon = QLabel("\U0001F464")  # 单人图标
        icon.setStyleSheet(f"font-size: {sp(48)}px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        text = QLabel("暂无角色信息")
        text.setObjectName("empty_text")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)

        hint = QLabel("点击\"编辑角色\"按钮添加角色")
        hint.setObjectName("empty_hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        return widget

    def _createCharacterCard(self, character):
        """创建角色卡片"""
        card = QFrame()
        card.setObjectName("character_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(dp(20), dp(16), dp(20), dp(16))
        card_layout.setSpacing(dp(12))

        # 顶部：头像 + 名字
        top_layout = QHBoxLayout()
        top_layout.setSpacing(dp(12))

        # 圆形头像（显示首字，带渐变背景）
        avatar = QLabel()
        avatar.setObjectName("avatar")
        avatar.setFixedSize(dp(56), dp(56))
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name = character.get('name', '')
        first_char = name[0] if name else '?'
        avatar.setText(first_char)
        top_layout.addWidget(avatar)

        # 名字和身份
        name_container = QWidget()
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(dp(4))

        name_label = QLabel(name or '未命名')
        name_label.setObjectName("char_name")
        name_layout.addWidget(name_label)

        identity = character.get('identity', '')
        if identity:
            identity_label = QLabel(identity)
            identity_label.setObjectName("char_identity")
            name_layout.addWidget(identity_label)

        top_layout.addWidget(name_container, stretch=1)
        card_layout.addLayout(top_layout)

        # 详细信息（使用标签式布局）
        fields = [
            ('personality', '性格', '\U0001F3AD'),  # 面具
            ('goal', '目标', '\U0001F3AF'),  # 靶心
            ('ability', '能力', '\u2728'),  # 星星
            ('relationship_with_protagonist', '与主角关系', '\U0001F91D')  # 握手
        ]

        for field_key, field_label, field_icon in fields:
            value = character.get(field_key)
            if value:
                field_widget = self._createFieldRow(field_icon, field_label, value)
                card_layout.addWidget(field_widget)

        return card

    def _createFieldRow(self, icon_text, label, value):
        """创建字段行"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(4))

        # 标签行
        label_row = QHBoxLayout()
        label_row.setSpacing(dp(6))

        icon = QLabel(icon_text)
        icon.setStyleSheet(f"font-size: {sp(12)}px;")
        label_row.addWidget(icon)

        label_widget = QLabel(label)
        label_widget.setObjectName("field_label")
        label_row.addWidget(label_widget)

        label_row.addStretch()
        layout.addLayout(label_row)

        # 值
        value_label = QLabel(value)
        value_label.setObjectName("field_value")
        value_label.setWordWrap(True)
        layout.addWidget(value_label)

        return widget

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        # Header样式
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
            #character_card {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(12)}px;
            }}
            #character_card:hover {{
                border-color: {theme_manager.PRIMARY_LIGHT};
            }}
            #avatar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme_manager.PRIMARY_LIGHT}, stop:1 {theme_manager.PRIMARY});
                color: {theme_manager.BUTTON_TEXT};
                font-size: {sp(20)}px;
                font-weight: 700;
                border-radius: {dp(28)}px;
            }}
            #char_name {{
                font-size: {sp(16)}px;
                font-weight: 700;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #char_identity {{
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
            }}
            #field_label {{
                font-size: {sp(12)}px;
                font-weight: 500;
                color: {theme_manager.TEXT_TERTIARY};
            }}
            #field_value {{
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_PRIMARY};
                padding-left: {dp(18)}px;
            }}
        """)

    def updateData(self, new_data):
        """更新数据并刷新显示"""
        self.data = new_data

        # 更新数量标签
        if self.count_label:
            self.count_label.setText(f"{len(new_data)} 个角色")

        # 获取主layout
        main_layout = self.layout()

        # 情况1：从无数据 -> 有数据
        if not self.grid_widget and new_data:
            # 移除空状态
            if self.no_data_widget:
                self.no_data_widget.deleteLater()
                self.no_data_widget = None

            # 创建网格
            self.grid_widget = QWidget()
            self.grid_layout = QGridLayout(self.grid_widget)
            self.grid_layout.setContentsMargins(0, 0, 0, 0)
            self.grid_layout.setSpacing(dp(16))

            for idx, character in enumerate(new_data):
                row = idx // 2
                col = idx % 2
                card = self._createCharacterCard(character)
                self.grid_layout.addWidget(card, row, col)
                self.character_cards.append(card)

            # 在stretch之前插入
            main_layout.insertWidget(main_layout.count() - 1, self.grid_widget)
            self._apply_theme()

        # 情况2：从有数据 -> 无数据
        elif self.grid_widget and not new_data:
            # 移除网格
            self.grid_widget.deleteLater()
            self.grid_widget = None
            self.grid_layout = None
            self.character_cards.clear()

            # 创建空状态
            self.no_data_widget = self._createEmptyState()
            main_layout.insertWidget(main_layout.count() - 1, self.no_data_widget)
            self._apply_theme()

        # 情况3：从有数据 -> 有数据（更新）
        elif self.grid_widget and new_data:
            # 清空现有卡片
            for card in self.character_cards:
                card.deleteLater()
            self.character_cards.clear()

            # 重新创建卡片
            for idx, character in enumerate(new_data):
                row = idx // 2
                col = idx % 2
                card = self._createCharacterCard(character)
                self.grid_layout.addWidget(card, row, col)
                self.character_cards.append(card)

            self._apply_theme()
