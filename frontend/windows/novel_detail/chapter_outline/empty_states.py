"""
空状态占位组件

用于显示长篇/短篇小说的空状态提示
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp


class OutlineEmptyState(QFrame):
    """章节大纲空状态基类"""

    actionClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_style()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_style()

    def _setup_ui(self):
        """设置UI结构"""
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.setSpacing(dp(16))

        # 图标（子类可重写）
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.icon_label)

        # 标题
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.title_label)

        # 描述
        self.desc_label = QLabel()
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.desc_label)

        # 操作按钮
        self.action_btn = QPushButton()
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.clicked.connect(self.actionClicked.emit)
        self._layout.addWidget(self.action_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_SECONDARY};
                border: 2px dashed {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(12)}px;
                padding: {dp(40)}px;
            }}
        """)

        self.title_label.setStyleSheet(
            f"font-size: {sp(16)}px; font-weight: 600; color: {theme_manager.TEXT_PRIMARY};"
        )
        self.desc_label.setStyleSheet(
            f"font-size: {sp(14)}px; color: {theme_manager.TEXT_SECONDARY};"
        )
        self.action_btn.setStyleSheet(ButtonStyles.primary())

    def update_theme(self):
        """更新主题"""
        self._apply_style()


class LongNovelEmptyState(OutlineEmptyState):
    """长篇小说空状态 - 需要先生成部分大纲"""

    def _setup_ui(self):
        super()._setup_ui()
        # 不显示图标
        self.icon_label.hide()
        self.title_label.setText("长篇小说需要先生成部分大纲")
        self.desc_label.setText("将自动规划整体故事结构，然后再生成详细章节大纲")
        self.action_btn.setText("生成部分大纲")


class ShortNovelEmptyState(OutlineEmptyState):
    """短篇小说空状态 - 直接生成章节大纲"""

    def _setup_ui(self):
        super()._setup_ui()
        self.icon_label.setText("*")
        self.icon_label.setStyleSheet(f"font-size: {sp(48)}px;")
        self.title_label.setText("还没有章节大纲")
        self.desc_label.setText("请使用下方的\"生成大纲\"按钮开始创作")
        self.action_btn.setText("生成章节大纲")

    def _apply_style(self):
        super()._apply_style()
        self.desc_label.setStyleSheet(
            f"font-size: {sp(13)}px; color: {theme_manager.TEXT_SECONDARY};"
        )
