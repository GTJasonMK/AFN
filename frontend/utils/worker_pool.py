"""
异步工作线程池

基于ThreadPoolExecutor实现的高性能线程池，避免每次创建新QThread的开销。

性能优化：
- 线程复用：使用固定大小的线程池，避免频繁创建/销毁线程
- 信号机制：通过Qt信号在主线程安全地处理结果
- 取消支持：支持取消正在等待的任务

使用方式：
    from utils.worker_pool import WorkerPool, PooledTask

    # 获取全局线程池
    pool = WorkerPool.instance()

    # 提交任务
    task = pool.submit(api_client.get_novels)
    task.success.connect(self.on_success)
    task.error.connect(self.on_error)

    # 取消任务
    task.cancel()
"""

import logging
import platform
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

# 默认线程池大小
_DEFAULT_POOL_SIZE = 8

# Windows COM 支持
_IS_WINDOWS = platform.system() == 'Windows'
_ole32 = None

if _IS_WINDOWS:
    try:
        import ctypes
        _ole32 = ctypes.windll.ole32
    except Exception:
        pass


def _com_initialize():
    """初始化 COM（线程内调用）"""
    if _ole32:
        hr = _ole32.CoInitializeEx(None, 0x0)
        return hr in (0, 1)
    return False


def _com_uninitialize():
    """释放 COM（线程内调用）"""
    if _ole32:
        _ole32.CoUninitialize()


class PooledTask(QObject):
    """线程池任务

    封装提交到线程池的任务，提供Qt信号用于结果回调。

    信号：
        success: 任务成功时发射，携带结果
        error: 任务失败时发射，携带错误消息
        error_detail: 任务失败时发射，携带详细错误信息
    """

    success = pyqtSignal(object)
    error = pyqtSignal(str)
    error_detail = pyqtSignal(dict)

    def __init__(self, future: Future, func_name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._future = future
        self._func_name = func_name
        self._cancelled = False

    def cancel(self) -> bool:
        """尝试取消任务

        Returns:
            True如果成功取消，False如果任务已开始执行
        """
        self._cancelled = True
        return self._future.cancel()

    def is_cancelled(self) -> bool:
        """检查任务是否已取消"""
        return self._cancelled or self._future.cancelled()

    def is_done(self) -> bool:
        """检查任务是否已完成（成功、失败或取消）"""
        return self._future.done()

    def _emit_success(self, result: Any):
        """发射成功信号（由线程池回调调用）"""
        if not self._cancelled:
            try:
                self.success.emit(result)
            except RuntimeError:
                # 接收者可能已被删除
                pass

    def _emit_error(self, message: str, detail: Dict[str, Any]):
        """发射错误信号（由线程池回调调用）"""
        if not self._cancelled:
            try:
                self.error.emit(message)
                self.error_detail.emit(detail)
            except RuntimeError:
                # 接收者可能已被删除
                pass


class WorkerPool:
    """异步工作线程池

    使用ThreadPoolExecutor管理后台任务，提供线程复用和资源控制。

    特性：
    - 单例模式：全局共享一个线程池
    - 线程复用：固定大小的线程池
    - 信号安全：通过Qt信号机制传递结果
    - Windows COM：自动处理COM初始化
    """

    _instance: Optional['WorkerPool'] = None
    _lock = threading.Lock()

    def __init__(self, max_workers: int = _DEFAULT_POOL_SIZE):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="AFN-Worker",
        )
        self._tasks: Dict[int, PooledTask] = {}
        self._task_counter = 0
        self._shutdown = False
        logger.info("WorkerPool initialized: max_workers=%d", max_workers)

    @classmethod
    def instance(cls, max_workers: int = _DEFAULT_POOL_SIZE) -> 'WorkerPool':
        """获取全局线程池实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(max_workers)
        return cls._instance

    def submit(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> PooledTask:
        """提交任务到线程池

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            PooledTask对象，可连接success/error信号
        """
        if self._shutdown:
            raise RuntimeError("WorkerPool已关闭")

        func_name = getattr(func, '__name__', str(func))

        # 包装函数以处理COM和异常
        def wrapped():
            com_initialized = False
            if _IS_WINDOWS:
                try:
                    com_initialized = _com_initialize()
                except Exception:
                    pass

            try:
                return func(*args, **kwargs)
            finally:
                if com_initialized:
                    try:
                        _com_uninitialize()
                    except Exception:
                        pass

        # 提交到线程池
        future = self._executor.submit(wrapped)

        # 创建任务对象
        task = PooledTask(future, func_name)

        # 添加完成回调
        def on_done(f: Future):
            if task.is_cancelled():
                return

            try:
                result = f.result()
                task._emit_success(result)
            except Exception as e:
                error_detail = self._build_error_detail(e, func_name)
                task._emit_error(error_detail.get('message', str(e)), error_detail)

            # 清理任务引用
            task.deleteLater()

        future.add_done_callback(on_done)

        logger.debug("Task submitted: func=%s", func_name)
        return task

    def _build_error_detail(self, e: Exception, func_name: str) -> Dict[str, Any]:
        """构建详细错误信息"""
        detail = {
            'type': type(e).__name__,
            'message': str(e),
            'traceback': traceback.format_exc(),
            'func_name': func_name,
        }

        # 处理HTTP错误
        if hasattr(e, 'response') and e.response is not None:
            response = e.response
            detail['status_code'] = getattr(response, 'status_code', None)
            detail['response_text'] = getattr(response, 'text', None)

            try:
                json_error = response.json()
                detail['response_json'] = json_error
                if 'detail' in json_error:
                    detail['message'] = json_error['detail']
                elif 'message' in json_error:
                    detail['message'] = json_error['message']
            except (ValueError, AttributeError):
                pass

        return detail

    def shutdown(self, wait: bool = True):
        """关闭线程池

        Args:
            wait: 是否等待所有任务完成
        """
        if self._shutdown:
            return

        self._shutdown = True
        self._executor.shutdown(wait=wait)
        logger.info("WorkerPool shutdown: wait=%s", wait)

    @property
    def active_count(self) -> int:
        """当前活跃的线程数"""
        return len([t for t in threading.enumerate() if t.name.startswith("AFN-Worker")])


def submit_task(func: Callable, *args, **kwargs) -> PooledTask:
    """便捷函数：提交任务到全局线程池

    Args:
        func: 要执行的函数
        *args: 函数位置参数
        **kwargs: 函数关键字参数

    Returns:
        PooledTask对象

    Usage:
        from utils.worker_pool import submit_task

        task = submit_task(api_client.get_novels)
        task.success.connect(self.on_success)
        task.error.connect(self.on_error)
    """
    return WorkerPool.instance().submit(func, *args, **kwargs)
