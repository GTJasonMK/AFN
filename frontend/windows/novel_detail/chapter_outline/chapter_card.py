"""
章节大纲卡片组件

显示单个章节的大纲信息
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class ChapterOutlineCard(QFrame):
    """单个章节大纲卡片"""

    regenerateClicked = pyqtSignal(int)  # 发送章节号

    def __init__(self, chapter: dict, editable: bool = True, parent=None):
        super().__init__(parent)
        self.chapter = chapter
        self.editable = editable
        self.chapter_number = chapter.get('chapter_number', 0)
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

    def _setup_ui(self):
        """设置UI结构"""
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(dp(12))

        # 标题行
        title_layout = QHBoxLayout()

        # 章节编号徽章
        self.num_badge = QLabel(str(self.chapter_number))
        self.num_badge.setFixedSize(dp(32), dp(32))
        self.num_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(self.num_badge)

        # 章节标题
        title_text = self.chapter.get('title', f"第{self.chapter_number}章")
        self.title_label = QLabel(title_text)
        title_layout.addWidget(self.title_label, stretch=1)

        # 章节号标签
        self.num_tag = QLabel(f"#{self.chapter_number}")
        title_layout.addWidget(self.num_tag)

        # 重新生成按钮
        if self.editable:
            self.regenerate_btn = QPushButton("重新生成")
            self.regenerate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.regenerate_btn.setFixedHeight(dp(24))
            self.regenerate_btn.clicked.connect(
                lambda: self.regenerateClicked.emit(self.chapter_number)
            )
            title_layout.addWidget(self.regenerate_btn)

        self._layout.addLayout(title_layout)

        # 摘要
        summary_text = self.chapter.get('summary', '暂无摘要')
        self.summary_label = QLabel(summary_text)
        self.summary_label.setWordWrap(True)
        self._layout.addWidget(self.summary_label)

    def _apply_style(self):
        """应用样式"""
        # 卡片样式
        self.setStyleSheet(f"""
            ChapterOutlineCard {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(12)}px;
                padding: {dp(20)}px;
            }}
        """)

        # 编号徽章样式
        self.num_badge.setStyleSheet(f"""
            font-family: {self.ui_font};
            background-color: {theme_manager.PRIMARY};
            color: {theme_manager.BUTTON_TEXT};
            border-radius: {dp(16)}px;
            font-size: {sp(12)}px;
            font-weight: 700;
        """)

        # 标题样式
        self.title_label.setStyleSheet(
            f"font-family: {self.ui_font}; font-size: {sp(16)}px; font-weight: 600; color: {theme_manager.TEXT_PRIMARY};"
        )

        # 章节号标签样式
        self.num_tag.setStyleSheet(
            f"font-family: {self.ui_font}; font-size: {sp(11)}px; color: {theme_manager.TEXT_SECONDARY};"
        )

        # 重新生成按钮样式
        if self.editable and hasattr(self, 'regenerate_btn'):
            self.regenerate_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {self.ui_font};
                    background-color: transparent;
                    color: {theme_manager.TEXT_SECONDARY};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(4)}px;
                    padding: 0 {dp(8)}px;
                    font-size: {sp(11)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.WARNING_BG};
                    color: {theme_manager.WARNING};
                    border-color: {theme_manager.WARNING};
                }}
            """)

        # 摘要样式
        self.summary_label.setStyleSheet(
            f"font-family: {self.ui_font}; font-size: {sp(14)}px; color: {theme_manager.TEXT_SECONDARY}; line-height: 1.6;"
        )

    def update_theme(self):
        """更新主题"""
        self._apply_style()

    def update_data(self, chapter: dict):
        """更新章节数据"""
        self.chapter = chapter
        self.chapter_number = chapter.get('chapter_number', 0)

        self.num_badge.setText(str(self.chapter_number))
        self.title_label.setText(chapter.get('title', f"第{self.chapter_number}章"))
        self.num_tag.setText(f"#{self.chapter_number}")
        self.summary_label.setText(chapter.get('summary', '暂无摘要'))

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass