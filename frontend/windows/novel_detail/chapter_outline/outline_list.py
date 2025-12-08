"""
大纲列表视图

使用横条形式显示所有大纲（章节大纲或部分大纲）
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from .outline_row import OutlineRow

logger = logging.getLogger(__name__)


class OutlineListView(QWidget):
    """大纲列表视图 - 横条形式"""

    itemClicked = pyqtSignal(dict)  # 点击某个大纲项

    def __init__(
        self,
        items: list,
        item_type: str = "chapter",  # "chapter" 或 "part"
        parent=None
    ):
        super().__init__(parent)
        self.items = items or []
        self.item_type = item_type
        self.row_widgets = []
        self._setup_ui()
        self._apply_style()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_style()
        for row in self.row_widgets:
            row.update_theme()

    def _setup_ui(self):
        """设置UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 内容容器
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, dp(8), 0, dp(8))
        self.content_layout.setSpacing(dp(8))

        # 创建横条列表
        self._create_rows()

        self.content_layout.addStretch()
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

    def _create_rows(self):
        """创建所有大纲横条"""
        self.row_widgets.clear()

        if not self.items:
            # 空状态
            empty_label = QLabel("暂无大纲数据")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(
                f"color: {theme_manager.TEXT_SECONDARY}; "
                f"font-size: {sp(14)}px; "
                f"padding: {dp(40)}px;"
            )
            self.content_layout.addWidget(empty_label)
            return

        for item in self.items:
            row = OutlineRow(data=item, row_type=self.item_type)
            row.detailClicked.connect(self.itemClicked.emit)
            self.row_widgets.append(row)
            self.content_layout.addWidget(row)

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet("background: transparent;")
        self.content.setStyleSheet("background: transparent;")
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

    def update_theme(self):
        """更新主题"""
        self._apply_style()
        for row in self.row_widgets:
            row.update_theme()

    def update_data(self, items: list):
        """更新数据"""
        self.items = items or []

        # 清除旧的横条
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.row_widgets.clear()

        # 重建横条
        self._create_rows()
        self.content_layout.addStretch()
        self._apply_style()

    def get_item_count(self) -> int:
        """获取当前项数量"""
        return len(self.items)
