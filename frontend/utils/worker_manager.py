"""
Worker 管理器 - 集中管理 QThread Worker 的生命周期

提供统一的 Worker 注册、启动、清理机制，避免内存泄漏和重复代码。

用法示例:
    from utils.worker_manager import WorkerManager
    from utils.async_worker import AsyncAPIWorker
    from utils.sse_worker import SSEWorker

    class MyComponent(QWidget):
        def __init__(self):
            super().__init__()
            self.worker_manager = WorkerManager(self)

        def start_api_call(self):
            worker = AsyncAPIWorker(api_client.get_data, self.project_id)
            worker.success.connect(self.on_success)
            worker.error.connect(self.on_error)
            self.worker_manager.start(worker, 'data_loader')

        def start_sse_stream(self):
            worker = SSEWorker(url, payload)
            worker.token_received.connect(self.on_token)
            worker.complete.connect(self.on_complete)
            worker.error.connect(self.on_error)
            self.worker_manager.start(worker, 'sse_stream')

        def cancel_operation(self):
            self.worker_manager.stop('data_loader')

        def closeEvent(self, event):
            self.worker_manager.cleanup_all()
            super().closeEvent(event)
"""

import logging
from typing import Optional, Dict, Set, Callable
from weakref import ref

from PyQt6.QtCore import QThread, QObject

from .constants import WorkerTimeouts

logger = logging.getLogger(__name__)


class WorkerManager:
    """Worker 生命周期管理器

    特性：
    - 自动跟踪所有活跃的 Worker
    - 支持命名 Worker（同名 Worker 会自动停止旧的）
    - Worker 完成后自动清理
    - 提供批量清理方法
    - 防止内存泄漏
    """

    def __init__(self, parent: Optional[QObject] = None):
        """
        初始化 WorkerManager

        Args:
            parent: 父对象（可选，用于日志标识）
        """
        self._parent_ref = ref(parent) if parent else None
        self._parent_name = type(parent).__name__ if parent else 'Unknown'

        # 命名 Worker 字典：name -> worker
        self._named_workers: Dict[str, QThread] = {}

        # 匿名 Worker 集合（使用强引用，确保能够停止所有线程）
        # 注意：不使用 WeakSet，因为 WeakSet 会在引用计数为 0 时自动移除对象，
        # 但不会停止线程，导致僵尸线程
        self._anonymous_workers: Set[QThread] = set()

        # 已清理标记
        self._is_cleaned_up = False

        logger.debug("WorkerManager created for %s", self._parent_name)

    def start(
        self,
        worker: QThread,
        name: Optional[str] = None,
        on_finished: Optional[Callable] = None
    ) -> QThread:
        """
        启动并注册一个 Worker

        Args:
            worker: QThread Worker 实例（AsyncAPIWorker 或 SSEWorker）
            name: Worker 名称（可选）。如果提供，同名的旧 Worker 会被停止
            on_finished: Worker 完成后的额外回调（可选）

        Returns:
            启动的 Worker 实例

        示例:
            # 命名 Worker（自动停止同名旧 Worker）
            manager.start(worker, 'chapter_generator')

            # 匿名 Worker
            manager.start(worker)
        """
        if self._is_cleaned_up:
            logger.warning(
                "WorkerManager for %s already cleaned up, cannot start worker",
                self._parent_name
            )
            return worker

        # 如果有名称，先停止同名的旧 Worker
        if name:
            self._stop_named_worker(name)
            self._named_workers[name] = worker
            logger.debug(
                "WorkerManager[%s]: Starting named worker '%s'",
                self._parent_name, name
            )
        else:
            self._anonymous_workers.add(worker)
            logger.debug(
                "WorkerManager[%s]: Starting anonymous worker",
                self._parent_name
            )

        # 连接完成信号以自动清理
        def on_worker_finished():
            self._on_worker_finished(worker, name)
            if on_finished:
                try:
                    on_finished()
                except Exception as e:
                    logger.error("Worker finish callback error: %s", e)

        worker.finished.connect(on_worker_finished)

        # 启动 Worker
        worker.start()

        return worker

    def stop(self, name: str, wait_ms: int = 1000) -> bool:
        """
        停止指定名称的 Worker

        Args:
            name: Worker 名称
            wait_ms: 等待 Worker 结束的毫秒数

        Returns:
            是否成功停止
        """
        return self._stop_named_worker(name, wait_ms)

    def stop_all(self, wait_ms: int = 1000):
        """
        停止所有 Worker

        Args:
            wait_ms: 等待每个 Worker 结束的毫秒数
        """
        logger.debug(
            "WorkerManager[%s]: Stopping all workers",
            self._parent_name
        )

        # 停止所有命名 Worker
        names = list(self._named_workers.keys())
        for name in names:
            self._stop_named_worker(name, wait_ms)

        # 停止所有匿名 Worker
        for worker in list(self._anonymous_workers):
            self._stop_worker(worker, wait_ms)

        self._anonymous_workers.clear()

    def cleanup_all(self):
        """
        清理所有 Worker 并标记为已清理

        在组件销毁时调用此方法。调用后，WorkerManager 将不再接受新的 Worker。
        """
        if self._is_cleaned_up:
            return

        logger.debug(
            "WorkerManager[%s]: Cleanup all workers",
            self._parent_name
        )

        self._is_cleaned_up = True
        self.stop_all(wait_ms=500)

        self._named_workers.clear()
        self._anonymous_workers.clear()

    def is_running(self, name: str) -> bool:
        """
        检查指定名称的 Worker 是否正在运行

        Args:
            name: Worker 名称

        Returns:
            是否正在运行
        """
        worker = self._named_workers.get(name)
        if worker:
            try:
                return worker.isRunning()
            except RuntimeError:
                return False
        return False

    def get_worker(self, name: str) -> Optional[QThread]:
        """
        获取指定名称的 Worker

        Args:
            name: Worker 名称

        Returns:
            Worker 实例或 None
        """
        return self._named_workers.get(name)

    def _stop_named_worker(self, name: str, wait_ms: int = 1000) -> bool:
        """停止命名 Worker（内部方法）"""
        worker = self._named_workers.pop(name, None)
        if worker:
            logger.debug(
                "WorkerManager[%s]: Stopping named worker '%s'",
                self._parent_name, name
            )
            return self._stop_worker(worker, wait_ms)
        return True

    def _stop_worker(self, worker: QThread, wait_ms: int = 1000) -> bool:
        """停止单个 Worker（内部方法）"""
        try:
            if not worker.isRunning():
                return True

            # 尝试调用 stop/cancel 方法（如果存在）
            if hasattr(worker, 'stop'):
                worker.stop()
            elif hasattr(worker, 'cancel'):
                worker.cancel()

            # 断开所有信号（防止回调到已销毁的对象）
            self._disconnect_signals(worker)

            # 请求线程退出
            worker.quit()

            # 等待线程结束
            if not worker.wait(wait_ms):
                logger.warning(
                    "WorkerManager[%s]: Worker did not stop within %dms, force terminating",
                    self._parent_name, wait_ms
                )
                worker.terminate()
                worker.wait(WorkerTimeouts.FORCE_TERMINATE_MS)

            return True

        except RuntimeError as e:
            # C++ 对象可能已被删除
            logger.debug(
                "WorkerManager[%s]: Worker already deleted: %s",
                self._parent_name, e
            )
            return True
        except Exception as e:
            logger.error(
                "WorkerManager[%s]: Error stopping worker: %s",
                self._parent_name, e
            )
            return False

    def _disconnect_signals(self, worker: QThread):
        """断开 Worker 的所有信号（内部方法）"""
        try:
            # 常见的信号名称
            signal_names = [
                # AsyncAPIWorker 信号
                'success', 'error',
                # SSEWorker 信号
                'token_received', 'progress_received', 'complete',
                'error_data', 'streaming_start', 'ai_message_chunk', 'option_received',
                # 通用信号
                'finished', 'started'
            ]

            for signal_name in signal_names:
                if hasattr(worker, signal_name):
                    signal = getattr(worker, signal_name)
                    if hasattr(signal, 'disconnect'):
                        try:
                            signal.disconnect()
                        except (TypeError, RuntimeError):
                            pass  # 信号可能未连接或对象已删除

        except RuntimeError:
            pass  # 对象可能已被删除

    def _on_worker_finished(self, worker: QThread, name: Optional[str]):
        """Worker 完成时的回调（内部方法）"""
        if self._is_cleaned_up:
            return

        if name:
            # 从命名字典中移除（如果仍然是同一个 Worker）
            if self._named_workers.get(name) is worker:
                self._named_workers.pop(name, None)
                logger.debug(
                    "WorkerManager[%s]: Named worker '%s' finished",
                    self._parent_name, name
                )
        else:
            # 从匿名 Worker 集合中移除（显式移除，因为使用强引用）
            self._anonymous_workers.discard(worker)
            logger.debug(
                "WorkerManager[%s]: Anonymous worker finished",
                self._parent_name
            )

    @property
    def active_worker_count(self) -> int:
        """获取活跃 Worker 数量"""
        named_count = sum(
            1 for w in self._named_workers.values()
            if self._is_worker_running(w)
        )
        anon_count = sum(
            1 for w in self._anonymous_workers
            if self._is_worker_running(w)
        )
        return named_count + anon_count

    @property
    def active_worker_names(self) -> Set[str]:
        """获取所有活跃的命名 Worker 名称"""
        return {
            name for name, worker in self._named_workers.items()
            if self._is_worker_running(worker)
        }

    def _is_worker_running(self, worker: QThread) -> bool:
        """检查 Worker 是否正在运行（内部方法）"""
        try:
            return worker.isRunning()
        except RuntimeError:
            return False
