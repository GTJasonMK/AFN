"""
内容管理Mixin

提供内容保存、版本管理等功能。
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from utils.async_worker import run_async_action
from utils.message_service import MessageService

if TYPE_CHECKING:
    from ..main import CodingDesk

logger = logging.getLogger(__name__)


class ContentManagementMixin:
    """内容管理Mixin

    提供：
    - 文件内容加载
    - 内容保存
    - 版本管理
    """

    def _init_content_mixin(self: 'CodingDesk'):
        """初始化内容管理相关状态"""
        self._current_file_id: Optional[int] = None
        self._current_file_data: Optional[Dict[str, Any]] = None

    def load_file_content(self: 'CodingDesk', file_data: Dict[str, Any]):
        """加载文件内容

        Args:
            file_data: 文件数据，包含id、filename、file_path等
        """
        self._current_file_id = file_data.get('id')
        self._current_file_data = file_data

        # 更新Header显示的文件路径
        file_path = file_data.get('file_path', '')
        self.header.set_current_file(file_path)

        # 在Sidebar中选中文件
        self.sidebar.select_file(self._current_file_id)

        # 加载文件详情
        run_async_action(
            self.worker_manager,
            self.api_client.get_source_file,
            self.project_id,
            self._current_file_id,
            task_name='load_file_content',
            on_success=self._on_file_content_loaded,
            on_error=self._on_file_content_error,
        )

    def _on_file_content_loaded(self: 'CodingDesk', data: Dict[str, Any]):
        """文件内容加载完成"""
        content = data.get('content', '')
        review_prompt = data.get('review_prompt', '')

        # 更新工作区
        self.workspace.load_file(
            self._current_file_data,
            content,
            review_prompt
        )

    def _on_file_content_error(self: 'CodingDesk', error_msg: str):
        """文件内容加载失败"""
        logger.error(f"加载文件内容失败: {error_msg}")
        MessageService.show_error(self, f"加载文件失败: {error_msg}")

    def save_file_content(self: 'CodingDesk', content: str):
        """保存文件内容

        Args:
            content: 要保存的Prompt内容
        """
        if not self._current_file_id:
            MessageService.show_warning(self, "请先选择一个文件")
            return

        if not content.strip():
            MessageService.show_warning(self, "内容不能为空")
            return

        self.workspace.set_status("保存中...")

        run_async_action(
            self.worker_manager,
            self.api_client.save_file_prompt,
            self.project_id,
            self._current_file_id,
            content,
            task_name='save_content',
            on_success=self._on_save_success,
            on_error=self._on_save_error,
        )

    def _on_save_success(self: 'CodingDesk', data: Dict):
        """保存成功"""
        self.workspace.set_status("已保存")

        # 更新文件状态
        if self._current_file_id:
            self.sidebar.update_file_status(self._current_file_id, 'generated')

        MessageService.show_success(self, "保存成功")

    def _on_save_error(self: 'CodingDesk', error_msg: str):
        """保存失败"""
        self.workspace.set_status("保存失败")
        logger.error(f"保存文件内容失败: {error_msg}")
        MessageService.show_error(self, f"保存失败: {error_msg}")

    def clear_current_file(self: 'CodingDesk'):
        """清除当前文件状态"""
        self._current_file_id = None
        self._current_file_data = None
        self.header.clear_current_file()
        self.workspace.clear()


__all__ = ["ContentManagementMixin"]
