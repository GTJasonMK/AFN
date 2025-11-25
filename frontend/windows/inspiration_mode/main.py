"""
灵感模式主类

通过AI对话生成项目蓝图
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QFrame, QLabel, QPushButton,
    QStackedWidget, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from pages.base_page import BasePage
from api.client import ArborisAPIClient
from themes.theme_manager import theme_manager
from themes import ModernEffects, ButtonStyles
from utils.message_service import MessageService, confirm
from utils.async_worker import AsyncAPIWorker
from utils.sse_worker import SSEWorker

from .chat_bubble import ChatBubble
from .conversation_input import ConversationInput
from .blueprint_confirmation import BlueprintConfirmation
from .blueprint_display import BlueprintDisplay
from .inspired_option_card import InspiredOptionsContainer


class InspirationMode(BasePage):
    """灵感模式 - AI对话生成蓝图"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.api_client = ArborisAPIClient()
        self.project_id = None
        self.blueprint = None
        self.current_worker = None  # 异步工作线程（SSE对话）
        self.blueprint_worker = None  # 蓝图生成工作线程
        self.current_ai_bubble = None  # 当前正在接收流式内容的AI气泡
        self.is_conversation_complete = False  # 对话是否完成

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
        """应用主题样式（可多次调用）"""
        # 整体背景 - 使用渐变
        gradient_colors = theme_manager.current_theme.BG_GRADIENT

        self.setStyleSheet(f"""
            InspirationMode {{
                background: {ModernEffects.linear_gradient(gradient_colors, 180)};
            }}
        """)

        # QStackedWidget - 透明背景
        if hasattr(self, 'stack'):
            self.stack.setStyleSheet("background: transparent;")

        # Header - 玻璃态效果
        if hasattr(self, 'header'):
            glass_bg = theme_manager.current_theme.GLASS_BG
            self.header.setStyleSheet(f"""
                QFrame {{
                    background-color: {glass_bg};
                    border: none;
                    border-bottom: 1px solid {theme_manager.BORDER_LIGHT};
                }}
            """)

        # 标题
        if hasattr(self, 'title'):
            self.title.setStyleSheet(f"""
                font-size: {theme_manager.FONT_SIZE_2XL};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
                letter-spacing: {theme_manager.LETTER_SPACING_WIDE};
            """)

        # 返回按钮 - 玻璃态次要按钮
        if hasattr(self, 'back_btn'):
            self.back_btn.setStyleSheet(f"""
                {ButtonStyles.secondary()}
                QPushButton {{
                    min-width: 80px;
                }}
            """)

        # 生成蓝图按钮 - 渐变主按钮
        if hasattr(self, 'generate_btn'):
            self.generate_btn.setStyleSheet(f"""
                {ButtonStyles.primary()}
                QPushButton {{
                    min-width: 100px;
                }}
            """)

        # 对话页面和聊天区域 - 透明背景以显示父级渐变
        if hasattr(self, 'conversation_page'):
            self.conversation_page.setStyleSheet("background: transparent;")

        if hasattr(self, 'chat_container'):
            self.chat_container.setStyleSheet("background: transparent;")

        # 聊天滚动区 - 透明背景+滚动条样式
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

    def initConversation(self):
        """初始化对话"""
        # 添加AI欢迎消息
        welcome_msg = "你好！我是Arboris AI助手。\n\n请告诉我你的创意想法，我会帮你创建一个完整的小说蓝图。"
        self.addMessage(welcome_msg, is_user=False)

    def addMessage(self, message, is_user=True, typing_effect=False):
        """添加消息到对话历史"""
        bubble = ChatBubble(message, is_user, typing_effect=typing_effect)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

        # 滚动到底部
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def onMessageSent(self, message):
        """用户发送消息（SSE流式版本）"""
        # 添加用户消息
        self.addMessage(message, is_user=True)

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

    def onGenerateBlueprint(self):
        """生成蓝图"""
        if not self.project_id:
            MessageService.show_warning(self, "请先进行对话", "提示")
            return

        # 检查对话是否完成
        if not self.is_conversation_complete:
            if not confirm(
                self,
                "AI表示还需要更多信息来生成蓝图。\n\n确定要继续生成吗？这可能导致生成失败或蓝图质量不佳。",
                "对话未完成"
            ):
                return

        if not confirm(self, "确定要根据当前对话生成蓝图吗？", "确认生成"):
            return

        self._do_generate_blueprint()

    def _do_generate_blueprint(self, force_regenerate=False):
        """执行蓝图生成（异步方式，不阻塞UI）

        Args:
            force_regenerate: 是否强制重新生成（将删除所有章节大纲、部分大纲、章节内容）
        """
        # 创建加载提示对话框
        from components.dialogs import LoadingDialog
        loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在生成蓝图...",
            cancelable=True
        )
        loading_dialog.show()

        # 禁用生成按钮，防止重复点击
        if hasattr(self, 'generate_btn'):
            self.generate_btn.setEnabled(False)

        # 清理之前的worker（如果有）
        if self.blueprint_worker and self.blueprint_worker.isRunning():
            self.blueprint_worker.cancel()
            self.blueprint_worker.quit()
            self.blueprint_worker.wait(1000)

        # 创建异步worker（传递force_regenerate参数）
        self.blueprint_worker = AsyncAPIWorker(
            self.api_client.generate_blueprint,
            self.project_id,
            force_regenerate=force_regenerate
        )

        # 成功回调
        def on_success(response):
            loading_dialog.close()
            # 恢复按钮状态
            if hasattr(self, 'generate_btn'):
                self.generate_btn.setEnabled(True)

            try:
                # 验证蓝图数据
                self.blueprint = response.get('blueprint', {})
                if not self.blueprint:
                    MessageService.show_error(self, "蓝图生成失败：蓝图数据为空", "生成蓝图失败")
                    return

                # 验证蓝图必需字段（移除chapter_outline，因为新工作流不在此阶段生成）
                required_fields = ['world_setting', 'characters']
                missing_fields = [f for f in required_fields if not self.blueprint.get(f)]
                if missing_fields:
                    MessageService.show_error(
                        self,
                        f"蓝图数据不完整，缺少字段：{', '.join(missing_fields)}",
                        "生成蓝图失败"
                    )
                    return

                # 更新蓝图数据并切换页面
                self.confirmation_page.setBlueprint(self.blueprint)
                self.stack.setCurrentWidget(self.confirmation_page)

            except Exception as e:
                MessageService.show_error(self, f"处理蓝图数据失败：{str(e)}", "生成蓝图失败")

        # 错误回调
        def on_error(error_msg):
            loading_dialog.close()
            # 恢复按钮状态
            if hasattr(self, 'generate_btn'):
                self.generate_btn.setEnabled(True)

            # 检查是否是冲突错误（已有章节大纲）
            if "已有" in error_msg and "章节大纲" in error_msg:
                # 显示确认对话框，明确告知会删除所有数据
                if confirm(
                    self,
                    "检测到项目已有章节大纲。\n\n"
                    "重新生成蓝图将会删除以下所有数据：\n"
                    "• 所有章节大纲\n"
                    "• 所有部分大纲（如有）\n"
                    "• 所有已生成的章节内容\n"
                    "• 所有章节版本\n"
                    "• 向量库数据\n\n"
                    "此操作不可恢复，确定要继续吗？",
                    "确认重新生成蓝图"
                ):
                    # 用户确认，强制重新生成
                    self._do_generate_blueprint(force_regenerate=True)
            else:
                # 其他错误，直接显示
                MessageService.show_error(self, f"生成蓝图失败：{error_msg}", "生成蓝图失败")

        # 取消回调
        def on_cancel():
            if self.blueprint_worker and self.blueprint_worker.isRunning():
                self.blueprint_worker.cancel()
                self.blueprint_worker.quit()
                self.blueprint_worker.wait(1000)
            # 恢复按钮状态
            if hasattr(self, 'generate_btn'):
                self.generate_btn.setEnabled(True)

        self.blueprint_worker.success.connect(on_success)
        self.blueprint_worker.error.connect(on_error)
        loading_dialog.rejected.connect(on_cancel)
        self.blueprint_worker.start()

    def onBlueprintConfirmed(self):
        """蓝图确认"""
        # 跳转到项目详情页
        self.navigateTo('DETAIL', project_id=self.project_id)

    def onBlueprintRejected(self):
        """重新生成蓝图"""
        # 返回对话页面
        self.stack.setCurrentWidget(self.conversation_page)

    def refresh(self, **params):
        """刷新页面"""
        # 清空对话历史
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 检查是否是继续未完成的项目
        project_id = params.get('project_id')

        if project_id:
            # 恢复未完成的对话
            self.project_id = project_id
            self.blueprint = None
            self.is_conversation_complete = False

            # 加载对话历史
            self._load_conversation_history(project_id)
        else:
            # 全新对话
            self.project_id = None
            self.blueprint = None
            self.is_conversation_complete = False

            # 重新初始化
            self.initConversation()

        self.stack.setCurrentIndex(0)

    def _load_conversation_history(self, project_id):
        """加载并恢复对话历史"""
        try:
            # 获取对话历史
            history = self.api_client.get_conversation_history(project_id)

            if not history:
                # 没有历史，显示初始欢迎消息
                self.initConversation()
                return

            # 逐条恢复对话气泡
            for record in history:
                role = record.get('role')
                content = record.get('content')

                if not role or not content:
                    continue

                # 解析content（JSON字符串）
                try:
                    import json
                    data = json.loads(content)
                except:
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
                        self.addMessage(user_msg, is_user=True)

                elif role == 'assistant':
                    # AI消息
                    if isinstance(data, dict):
                        ai_message = data.get('ai_message', '')
                        ui_control = data.get('ui_control', {})

                        # 添加AI消息气泡
                        if ai_message:
                            self.addMessage(ai_message, is_user=False)

                        # 恢复灵感选项（如果有）
                        if ui_control.get('type') == 'inspired_options':
                            options_data = ui_control.get('options', [])
                            if options_data:
                                self._add_inspired_options(options_data)

                        # 更新对话完成状态
                        if data.get('is_complete'):
                            self.is_conversation_complete = True

        except Exception as e:
            logger.error(f"加载对话历史失败: {str(e)}")
            # 加载失败，显示初始欢迎消息
            self.initConversation()


    def onRestart(self):
        """重新开始对话"""
        if confirm(self, "确定要重新开始吗？当前对话将被清空。", "确认重启"):
            self.refresh()

    def onHide(self):
        """页面隐藏时清理资源"""
        self._cleanup_worker()

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self._cleanup_worker()
        super().closeEvent(event)

    def _cleanup_worker(self):
        """清理异步worker（包括SSE Worker和蓝图Worker）"""
        # 清理SSE/对话worker
        if self.current_worker:
            try:
                if self.current_worker.isRunning():
                    try:
                        # 尝试断开SSE Worker的信号
                        if isinstance(self.current_worker, SSEWorker):
                            self.current_worker.token_received.disconnect()
                            self.current_worker.complete.disconnect()
                            self.current_worker.error.disconnect()
                            # 停止SSE监听
                            self.current_worker.stop()
                        else:
                            # 旧的AsyncAPIWorker信号
                            self.current_worker.success.disconnect()
                            self.current_worker.error.disconnect()
                    except:
                        pass  # 信号可能已经断开

                    # 终止线程
                    self.current_worker.quit()
                    self.current_worker.wait(1000)  # 等待最多1秒
            except RuntimeError:
                pass  # C++ 对象可能已被删除
            finally:
                self.current_worker = None

        # 清理蓝图生成worker
        if self.blueprint_worker:
            try:
                if self.blueprint_worker.isRunning():
                    try:
                        self.blueprint_worker.success.disconnect()
                        self.blueprint_worker.error.disconnect()
                        self.blueprint_worker.cancel()
                    except:
                        pass  # 信号可能已经断开

                    self.blueprint_worker.quit()
                    self.blueprint_worker.wait(1000)
            except RuntimeError:
                pass  # C++ 对象可能已被删除
            finally:
                self.blueprint_worker = None

    def _start_sse_stream(self, message):
        """启动SSE流式监听"""
        # 如果没有项目ID，先创建项目
        if not self.project_id:
            try:
                response = self.api_client.create_novel(
                    title="未命名项目",
                    initial_prompt=message
                )
                self.project_id = response.get('id')
            except Exception as e:
                MessageService.show_error(self, f"创建项目失败：{str(e)}", "错误")
                self.input_widget.setEnabled(True)
                return

        # 构造SSE URL
        url = f"{self.api_client.base_url}/api/novels/{self.project_id}/inspiration/converse-stream"

        # 构造请求负载
        payload = {
            "user_input": {"message": message},
            "conversation_state": {}
        }

        # 创建SSE Worker
        self.current_worker = SSEWorker(url, payload)
        self.current_worker.token_received.connect(self._on_token_received)
        self.current_worker.complete.connect(self._on_stream_complete)
        self.current_worker.error.connect(self._on_stream_error)
        self.current_worker.start()

    def _on_token_received(self, token):
        """收到一个token（SSE回调）"""
        if self.current_ai_bubble:
            # 追加token到当前AI气泡
            self.current_ai_bubble.append_text(token)

            # 滚动到底部
            QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            ))

    def _on_stream_complete(self, metadata):
        """流式响应完成（SSE回调）"""
        # 清理worker引用
        self.current_worker = None
        self.current_ai_bubble = None

        # 检查是否有UI控件（灵感选项）
        ui_control = metadata.get('ui_control', {})
        control_type = ui_control.get('type')

        if control_type == 'inspired_options':
            # 显示灵感选项卡片
            options_data = ui_control.get('options', [])
            if options_data:
                self._add_inspired_options(options_data)

                # 更新输入框placeholder
                placeholder = ui_control.get('placeholder', '选择上面的选项，或输入你的新想法...')
                self.input_widget.setPlaceholder(placeholder)
        else:
            # 恢复默认placeholder
            self.input_widget.setPlaceholder('输入你的想法...')

        # 检查对话是否完成
        self.is_conversation_complete = metadata.get('is_complete', False)

        # 启用输入
        self.input_widget.setEnabled(True)
        self.input_widget.setFocus()

    def _on_stream_error(self, error_msg):
        """流式响应错误（SSE回调）"""
        # 清理worker引用
        self.current_worker = None

        # 显示错误消息
        MessageService.show_error(self, f"对话失败：{error_msg}", "错误")

        # 移除空的AI气泡（如果存在）
        if self.current_ai_bubble:
            self.chat_layout.removeWidget(self.current_ai_bubble)
            self.current_ai_bubble.deleteLater()
            self.current_ai_bubble = None

        # 启用输入
        self.input_widget.setEnabled(True)

    def _add_inspired_options(self, options_data):
        """添加灵感选项卡片"""
        # 创建选项容器
        options_container = InspiredOptionsContainer(options_data)
        options_container.option_selected.connect(self._on_option_selected)

        # 添加到对话历史（在stretch之前）
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, options_container)

        # 滚动到底部
        QTimer.singleShot(200, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def _on_option_selected(self, option_id, option_label):
        """用户选择了某个灵感选项"""
        # 自动发送选择的选项作为用户消息
        message = f"选择：{option_label}"
        self.onMessageSent(message)
