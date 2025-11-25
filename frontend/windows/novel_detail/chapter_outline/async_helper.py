"""
异步操作辅助类

封装异步API调用的通用模式，减少重复代码
"""

from PyQt6.QtWidgets import QProgressDialog, QApplication, QWidget
from PyQt6.QtCore import Qt
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService
import logging

logger = logging.getLogger(__name__)


class AsyncOperationHelper:
    """异步操作辅助类 - 封装通用的异步API调用模式"""

    def __init__(self, parent: QWidget):
        """
        初始化辅助类

        Args:
            parent: 父窗口组件（用于显示对话框）
        """
        self.parent = parent
        self._active_workers = []

    def execute(
        self,
        api_func,
        *args,
        loading_message: str = "正在处理...",
        success_message: str = "操作成功",
        error_context: str = "操作",
        on_success=None,
        on_error=None,
        **kwargs
    ):
        """
        执行异步API操作

        Args:
            api_func: API函数
            *args: API函数的位置参数
            loading_message: 加载时显示的消息
            success_message: 成功时显示的消息
            error_context: 错误时的上下文描述
            on_success: 成功后的额外回调（接收result参数）
            on_error: 错误后的额外回调（接收error_msg参数）
            **kwargs: API函数的关键字参数
        """
        # 创建加载对话框
        loading_dialog = QProgressDialog(loading_message, "取消", 0, 0, self.parent)
        loading_dialog.setWindowTitle("请稍候")
        loading_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        loading_dialog.setMinimumDuration(0)
        loading_dialog.setValue(0)
        loading_dialog.show()
        QApplication.processEvents()

        # 创建异步Worker
        worker = AsyncAPIWorker(api_func, *args, **kwargs)
        self._active_workers.append(worker)

        # 成功回调
        def handle_success(result):
            loading_dialog.close()
            self._remove_worker(worker)
            if success_message:
                MessageService.show_operation_success(self.parent, success_message)
            if on_success:
                on_success(result)

        # 错误回调
        def handle_error(error_msg):
            loading_dialog.close()
            self._remove_worker(worker)
            MessageService.show_api_error(self.parent, error_msg, error_context)
            if on_error:
                on_error(error_msg)

        # 取消回调
        def handle_cancel():
            if worker.isRunning():
                worker.cancel()
                worker.quit()
                worker.wait(1000)
            self._remove_worker(worker)
            loading_dialog.close()

        worker.success.connect(handle_success)
        worker.error.connect(handle_error)
        loading_dialog.canceled.connect(handle_cancel)
        worker.start()

    def _remove_worker(self, worker):
        """从活动列表中移除worker"""
        if worker in self._active_workers:
            self._active_workers.remove(worker)

    def stop_all(self):
        """停止所有活动的异步任务"""
        for worker in self._active_workers[:]:
            try:
                if worker.isRunning():
                    worker.cancel()
                    worker.quit()
                    worker.wait(1000)
                logger.debug(f"停止异步Worker: {worker}")
            except Exception as e:
                logger.debug(f"停止异步Worker时出错: {e}")
        self._active_workers.clear()

    @property
    def active_count(self):
        """返回活动任务数量"""
        return len(self._active_workers)
