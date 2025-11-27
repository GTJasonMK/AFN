"""
写作台 AI 助手面板

提供上下文感知的 AI 辅助对话功能。
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, 
    QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from components.base import ThemeAwareWidget, ThemeAwareFrame
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService
from api.client import ArborisAPIClient

# 复用灵感模式的组件
from windows.inspiration_mode.chat_bubble import ChatBubble
from windows.inspiration_mode.conversation_input import ConversationInput


class AssistantPanel(ThemeAwareFrame):
    """写作台右侧的 AI 助手面板"""
    
    def __init__(self, project_id: str, parent=None):
        self.project_id = project_id
        self.api_client = ArborisAPIClient()
        
        # 状态
        self.is_loading = False
        
        super().__init__(parent)
        self.setupUI()
        
        # 初始欢迎语
        QTimer.singleShot(500, self._show_welcome_message)

    def _create_ui_structure(self):
        """创建 UI 结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. 标题栏
        self.header_bar = QWidget()
        self.header_bar.setFixedHeight(dp(50))
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(dp(16), 0, dp(16), 0)
        
        title_label = QLabel("AI 助手")
        title_label.setObjectName("assistant_title")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(self.header_bar)
        
        # 分割线
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setFixedHeight(1)
        layout.addWidget(self.divider)
        
        # 2. 对话历史区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        self.chat_layout.setSpacing(dp(16))
        self.chat_layout.addStretch()  # 保持消息在底部
        
        self.scroll_area.setWidget(self.chat_content)
        layout.addWidget(self.scroll_area)
        
        # 3. 输入区域
        self.input_container = QWidget()
        input_layout = QVBoxLayout(self.input_container)
        input_layout.setContentsMargins(dp(16), dp(12), dp(16), dp(16))
        
        self.input_box = ConversationInput()
        self.input_box.setPlaceholder("询问关于情节、人物的问题，或寻求写作建议...")
        self.input_box.messageSent.connect(self._on_send_message)
        
        input_layout.addWidget(self.input_box)
        layout.addWidget(self.input_container)

    def _apply_theme(self):
        """应用主题"""
        # 背景
        self.setStyleSheet(f"""
            AssistantPanel {{
                background-color: {theme_manager.BG_SECONDARY};
                border-left: 1px solid {theme_manager.BORDER_LIGHT};
            }}
        """)
        
        # 标题栏
        title_label = self.header_bar.findChild(QLabel, "assistant_title")
        if title_label:
            title_label.setStyleSheet(f"""
                font-size: {theme_manager.FONT_SIZE_MD};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
            """)
            
        # 分割线
        self.divider.setStyleSheet(f"background-color: {theme_manager.BORDER_LIGHT};")
        
        # 滚动区域背景
        self.scroll_area.setStyleSheet(f"background-color: transparent;")
        self.chat_content.setStyleSheet(f"background-color: transparent;")
        
        # 输入区域背景
        self.input_container.setStyleSheet(f"""
            background-color: {theme_manager.BG_SECONDARY};
            border-top: 1px solid {theme_manager.BORDER_LIGHT};
        """)

    def _show_welcome_message(self):
        """显示欢迎消息"""
        welcome_msg = "你好！我是你的写作助手。有什么我可以帮你的吗？我可以帮你构思情节、完善设定，或者润色段落。"
        self._add_ai_message(welcome_msg)

    def _on_send_message(self, text: str):
        """处理用户发送消息"""
        if not text.strip() or self.is_loading:
            return
            
        # 1. 显示用户消息
        self._add_user_message(text)
        
        # 2. 禁用输入
        self.input_box.setEnabled(False)
        self.is_loading = True
        
        # 3. 显示加载气泡
        self.loading_bubble = ChatBubble("", is_user=False, show_loading=True)
        self.chat_layout.addWidget(self.loading_bubble)
        self._scroll_to_bottom()
        
        # 4. 异步请求 API
        self.worker = AsyncAPIWorker(
            self.api_client.inspiration_converse,
            self.project_id,
            text
        )
        self.worker.success.connect(self._on_ai_response)
        self.worker.error.connect(self._on_ai_error)
        self.worker.start()

    def _on_ai_response(self, response: dict):
        """处理 AI 响应"""
        self.is_loading = False
        self.input_box.setEnabled(True)
        
        # 移除加载气泡
        if hasattr(self, 'loading_bubble'):
            self.loading_bubble.deleteLater()
            del self.loading_bubble
            
        # 提取 AI 回复
        ai_message = response.get('ai_message', '')
        if ai_message:
            self._add_ai_message(ai_message)
            
        self.input_box.input_field.setFocus()

    def _on_ai_error(self, error_msg: str):
        """处理错误"""
        self.is_loading = False
        self.input_box.setEnabled(True)
        
        # 移除加载气泡
        if hasattr(self, 'loading_bubble'):
            self.loading_bubble.deleteLater()
            del self.loading_bubble
            
        MessageService.show_error(self, f"助手响应失败: {error_msg}")
        
    def _add_user_message(self, text: str):
        """添加用户消息气泡"""
        bubble = ChatBubble(text, is_user=True)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()
        
    def _add_ai_message(self, text: str):
        """添加 AI 消息气泡"""
        bubble = ChatBubble(text, is_user=False, typing_effect=True)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """滚动到底部"""
        # 使用延时确保布局已更新
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
