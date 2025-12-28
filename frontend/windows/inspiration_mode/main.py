"""
灵感模式主类

通过AI对话生成项目蓝图
"""

import logging

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QFrame, QLabel, QPushButton,
    QStackedWidget, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from pages.base_page import BasePage
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.message_service import confirm
from utils.dpi_utils import dp, sp

from .components import (
    ChatBubble,
    ConversationInput,
    BlueprintConfirmation,
    BlueprintDisplay,
    InspiredOptionsContainer,
)
from .services import ConversationState
from .mixins import BlueprintHandlerMixin, ConversationManagerMixin

logger = logging.getLogger(__name__)


class InspirationMode(BlueprintHandlerMixin, ConversationManagerMixin, BasePage):
    """灵感模式 - AI对话生成蓝图"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.api_client = APIClientManager.get_client()

        # 对话状态（封装为独立类）
        self._state = ConversationState()

        # Worker线程管理
        self.current_worker = None  # 异步工作线程（SSE对话）
        self.blueprint_worker = None  # 蓝图生成工作线程
        self._refine_worker = None  # 蓝图优化工作线程

        # UI状态（对话框和气泡）
        self._blueprint_loading_dialog = None  # 蓝图生成加载对话框
        self._refine_loading_dialog = None  # 蓝图优化加载对话框
        self.current_ai_bubble = None  # 当前正在接收流式内容的AI气泡
        self._current_options_container = None  # 当前选项容器（用于选择后锁定）
        self._prev_options_container = None  # 上一轮选项容器（用于错误恢复）

        self.setupUI()

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self.header = QFrame()
        self.header.setFixedHeight(64)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        self.title = QLabel("灵感对话")
        header_layout.addWidget(self.title, stretch=1)

        # 生成蓝图按钮
        self.generate_btn = QPushButton("生成蓝图")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self.onGenerateBlueprint)
        header_layout.addWidget(self.generate_btn)

        self.back_btn = QPushButton("返回")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.goBack)
        header_layout.addWidget(self.back_btn)

        main_layout.addWidget(self.header)

        # 主内容区（堆叠布局）
        self.stack = QStackedWidget()

        # 页面1: 对话页面
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
        self.input_widget.messageSent.connect(self.onMessageSent)
        conv_layout.addWidget(self.input_widget)

        self.stack.addWidget(self.conversation_page)

        # 页面2: 确认页面
        self.confirmation_page = BlueprintConfirmation()
        self.confirmation_page.confirmed.connect(self.onBlueprintConfirmed)
        self.confirmation_page.rejected.connect(self.onBlueprintRejected)
        self.stack.addWidget(self.confirmation_page)

        # 页面3: 蓝图展示
        self.display_page = BlueprintDisplay()
        self.stack.addWidget(self.display_page)

        main_layout.addWidget(self.stack, stretch=1)

        # 初始化对话
        self.initConversation()

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格"""
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QWidget
        from themes.modern_effects import ModernEffects

        # 使用 theme_manager 的书香风格便捷方法
        bg_color = theme_manager.book_bg_primary()
        header_bg = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        border_color = theme_manager.book_border_color()
        highlight_color = theme_manager.book_accent_color()
        serif_font = theme_manager.serif_font()

        # 获取透明效果配置
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        content_opacity = transparency_config.get("content_opacity", 0.95)

        if transparency_enabled:
            # 透明模式：页面背景使用RGBA实现半透明
            bg_rgba = ModernEffects.hex_to_rgba(bg_color, content_opacity)
            self.setStyleSheet(f"background-color: {bg_rgba};")

            # 设置WA_TranslucentBackground使透明生效
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)

            # 指定容器设置透明（不使用findChildren避免影响其他页面）
            transparent_containers = ['header', 'stack', 'conversation_page', 'chat_container', 'confirmation_page', 'display_page']
            for container_name in transparent_containers:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(False)
        else:
            # 普通模式：使用实色背景，恢复背景填充
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)

            # 恢复容器的背景填充
            containers_to_restore = ['header', 'stack', 'conversation_page', 'chat_container', 'confirmation_page', 'display_page']
            for container_name in containers_to_restore:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(True)

        # QStackedWidget - 透明背景
        if hasattr(self, 'stack'):
            self.stack.setStyleSheet("background: transparent;")

        # Header - 简约风格（透明模式下使用半透明背景）
        if hasattr(self, 'header'):
            if transparency_enabled:
                header_opacity = transparency_config.get("header_opacity", 0.90)
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

        # 按钮通用样式
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

        # 返回按钮
        if hasattr(self, 'back_btn'):
            self.back_btn.setStyleSheet(btn_style)

        # 生成蓝图按钮 - 实心强调
        if hasattr(self, 'generate_btn'):
            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {highlight_color};
                    border: 1px solid {highlight_color};
                    border-radius: {dp(4)}px;
                    color: {theme_manager.BUTTON_TEXT};
                    font-family: {serif_font};
                    padding: {dp(4)}px {dp(12)}px;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
                    border-color: {text_primary};
                }}
            """)

        # 对话页面和聊天区域 - 透明背景
        if hasattr(self, 'conversation_page'):
            self.conversation_page.setStyleSheet("background: transparent;")

        if hasattr(self, 'chat_container'):
            self.chat_container.setStyleSheet("background: transparent;")

        # 聊天滚动区
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
            # 设置viewport透明背景
            if self.chat_scroll.viewport():
                self.chat_scroll.viewport().setStyleSheet("background-color: transparent;")

    def initConversation(self):
        """初始化对话"""
        # 添加AI欢迎消息
        welcome_msg = "你好！我是AFN AI助手。\n\n请告诉我你的创意想法，我会帮你创建一个完整的小说蓝图。"
        self.addMessage(welcome_msg, is_user=False)

    def addMessage(self, message: str, is_user: bool = True, typing_effect: bool = False):
        """添加消息到对话历史"""
        bubble = ChatBubble(message, is_user, typing_effect=typing_effect)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

        # 滚动到底部
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def onMessageSent(self, message: str):
        """用户发送消息（SSE流式版本）"""
        # 添加用户消息
        self.addMessage(message, is_user=True)

        # 立即锁定当前选项容器（如果有），防止重复点击
        # 无论用户是点击选项还是输入文本，都需要锁定
        if self._current_options_container:
            try:
                self._current_options_container.lock()
            except RuntimeError:
                pass

        # 禁用输入并显示加载状态
        self.input_widget.setEnabled(False)

        # 创建带加载动画的AI消息气泡（用于接收流式内容）
        self.current_ai_bubble = ChatBubble("", is_user=False, typing_effect=False, show_loading=True)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.current_ai_bubble)

        # 滚动到底部
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

        # 启动SSE流式监听
        self._start_sse_stream(message)

    def _show_confirmation_page(self):
        """切换到蓝图确认页面"""
        if hasattr(self, 'stack') and self.stack:
            self.stack.setCurrentWidget(self.confirmation_page)
        # 隐藏生成蓝图按钮（确认页面已有自己的操作按钮）
        if hasattr(self, 'generate_btn') and self.generate_btn:
            self.generate_btn.hide()

    def _show_conversation_page(self):
        """切换回对话页面"""
        if hasattr(self, 'stack') and self.stack:
            self.stack.setCurrentIndex(0)
        # 显示生成蓝图按钮
        if hasattr(self, 'generate_btn') and self.generate_btn:
            self.generate_btn.show()

    def refresh(self, **params):
        """刷新页面"""
        # 清空对话历史
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重置UI状态
        self._current_options_container = None
        self._prev_options_container = None

        # 检查是否是继续未完成的项目
        project_id = params.get('project_id')

        # 使用 ConversationState.reset() 重置对话状态
        self._state.reset(project_id=project_id)

        if project_id:
            # 恢复未完成的对话 - 加载对话历史
            self._load_conversation_history(project_id)
        else:
            # 全新对话 - 重新初始化
            self.initConversation()

        self._show_conversation_page()

    def onRestart(self):
        """重新开始对话"""
        if confirm(self, "确定要重新开始吗？当前对话将被清空。", "确认重启"):
            self.refresh()

    def onHide(self):
        """页面隐藏时清理资源"""
        self._cleanup_all_workers()

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        # 先关闭可能打开的对话框
        self._close_blueprint_loading_dialog()
        self._close_refine_loading_dialog()
        # 清理所有worker
        self._cleanup_all_workers()
        super().closeEvent(event)

    def _cleanup_all_workers(self):
        """统一清理所有Worker资源

        确保所有异步任务被正确停止和清理，防止资源泄漏。
        包括：
        - SSE对话Worker
        - 蓝图生成Worker
        - 蓝图优化Worker
        """
        self._cleanup_sse_worker()
        self._cleanup_blueprint_worker()
        self._cleanup_refine_worker()

    def _cleanup_worker(self):
        """清理异步worker - 兼容旧调用，内部转发到统一清理方法"""
        self._cleanup_all_workers()

    def _add_inspired_options(self, options_data: list, locked: bool = False):
        """添加灵感选项卡片

        Args:
            options_data: 选项数据列表
            locked: 是否锁定（用于恢复历史记录时已选择的选项）
        """
        # 创建选项容器
        options_container = InspiredOptionsContainer(options_data)
        options_container.option_selected.connect(self._on_option_selected)

        # 如果是锁定状态（恢复历史），直接锁定
        if locked:
            options_container.lock()

        # 添加到对话历史（在stretch之前）
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, options_container)

        # 保存当前选项容器引用（用于选择后锁定）
        self._current_options_container = options_container

        # 滚动到底部
        QTimer.singleShot(200, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def _on_option_selected(self, option_id: str, option_label: str):
        """用户选择了某个灵感选项"""
        # 注意：不立即锁定，等待SSE流成功完成后再锁定
        # 保存当前选项容器引用，用于成功后锁定
        # （_current_options_container 在 _add_inspired_options 中已设置）

        # 自动发送选择的选项作为用户消息
        message = f"选择：{option_label}"
        self.onMessageSent(message)
