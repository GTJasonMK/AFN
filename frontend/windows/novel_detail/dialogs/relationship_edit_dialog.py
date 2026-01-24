"""
关系列表编辑对话框

用于编辑角色关系列表，每个关系包含：
- character1: 角色1
- character2: 角色2
- relationship_type: 关系类型
- description: 关系描述
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QWidget, QComboBox
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

from .base_book_list_edit_dialog import BaseBookListEditDialog


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


class RelationshipListEditDialog(BaseBookListEditDialog):
    """关系列表编辑对话框"""

    def __init__(self, relationships: list, characters: list = None, parent=None):
        self.relationships = relationships or []
        self.characters = characters or []
        super().__init__(
            dialog_title="编辑角色关系",
            items=self.relationships,
            add_button_text="+ 添加关系",
            min_width_dp=700,
            min_height_dp=550,
            default_width_dp=800,
            default_height_dp=650,
            content_spacing_dp=16,
            parent=parent,
        )

    def _create_item_widget(self, item_data: dict, index: int) -> QFrame:
        return RelationshipItemWidget(item_data, self.characters, index)

    def _format_count_text(self, count: int) -> str:
        return f"共 {count} 个关系"

    def _should_keep_item_data(self, data: dict) -> bool:
        return bool(data.get("character1") and data.get("character2"))

    def _focus_new_item(self, widget: QWidget) -> None:
        """新增后聚焦到角色1选择框"""
        try:
            widget.char1_combo.setFocus()
        except Exception:
            pass

    def get_relationships(self) -> list:
        """获取编辑后的关系列表"""
        return self.get_items()
