"""
大纲横条组件

用于显示单个章节大纲或部分大纲的横条形式
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class OutlineRow(QFrame):
    """大纲横条 - 紧凑的单行显示"""

    detailClicked = pyqtSignal(dict)  # 点击查看详情

    def __init__(
        self,
        data: dict,
        row_type: str = "chapter",  # "chapter" 或 "part"
        parent=None
    ):
        super().__init__(parent)
        self.data = data
        self.row_type = row_type
        # 使用现代UI字体
        self.ui_font = theme_manager.ui_font()
        self._setup_ui()
        self._apply_style()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self.ui_font = theme_manager.ui_font()
        self._apply_style()

    def _show_detail_dialog(self):
        """显示详情对话框"""
        if self.row_type == "chapter":
            from .chapter_detail_dialog import ChapterOutlineDetailDialog
            dialog = ChapterOutlineDetailDialog(self.data, parent=self)
        else:
            from .part_detail_dialog import PartOutlineDetailDialog
            dialog = PartOutlineDetailDialog(self.data, parent=self)
        dialog.exec()

    def _setup_ui(self):
        """设置UI结构"""
        # 使用最小高度，允许内容自适应
        self.setMinimumHeight(dp(56))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(10), dp(16), dp(10))
        layout.setSpacing(dp(16))

        # 编号徽章
        if self.row_type == "chapter":
            number = self.data.get('chapter_number', 0)
            badge_text = str(number)
        else:
            number = self.data.get('part_number', 0)
            badge_text = f"P{number}"

        self.num_badge = QLabel(badge_text)
        self.num_badge.setFixedSize(dp(36), dp(36))
        self.num_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.num_badge, alignment=Qt.AlignmentFlag.AlignTop)

        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(dp(4))
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 标题行
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(dp(8))

        title = self.data.get('title', '')
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_layout.addWidget(self.title_label, stretch=1)

        # 章节范围（仅部分大纲）
        if self.row_type == "part":
            start = self.data.get('start_chapter', 0)
            end = self.data.get('end_chapter', 0)
            self.range_label = QLabel(f"{start}-{end}章")
            title_layout.addWidget(self.range_label)

        content_layout.addWidget(title_widget)

        # 摘要（限制显示2行，超出省略）
        summary = self.data.get('summary', '')
        if summary:
            # 截断显示，约2行（约60字符）
            display_summary = summary[:60] + "..." if len(summary) > 60 else summary
            self.summary_label = QLabel(display_summary)
            self.summary_label.setWordWrap(True)
            self.summary_label.setMaximumHeight(dp(40))  # 限制最大高度约2行
            self.summary_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            content_layout.addWidget(self.summary_label)

        layout.addWidget(content_widget, stretch=1)

        # 查看详情按钮
        self.detail_btn = QPushButton("详情")
        self.detail_btn.setFixedSize(dp(60), dp(28))
        self.detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_btn.clicked.connect(self._show_detail_dialog)
        layout.addWidget(self.detail_btn, alignment=Qt.AlignmentFlag.AlignTop)

    def _apply_style(self):
        """应用样式"""
        # 行样式
        self.setStyleSheet(f"""
            OutlineRow {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(8)}px;
            }}
            OutlineRow:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """)

        # 编号徽章样式
        if self.row_type == "chapter":
            badge_bg = theme_manager.PRIMARY
        else:
            badge_bg = theme_manager.ACCENT
        self.num_badge.setStyleSheet(f"""
            font-family: {self.ui_font};
            background-color: {badge_bg};
            color: {theme_manager.BUTTON_TEXT};
            border-radius: {dp(18)}px;
            font-size: {sp(12)}px;
            font-weight: 700;
        """)

        # 标题样式
        self.title_label.setStyleSheet(
            f"font-family: {self.ui_font}; font-size: {sp(14)}px; font-weight: 600; color: {theme_manager.TEXT_PRIMARY}; background: transparent;"
        )

        # 范围标签样式
        if hasattr(self, 'range_label'):
            self.range_label.setStyleSheet(
                f"font-family: {self.ui_font}; font-size: {sp(11)}px; color: {theme_manager.TEXT_SECONDARY}; background: transparent;"
            )

        # 摘要样式
        if hasattr(self, 'summary_label'):
            self.summary_label.setStyleSheet(
                f"font-family: {self.ui_font}; font-size: {sp(12)}px; color: {theme_manager.TEXT_SECONDARY}; background: transparent;"
            )

        # 详情按钮样式
        self.detail_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {self.ui_font};
                background-color: transparent;
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                font-size: {sp(11)}px;
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

        if self.row_type == "chapter":
            number = data.get('chapter_number', 0)
            self.num_badge.setText(str(number))
        else:
            number = data.get('part_number', 0)
            self.num_badge.setText(f"P{number}")

        self.title_label.setText(data.get('title', ''))

        if hasattr(self, 'range_label'):
            start = data.get('start_chapter', 0)
            end = data.get('end_chapter', 0)
            self.range_label.setText(f"{start}-{end}章")

        if hasattr(self, 'summary_label'):
            summary = data.get('summary', '')
            display_summary = summary[:60] + "..." if len(summary) > 60 else summary
            self.summary_label.setText(display_summary)