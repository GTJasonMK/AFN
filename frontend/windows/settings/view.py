"""
设置页面主视图 - 书籍风格 (侧边导航布局)
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QWidget, QListWidget, QStackedWidget, QListWidgetItem,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from pages.base_page import BasePage
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from .llm_settings_widget import LLMSettingsWidget
from .embedding_settings_widget import EmbeddingSettingsWidget
from .advanced_settings_widget import AdvancedSettingsWidget
from .image_settings_widget import ImageSettingsWidget
from .queue_settings_widget import QueueSettingsWidget


class SettingsView(BasePage):
    """设置页面 - 书籍风格 (侧边导航布局)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_ui_structure()
        self._apply_theme()
        theme_manager.theme_changed.connect(lambda _: self._apply_theme())

    def _create_ui_structure(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 主容器
        self.main_container = QWidget()
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(dp(32), dp(24), dp(32), dp(24))
        container_layout.setSpacing(dp(16))

        # 顶部：返回按钮 + 标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(16))

        # 返回按钮
        self.back_btn = QPushButton("< 返回")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.goBack)
        header_layout.addWidget(self.back_btn)

        # 页面标题
        self.title_label = QLabel("系统设置")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()
        container_layout.addLayout(header_layout)

        # 内容区域 - 左右分栏
        content_layout = QHBoxLayout()
        content_layout.setSpacing(dp(24))

        # 左侧：导航列表
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("nav_list")
        self.nav_list.setFixedWidth(dp(180))
        self.nav_list.setFrameShape(QFrame.Shape.NoFrame)
        self.nav_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_list.setCursor(Qt.CursorShape.PointingHandCursor)

        # 添加导航项
        self._add_nav_item("LLM 服务")
        self._add_nav_item("嵌入模型")
        self._add_nav_item("生图模型")
        self._add_nav_item("请求队列")
        self._add_nav_item("高级配置")

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        content_layout.addWidget(self.nav_list)

        # 右侧：内容区域
        self.page_frame = QFrame()
        self.page_frame.setObjectName("page_frame")

        # 添加阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(dp(16))
        shadow.setXOffset(0)
        shadow.setYOffset(dp(2))
        shadow.setColor(QColor(0, 0, 0, 20))
        self.page_frame.setGraphicsEffect(shadow)

        page_layout = QVBoxLayout(self.page_frame)
        page_layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))  # 修正：20不符合8pt网格，改为24
        page_layout.setSpacing(0)

        # 堆叠页面
        self.page_stack = QStackedWidget()

        self.llm_settings = LLMSettingsWidget()
        self.page_stack.addWidget(self.llm_settings)

        self.embedding_settings = EmbeddingSettingsWidget()
        self.page_stack.addWidget(self.embedding_settings)

        self.image_settings = ImageSettingsWidget()
        self.page_stack.addWidget(self.image_settings)

        self.queue_settings = QueueSettingsWidget()
        self.page_stack.addWidget(self.queue_settings)

        self.advanced_settings = AdvancedSettingsWidget()
        self.page_stack.addWidget(self.advanced_settings)

        page_layout.addWidget(self.page_stack)
        content_layout.addWidget(self.page_frame, stretch=1)

        container_layout.addLayout(content_layout, stretch=1)
        main_layout.addWidget(self.main_container)

        # 默认选中第一项
        self.nav_list.setCurrentRow(0)

    def _add_nav_item(self, title):
        """添加导航项"""
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, dp(48)))  # 修正：44不符合8pt网格，改为48
        item.setText(title)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.nav_list.addItem(item)

    def _on_nav_changed(self, row):
        """导航切换"""
        self.page_stack.setCurrentIndex(row)

    def _apply_theme(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 主容器背景
        self.main_container.setStyleSheet(f"""
            QWidget {{
                background-color: {palette.bg_primary};
            }}
        """)

        # 返回按钮
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: none;
                font-size: {sp(14)}px;
                padding: {dp(4)}px {dp(8)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
            }}
        """)

        # 标题
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.serif_font};
                font-size: {sp(24)}px;
                font-weight: 700;
                color: {palette.text_primary};
            }}
        """)

        # 导航列表
        self.nav_list.setStyleSheet(f"""
            QListWidget#nav_list {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#nav_list::item {{
                background-color: transparent;
                color: {palette.text_secondary};
                border: none;
                border-left: 2px solid transparent;
                padding: {dp(12)}px {dp(12)}px;  /* 修正：10不符合8pt网格，改为12 */
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
            }}
            QListWidget#nav_list::item:hover {{
                color: {palette.text_primary};
                background-color: rgba(0,0,0,0.02);
            }}
            QListWidget#nav_list::item:selected {{
                color: {palette.accent_color};
                border-left: 2px solid {palette.accent_color};
                background-color: {palette.bg_secondary};
                font-weight: 500;
            }}
        """)

        # 页面容器
        self.page_frame.setStyleSheet(f"""
            QFrame#page_frame {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
            }}
        """)

    def refresh(self, **params):
        """刷新页面"""
        if hasattr(self, 'llm_settings'):
            self.llm_settings.loadConfigs()
        if hasattr(self, 'embedding_settings'):
            self.embedding_settings.loadConfigs()
        if hasattr(self, 'image_settings'):
            self.image_settings.loadConfigs()
        if hasattr(self, 'advanced_settings'):
            self.advanced_settings.loadConfig()
