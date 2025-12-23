"""
角色列表 Section - 带Tab的双面板布局

展示主要角色信息和角色立绘，采用Tab切换方式。
- 基本信息Tab：显示角色列表
- 角色立绘Tab：生成和管理角色立绘
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QWidget, QScrollArea, QTabBar, QStackedWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp

from .character_row import CharacterRow
from .section_styles import SectionStyles
from .character_portraits_widget import CharacterPortraitsWidget


class CharactersSection(ThemeAwareWidget):
    """主要角色组件 - 带Tab的双面板布局"""

    editRequested = pyqtSignal(str, str, object)

    def __init__(self, data=None, editable=True, project_id: str = "", parent=None):
        self.data = data or []
        self.editable = editable
        self.project_id = project_id

        # 保存组件引用
        self.header_widget = None
        self.count_label = None
        self.edit_btn = None
        self.tab_bar = None
        self.stacked_widget = None

        # 基本信息Tab的组件
        self.info_widget = None
        self.scroll_area = None
        self.content_widget = None
        self.content_layout = None
        self.no_data_widget = None
        self.character_rows = []

        # 角色立绘Tab的组件
        self.portraits_widget = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(12))

        # 顶部标题栏（包含Tab）
        self._create_header(layout)

        # Tab内容区域
        self.stacked_widget = QStackedWidget()

        # Tab 0: 基本信息
        self.info_widget = QWidget()
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(8))
        self._create_content_area(info_layout)
        self.stacked_widget.addWidget(self.info_widget)

        # Tab 1: 角色立绘
        self.portraits_widget = CharacterPortraitsWidget(self.project_id)
        self.portraits_widget.setCharacters(self.data)
        self.stacked_widget.addWidget(self.portraits_widget)

        layout.addWidget(self.stacked_widget, stretch=1)

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

        # Tab切换栏
        self.tab_bar = QTabBar()
        self.tab_bar.addTab("基本信息")
        self.tab_bar.addTab("角色立绘")
        self.tab_bar.setObjectName("section_tab_bar")
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        header_layout.addWidget(self.tab_bar)

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

    def _on_tab_changed(self, index: int):
        """Tab切换处理"""
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(index)

        # 切换到立绘Tab时刷新数据
        if index == 1 and self.portraits_widget:
            self.portraits_widget._load_data()

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
        # 使用共享的 Section 样式
        self.setStyleSheet(SectionStyles.list_section_stylesheet())
        self.scroll_area.setStyleSheet(SectionStyles.scroll_area_stylesheet())
        self.content_widget.setStyleSheet(SectionStyles.transparent_background())

        # TabBar样式
        if self.tab_bar:
            self.tab_bar.setStyleSheet(f"""
                QTabBar {{
                    background: transparent;
                }}
                QTabBar::tab {{
                    background: transparent;
                    color: {theme_manager.TEXT_SECONDARY};
                    padding: {dp(6)}px {dp(12)}px;
                    margin-right: {dp(4)}px;
                    border: none;
                    border-bottom: 2px solid transparent;
                    font-size: {sp(13)}px;
                }}
                QTabBar::tab:selected {{
                    color: {theme_manager.ACCENT};
                    border-bottom: 2px solid {theme_manager.ACCENT};
                }}
                QTabBar::tab:hover {{
                    color: {theme_manager.TEXT_PRIMARY};
                }}
            """)

        # 更新所有角色横条样式
        for row in self.character_rows:
            row.update_theme()

        # 更新立绘widget样式
        if self.portraits_widget:
            self.portraits_widget.refresh_theme()

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

        # 更新立绘widget的角色数据
        if self.portraits_widget:
            self.portraits_widget.setCharacters(new_data)

    def setProjectId(self, project_id: str):
        """设置项目ID"""
        self.project_id = project_id
        if self.portraits_widget:
            self.portraits_widget.setProjectId(project_id)
