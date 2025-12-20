"""
通用列表编辑对话框

用于编辑 key_locations, factions 等简单列表字段。
每个列表项包含 name 和 description 两个字段。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


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
            'description': self.desc_input.toPlainText().strip()
        }

    def update_index(self, new_index: int):
        """更新序号"""
        self.index = new_index
        self.index_label.setText(f"#{new_index + 1}")


class ListEditDialog(QDialog):
    """通用列表编辑对话框"""

    def __init__(
        self,
        title: str,
        items: list,
        item_fields: list = None,
        field_labels: dict = None,
        parent=None
    ):
        super().__init__(parent)
        self.dialog_title = title
        self.items = items or []
        self.item_fields = item_fields or ['name', 'description']
        self.field_labels = field_labels or {'name': '名称', 'description': '描述'}

        self.item_widgets = []
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle(self.dialog_title)
        self.setMinimumSize(dp(600), dp(500))
        self.resize(dp(700), dp(600))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(16))

        # 标题
        title_label = QLabel(self.dialog_title)
        title_label.setObjectName("dialog_title")
        layout.addWidget(title_label)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(dp(12))

        self.add_btn = QPushButton("+ 添加项目")
        self.add_btn.setObjectName("add_btn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_item)
        toolbar.addWidget(self.add_btn)

        toolbar.addStretch()

        self.count_label = QLabel(f"共 {len(self.items)} 项")
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
        self.content_layout.setSpacing(dp(12))

        # 创建列表项
        self._create_items()

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

    def _create_items(self):
        """创建所有列表项"""
        self.item_widgets.clear()

        for idx, item in enumerate(self.items):
            widget = ListItemWidget(item, self.field_labels, idx)
            widget.delete_btn.clicked.connect(lambda checked, w=widget: self._delete_item(w))
            self.item_widgets.append(widget)
            self.content_layout.addWidget(widget)

    def _add_item(self):
        """添加新项目"""
        idx = len(self.item_widgets)
        widget = ListItemWidget({}, self.field_labels, idx)
        widget.delete_btn.clicked.connect(lambda checked, w=widget: self._delete_item(w))
        self.item_widgets.append(widget)

        # 在stretch之前插入
        self.content_layout.insertWidget(self.content_layout.count() - 1, widget)
        self._update_count()

        # 聚焦到新项目的名称输入框
        widget.name_input.setFocus()

    def _delete_item(self, widget: ListItemWidget):
        """删除项目"""
        if widget in self.item_widgets:
            self.item_widgets.remove(widget)
            self.content_layout.removeWidget(widget)
            widget.deleteLater()
            self._update_indices()
            self._update_count()

    def _update_indices(self):
        """更新所有项目的序号"""
        for idx, widget in enumerate(self.item_widgets):
            widget.update_index(idx)

    def _update_count(self):
        """更新计数"""
        self.count_label.setText(f"共 {len(self.item_widgets)} 项")

    def get_items(self) -> list:
        """获取编辑后的列表"""
        result = []
        for widget in self.item_widgets:
            data = widget.get_data()
            # 过滤掉空项
            if data.get('name'):
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
