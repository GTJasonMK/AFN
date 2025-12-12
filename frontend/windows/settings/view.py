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
        container_layout.setContentsMargins(dp(40), dp(30), dp(40), dp(30))
        container_layout.setSpacing(dp(20))

        # 顶部导航栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(16))

        # 返回按钮
        self.back_btn = QPushButton("返回")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setFixedSize(dp(80), dp(32))
        self.back_btn.clicked.connect(self.goBack)
        header_layout.addWidget(self.back_btn)

        header_layout.addStretch()
        container_layout.addLayout(header_layout)

        # 页面标题区
        title_section = QVBoxLayout()
        title_section.setSpacing(dp(4))
        
        self.title_label = QLabel("系统设置")
        title_section.addWidget(self.title_label)

        self.subtitle_label = QLabel("System Configuration")
        title_section.addWidget(self.subtitle_label)
        
        container_layout.addLayout(title_section)
        container_layout.addSpacing(dp(10))

        # 内容区域 - 左右分栏 (左侧目录，右侧书页)
        content_split_layout = QHBoxLayout()
        content_split_layout.setSpacing(dp(30))

        # 左侧：导航目录 (Table of Contents)
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(dp(220)) # Width optimized
        self.nav_list.setFrameShape(QFrame.Shape.NoFrame)
        self.nav_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_list.setWordWrap(True) # Ensure text wraps if needed
        
        # 添加导航项 - Clean plain text for stability
        self._add_nav_item("LLM 服务", "配置大语言模型连接")
        self._add_nav_item("嵌入模型", "配置向量数据库模型")
        self._add_nav_item("高级配置", "生成参数与系统调优")
        
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        content_split_layout.addWidget(self.nav_list)

        # 右侧：书页内容容器
        self.page_frame = QFrame()
        self.page_frame.setObjectName("page_frame")
        
        # 添加阴影效果，模拟纸张浮起感
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(dp(20))
        shadow.setXOffset(0)
        shadow.setYOffset(dp(4))
        shadow.setColor(QColor(0, 0, 0, 20))
        self.page_frame.setGraphicsEffect(shadow)

        page_layout = QVBoxLayout(self.page_frame)
        page_layout.setContentsMargins(dp(30), dp(30), dp(30), dp(30))
        page_layout.setSpacing(0)

        # 堆叠页面 - Standard StackedWidget for stability
        self.page_stack = QStackedWidget()
        
        # 1. LLM配置
        self.llm_settings = LLMSettingsWidget()
        self.page_stack.addWidget(self.llm_settings)

        # 2. 嵌入模型配置
        self.embedding_settings = EmbeddingSettingsWidget()
        self.page_stack.addWidget(self.embedding_settings)

        # 3. 高级配置
        self.advanced_settings = AdvancedSettingsWidget()
        self.page_stack.addWidget(self.advanced_settings)

        page_layout.addWidget(self.page_stack)
        content_split_layout.addWidget(self.page_frame, stretch=1)

        container_layout.addLayout(content_split_layout, stretch=1)
        main_layout.addWidget(self.main_container)

        # 默认选中第一项
        self.nav_list.setCurrentRow(0)

    def _add_nav_item(self, title, subtitle):
        """添加导航项"""
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, dp(70)))
        item.setText(f"{title}\n{subtitle}")
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

        # 返回按钮 - 胶囊风格
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
                background-color: {palette.bg_secondary};
            }}
        """)

        # 标题
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.serif_font};
                font-size: {sp(32)}px;
                font-weight: 700;
                color: {palette.text_primary};
                letter-spacing: {dp(1)}px;
            }}
        """)
        
        self.subtitle_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.serif_font};
                font-size: {sp(14)}px;
                font-style: italic;
                color: {palette.text_tertiary};
                letter-spacing: {dp(0.5)}px;
            }}
        """)

        # 导航列表 - 目录风格 (Refined)
        self.nav_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                color: {palette.text_secondary};
                border-left: 3px solid transparent;
                padding-left: {dp(12)}px;
                margin-bottom: {dp(8)}px;
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
            }}
            QListWidget::item:hover {{
                color: {palette.text_primary};
                background-color: rgba(0,0,0,0.02);
            }}
            QListWidget::item:selected {{
                color: {palette.accent_color};
                border-left: 3px solid {palette.accent_color};
                background-color: {palette.bg_secondary};
                font-weight: 600;
            }}
        """)

        # 页面容器 - 纸张质感
        self.findChild(QFrame, "page_frame").setStyleSheet(f"""
            QFrame#page_frame {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(12)}px;
            }}
        """)

    def refresh(self, **params):
        """刷新页面"""
        # 刷新子组件
        if hasattr(self, 'llm_settings'):
            self.llm_settings.loadConfigs()
        if hasattr(self, 'embedding_settings'):
            self.embedding_settings.loadConfigs()
        if hasattr(self, 'advanced_settings'):
            self.advanced_settings.loadConfig()