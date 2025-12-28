"""
角色列表编辑对话框

用于编辑角色列表，每个角色包含：
- name: 姓名
- identity: 身份
- personality: 性格
- goal: 目标
- ability: 能力
- background: 背景
- relationship_with_protagonist: 与主角关系
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame, QScrollArea, QWidget, QTabWidget
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from components.base import ThemeAwareWidget
from utils.dpi_utils import dp, sp


class CharacterItemWidget(ThemeAwareWidget, QFrame):
    """单个角色编辑组件"""

    def __init__(self, character_data: dict, index: int, parent=None):
        self.character_data = character_data or {}
        self.index = index
        # 初始化UI组件引用
        self.avatar = None
        self.index_label = None
        self.delete_btn = None
        self.name_input = None
        self.identity_input = None
        self.personality_input = None
        self.goal_input = None
        self.ability_input = None
        self.background_input = None
        self.relation_input = None
        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("character_item_widget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(10))

        # 标题行（头像 + 序号 + 删除按钮）
        header = QHBoxLayout()
        header.setSpacing(dp(12))

        # 头像预览
        name = self.character_data.get('name', '')
        first_char = name[0] if name else '?'
        self.avatar = QLabel(first_char)
        self.avatar.setObjectName("avatar")
        self.avatar.setFixedSize(dp(40), dp(40))
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.avatar)

        self.index_label = QLabel(f"角色 #{self.index + 1}")
        self.index_label.setObjectName("index_label")
        header.addWidget(self.index_label)

        header.addStretch()

        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("delete_btn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setFixedSize(dp(60), dp(28))
        header.addWidget(self.delete_btn)

        layout.addLayout(header)

        # 基本信息行
        basic_row = QHBoxLayout()
        basic_row.setSpacing(dp(12))

        # 姓名
        name_col = QVBoxLayout()
        name_label = QLabel("姓名 *")
        name_label.setObjectName("field_label")
        name_col.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setObjectName("field_input")
        self.name_input.setPlaceholderText("角色姓名")
        self.name_input.setText(self.character_data.get('name', ''))
        self.name_input.textChanged.connect(self._update_avatar)
        name_col.addWidget(self.name_input)
        basic_row.addLayout(name_col, stretch=1)

        # 身份
        identity_col = QVBoxLayout()
        identity_label = QLabel("身份")
        identity_label.setObjectName("field_label")
        identity_col.addWidget(identity_label)
        self.identity_input = QLineEdit()
        self.identity_input.setObjectName("field_input")
        self.identity_input.setPlaceholderText("如：主角、反派、配角")
        self.identity_input.setText(self.character_data.get('identity', ''))
        identity_col.addWidget(self.identity_input)
        basic_row.addLayout(identity_col, stretch=1)

        layout.addLayout(basic_row)

        # 性格
        personality_label = QLabel("性格")
        personality_label.setObjectName("field_label")
        layout.addWidget(personality_label)
        self.personality_input = QTextEdit()
        self.personality_input.setObjectName("field_textarea")
        self.personality_input.setPlaceholderText("描述角色的性格特点...")
        self.personality_input.setText(self.character_data.get('personality', ''))
        self.personality_input.setMaximumHeight(dp(60))
        layout.addWidget(self.personality_input)

        # 目标和能力（同一行）
        goal_ability_row = QHBoxLayout()
        goal_ability_row.setSpacing(dp(12))

        goal_col = QVBoxLayout()
        goal_label = QLabel("目标")
        goal_label.setObjectName("field_label")
        goal_col.addWidget(goal_label)
        self.goal_input = QLineEdit()
        self.goal_input.setObjectName("field_input")
        self.goal_input.setPlaceholderText("角色的目标或动机")
        self.goal_input.setText(self.character_data.get('goal', ''))
        goal_col.addWidget(self.goal_input)
        goal_ability_row.addLayout(goal_col, stretch=1)

        ability_col = QVBoxLayout()
        ability_label = QLabel("能力")
        ability_label.setObjectName("field_label")
        ability_col.addWidget(ability_label)
        self.ability_input = QLineEdit()
        self.ability_input.setObjectName("field_input")
        self.ability_input.setPlaceholderText("角色的特殊能力或技能")
        self.ability_input.setText(self.character_data.get('ability', ''))
        ability_col.addWidget(self.ability_input)
        goal_ability_row.addLayout(ability_col, stretch=1)

        layout.addLayout(goal_ability_row)

        # 背景
        background_label = QLabel("背景")
        background_label.setObjectName("field_label")
        layout.addWidget(background_label)
        self.background_input = QTextEdit()
        self.background_input.setObjectName("field_textarea")
        self.background_input.setPlaceholderText("角色的背景故事...")
        self.background_input.setText(self.character_data.get('background', ''))
        self.background_input.setMaximumHeight(dp(60))
        layout.addWidget(self.background_input)

        # 与主角关系
        relation_label = QLabel("与主角关系")
        relation_label.setObjectName("field_label")
        layout.addWidget(relation_label)
        self.relation_input = QLineEdit()
        self.relation_input.setObjectName("field_input")
        self.relation_input.setPlaceholderText("描述与主角的关系...")
        self.relation_input.setText(self.character_data.get('relationship_with_protagonist', ''))
        layout.addWidget(self.relation_input)

    def _update_avatar(self, text: str):
        """更新头像预览"""
        first_char = text[0] if text else '?'
        self.avatar.setText(first_char)

    def _apply_theme(self):
        """应用主题样式"""
        if not self.avatar:
            return

        ui_font = theme_manager.ui_font()
        bg_color = theme_manager.book_bg_secondary()
        bg_primary = theme_manager.book_bg_primary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        accent_color = theme_manager.book_accent_color()

        self.setStyleSheet(f"""
            QFrame#character_item_widget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {dp(8)}px;
            }}
            QLabel#avatar {{
                font-family: {ui_font};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {accent_color}, stop:1 {text_primary});
                color: white;
                font-size: {sp(16)}px;
                font-weight: 700;
                border-radius: {dp(20)}px;
            }}
            QLabel#index_label {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: 700;
                color: {accent_color};
            }}
            QLabel#field_label {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
            }}
            QLineEdit#field_input {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_primary};
                background-color: {bg_primary};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QLineEdit#field_input:focus {{
                border-color: {accent_color};
            }}
            QTextEdit#field_textarea {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_primary};
                background-color: {bg_primary};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(6)}px;
            }}
            QTextEdit#field_textarea:focus {{
                border-color: {accent_color};
            }}
            QPushButton#delete_btn {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.ERROR};
                background-color: transparent;
                border: 1px solid {theme_manager.ERROR};
                border-radius: {dp(4)}px;
            }}
            QPushButton#delete_btn:hover {{
                background-color: {theme_manager.ERROR};
                color: white;
            }}
        """)

    def get_data(self) -> dict:
        """获取编辑后的数据"""
        return {
            'name': self.name_input.text().strip(),
            'identity': self.identity_input.text().strip(),
            'personality': self.personality_input.toPlainText().strip(),
            'goal': self.goal_input.text().strip(),
            'ability': self.ability_input.text().strip(),
            'background': self.background_input.toPlainText().strip(),
            'relationship_with_protagonist': self.relation_input.text().strip()
        }

    def update_index(self, new_index: int):
        """更新序号"""
        self.index = new_index
        self.index_label.setText(f"角色 #{new_index + 1}")


class CharacterListEditDialog(ThemeAwareWidget, QDialog):
    """角色列表编辑对话框"""

    def __init__(self, characters: list, parent=None):
        self.characters = characters or []
        self.character_widgets = []
        # 初始化UI组件引用
        self.add_btn = None
        self.count_label = None
        self.scroll = None
        self.content = None
        self.content_layout = None
        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("编辑角色列表")
        self.setMinimumSize(dp(700), dp(600))
        self.resize(dp(800), dp(700))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(16))

        # 标题
        title_label = QLabel("编辑角色列表")
        title_label.setObjectName("dialog_title")
        layout.addWidget(title_label)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(dp(12))

        self.add_btn = QPushButton("+ 添加角色")
        self.add_btn.setObjectName("add_btn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_character)
        toolbar.addWidget(self.add_btn)

        toolbar.addStretch()

        self.count_label = QLabel(f"共 {len(self.characters)} 个角色")
        self.count_label.setObjectName("count_label")
        toolbar.addWidget(self.count_label)

        layout.addLayout(toolbar)

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, dp(8), 0)
        self.content_layout.setSpacing(dp(16))

        # 创建角色编辑组件
        self._create_characters()

        self.content_layout.addStretch()
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, stretch=1)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(12))
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(dp(38))
        cancel_btn.setMinimumWidth(dp(80))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确定")
        confirm_btn.setObjectName("confirm_btn")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setFixedHeight(dp(38))
        confirm_btn.setMinimumWidth(dp(80))
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setDefault(True)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _create_characters(self):
        """创建所有角色编辑组件"""
        self.character_widgets.clear()

        for idx, character in enumerate(self.characters):
            widget = CharacterItemWidget(character, idx)
            widget.delete_btn.clicked.connect(lambda checked, w=widget: self._delete_character(w))
            self.character_widgets.append(widget)
            self.content_layout.addWidget(widget)

    def _add_character(self):
        """添加新角色"""
        idx = len(self.character_widgets)
        widget = CharacterItemWidget({}, idx)
        widget.delete_btn.clicked.connect(lambda checked, w=widget: self._delete_character(w))
        self.character_widgets.append(widget)

        # 在stretch之前插入
        self.content_layout.insertWidget(self.content_layout.count() - 1, widget)
        self._update_count()

        # 聚焦到新角色的名称输入框
        widget.name_input.setFocus()

    def _delete_character(self, widget: CharacterItemWidget):
        """删除角色"""
        if widget in self.character_widgets:
            self.character_widgets.remove(widget)
            self.content_layout.removeWidget(widget)
            widget.deleteLater()
            self._update_indices()
            self._update_count()

    def _update_indices(self):
        """更新所有角色的序号"""
        for idx, widget in enumerate(self.character_widgets):
            widget.update_index(idx)

    def _update_count(self):
        """更新计数"""
        self.count_label.setText(f"共 {len(self.character_widgets)} 个角色")

    def get_characters(self) -> list:
        """获取编辑后的角色列表"""
        result = []
        for widget in self.character_widgets:
            data = widget.get_data()
            # 过滤掉没有名字的角色
            if data.get('name'):
                result.append(data)
        return result

    def _apply_theme(self):
        """应用主题样式"""
        if not self.add_btn:
            return

        ui_font = theme_manager.ui_font()
        bg_color = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel#dialog_title {{
                font-family: {ui_font};
                font-size: {sp(18)}px;
                font-weight: 700;
                color: {text_primary};
            }}
            QLabel#count_label {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_secondary};
            }}
            QPushButton#add_btn {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {accent_color};
                background-color: transparent;
                border: 1px dashed {accent_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
            }}
            QPushButton#add_btn:hover {{
                background-color: {bg_secondary};
            }}
            QPushButton#cancel_btn {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {text_secondary};
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
            }}
            QPushButton#cancel_btn:hover {{
                color: {accent_color};
                border-color: {accent_color};
            }}
            QPushButton#confirm_btn {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: white;
                background-color: {accent_color};
                border: none;
                border-radius: {dp(6)}px;
            }}
            QPushButton#confirm_btn:hover {{
                background-color: {text_primary};
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

        self.content.setStyleSheet("background: transparent;")
