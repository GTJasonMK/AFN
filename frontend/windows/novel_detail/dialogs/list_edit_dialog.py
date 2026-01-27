"""
通用列表编辑对话框

用于编辑 key_locations, factions 等简单列表字段。
每个列表项包含 name 和 description 两个字段。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

from .base_book_list_edit_dialog import (
    BaseBookListEditDialog,
    build_delete_button_style,
    build_index_and_field_label_style,
)


class ListItemWidget(QFrame):
    """单个列表项编辑组件"""

    def __init__(self, item_data: dict, field_labels: dict, index: int, parent=None):
        super().__init__(parent)
        self.item_data = item_data or {}
        self.field_labels = field_labels
        self.index = index
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("list_item_widget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(8))

        # 标题行（序号 + 删除按钮）
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        self.index_label = QLabel(f"#{self.index + 1}")
        self.index_label.setObjectName("index_label")
        header.addWidget(self.index_label)

        header.addStretch()

        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("delete_btn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setFixedSize(dp(60), dp(28))
        header.addWidget(self.delete_btn)

        layout.addLayout(header)

        # 名称输入
        name_label = QLabel(self.field_labels.get('name', '名称'))
        name_label.setObjectName("field_label")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setObjectName("name_input")
        self.name_input.setPlaceholderText("请输入名称...")
        self.name_input.setText(self.item_data.get('name', self.item_data.get('title', '')))
        layout.addWidget(self.name_input)

        # 描述输入
        desc_label = QLabel(self.field_labels.get('description', '描述'))
        desc_label.setObjectName("field_label")
        layout.addWidget(desc_label)

        self.desc_input = QTextEdit()
        self.desc_input.setObjectName("desc_input")
        self.desc_input.setPlaceholderText("请输入描述...")
        self.desc_input.setText(self.item_data.get('description', ''))
        self.desc_input.setMaximumHeight(dp(80))
        layout.addWidget(self.desc_input)

    def _apply_style(self):
        """应用样式"""
        ui_font = theme_manager.ui_font()
        bg_color = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        accent_color = theme_manager.book_accent_color()

        self.setStyleSheet(f"""
            QFrame#list_item_widget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {dp(8)}px;
            }}
            {build_index_and_field_label_style(ui_font, accent_color=accent_color, text_secondary=text_secondary)}
            QLineEdit#name_input {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {text_primary};
                background-color: {theme_manager.book_bg_primary()};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
            }}
            QLineEdit#name_input:focus {{
                border-color: {accent_color};
            }}
            QTextEdit#desc_input {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_primary};
                background-color: {theme_manager.book_bg_primary()};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px;
            }}
            QTextEdit#desc_input:focus {{
                border-color: {accent_color};
            }}
            {build_delete_button_style(ui_font)}
        """)

    def get_data(self) -> dict:
        """获取编辑后的数据"""
        return {
            'name': self.name_input.text().strip(),
            'description': self.desc_input.toPlainText().strip()
        }

    def update_index(self, new_index: int):
        """更新序号"""
        self.index = new_index
        self.index_label.setText(f"#{new_index + 1}")


class ListEditDialog(BaseBookListEditDialog):
    """通用列表编辑对话框"""

    def __init__(
        self,
        title: str,
        items: list,
        item_fields: list = None,
        field_labels: dict = None,
        parent=None
    ):
        self.dialog_title = title
        self.items = items or []
        self.item_fields = item_fields or ['name', 'description']
        self.field_labels = field_labels or {'name': '名称', 'description': '描述'}
        super().__init__(
            dialog_title=self.dialog_title,
            items=self.items,
            add_button_text="+ 添加项目",
            min_width_dp=600,
            min_height_dp=500,
            default_width_dp=700,
            default_height_dp=600,
            content_spacing_dp=12,
            parent=parent,
        )

    def _create_item_widget(self, item_data: dict, index: int) -> QFrame:
        return ListItemWidget(item_data, self.field_labels, index)

    def _format_count_text(self, count: int) -> str:
        return f"共 {count} 项"

    def _focus_new_item(self, widget: QWidget) -> None:
        """新增后聚焦到名称输入框"""
        try:
            widget.name_input.setFocus()
        except Exception:
            pass
