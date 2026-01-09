"""
编程项目需求分析对话主类

通过AI对话进行需求分析，生成项目架构设计蓝图。
复用小说灵感对话的组件，适配编程项目的API和文案。
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
from utils.message_service import MessageService, confirm
from utils.dpi_utils import dp, sp
from utils.sse_worker import SSEWorker

# 复用小说灵感对话的组件
from windows.inspiration_mode.components import (
    ChatBubble,
    ConversationInput,
    InspiredOptionsContainer,
)
from windows.inspiration_mode.services import ConversationState

logger = logging.getLogger(__name__)


class CodingInspirationMode(BasePage):
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

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()

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

        self.title = QLabel("需求分析对话")
        header_layout.addWidget(self.title, stretch=1)

        # 生成架构按钮 - 始终可见
        self.generate_btn = QPushButton("生成架构设计")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self._on_generate_blueprint)
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
        self.input_widget.messageSent.connect(self._on_message_sent)
        conv_layout.addWidget(self.input_widget)

        self.stack.addWidget(self.conversation_page)

        main_layout.addWidget(self.stack, stretch=1)

        # 初始化对话
        self._init_conversation()

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
        else:
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)

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

        # 生成架构按钮 - 强调样式
        if hasattr(self, 'generate_btn'):
            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {highlight_color};
                    border: 1px solid {highlight_color};
                    border-radius: {dp(4)}px;
                    color: {theme_manager.BUTTON_TEXT};
                    font-family: {serif_font};
                    padding: {dp(4)}px {dp(12)}px;
                    min-width: 120px;
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

    def _init_conversation(self):
        """初始化对话"""
        welcome_msg = "你好！我是AFN需求分析助手。\n\n请告诉我你想要构建什么样的系统，我会帮你分析需求并设计项目架构。"
        self._add_message(welcome_msg, is_user=False)

    def _add_message(self, message: str, is_user: bool = True, typing_effect: bool = False):
        """添加消息到对话历史"""
        bubble = ChatBubble(message, is_user, typing_effect=typing_effect)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

        # 滚动到底部
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

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

    def _start_sse_stream(self, message: str):
        """启动SSE流式监听"""
        # 如果没有项目ID，先创建项目
        if not self._state.project_id:
            try:
                response = self.api_client.create_coding_project(
                    title="未命名项目",
                    initial_prompt=message,
                    skip_conversation=False
                )
                self._state.project_id = response.get('id')
            except Exception as e:
                MessageService.show_error(self, f"创建项目失败：{str(e)}", "错误")
                self.input_widget.setEnabled(True)
                return

        # 构造SSE URL（编程项目API）
        url = f"{self.api_client.base_url}/api/coding/{self._state.project_id}/inspiration/converse-stream"

        # 构造请求负载
        payload = {
            "user_input": {"message": message},
            "conversation_state": {}
        }

        # 重置选项缓存
        self._state.pending_options = []
        self._prev_options_container = None

        # 创建SSE Worker
        self.current_worker = SSEWorker(url, payload)

        # 连接信号
        self.current_worker.streaming_start.connect(self._on_streaming_start)
        self.current_worker.ai_message_chunk.connect(self._on_ai_message_chunk)
        self.current_worker.option_received.connect(self._on_option_received)
        self.current_worker.complete.connect(self._on_stream_complete)
        self.current_worker.error.connect(self._on_stream_error)

        self.current_worker.start()

    def _on_streaming_start(self, data: dict):
        """流式输出开始"""
        self.input_widget.setEnabled(False)
        if hasattr(self, 'generate_btn'):
            self.generate_btn.setEnabled(False)
        if hasattr(self, 'back_btn'):
            self.back_btn.setEnabled(False)

    def _on_ai_message_chunk(self, text: str):
        """收到AI消息片段"""
        if self.current_ai_bubble:
            self.current_ai_bubble.append_text(text)
            QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            ))

    def _on_option_received(self, data: dict):
        """收到单个选项"""
        option = data.get('option', {})
        if option:
            self._state.pending_options.append(option)

            index = data.get('index', 0)

            # 第一个选项时创建容器
            if index == 0:
                self._prev_options_container = self._current_options_container
                if self._prev_options_container:
                    try:
                        self._prev_options_container.lock()
                    except RuntimeError:
                        self._prev_options_container = None

                self._current_options_container = InspiredOptionsContainer([])
                self._current_options_container.option_selected.connect(self._on_option_selected)
                self.chat_layout.insertWidget(self.chat_layout.count() - 1, self._current_options_container)

            # 添加选项
            if self._current_options_container:
                self._current_options_container.add_option(option)
                QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
                    self.chat_scroll.verticalScrollBar().maximum()
                ))

    def _on_stream_complete(self, data: dict):
        """流式完成"""
        # 停止加载动画
        if self.current_ai_bubble:
            self.current_ai_bubble.stop_loading()

        # 恢复输入
        self.input_widget.setEnabled(True)
        if hasattr(self, 'back_btn'):
            self.back_btn.setEnabled(True)
        if hasattr(self, 'generate_btn'):
            self.generate_btn.setEnabled(True)

        # 更新对话完成状态
        is_complete = data.get('is_complete', False)
        ready_for_blueprint = data.get('ready_for_blueprint', False)

        if is_complete or ready_for_blueprint:
            self._state.is_complete = True

        self.current_worker = None

    def _on_stream_error(self, error_msg: str):
        """流式错误"""
        logger.error("SSE流式错误: %s", error_msg)

        # 停止加载动画
        if self.current_ai_bubble:
            self.current_ai_bubble.stop_loading()
            self.current_ai_bubble.set_error("对话出错，请重试")

        # 恢复输入
        self.input_widget.setEnabled(True)
        if hasattr(self, 'back_btn'):
            self.back_btn.setEnabled(True)
        if hasattr(self, 'generate_btn'):
            self.generate_btn.setEnabled(True)

        MessageService.show_error(self, f"对话出错：{error_msg}", "错误")
        self.current_worker = None

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

    def _on_generate_blueprint(self):
        """生成架构设计 - 类似小说蓝图生成逻辑"""
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

    def _do_generate_blueprint(self, allow_incomplete: bool = False):
        """执行架构设计生成

        Args:
            allow_incomplete: 是否允许在对话未完成时生成（自动补全模式）
        """
        from utils.async_worker import AsyncWorker
        from components.dialogs import LoadingDialog

        # 防御性检查
        if not self._state.project_id:
            MessageService.show_warning(self, "请先进行对话创建项目", "提示")
            return

        # 创建加载对话框
        self._blueprint_loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在生成架构设计...\n\nAI正在分析需求并设计项目架构",
            cancelable=True
        )
        self._blueprint_loading_dialog.show()

        # 禁用按钮
        if hasattr(self, 'generate_btn') and self.generate_btn:
            try:
                self.generate_btn.setEnabled(False)
            except RuntimeError:
                pass

        # 清理之前的worker
        self._cleanup_blueprint_worker()

        def do_generate():
            return self.api_client.generate_coding_blueprint(
                self._state.project_id,
                allow_incomplete=allow_incomplete
            )

        self.blueprint_worker = AsyncWorker(do_generate)
        self.blueprint_worker.success.connect(self._on_blueprint_success)
        self.blueprint_worker.error.connect(self._on_blueprint_error)
        self._blueprint_loading_dialog.rejected.connect(self._on_blueprint_cancelled)
        self.blueprint_worker.start()

    def _close_blueprint_loading_dialog(self):
        """安全关闭加载对话框"""
        try:
            if hasattr(self, '_blueprint_loading_dialog') and self._blueprint_loading_dialog:
                if self._blueprint_loading_dialog.isVisible():
                    self._blueprint_loading_dialog.close()
        except RuntimeError:
            pass
        self._blueprint_loading_dialog = None

    def _restore_generate_button(self):
        """恢复生成按钮状态"""
        if hasattr(self, 'generate_btn') and self.generate_btn:
            try:
                self.generate_btn.setEnabled(True)
            except RuntimeError:
                pass

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

    def _on_blueprint_cancelled(self):
        """架构设计生成取消"""
        self._cleanup_blueprint_worker()
        self._restore_generate_button()

    def _cleanup_blueprint_worker(self):
        """清理架构生成worker"""
        if self.blueprint_worker:
            try:
                try:
                    self.blueprint_worker.success.disconnect()
                    self.blueprint_worker.error.disconnect()
                except (TypeError, RuntimeError):
                    pass

                if self.blueprint_worker.isRunning():
                    self.blueprint_worker.cancel()
            except RuntimeError:
                pass
            finally:
                self.blueprint_worker = None

    def _load_conversation_history(self, project_id: str):
        """加载对话历史"""
        import json

        try:
            history = self.api_client.get_coding_inspiration_history(project_id)

            if not history:
                # 没有历史，显示初始欢迎消息
                self._init_conversation()
                return

            # 预处理：找出所有用户选择消息的索引，用于判断哪些选项需要锁定
            user_selection_indices = set()
            for i, record in enumerate(history):
                role = record.get('role')
                content = record.get('content')
                if role == 'user' and content:
                    try:
                        data = json.loads(content)
                        user_msg = None
                        if isinstance(data, dict):
                            user_msg = data.get('message') or data.get('value')
                        elif isinstance(data, str):
                            user_msg = data
                        # 检查是否是选择消息
                        if user_msg and user_msg.startswith('选择：'):
                            user_selection_indices.add(i)
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        pass

            # 逐条恢复对话气泡
            for i, record in enumerate(history):
                role = record.get('role')
                content = record.get('content')

                if not role or not content:
                    continue

                # 解析content（JSON字符串）
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    # JSON格式错误，跳过此记录
                    continue

                if role == 'user':
                    # 用户消息
                    # 兼容多种格式：{"message": "..."} 或 {"value": "..."}
                    user_msg = None
                    if isinstance(data, dict):
                        user_msg = data.get('message') or data.get('value')
                    elif isinstance(data, str):
                        user_msg = data

                    if user_msg:
                        self._add_message(user_msg, is_user=True)

                elif role == 'assistant':
                    # AI消息
                    if isinstance(data, dict):
                        ai_message = data.get('ai_message', '')
                        ui_control = data.get('ui_control', {})

                        # 添加AI消息气泡
                        if ai_message:
                            self._add_message(ai_message, is_user=False)

                        # 恢复灵感选项（如果有）
                        if ui_control.get('type') == 'inspired_options':
                            options_data = ui_control.get('options', [])
                            if options_data:
                                # 检查下一条消息是否是用户选择，如果是则锁定选项
                                should_lock = (i + 1) in user_selection_indices
                                self._add_inspired_options(options_data, locked=should_lock)

                        # 更新对话完成状态
                        if data.get('is_complete'):
                            self._state.is_complete = True

        except Exception as e:
            logger.error("加载对话历史失败: %s", e)
            # 加载失败，显示初始欢迎消息
            self._init_conversation()

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
