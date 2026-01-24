"""
灵感对话与需求分析页面通用UI/主题Mixin

统一 Header、对话页与主题样式构建，允许页面注入文案与附加页面。
"""

from typing import Callable, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QStackedWidget,
    QScrollArea,
)

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from ..components import ConversationInput


class InspirationBaseUIMixin:
    """灵感/需求分析页面UI与主题复用基类"""

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()

    def _get_page_title(self) -> str:
        """页面标题文案"""
        return "灵感对话"

    def _get_generate_button_text(self) -> str:
        """生成按钮文案"""
        return "生成蓝图"

    def _get_generate_button_min_width(self) -> int:
        """生成按钮最小宽度"""
        return 100

    def _get_message_sent_handler(self) -> Optional[Callable]:
        """获取输入框消息发送回调"""
        return None

    def _get_transparent_containers(self) -> List[str]:
        """透明模式下需要关闭背景填充的容器"""
        return []

    def _get_restore_containers(self) -> List[str]:
        """普通模式下需要恢复背景填充的容器"""
        return []

    def _add_extra_pages(self):
        """在堆叠容器中追加额外页面"""
        return

    def _create_ui_structure(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self.header = QFrame()
        self.header.setFixedHeight(64)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        self.title = QLabel(self._get_page_title())
        header_layout.addWidget(self.title, stretch=1)

        # 生成按钮
        self.generate_btn = QPushButton(self._get_generate_button_text())
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self.onGenerateBlueprint)
        header_layout.addWidget(self.generate_btn)

        self.back_btn = QPushButton("返回")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.goBack)
        header_layout.addWidget(self.back_btn)

        main_layout.addWidget(self.header)

        # 主内容区
        self.stack = QStackedWidget()

        # 对话页面
        self.conversation_page = QWidget()
        conv_layout = QVBoxLayout(self.conversation_page)
        conv_layout.setContentsMargins(24, 16, 24, 16)
        conv_layout.setSpacing(16)

        # 对话历史滚动区
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_container)
        conv_layout.addWidget(self.chat_scroll, stretch=1)

        # 输入框
        self.input_widget = ConversationInput()
        handler = self._get_message_sent_handler()
        if handler:
            self.input_widget.messageSent.connect(handler)
        conv_layout.addWidget(self.input_widget)

        self.stack.addWidget(self.conversation_page)

        # 追加页面
        self._add_extra_pages()

        main_layout.addWidget(self.stack, stretch=1)

        # 初始化对话
        self.initConversation()

    def _apply_theme(self):
        """应用主题样式"""
        from themes.modern_effects import ModernEffects

        # 使用 theme_manager 的书香风格便捷方法
        bg_color = theme_manager.book_bg_primary()
        header_bg = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        border_color = theme_manager.book_border_color()
        highlight_color = theme_manager.book_accent_color()
        serif_font = theme_manager.serif_font()

        # 透明效果
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        content_opacity = theme_manager.get_component_opacity("content")

        if transparency_enabled:
            bg_rgba = ModernEffects.hex_to_rgba(bg_color, content_opacity)
            self.setStyleSheet(f"background-color: {bg_rgba};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)

            for container_name in self._get_transparent_containers():
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(False)
        else:
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)

            for container_name in self._get_restore_containers():
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(True)

        # QStackedWidget
        if hasattr(self, 'stack'):
            self.stack.setStyleSheet("background: transparent;")

        # Header
        if hasattr(self, 'header'):
            if transparency_enabled:
                header_opacity = theme_manager.get_component_opacity("header")
                header_bg_rgba = ModernEffects.hex_to_rgba(header_bg, header_opacity)
                border_rgba = ModernEffects.hex_to_rgba(border_color, 0.3)
                self.header.setStyleSheet(f"""
                    QFrame {{
                        background-color: {header_bg_rgba};
                        border: none;
                        border-bottom: 1px solid {border_rgba};
                    }}
                """)
            else:
                self.header.setStyleSheet(f"""
                    QFrame {{
                        background-color: {header_bg};
                        border: none;
                        border-bottom: 1px solid {border_color};
                    }}
                """)

        # 标题
        if hasattr(self, 'title'):
            self.title.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(20)}px;
                font-weight: bold;
                color: {text_primary};
                letter-spacing: {dp(2)}px;
            """)

        # 按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                color: {text_primary};
                font-family: {serif_font};
                padding: {dp(4)}px {dp(12)}px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                color: {highlight_color};
                border-color: {highlight_color};
                background-color: {theme_manager.PRIMARY_PALE};
            }}
        """

        if hasattr(self, 'back_btn'):
            self.back_btn.setStyleSheet(btn_style)

        # 生成按钮 - 强调样式
        if hasattr(self, 'generate_btn'):
            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {highlight_color};
                    border: 1px solid {highlight_color};
                    border-radius: {dp(4)}px;
                    color: {theme_manager.BUTTON_TEXT};
                    font-family: {serif_font};
                    padding: {dp(4)}px {dp(12)}px;
                    min-width: {self._get_generate_button_min_width()}px;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
                    border-color: {text_primary};
                }}
            """)

        # 对话页面和聊天区域
        if hasattr(self, 'conversation_page'):
            self.conversation_page.setStyleSheet("background: transparent;")

        if hasattr(self, 'chat_container'):
            self.chat_container.setStyleSheet("background: transparent;")

        if hasattr(self, 'chat_scroll'):
            self.chat_scroll.setStyleSheet(f"""
                QScrollArea {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea > QWidget > QWidget {{
                    background: transparent;
                }}
                {theme_manager.scrollbar()}
            """)
            if self.chat_scroll.viewport():
                self.chat_scroll.viewport().setStyleSheet("background-color: transparent;")


__all__ = [
    "InspirationBaseUIMixin",
]
