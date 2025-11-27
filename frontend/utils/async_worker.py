"""
异步工作线程工具

提供QThread包装器，用于在后台执行耗时的API调用，避免UI冻结
"""

import logging
import sys
import traceback
from typing import Callable, Any, Optional

from PyQt6.QtCore import QThread, pyqtSignal


logger = logging.getLogger(__name__)


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
        self._func_name = getattr(func, '__name__', str(func))

        logger.debug(
            "AsyncAPIWorker created: func=%s, args=%s, kwargs_keys=%s",
            self._func_name, self.args, list(self.kwargs.keys())
        )

        # 线程完成后自动删除，防止内存泄漏
        self.finished.connect(self._safe_delete_later)

    def _safe_delete_later(self):
        """安全地延迟删除"""
        try:
            self.deleteLater()
        except RuntimeError:
            pass  # 对象可能已被删除

    def run(self):
        """线程执行入口"""
        logger.info(
            "AsyncAPIWorker.run() started: func=%s, thread_id=%s",
            self._func_name, int(QThread.currentThreadId())
        )
        sys.stdout.flush()

        try:
            if self._is_cancelled:
                logger.info("AsyncAPIWorker cancelled before execution: func=%s", self._func_name)
                return

            logger.info("AsyncAPIWorker calling func: %s", self._func_name)
            sys.stdout.flush()

            result = self.func(*self.args, **self.kwargs)

            logger.info(
                "AsyncAPIWorker func returned: func=%s, result_type=%s",
                self._func_name, type(result).__name__
            )
            sys.stdout.flush()

            if not self._is_cancelled:
                logger.info("AsyncAPIWorker emitting success signal: func=%s", self._func_name)
                sys.stdout.flush()
                self.success.emit(result)
                logger.info("AsyncAPIWorker success signal emitted: func=%s", self._func_name)
                sys.stdout.flush()

        except Exception as e:
            logger.error(
                "AsyncAPIWorker exception: func=%s, error_type=%s, error=%s",
                self._func_name, type(e).__name__, str(e),
                exc_info=True
            )
            sys.stdout.flush()

            if not self._is_cancelled:
                error_msg = f"{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
                logger.info("AsyncAPIWorker emitting error signal: func=%s", self._func_name)
                sys.stdout.flush()
                self.error.emit(error_msg)
        except BaseException as e:
            # 捕获所有异常，包括SystemExit, KeyboardInterrupt等
            logger.critical(
                "AsyncAPIWorker BaseException: func=%s, error_type=%s, error=%s",
                self._func_name, type(e).__name__, str(e),
                exc_info=True
            )
            sys.stdout.flush()
            raise
        finally:
            logger.info("AsyncAPIWorker.run() finished: func=%s", self._func_name)
            sys.stdout.flush()

    def cancel(self):
        """取消任务（注意：无法中断已经开始的API调用）"""
        logger.info("AsyncAPIWorker.cancel() called: func=%s", self._func_name)
        self._is_cancelled = True
