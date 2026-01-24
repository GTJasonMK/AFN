"""
文件Prompt生成Mixin

提供SSE流式生成文件Prompt的功能。
"""

import logging
from typing import Optional, TYPE_CHECKING

from utils.async_worker import run_async_action
from utils.sse_worker import SSEWorker, start_sse_worker, reset_sse_generation_state
from utils.message_service import MessageService

if TYPE_CHECKING:
    from ..main import CodingDesk

logger = logging.getLogger(__name__)


class FileGenerationMixin:
    """文件Prompt生成Mixin

    提供：
    - SSE流式生成文件Prompt
    - 进度显示
    - 生成状态管理
    """

    def _init_generation_mixin(self: 'CodingDesk'):
        """初始化生成相关状态"""
        self._sse_worker: Optional[SSEWorker] = None
        self._is_generating = False

    def start_file_generation(self: 'CodingDesk'):
        """开始生成文件Prompt"""
        if not self._current_file_id:
            MessageService.show_warning(self, "请先选择一个文件")
            return

        if self._is_generating:
            MessageService.show_warning(self, "正在生成中，请稍候")
            return

        self._is_generating = True

        # 更新UI状态
        self.workspace.set_generating(True)
        self.sidebar.update_file_status(self._current_file_id, 'generating')

        # 获取SSE URL
        url = self.api_client.get_file_prompt_generate_stream_url(
            self.project_id,
            self._current_file_id
        )

        # 启动SSE Worker
        self._sse_worker = start_sse_worker(
            url,
            {},
            on_token=self._on_generation_token,
            on_progress=self._on_generation_progress,
            on_complete=self._on_generation_complete,
            on_error=self._on_generation_error,
        )

    def _on_generation_token(self: 'CodingDesk', token: str):
        """收到生成的token"""
        self.workspace.append_content(token)

    def _on_generation_progress(self: 'CodingDesk', data: dict):
        """收到进度信息"""
        message = data.get('message', '')
        self.workspace.set_status(message)

    def _on_generation_complete(self: 'CodingDesk', data: dict):
        """生成完成"""
        reset_sse_generation_state(self)

        # 更新UI状态
        self.workspace.set_generate_complete()
        self.sidebar.update_file_status(self._current_file_id, 'generated')

        # 刷新目录树以更新状态
        self._refresh_directory_tree()

        MessageService.show_success(self, "Prompt生成完成")

    def _on_generation_error(self: 'CodingDesk', error_msg: str):
        """生成错误"""
        reset_sse_generation_state(self)

        # 更新UI状态
        self.workspace.set_status("生成失败")
        self.workspace.set_generating(False)
        self.sidebar.update_file_status(self._current_file_id, 'failed')

        logger.error(f"文件Prompt生成失败: {error_msg}")
        MessageService.show_error(self, f"生成失败: {error_msg}")

    def start_review_generation(self: 'CodingDesk'):
        """生成审查Prompt"""
        if not self._current_file_id:
            MessageService.show_warning(self, "请先选择一个文件")
            return

        content = self.workspace.get_content()
        if not content.strip():
            MessageService.show_warning(self, "请先生成实现Prompt")
            return

        self.workspace.set_status("正在生成审查Prompt...")

        run_async_action(
            self.worker_manager,
            self.api_client.generate_file_review,
            self.project_id,
            self._current_file_id,
            task_name='generate_review',
            on_success=self._on_review_generated,
            on_error=self._on_review_error,
        )

    def _on_review_generated(self: 'CodingDesk', data: dict):
        """审查Prompt生成完成"""
        content = data.get('content', '')
        self.workspace.set_review_content(content)
        self.workspace.set_status("审查Prompt生成完成")
        MessageService.show_success(self, "审查Prompt生成完成")

    def _on_review_error(self: 'CodingDesk', error_msg: str):
        """审查Prompt生成失败"""
        self.workspace.set_status("审查Prompt生成失败")
        logger.error(f"审查Prompt生成失败: {error_msg}")
        MessageService.show_error(self, f"生成失败: {error_msg}")

    def stop_generation(self: 'CodingDesk'):
        """停止生成"""
        reset_sse_generation_state(self)


__all__ = ["FileGenerationMixin"]
