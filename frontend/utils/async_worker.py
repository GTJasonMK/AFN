"""
异步工作线程工具

提供QThread包装器，用于在后台执行耗时的API调用，避免UI冻结
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import Callable, Any, Optional
import traceback


class AsyncAPIWorker(QThread):
    """异步API调用工作线程

    用法:
        worker = AsyncAPIWorker(api_client.generate_chapter, project_id, chapter_number)
        worker.success.connect(self.onSuccess)
        worker.error.connect(self.onError)
        worker.start()
    """

    # 信号
    success = pyqtSignal(object)  # 成功时发射结果
    error = pyqtSignal(str)       # 失败时发射错误信息

    def __init__(self, func: Callable, *args, **kwargs):
        """初始化工作线程

        Args:
            func: 要执行的函数（通常是API客户端方法）
            *args: 函数位置参数
            **kwargs: 函数关键字参数
        """
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False

        # 线程完成后自动删除，防止内存泄漏
        self.finished.connect(self.deleteLater)

    def run(self):
        """线程执行入口"""
        try:
            if self._is_cancelled:
                return

            result = self.func(*self.args, **self.kwargs)

            if not self._is_cancelled:
                self.success.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                error_msg = f"{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
                self.error.emit(error_msg)

    def cancel(self):
        """取消任务（注意：无法中断已经开始的API调用）"""
        self._is_cancelled = True
