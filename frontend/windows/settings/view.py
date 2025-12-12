"""
设置页面主视图 - 书籍风格
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QWidget, QTabWidget
)
from PyQt6.QtCore import Qt
from pages.base_page import BasePage
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from .llm_settings_widget import LLMSettingsWidget
from .embedding_settings_widget import EmbeddingSettingsWidget
from .advanced_settings_widget import AdvancedSettingsWidget


class SettingsView(BasePage):
    """设置页面 - 书籍风格"""

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
        container_layout.setContentsMargins(dp(60), dp(40), dp(60), dp(40))
        container_layout.setSpacing(dp(24))

        # 顶部导航栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(16))

        # 返回按钮
        self.back_btn = QPushButton("< 返回")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setFixedHeight(dp(36))
        self.back_btn.clicked.connect(self.goBack)
        header_layout.addWidget(self.back_btn)

        header_layout.addStretch()
        container_layout.addLayout(header_layout)

        # 页面标题区
        title_section = QVBoxLayout()
        title_section.setSpacing(dp(8))

        self.title_label = QLabel("系统设置")
        title_section.addWidget(self.title_label)

        self.subtitle_label = QLabel("配置LLM服务、嵌入模型和系统参数")
        title_section.addWidget(self.subtitle_label)

        container_layout.addLayout(title_section)

        # 内容区域 - 使用卡片式Tab
        content_card = QFrame()
        content_card.setObjectName("content_card")
        card_layout = QVBoxLayout(content_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Tab控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        # LLM配置Tab
        self.llm_settings = LLMSettingsWidget()
        self.tab_widget.addTab(self.llm_settings, "LLM 配置")

        # 嵌入模型配置Tab
        self.embedding_settings = EmbeddingSettingsWidget()
        self.tab_widget.addTab(self.embedding_settings, "嵌入模型")

        # 高级配置Tab
        self.advanced_settings = AdvancedSettingsWidget()
        self.tab_widget.addTab(self.advanced_settings, "高级配置")

        card_layout.addWidget(self.tab_widget)
        container_layout.addWidget(content_card, stretch=1)

        main_layout.addWidget(self.main_container)

    def _apply_theme(self):
        """应用书籍风格主题"""
        bg_primary = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()
        serif_font = theme_manager.serif_font()
        ui_font = theme_manager.ui_font()

        # 主容器背景
        self.main_container.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_primary};
            }}
        """)

        # 返回按钮
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {ui_font};
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
            }}
            QPushButton:hover {{
                color: {accent_color};
                border-color: {accent_color};
                background-color: {bg_secondary};
            }}
        """)

        # 页面标题
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {serif_font};
                font-size: {sp(32)}px;
                font-weight: bold;
                color: {text_primary};
                letter-spacing: {dp(1)}px;
            }}
        """)

        # 副标题
        self.subtitle_label.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {text_secondary};
            }}
        """)

        # 内容卡片
        self.findChild(QFrame, "content_card").setStyleSheet(f"""
            QFrame#content_card {{
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: {dp(12)}px;
            }}
        """)

        # Tab控件样式
        self.tab_widget.setStyleSheet(f"""
            QTabWidget {{
                background-color: transparent;
            }}
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
                padding: {dp(20)}px;
            }}
            QTabBar {{
                background-color: transparent;
            }}
            QTabBar::tab {{
                font-family: {ui_font};
                background-color: transparent;
                color: {text_secondary};
                border: none;
                border-bottom: 2px solid transparent;
                padding: {dp(12)}px {dp(24)}px;
                margin-right: {dp(8)}px;
                font-size: {sp(14)}px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                color: {accent_color};
                border-bottom: 2px solid {accent_color};
            }}
            QTabBar::tab:hover:!selected {{
                color: {text_primary};
                background-color: rgba(0, 0, 0, 0.03);
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