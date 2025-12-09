"""
设置页面主视图
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QWidget, QTabWidget
)
from PyQt6.QtCore import Qt
from pages.base_page import BasePage
from themes.theme_manager import theme_manager
from .llm_settings_widget import LLMSettingsWidget
from .embedding_settings_widget import EmbeddingSettingsWidget
from .advanced_settings_widget import AdvancedSettingsWidget


class SettingsView(BasePage):
    """设置页面 - 禅意风格（对应SettingsView.vue）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """初始化UI"""
        # 清空现有布局
        existing_layout = self.layout()
        if existing_layout is not None:
            while existing_layout.count():
                item = existing_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_sublayout(item.layout())
            main_layout = existing_layout
        else:
            main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 主容器（禅意风格渐变背景 - 与首页一致）
        main_container = QWidget()
        main_container.setStyleSheet(f"""
            QWidget {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """)

        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(48, 20, 48, 20)
        container_layout.setSpacing(16)

        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 返回按钮
        back_btn = QPushButton("← 返回")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_CARD};
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                padding: 10px 20px;
                font-size: 14px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.ACCENT_PRIMARY};
                border-color: {theme_manager.ACCENT_PRIMARY};
            }}
        """)
        back_btn.setFixedWidth(120)
        back_btn.clicked.connect(self.goBack)
        container_layout.addWidget(back_btn)

        # 主内容区
        content_layout = QVBoxLayout()
        content_layout.setSpacing(16)

        # 顶部标题
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 16)

        title_label = QLabel("系统设置")
        title_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: 24px;
            font-weight: 700;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        content_layout.addLayout(title_layout)

        # Tab控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_SM};
                background-color: {theme_manager.BG_CARD};
                padding: 16px;
            }}
            QTabBar::tab {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-bottom: none;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: {theme_manager.RADIUS_SM};
                border-top-right-radius: {theme_manager.RADIUS_SM};
                font-size: 14px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme_manager.BG_CARD};
                color: {theme_manager.ACCENT_PRIMARY};
                border-bottom: 2px solid {theme_manager.ACCENT_PRIMARY};
                font-weight: 600;
            }}
            QTabBar::tab:hover {{
                background-color: {theme_manager.BG_TERTIARY};
            }}
        """)

        # LLM配置Tab
        self.llm_settings = LLMSettingsWidget()
        self.tab_widget.addTab(self.llm_settings, "LLM配置")

        # 嵌入模型配置Tab
        self.embedding_settings = EmbeddingSettingsWidget()
        self.tab_widget.addTab(self.embedding_settings, "嵌入模型")

        # 高级配置Tab
        self.advanced_settings = AdvancedSettingsWidget()
        self.tab_widget.addTab(self.advanced_settings, "高级配置")

        content_layout.addWidget(self.tab_widget, stretch=1)

        container_layout.addLayout(content_layout, stretch=1)

        # 添加主容器到主布局
        main_layout.addWidget(main_container)

    def _clear_sublayout(self, layout):
        """递归清空子布局"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_sublayout(item.layout())

    def refresh(self, **params):
        """刷新页面"""
        # 主题切换后重建UI以应用新主题样式
        self.setupUI()