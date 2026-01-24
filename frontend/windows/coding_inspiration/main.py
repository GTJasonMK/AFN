"""
编程项目需求分析对话主类

通过AI对话进行需求分析，生成项目架构设计蓝图。
复用小说灵感对话的组件，适配编程项目的API和文案。
"""

import logging

from PyQt6.QtCore import QTimer
from pages.base_page import BasePage
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.message_service import MessageService, confirm
from utils.dpi_utils import dp
from windows.inspiration_mode.mixins import InspirationBaseUIMixin, BlueprintHandlerMixin, ConversationManagerMixin

# 复用小说灵感对话的组件
from windows.inspiration_mode.components import (
    ChatBubble,
    InspiredOptionsContainer,
)
from windows.inspiration_mode.services import ConversationState

logger = logging.getLogger(__name__)


class CodingInspirationMode(InspirationBaseUIMixin, BlueprintHandlerMixin, ConversationManagerMixin, BasePage):
    """编程项目需求分析对话 - AI对话生成架构设计"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.api_client = APIClientManager.get_client()

        # 对话状态
        self._state = ConversationState()

        # Worker线程管理
        self.current_worker = None  # SSE对话Worker
        self.blueprint_worker = None  # 架构生成Worker
        self._blueprint_loading_dialog = None  # 加载对话框

        # UI状态
        self.current_ai_bubble = None  # 当前AI消息气泡
        self._current_options_container = None  # 当前选项容器
        self._prev_options_container = None  # 上一轮选项容器

        self.setupUI()

    def _get_page_title(self) -> str:
        """页面标题文案"""
        return "需求分析对话"

    def _get_generate_button_text(self) -> str:
        """生成按钮文案"""
        return "生成架构设计"

    def _get_generate_button_min_width(self) -> int:
        """生成按钮最小宽度"""
        return 120

    def _get_message_sent_handler(self):
        """输入框消息发送回调"""
        return self._on_message_sent

    def _get_transparent_containers(self):
        """透明模式容器列表"""
        return []

    def _get_restore_containers(self):
        """普通模式容器列表"""
        return []

    def _add_extra_pages(self):
        """编程需求分析暂无额外页面"""
        return

    def _init_conversation(self):
        """初始化对话"""
        welcome_msg = "你好！我是AFN需求分析助手。\n\n请告诉我你想要构建什么样的系统，我会帮你分析需求并设计项目架构。"
        self._add_message(welcome_msg, is_user=False)

    def initConversation(self):
        """兼容对话管理Mixin的初始化入口"""
        self._init_conversation()

    def _add_message(self, message: str, is_user: bool = True, typing_effect: bool = False):
        """添加消息到对话历史"""
        bubble = ChatBubble(message, is_user, typing_effect=typing_effect)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

        # 滚动到底部
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def addMessage(self, message: str, is_user: bool = True, typing_effect: bool = False):
        """兼容对话管理Mixin的消息入口"""
        self._add_message(message, is_user=is_user, typing_effect=typing_effect)

    def _on_message_sent(self, message: str):
        """用户发送消息"""
        # 添加用户消息
        self._add_message(message, is_user=True)

        # 锁定当前选项容器
        if self._current_options_container:
            try:
                self._current_options_container.lock()
            except RuntimeError:
                pass

        # 禁用输入
        self.input_widget.setEnabled(False)

        # 创建AI消息气泡
        self.current_ai_bubble = ChatBubble("", is_user=False, typing_effect=False, show_loading=True)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.current_ai_bubble)

        # 滚动到底部
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

        # 启动SSE流式对话
        self._start_sse_stream(message)

    def _show_completion_hint(self):
        """显示对话完成提示"""
        # 添加一条系统提示消息
        hint_msg = "需求分析已完成！点击右上角「生成架构设计」按钮，开始生成项目架构。"
        hint_bubble = ChatBubble(hint_msg, is_user=False, typing_effect=False)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, hint_bubble)

        # 滚动到底部
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

        # 高亮生成按钮
        if hasattr(self, 'generate_btn') and self.generate_btn:
            highlight_color = theme_manager.book_accent_color()
            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {highlight_color};
                    border: 2px solid {highlight_color};
                    border-radius: {dp(4)}px;
                    color: {theme_manager.BUTTON_TEXT};
                    font-family: {theme_manager.serif_font()};
                    font-weight: bold;
                    padding: {dp(6)}px {dp(16)}px;
                    min-width: 120px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.book_text_primary()};
                    border-color: {theme_manager.book_text_primary()};
                }}
            """)

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
        """用户选择了选项"""
        message = f"选择：{option_label}"
        self._on_message_sent(message)

    def _get_conversation_mode(self) -> str:
        """获取对话模式类型"""
        return "coding"

    def _handle_conversation_error_bubble(self, error_msg: str) -> None:
        """编程对话错误时保留气泡并标记错误"""
        if self.current_ai_bubble:
            try:
                self.current_ai_bubble.stop_loading()
                self.current_ai_bubble.set_error("对话出错，请重试")
            except RuntimeError:
                pass

    def _after_stream_complete(self, metadata: dict) -> None:
        """流式完成后补充提示引导"""
        is_complete = metadata.get('is_complete', False)
        ready_for_blueprint = metadata.get('ready_for_blueprint', False)
        if is_complete or ready_for_blueprint:
            self._state.is_complete = True
            self._show_completion_hint()

    def onGenerateBlueprint(self):
        """生成架构设计"""
        if not self._state.project_id:
            MessageService.show_warning(self, "请先进行对话", "提示")
            return

        # 检查对话是否完成
        if not self._state.is_complete:
            if not confirm(
                self,
                "AI表示还需要更多信息来完成需求分析。\n\n"
                "确定要继续生成吗？将使用「自动补全」模式，AI会根据已有信息自动补全缺失的需求。",
                "对话未完成"
            ):
                return
            # 用户确认使用自动补全模式
            self._do_generate_blueprint(allow_incomplete=True)
            return

        if not confirm(self, "确定要根据当前对话生成架构设计吗？", "确认生成"):
            return

        self._do_generate_blueprint()

    def _get_blueprint_loading_message(self) -> str:
        """获取加载提示文案"""
        return "正在生成架构设计...\n\nAI正在分析需求并设计项目架构"

    def _call_generate_blueprint(self, *, force_regenerate: bool, allow_incomplete: bool):
        """调用架构设计生成接口"""
        return self.api_client.generate_coding_blueprint(
            self._state.project_id,
            allow_incomplete=allow_incomplete
        )

    def _on_blueprint_success(self, response):
        """架构设计生成成功"""
        logger.info("架构设计生成成功")
        self._close_blueprint_loading_dialog()
        self._restore_generate_button()

        try:
            if not isinstance(response, dict):
                MessageService.show_error(self, "架构设计生成失败：API响应格式错误", "生成失败")
                return

            blueprint = response.get('blueprint', {})

            if not blueprint:
                MessageService.show_error(self, "架构设计生成失败：数据为空", "生成失败")
                return

            MessageService.show_success(self, "架构设计生成成功！")
            # 导航到详情页
            self.navigateTo('CODING_DETAIL', project_id=self._state.project_id)

        except Exception as e:
            logger.error("处理架构设计数据失败: %s", str(e), exc_info=True)
            MessageService.show_error(self, f"处理数据失败：{str(e)}", "生成失败")

    def _on_blueprint_error(self, error_msg):
        """架构设计生成失败"""
        logger.error("架构设计生成错误: %s", error_msg[:100] if error_msg else "empty")
        self._close_blueprint_loading_dialog()
        self._restore_generate_button()
        MessageService.show_error(self, f"生成架构设计失败：{error_msg}", "生成失败")

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
        self._state.reset(project_id=project_id)

        if project_id:
            self._load_conversation_history(project_id)
        else:
            self._init_conversation()

    def onHide(self):
        """页面隐藏时清理资源"""
        self._cleanup_workers()

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self._close_blueprint_loading_dialog()
        self._cleanup_workers()
        super().closeEvent(event)

    def _cleanup_workers(self):
        """清理Worker资源"""
        if self.current_worker:
            try:
                self.current_worker.stop()
            except Exception:
                pass
            self.current_worker = None

        self._cleanup_blueprint_worker()
