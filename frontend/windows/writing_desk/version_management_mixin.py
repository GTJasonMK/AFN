"""
版本管理Mixin

处理版本相关的所有方法，包括：
- 选择版本
- 重试生成版本
"""

import logging

from api.manager import APIClientManager
from components.dialogs import TextInputDialog
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService, confirm

logger = logging.getLogger(__name__)


class VersionManagementMixin:
    """版本管理相关方法的Mixin"""

    def onSelectVersion(self, version_index):
        """选择版本"""
        if self.selected_chapter_number is None:
            MessageService.show_warning(self, "请先选择一个章节")
            return

        logger.info(
            f"版本切换请求: project_id={self.project_id}, chapter={self.selected_chapter_number}, version_index={version_index}"
        )
        self.show_loading("正在切换版本...")

        def do_select():
            client = APIClientManager.get_client()
            return client.select_chapter_version(
                self.project_id,
                self.selected_chapter_number,
                version_index,
            )

        worker = AsyncAPIWorker(do_select)
        worker.success.connect(lambda result: self.onSelectVersionSuccess(result, version_index))
        worker.error.connect(self.onSelectVersionError)
        self.worker_manager.start(worker, 'select_version')

    def onSelectVersionSuccess(self, result, version_index):
        """选择版本成功回调"""
        self.hide_loading()

        logger.info(f"版本切换成功: version_index={version_index}, 正在刷新界面")

        # 刷新workspace显示
        self.workspace.refreshCurrentChapter()

        # 重新加载项目数据以刷新侧边栏
        self.loadProject()

        MessageService.show_success(self, f"已切换到版本{version_index + 1}")

    def onSelectVersionError(self, error_msg):
        """选择版本失败回调"""
        self.hide_loading()
        MessageService.show_error(self, f"切换版本失败：{error_msg}")

    def onRetryVersion(self, version_index):
        """重新生成指定版本"""
        if self.selected_chapter_number is None:
            MessageService.show_warning(self, "请先选择一个章节")
            return

        if not confirm(
            self,
            f"确定要重新生成第{self.selected_chapter_number}章的版本{version_index + 1}吗？\n\n这将替换当前版本的内容。",
            "确认重新生成"
        ):
            return

        # 询问用户输入优化提示词
        custom_prompt, ok = TextInputDialog.getTextStatic(
            parent=self,
            title="优化方向",
            label=f"请输入第{self.selected_chapter_number}章版本{version_index + 1}的优化方向：\n\n"
                  "（可选，留空则按原设定重新生成）",
            placeholder="示例：增加对话、加强冲突、优化节奏..."
        )

        if not ok:
            return

        self.show_loading("正在重新生成...")

        def do_retry():
            client = APIClientManager.get_client()
            return client.retry_chapter_version(
                self.project_id,
                self.selected_chapter_number,
                version_index,
                custom_prompt=custom_prompt.strip() if custom_prompt else None,
            )

        worker = AsyncAPIWorker(do_retry)
        worker.success.connect(lambda result: self.onRetrySuccess(result, version_index))
        worker.error.connect(self.onRetryError)
        self.worker_manager.start(worker, 'retry_version')

    def onRetrySuccess(self, result, version_index):
        """重新生成成功回调"""
        self.hide_loading()

        # 刷新workspace显示
        self.workspace.refreshCurrentChapter()

        # 重新加载项目数据以刷新侧边栏
        self.loadProject()

        MessageService.show_success(self, f"版本{version_index + 1}已重新生成")

    def onRetryError(self, error_msg):
        """重新生成失败回调"""
        self.hide_loading()
        MessageService.show_error(self, f"重新生成失败：{error_msg}")
