"""
异步任务监控管理器

提供对后端异步任务的轮询和状态监控功能
"""

import logging
from typing import Callable, Dict, Optional, Any
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from api.client import ArborisAPIClient

logger = logging.getLogger(__name__)


class TaskMonitor(QObject):
    """
    单个任务的监控器

    负责轮询单个任务的状态并在状态变化时发出信号
    """

    # 任务状态变化信号
    status_changed = pyqtSignal(str)  # 状态: pending, running, completed, failed, cancelled

    # 任务进度更新信号
    progress_updated = pyqtSignal(int, str)  # (进度百分比, 当前步骤描述)

    # 任务完成信号
    completed = pyqtSignal(dict)  # 任务结果数据

    # 任务失败信号
    failed = pyqtSignal(str, dict)  # (错误消息, 错误详情)

    def __init__(
        self,
        task_id: str,
        api_client: ArborisAPIClient,
        poll_interval: int = 2000,  # 默认2秒轮询一次
        parent: Optional[QObject] = None
    ):
        """
        初始化任务监控器

        Args:
            task_id: 任务ID
            api_client: API客户端实例
            poll_interval: 轮询间隔（毫秒）
            parent: 父对象
        """
        super().__init__(parent)

        self.task_id = task_id
        self.api_client = api_client
        self.poll_interval = poll_interval

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_task_status)

        self._last_status: Optional[str] = None
        self._last_progress: Optional[int] = None
        self._is_monitoring = False

    def start(self):
        """开始监控任务"""
        if self._is_monitoring:
            logger.warning(f"任务 {self.task_id} 已在监控中")
            return

        logger.info(f"开始监控任务: {self.task_id}")
        self._is_monitoring = True
        self._timer.start(self.poll_interval)

        # 立即执行一次查询
        self._poll_task_status()

    def stop(self):
        """停止监控任务"""
        if not self._is_monitoring:
            return

        logger.info(f"停止监控任务: {self.task_id}")
        self._is_monitoring = False
        self._timer.stop()

    def _poll_task_status(self):
        """轮询任务状态"""
        try:
            task_data = self.api_client.get_task(self.task_id)

            status = task_data.get('status')
            progress = task_data.get('progress', 0)
            step_description = task_data.get('step_description', '')

            # 检查状态变化
            if status != self._last_status:
                logger.info(f"任务 {self.task_id} 状态变化: {self._last_status} -> {status}")
                self._last_status = status
                self.status_changed.emit(status)

            # 检查进度变化
            if progress != self._last_progress:
                self._last_progress = progress
                self.progress_updated.emit(progress, step_description)

            # 处理终态
            if status == 'completed':
                logger.info(f"任务 {self.task_id} 已完成")
                self.stop()
                result_data = task_data.get('result_data', {})
                self.completed.emit(result_data)

            elif status == 'failed':
                logger.error(f"任务 {self.task_id} 失败: {task_data.get('error_message')}")
                self.stop()
                error_message = task_data.get('error_message', '未知错误')
                error_details = task_data.get('error_details', {})
                self.failed.emit(error_message, error_details)

            elif status == 'cancelled':
                logger.info(f"任务 {self.task_id} 已取消")
                self.stop()
                self.status_changed.emit('cancelled')

        except Exception as e:
            logger.exception(f"轮询任务 {self.task_id} 状态时出错: {e}")
            # 网络错误等不停止监控，继续尝试


class TaskMonitorManager(QObject):
    """
    任务监控管理器

    统一管理多个异步任务的监控
    """

    def __init__(
        self,
        api_client: ArborisAPIClient,
        parent: Optional[QObject] = None
    ):
        """
        ���始化任务监控管理器

        Args:
            api_client: API客户端实例
            parent: 父对象
        """
        super().__init__(parent)

        self.api_client = api_client
        self._monitors: Dict[str, TaskMonitor] = {}

    def monitor_task(
        self,
        task_id: str,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_completed: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_failed: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        poll_interval: int = 2000
    ) -> TaskMonitor:
        """
        开始监控一个任务

        Args:
            task_id: 任务ID
            on_progress: 进度更新回调
            on_completed: 完成回调
            on_failed: 失败回调
            poll_interval: 轮询间隔（毫秒）

        Returns:
            TaskMonitor实例
        """
        # 如果已有监控器，先停止
        if task_id in self._monitors:
            logger.warning(f"任务 {task_id} 已有监控器，将替换")
            self._monitors[task_id].stop()
            self._monitors[task_id].deleteLater()

        # 创建新监控器
        monitor = TaskMonitor(
            task_id=task_id,
            api_client=self.api_client,
            poll_interval=poll_interval,
            parent=self
        )

        # 连接回调
        if on_progress:
            monitor.progress_updated.connect(on_progress)

        if on_completed:
            monitor.completed.connect(on_completed)

        if on_failed:
            monitor.failed.connect(on_failed)

        # 任务完成或失败后自动清理
        def cleanup():
            if task_id in self._monitors:
                del self._monitors[task_id]
                logger.info(f"清理任务监控器: {task_id}")

        monitor.completed.connect(cleanup)
        monitor.failed.connect(lambda *args: cleanup())

        # 保存并启动监控器
        self._monitors[task_id] = monitor
        monitor.start()

        logger.info(f"添加任务监控器: {task_id}")
        return monitor

    def stop_monitoring(self, task_id: str):
        """
        停止监控指定任务

        Args:
            task_id: 任务ID
        """
        if task_id in self._monitors:
            self._monitors[task_id].stop()
            self._monitors[task_id].deleteLater()
            del self._monitors[task_id]
            logger.info(f"停止监控任务: {task_id}")

    def stop_all(self):
        """停止所有任务监控"""
        task_ids = list(self._monitors.keys())
        for task_id in task_ids:
            self.stop_monitoring(task_id)
        logger.info("停止所有任务监控")

    def get_monitor(self, task_id: str) -> Optional[TaskMonitor]:
        """
        获取指定任务的监控器

        Args:
            task_id: 任务ID

        Returns:
            TaskMonitor实例，如果不存在则返回None
        """
        return self._monitors.get(task_id)

    def is_monitoring(self, task_id: str) -> bool:
        """
        检查是否正在监控指定任务

        Args:
            task_id: 任务ID

        Returns:
            是否正在监控
        """
        return task_id in self._monitors

    def get_monitoring_count(self) -> int:
        """获取正在监控的任务数量"""
        return len(self._monitors)
