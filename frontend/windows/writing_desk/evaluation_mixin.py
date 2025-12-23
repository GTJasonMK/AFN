"""
章节评估Mixin

处理章节评估相关的所有方法
"""

import logging

from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class EvaluationMixin:
    """章节评估相关方法的Mixin"""

    def onEvaluateChapter(self):
        """评估当前章节"""
        if self.selected_chapter_number is None:
            MessageService.show_warning(self, "请先选择一个章节")
            return

        self.show_loading("正在分析章节...")

        def do_evaluate():
            client = APIClientManager.get_client()
            return client.evaluate_chapter(
                self.project_id,
                self.selected_chapter_number,
            )

        worker = AsyncAPIWorker(do_evaluate)
        worker.success.connect(self.onEvaluateSuccess)
        worker.error.connect(self.onEvaluateError)
        self.worker_manager.start(worker, 'evaluate_chapter')

    def onEvaluateSuccess(self, result):
        """评估成功回调"""
        self.hide_loading()

        # 在workspace中显示评估结果
        self.workspace.showEvaluationResult(result)

        MessageService.show_success(self, "章节分析完成")

    def onEvaluateError(self, error_msg):
        """评估失败回调"""
        self.hide_loading()
        MessageService.show_error(self, f"分析失败：{error_msg}")
