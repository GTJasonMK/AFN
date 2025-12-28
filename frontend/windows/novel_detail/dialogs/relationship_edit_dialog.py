"""
关系列表编辑对话框

用于编辑角色关系列表，每个关系包含：
- character1: 角色1
- character2: 角色2
- relationship_type: 关系类型
- description: 关系描述
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame, QScrollArea, QWidget, QComboBox
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


# 预设关系类型
RELATIONSHIP_TYPES = [
    "朋友",
    "敌人",
    "恋人",
    "师徒",
    "同事",
    "亲人",
    "竞争对手",
    "盟友",
    "主仆",
    "其他"
]


class RelationshipItemWidget(QFrame):
    """单个关系编辑组件"""

    def __init__(self, relationship_data: dict, characters: list, index: int, parent=None):
        super().__init__(parent)
        self.relationship_data = relationship_data or {}
        self.characters = characters or []
        self.index = index
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("relationship_item_widget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(10))

        # 标题行（序号 + 删除按钮）
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        self.index_label = QLabel(f"关系 #{self.index + 1}")
        self.index_label.setObjectName("index_label")
        header.addWidget(self.index_label)

        header.addStretch()

        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("delete_btn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setFixedSize(dp(60), dp(28))
        header.addWidget(self.delete_btn)

        layout.addLayout(header)

        # 角色选择行
        chars_row = QHBoxLayout()
        chars_row.setSpacing(dp(12))

        # 角色1
        char1_col = QVBoxLayout()
        char1_label = QLabel("角色1 *")
        char1_label.setObjectName("field_label")
        char1_col.addWidget(char1_label)
        self.char1_combo = QComboBox()
        self.char1_combo.setObjectName("char_combo")
        self.char1_combo.setEditable(True)
        self.char1_combo.setPlaceholderText("选择或输入角色名")
        self._populate_character_combo(self.char1_combo)
        self.char1_combo.setCurrentText(self.relationship_data.get('character1', ''))
        char1_col.addWidget(self.char1_combo)
        chars_row.addLayout(char1_col, stretch=1)

        # 关系类型
        type_col = QVBoxLayout()
        type_label = QLabel("关系类型")
        type_label.setObjectName("field_label")
        type_col.addWidget(type_label)
        self.type_combo = QComboBox()
        self.type_combo.setObjectName("type_combo")
        self.type_combo.setEditable(True)
        self.type_combo.addItems(RELATIONSHIP_TYPES)
        current_type = self.relationship_data.get('relationship_type', '')
        if current_type:
            self.type_combo.setCurrentText(current_type)
        type_col.addWidget(self.type_combo)
        chars_row.addLayout(type_col, stretch=1)

        # 角色2
        char2_col = QVBoxLayout()
        char2_label = QLabel("角色2 *")
        char2_label.setObjectName("field_label")
        char2_col.addWidget(char2_label)
        self.char2_combo = QComboBox()
        self.char2_combo.setObjectName("char_combo")
        self.char2_combo.setEditable(True)
        self.char2_combo.setPlaceholderText("选择或输入角色名")
        self._populate_character_combo(self.char2_combo)
        self.char2_combo.setCurrentText(self.relationship_data.get('character2', ''))
        char2_col.addWidget(self.char2_combo)
        chars_row.addLayout(char2_col, stretch=1)

        layout.addLayout(chars_row)

        # 关系描述
        desc_label = QLabel("关系描述")
        desc_label.setObjectName("field_label")
        layout.addWidget(desc_label)
        self.desc_input = QTextEdit()
        self.desc_input.setObjectName("desc_input")
        self.desc_input.setPlaceholderText("详细描述两者之间的关系...")
        self.desc_input.setText(self.relationship_data.get('description', ''))
        self.desc_input.setMaximumHeight(dp(80))
        layout.addWidget(self.desc_input)

    def _populate_character_combo(self, combo: QComboBox):
        """填充角色下拉列表"""
        combo.addItem("")  # 空选项
        for char in self.characters:
            name = char.get('name', '')
            if name:
                combo.addItem(name)

    def _apply_style(self):
        """应用样式"""
        ui_font = theme_manager.ui_font()
        bg_color = theme_manager.book_bg_secondary()
        bg_primary = theme_manager.book_bg_primary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        accent_color = theme_manager.book_accent_color()

        self.setStyleSheet(f"""
            QFrame#relationship_item_widget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {dp(8)}px;
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
            QComboBox#char_combo, QComboBox#type_combo {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_primary};
                background-color: {bg_primary};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(8)}px;
            }}
            QComboBox#char_combo:focus, QComboBox#type_combo:focus {{
                border-color: {accent_color};
            }}
            QComboBox#char_combo::drop-down, QComboBox#type_combo::drop-down {{
                border: none;
                width: {dp(20)}px;
            }}
            QComboBox#char_combo QAbstractItemView, QComboBox#type_combo QAbstractItemView {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_primary};
                background-color: {bg_primary};
                border: 1px solid {border_color};
                selection-background-color: {accent_color};
                selection-color: {theme_manager.BUTTON_TEXT};
            }}
            QTextEdit#desc_input {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_primary};
                background-color: {bg_primary};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(6)}px;
            }}
            QTextEdit#desc_input:focus {{
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
                color: {theme_manager.BUTTON_TEXT};
            }}
        """)

    def get_data(self) -> dict:
        """获取编辑后的数据"""
        return {
            'character1': self.char1_combo.currentText().strip(),
            'character2': self.char2_combo.currentText().strip(),
            'relationship_type': self.type_combo.currentText().strip(),
            'description': self.desc_input.toPlainText().strip()
        }

    def update_index(self, new_index: int):
        """更新序号"""
        self.index = new_index
        self.index_label.setText(f"关系 #{new_index + 1}")


class RelationshipListEditDialog(QDialog):
    """关系列表编辑对话框"""

    def __init__(self, relationships: list, characters: list = None, parent=None):
        super().__init__(parent)
        self.relationships = relationships or []
        self.characters = characters or []
        self.relationship_widgets = []
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("编辑角色关系")
        self.setMinimumSize(dp(700), dp(550))
        self.resize(dp(800), dp(650))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(16))

        # 标题
        title_label = QLabel("编辑角色关系")
        title_label.setObjectName("dialog_title")
        layout.addWidget(title_label)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(dp(12))

        self.add_btn = QPushButton("+ 添加关系")
        self.add_btn.setObjectName("add_btn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_relationship)
        toolbar.addWidget(self.add_btn)

        toolbar.addStretch()

        self.count_label = QLabel(f"共 {len(self.relationships)} 个关系")
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

        # 创建关系编辑组件
        self._create_relationships()

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

    def _create_relationships(self):
        """创建所有关系编辑组件"""
        self.relationship_widgets.clear()

        for idx, relationship in enumerate(self.relationships):
            widget = RelationshipItemWidget(relationship, self.characters, idx)
            widget.delete_btn.clicked.connect(lambda checked, w=widget: self._delete_relationship(w))
            self.relationship_widgets.append(widget)
            self.content_layout.addWidget(widget)

    def _add_relationship(self):
        """添加新关系"""
        idx = len(self.relationship_widgets)
        widget = RelationshipItemWidget({}, self.characters, idx)
        widget.delete_btn.clicked.connect(lambda checked, w=widget: self._delete_relationship(w))
        self.relationship_widgets.append(widget)

        # 在stretch之前插入
        self.content_layout.insertWidget(self.content_layout.count() - 1, widget)
        self._update_count()

        # 聚焦到新关系的角色1选择框
        widget.char1_combo.setFocus()

    def _delete_relationship(self, widget: RelationshipItemWidget):
        """删除关系"""
        if widget in self.relationship_widgets:
            self.relationship_widgets.remove(widget)
            self.content_layout.removeWidget(widget)
            widget.deleteLater()
            self._update_indices()
            self._update_count()

    def _update_indices(self):
        """更新所有关系的序号"""
        for idx, widget in enumerate(self.relationship_widgets):
            widget.update_index(idx)

    def _update_count(self):
        """更新计数"""
        self.count_label.setText(f"共 {len(self.relationship_widgets)} 个关系")

    def get_relationships(self) -> list:
        """获取编辑后的关系列表"""
        result = []
        for widget in self.relationship_widgets:
            data = widget.get_data()
            # 过滤掉没有角色的关系
            if data.get('character1') and data.get('character2'):
                result.append(data)
        return result

    def _apply_style(self):
        """应用样式"""
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
                color: {theme_manager.BUTTON_TEXT};
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
