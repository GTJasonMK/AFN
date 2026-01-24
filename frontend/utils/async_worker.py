"""
异步工作线程工具

提供QThread包装器，用于在后台执行耗时的API调用，避免UI冻结

线程安全设计：
- 使用 threading.Event 实现线程安全的取消机制
- 信号发射前检查取消状态
- 自动在线程完成后清理资源
- Windows 上初始化 COM 避免线程冲突
"""

import logging
import platform
import threading
import traceback
from typing import Callable, Any, Optional, Dict

from PyQt6.QtCore import QThread, pyqtSignal


logger = logging.getLogger(__name__)

# Windows COM 支持
_IS_WINDOWS = platform.system() == 'Windows'
_pythoncom = None
_ole32 = None
_com_init_lock = threading.Lock()  # COM 初始化锁，避免竞态条件

if _IS_WINDOWS:
    try:
        import pythoncom
        _pythoncom = pythoncom
    except ImportError:
        # pythoncom 不可用，使用 ctypes 作为回退
        try:
            import ctypes
            _ole32 = ctypes.windll.ole32
        except Exception:
            pass


def _com_initialize():
    """初始化 COM（线程内调用）

    使用 COINIT_MULTITHREADED (MTA) 模式，适合后台网络 I/O 线程。
    避免使用 COINIT_APARTMENTTHREADED (STA) 因为它需要消息循环。

    Returns:
        bool: True 表示初始化成功或已初始化，False 表示失败
    """
    with _com_init_lock:
        if _pythoncom:
            try:
                # 使用 MTA 模式
                _pythoncom.CoInitializeEx(_pythoncom.COINIT_MULTITHREADED)
                return True
            except Exception as e:
                # 可能已经初始化，忽略错误
                logger.debug("COM init with pythoncom: %s", e)
                return True  # 假设已初始化
        elif _ole32:
            try:
                # COINIT_MULTITHREADED = 0x0 (MTA, 适合后台线程)
                hr = _ole32.CoInitializeEx(None, 0x0)
                # S_OK = 0, S_FALSE = 1 (already initialized), RPC_E_CHANGED_MODE = 0x80010106
                if hr in (0, 1):
                    return True
                elif hr == -2147417850:  # RPC_E_CHANGED_MODE (0x80010106 as signed)
                    # 线程已经以不同模式初始化，这是可以接受的
                    logger.debug("COM already initialized in different mode")
                    return True
                else:
                    logger.warning("COM init failed with hr=%s", hr)
                    return False
            except Exception as e:
                logger.debug("COM init with ole32 failed: %s", e)
                return False
        return False


def _com_uninitialize():
    """释放 COM（线程内调用）"""
    if _pythoncom:
        _pythoncom.CoUninitialize()
    elif _ole32:
        _ole32.CoUninitialize()


class AsyncAPIWorker(QThread):
    """异步API调用工作线程

    线程安全设计：
    - 使用 threading.Event 实现线程安全的取消机制
    - 信号发射前检查取消状态
    - 自动在线程完成后清理资源

    用法:
        worker = AsyncAPIWorker(api_client.generate_chapter, project_id, chapter_number)
        worker.success.connect(self.onSuccess)
        worker.error.connect(self.onError)
        worker.error_detail.connect(self.onErrorDetail)  # 可选：获取详细错误信息
        worker.start()
    """

    # 信号
    success = pyqtSignal(object)       # 成功时发射结果
    error = pyqtSignal(str)            # 失败时发射错误信息（向后兼容）
    error_detail = pyqtSignal(dict)    # 失败时发射详细错误信息

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
        self._func_name = getattr(func, '__name__', str(func))

        # 线程安全的取消事件
        self._cancel_event = threading.Event()

        logger.debug(
            "AsyncAPIWorker created: func=%s, args=%s",
            self._func_name, self.args
        )

        # 线程完成后自动删除，防止内存泄漏
        self.finished.connect(self._on_finished)

    def _on_finished(self):
        """线程完成时的清理"""
        try:
            self.deleteLater()
        except RuntimeError:
            pass  # 对象可能已被删除

    def run(self):
        """线程执行入口"""
        logger.info("AsyncAPIWorker started: func=%s", self._func_name)

        # Windows 上初始化 COM，避免线程冲突错误 (0x8001010d)
        com_initialized = False
        if _IS_WINDOWS:
            try:
                com_initialized = _com_initialize()
                if com_initialized:
                    logger.debug("COM initialized for worker thread")
            except Exception as e:
                logger.debug("COM initialization skipped: %s", e)

        try:
            # 检查是否已取消
            if self._cancel_event.is_set():
                logger.info("AsyncAPIWorker cancelled before execution: func=%s", self._func_name)
                return

            # 执行函数
            result = self.func(*self.args, **self.kwargs)

            logger.debug(
                "AsyncAPIWorker func returned: func=%s, result_type=%s",
                self._func_name, type(result).__name__
            )

            # 发射成功信号（检查取消状态）
            if not self._cancel_event.is_set():
                try:
                    self.success.emit(result)
                except RuntimeError:
                    # 接收者对象可能已被删除
                    logger.debug("AsyncAPIWorker: receiver deleted, signal not emitted")

        except Exception as e:
            self._handle_exception(e)
        finally:
            # Windows 上释放 COM
            if com_initialized:
                try:
                    _com_uninitialize()
                except Exception:
                    pass

    def _handle_exception(self, e: Exception):
        """处理异常并发射错误信号"""
        logger.error(
            "AsyncAPIWorker exception: func=%s, error_type=%s, error=%s",
            self._func_name, type(e).__name__, str(e),
            exc_info=True
        )

        # 如果已取消，不发射错误信号
        if self._cancel_event.is_set():
            return

        # 构建错误详情
        error_detail = self._build_error_detail(e)

        # 发射信号（保护性处理，接收者可能已被删除）
        try:
            self.error.emit(error_detail.get('message', str(e)))
            self.error_detail.emit(error_detail)
        except RuntimeError:
            # 接收者对象可能已被删除
            logger.debug("AsyncAPIWorker: receiver deleted, error signal not emitted")

    def _build_error_detail(self, e: Exception) -> Dict[str, Any]:
        """构建详细错误信息

        Args:
            e: 异常对象

        Returns:
            包含错误详情的字典
        """
        detail = {
            'type': type(e).__name__,
            'message': str(e),
            'traceback': traceback.format_exc(),
            'func_name': self._func_name,
        }

        # 处理 requests 库的 HTTP 错误
        if hasattr(e, 'response') and e.response is not None:
            response = e.response
            detail['status_code'] = getattr(response, 'status_code', None)
            detail['response_text'] = getattr(response, 'text', None)

            # 尝试解析JSON错误响应
            try:
                json_error = response.json()
                detail['response_json'] = json_error
                # 提取常见的错误字段
                if 'detail' in json_error:
                    detail['message'] = json_error['detail']
                elif 'message' in json_error:
                    detail['message'] = json_error['message']
            except (ValueError, AttributeError):
                pass

        # 处理自定义异常的额外属性
        for attr in ['code', 'status_code', 'detail', 'reason']:
            if hasattr(e, attr):
                detail[attr] = getattr(e, attr)

        return detail

    def cancel(self):
        """取消任务（线程安全）

        注意：无法中断已经开始的API调用，只能阻止信号发射
        """
        logger.info("AsyncAPIWorker.cancel() called: func=%s", self._func_name)
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """检查是否已取消（线程安全）"""
        return self._cancel_event.is_set()


def run_async_action(
    worker_manager,
    func: Callable,
    *args,
    task_name: str,
    on_success: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
    **kwargs
) -> AsyncAPIWorker:
    """统一执行异步API调用并注册到WorkerManager"""
    worker = AsyncAPIWorker(func, *args, **kwargs)
    if on_success:
        worker.success.connect(on_success)
    if on_error:
        worker.error.connect(on_error)
    worker_manager.start(worker, task_name)
    return worker


# 向后兼容的别名
AsyncWorker = AsyncAPIWorker
