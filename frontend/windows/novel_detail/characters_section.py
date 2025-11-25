"""
角色列表 Section - 垂直列表布局

展示主要角色的信息，采用横条式垂直列表布局（无水平滚动）
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QWidget, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

from .character_row import CharacterRow


class CharactersSection(ThemeAwareWidget):
    """主要角色组件 - 垂直列表布局"""

    editRequested = pyqtSignal(str, str, object)

    def __init__(self, data=None, editable=True, parent=None):
        self.data = data or []
        self.editable = editable

        # 保存组件引用
        self.header_widget = None
        self.count_label = None
        self.edit_btn = None
        self.scroll_area = None
        self.content_widget = None
        self.content_layout = None
        self.no_data_widget = None
        self.character_rows = []

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 顶部标题栏
        self._create_header(layout)

        # 内容区域（带滚动）
        self._create_content_area(layout)

    def _create_header(self, parent_layout):
        """创建标题栏"""
        self.header_widget = QFrame()
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(12))

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
            self.edit_btn.clicked.connect(
                lambda: self.editRequested.emit('characters', '主要角色', self.data)
            )
            header_layout.addWidget(self.edit_btn)

        parent_layout.addWidget(self.header_widget)

    def _create_content_area(self, parent_layout):
        """创建内容区域"""
        # 滚动区域（只允许垂直滚动）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, dp(8), 0)  # 右边留出滚动条空间
        self.content_layout.setSpacing(dp(8))

        if not self.data:
            self._create_empty_state()
        else:
            self._create_character_rows()

        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        parent_layout.addWidget(self.scroll_area, stretch=1)

    def _create_empty_state(self):
        """创建空状态提示"""
        self.no_data_widget = QFrame()
        self.no_data_widget.setObjectName("empty_state")
        layout = QVBoxLayout(self.no_data_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(dp(12))

        text = QLabel("暂无角色信息")
        text.setObjectName("empty_text")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)

        hint = QLabel("点击\"编辑角色\"按钮添加角色")
        hint.setObjectName("empty_hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.content_layout.addWidget(self.no_data_widget)

    def _create_character_rows(self):
        """创建角色横条列表"""
        self.character_rows.clear()

        for character in self.data:
            row = CharacterRow(character)
            self.character_rows.append(row)
            self.content_layout.addWidget(row)

    def _apply_theme(self):
        """应用主题样式"""
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
        """)

        # 滚动区域样式
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

        self.content_widget.setStyleSheet("background: transparent;")

        # 更新所有角色横条样式
        for row in self.character_rows:
            row.update_theme()

    def updateData(self, new_data):
        """更新数据并刷新显示"""
        self.data = new_data

        # 更新数量标签
        if self.count_label:
            self.count_label.setText(f"{len(new_data)} 个角色")

        # 清空现有内容
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.character_rows.clear()
        self.no_data_widget = None

        # 重建内容
        if not new_data:
            self._create_empty_state()
        else:
            self._create_character_rows()

        self.content_layout.addStretch()
        self._apply_theme()
