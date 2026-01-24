"""
灵感模式主类

通过AI对话生成小说项目蓝图
"""

import logging

from PyQt6.QtCore import QTimer
from pages.base_page import BasePage
from api.manager import APIClientManager
from utils.message_service import confirm

from .components import (
    ChatBubble,
    BlueprintConfirmation,
    BlueprintDisplay,
    InspiredOptionsContainer,
)
from .services import ConversationState
from .mixins import InspirationBaseUIMixin, BlueprintHandlerMixin, ConversationManagerMixin

logger = logging.getLogger(__name__)


class InspirationMode(InspirationBaseUIMixin, BlueprintHandlerMixin, ConversationManagerMixin, BasePage):
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

    def _get_page_title(self) -> str:
        """页面标题文案"""
        return "灵感对话"

    def _get_generate_button_text(self) -> str:
        """生成按钮文案"""
        return "生成蓝图"

    def _get_generate_button_min_width(self) -> int:
        """生成按钮最小宽度"""
        return 100

    def _get_message_sent_handler(self):
        """输入框消息发送回调"""
        return self.onMessageSent

    def _get_transparent_containers(self):
        """透明模式容器列表"""
        return [
            'header',
            'stack',
            'conversation_page',
            'chat_container',
            'confirmation_page',
            'display_page',
        ]

    def _get_restore_containers(self):
        """普通模式容器列表"""
        return [
            'header',
            'stack',
            'conversation_page',
            'chat_container',
            'confirmation_page',
            'display_page',
        ]

    def _add_extra_pages(self):
        """追加蓝图确认与展示页面"""
        self.confirmation_page = BlueprintConfirmation()
        self.confirmation_page.confirmed.connect(self.onBlueprintConfirmed)
        self.confirmation_page.rejected.connect(self.onBlueprintRejected)
        self.stack.addWidget(self.confirmation_page)

        self.display_page = BlueprintDisplay()
        self.stack.addWidget(self.display_page)

    def initConversation(self):
        """初始化对话"""
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
