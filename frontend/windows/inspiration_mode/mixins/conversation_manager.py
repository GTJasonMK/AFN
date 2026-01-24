"""
对话管理Mixin

负责SSE流式对话的启动、事件处理和错误恢复。
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer

if TYPE_CHECKING:
    from ..main import InspirationMode

logger = logging.getLogger(__name__)


class ConversationManagerMixin:
    """
    对话管理Mixin

    负责：
    - SSE流式对话启动
    - 流式事件处理（token、选项、完成、错误）
    - 对话历史加载
    - Worker清理
    """

    def _get_conversation_mode(self: "InspirationMode") -> str:
        """获取对话模式类型（novel/coding）"""
        return "novel"

    def _create_conversation_project(self: "InspirationMode", message: str) -> str:
        """创建对话项目并返回项目ID"""
        mode = self._get_conversation_mode()
        if mode == "coding":
            response = self.api_client.create_coding_project(
                title="未命名项目",
                initial_prompt=message,
                skip_conversation=False
            )
        else:
            response = self.api_client.create_novel(
                title="未命名项目",
                initial_prompt=message,
                skip_inspiration=False
            )
        project_id = response.get('id')
        if not project_id:
            raise ValueError("创建项目失败：未返回项目ID")
        return project_id

    def _build_conversation_stream_url(self: "InspirationMode", project_id: str) -> str:
        """构建对话SSE地址"""
        mode = self._get_conversation_mode()
        if mode == "coding":
            return f"{self.api_client.base_url}/api/coding/{project_id}/inspiration/converse-stream"
        return f"{self.api_client.base_url}/api/novels/{project_id}/inspiration/converse-stream"

    def _build_conversation_payload(self: "InspirationMode", message: str) -> dict:
        """构建对话请求负载"""
        return {
            "user_input": {"message": message},
            "conversation_state": {}
        }

    def _get_conversation_history_records(self: "InspirationMode", project_id: str):
        """获取对话历史记录"""
        mode = self._get_conversation_mode()
        if mode == "coding":
            return self.api_client.get_coding_inspiration_history(project_id)
        return self.api_client.get_conversation_history(project_id)

    def _get_conversation_error_prefix(self: "InspirationMode") -> str:
        """获取对话失败提示前缀"""
        mode = self._get_conversation_mode()
        if mode == "coding":
            return "对话出错"
        return "对话失败"

    def _handle_conversation_error_bubble(self: "InspirationMode", error_msg: str) -> None:
        """处理对话错误气泡展示"""
        if self.current_ai_bubble:
            self.chat_layout.removeWidget(self.current_ai_bubble)
            self.current_ai_bubble.deleteLater()
            self.current_ai_bubble = None

    def _after_stream_complete(self: "InspirationMode", metadata: dict) -> None:
        """流式完成后的扩展处理（预留钩子）"""
        return None

    def _start_sse_stream(self: "InspirationMode", message: str):
        """启动SSE流式监听"""
        from utils.message_service import MessageService
        from utils.sse_worker import SSEWorker

        # 如果没有项目ID，先创建项目
        if not self._state.project_id:
            try:
                self._state.project_id = self._create_conversation_project(message)
            except Exception as e:
                MessageService.show_error(self, f"创建项目失败：{str(e)}", "错误")
                self.input_widget.setEnabled(True)
                return

        # 构造SSE URL与请求负载
        url = self._build_conversation_stream_url(self._state.project_id)
        payload = self._build_conversation_payload(message)

        # 重置选项缓存和上一轮容器引用（用于错误恢复）
        self._state.pending_options = []
        self._prev_options_container = None

        # 创建SSE Worker
        self.current_worker = SSEWorker(url, payload)

        # 连接结构化流式事件信号（新版）
        self.current_worker.streaming_start.connect(self._on_streaming_start)
        self.current_worker.ai_message_chunk.connect(self._on_ai_message_chunk)
        self.current_worker.option_received.connect(self._on_option_received)

        # 连接完成和错误信号
        self.current_worker.complete.connect(self._on_stream_complete)
        self.current_worker.error.connect(self._on_stream_error)

        # 兼容旧版token信号（如果有其他地方使用）
        self.current_worker.token_received.connect(self._on_token_received)

        self.current_worker.start()

    def _on_token_received(self: "InspirationMode", token: str):
        """收到一个token（SSE回调 - 兼容旧版）"""
        if self.current_ai_bubble:
            # 追加token到当前AI气泡
            self.current_ai_bubble.append_text(token)

            # 滚动到底部
            QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            ))

    def _on_streaming_start(self: "InspirationMode", data: dict):
        """流式输出开始（禁用用户交互）"""
        # 确保输入框被禁用
        self.input_widget.setEnabled(False)

        # 禁用生成蓝图按钮
        if hasattr(self, 'generate_btn') and self.generate_btn:
            self.generate_btn.setEnabled(False)

        # 禁用返回按钮（可选，防止用户中途离开）
        if hasattr(self, 'back_btn') and self.back_btn:
            self.back_btn.setEnabled(False)

    def _on_ai_message_chunk(self: "InspirationMode", text: str):
        """收到AI消息文本片段（结构化流式）"""
        if self.current_ai_bubble:
            # 追加文本到当前AI气泡
            self.current_ai_bubble.append_text(text)

            # 滚动到底部
            QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            ))

    def _on_option_received(self: "InspirationMode", data: dict):
        """收到单个选项（结构化流式）"""
        from ..components.inspired_option_card import InspiredOptionsContainer

        # 缓存选项数据
        if not hasattr(self, '_pending_options'):
            self._state.pending_options = []

        option = data.get('option', {})
        if option:
            self._state.pending_options.append(option)

            # 动态添加选项到界面（逐个出现效果）
            index = data.get('index', 0)

            # 如果是第一个选项，创建选项容器
            if index == 0:
                # 保存当前容器引用用于错误恢复，然后锁定它
                self._prev_options_container = self._current_options_container
                if self._prev_options_container:
                    try:
                        self._prev_options_container.lock()
                    except RuntimeError:
                        self._prev_options_container = None

                # 创建新的空容器，后续逐个添加选项
                self._current_options_container = InspiredOptionsContainer([])
                self._current_options_container.option_selected.connect(self._on_option_selected)
                self.chat_layout.insertWidget(self.chat_layout.count() - 1, self._current_options_container)

            # 向容器添加单个选项
            if self._current_options_container:
                self._current_options_container.add_option(option)

                # 滚动到底部
                QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
                    self.chat_scroll.verticalScrollBar().maximum()
                ))

    def _on_stream_complete(self: "InspirationMode", metadata: dict):
        """流式响应完成（SSE回调）"""
        # 清理worker引用
        self.current_worker = None
        if self.current_ai_bubble:
            try:
                self.current_ai_bubble.stop_loading()
            except RuntimeError:
                pass
        self.current_ai_bubble = None

        # 注意：不锁定当前选项容器，保持可点击状态
        # _current_options_container 保留引用，用于用户选择后锁定

        # 清理选项缓存和上一轮容器引用（流成功完成，不再需要恢复）
        self._state.pending_options = []
        self._prev_options_container = None

        # 恢复被禁用的按钮状态
        if hasattr(self, 'generate_btn') and self.generate_btn:
            self.generate_btn.setEnabled(True)
        if hasattr(self, 'back_btn') and self.back_btn:
            self.back_btn.setEnabled(True)

        # 更新输入框placeholder（从complete事件的metadata中获取）
        placeholder = metadata.get('placeholder', '输入你的想法...')
        self.input_widget.setPlaceholder(placeholder)

        # 检查对话是否完成
        self._state.is_complete = metadata.get('is_complete', False)

        # 启用输入
        self.input_widget.setEnabled(True)
        self.input_widget.setFocus()
        self._after_stream_complete(metadata)

    def _on_stream_error(self: "InspirationMode", error_msg: str):
        """流式响应错误（SSE回调）"""
        from utils.message_service import MessageService

        # 清理worker引用
        self.current_worker = None

        # 错误恢复：处理选项容器状态
        if self._state.pending_options and self._current_options_container:
            # 如果有选项被部分接收，说明新容器已创建，需要移除它
            try:
                self.chat_layout.removeWidget(self._current_options_container)
                self._current_options_container.deleteLater()
            except RuntimeError:
                pass
            self._current_options_container = None

            # 恢复上一轮容器（如果有），解锁它允许用户重试
            if self._prev_options_container:
                try:
                    self._prev_options_container.unlock()
                    self._current_options_container = self._prev_options_container
                except RuntimeError:
                    pass
        elif self._current_options_container:
            # 没有新选项被接收，直接解锁当前容器
            try:
                self._current_options_container.unlock()
            except RuntimeError:
                pass

        # 清理状态
        self._state.pending_options = []
        self._prev_options_container = None

        # 恢复被禁用的按钮状态
        if hasattr(self, 'generate_btn') and self.generate_btn:
            self.generate_btn.setEnabled(True)
        if hasattr(self, 'back_btn') and self.back_btn:
            self.back_btn.setEnabled(True)

        # 显示错误消息
        MessageService.show_error(
            self,
            f"{self._get_conversation_error_prefix()}：{error_msg}",
            "错误"
        )
        self._handle_conversation_error_bubble(error_msg)

        # 启用输入
        self.input_widget.setEnabled(True)

    def _load_conversation_history(self: "InspirationMode", project_id: str):
        """加载并恢复对话历史"""
        import json

        try:
            # 获取对话历史
            history = self._get_conversation_history_records(project_id)

            if not history:
                # 没有历史，显示初始欢迎消息
                self.initConversation()
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
                        # JSON解析失败或类型错误，跳过此记录
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
                                # 检查下一条消息是否是用户选择，如果是则锁定选项
                                should_lock = (i + 1) in user_selection_indices
                                self._add_inspired_options(options_data, locked=should_lock)

                        # 更新对话完成状态
                        if data.get('is_complete'):
                            self._state.is_complete = True

        except Exception as e:
            logger.error(f"加载对话历史失败: {str(e)}")
            # 加载失败，显示初始欢迎消息
            self.initConversation()

    def _cleanup_sse_worker(self: "InspirationMode"):
        """清理SSE对话Worker"""
        from utils.sse_worker import SSEWorker
        from utils.constants import WorkerTimeouts

        if not self.current_worker:
            return

        try:
            if self.current_worker.isRunning():
                # SSEWorker有专门的stop方法，会断开信号并关闭连接
                if isinstance(self.current_worker, SSEWorker):
                    self.current_worker.stop()
                else:
                    # 旧的AsyncAPIWorker
                    try:
                        self.current_worker.success.disconnect()
                        self.current_worker.error.disconnect()
                    except (TypeError, RuntimeError):
                        pass

                # 终止线程
                self.current_worker.quit()
                self.current_worker.wait(WorkerTimeouts.DEFAULT_MS)
        except RuntimeError:
            pass  # C++ 对象可能已被删除
        finally:
            self.current_worker = None


__all__ = [
    "ConversationManagerMixin",
]
