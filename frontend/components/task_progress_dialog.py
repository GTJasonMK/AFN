"""
任务进度对话框

显示异步任务的执行进度和状态
"""

import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

from api.client import ArborisAPIClient
from utils.task_monitor import TaskMonitor, TaskMonitorManager
from utils.dpi_utils import dpi_helper, dp, sp
from themes.theme_manager import theme_manager

logger = logging.getLogger(__name__)


class TaskProgressDialog(QDialog):
    """
    任务进度对话框

    用于显示异步任务的执行进度，支持取消任务
    """

    # 任务完成信号
    task_completed = pyqtSignal(dict)  # 任务结果

    # 任务失败信号
    task_failed = pyqtSignal(str)  # 错误消���

    def __init__(
        self,
        task_id: str,
        task_name: str,
        api_client: ArborisAPIClient,
        monitor_manager: TaskMonitorManager,
        parent=None,
        can_cancel: bool = True
    ):
        """
        初始化任务进度对话框

        Args:
            task_id: 任务ID
            task_name: 任务名称（显示用）
            api_client: API客户端
            monitor_manager: 任务监控管理器
            parent: 父窗口
            can_cancel: 是否允许取消任务
        """
        super().__init__(parent)

        self.task_id = task_id
        self.task_name = task_name
        self.api_client = api_client
        self.monitor_manager = monitor_manager
        self.can_cancel = can_cancel

        self._monitor: Optional[TaskMonitor] = None
        self._is_completed = False
        self._is_cancelled = False

        self._setup_ui()
        self._start_monitoring()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle(f"{self.task_name} - 执行中")
        self.setModal(True)
        self.setMinimumWidth(dp(500))
        self.setMinimumHeight(dp(250))

        # 禁止关闭窗口（必须等待任务完成或取消）
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(dp(15))
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))

        # 任务名称标签
        self.task_label = QLabel(f"任务: {self.task_name}")
        self.task_label.setStyleSheet(f"font-size: {sp(14)}px; font-weight: bold;")
        layout.addWidget(self.task_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("正在准备...")
        self.status_label.setStyleSheet(f"color: {theme_manager.TEXT_SECONDARY}; font-size: {sp(12)}px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # 详细日志（可选，默认隐藏）
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(dp(100))
        self.log_text.setVisible(False)
        layout.addWidget(self.log_text)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 显示/隐藏日志按钮
        self.toggle_log_button = QPushButton("显示详情")
        self.toggle_log_button.clicked.connect(self._toggle_log)
        button_layout.addWidget(self.toggle_log_button)

        # 取消按钮
        if self.can_cancel:
            self.cancel_button = QPushButton("取消任务")
            self.cancel_button.clicked.connect(self._cancel_task)
            button_layout.addWidget(self.cancel_button)

        # 关闭按钮（初始禁用）
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def _start_monitoring(self):
        """开始监控任务"""
        self._monitor = self.monitor_manager.monitor_task(
            task_id=self.task_id,
            on_progress=self._on_progress_updated,
            on_completed=self._on_task_completed,
            on_failed=self._on_task_failed
        )

        self._log(f"开始监控任务: {self.task_id}")

    def _on_progress_updated(self, progress: int, description: str):
        """进度更新回调"""
        self.progress_bar.setValue(progress)

        if description:
            self.status_label.setText(description)
            self._log(f"[{progress}%] {description}")

    def _on_task_completed(self, result_data: Dict[str, Any]):
        """任务完成回调"""
        self._is_completed = True

        self.progress_bar.setValue(100)
        self.status_label.setText("任务已完成！")
        self.status_label.setStyleSheet(f"color: {theme_manager.SUCCESS}; font-size: {sp(12)}px; font-weight: bold;")

        self.setWindowTitle(f"{self.task_name} - 已完成")

        if self.can_cancel:
            self.cancel_button.setEnabled(False)

        self.close_button.setEnabled(True)

        self._log("任务执行成功！")
        logger.info(f"任务 {self.task_id} 完成")

        # 发出完成信号
        self.task_completed.emit(result_data)

    def _on_task_failed(self, error_message: str, error_details: Dict[str, Any]):
        """任务失败回调"""
        self._is_completed = True

        self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {theme_manager.ERROR}; }}")
        self.status_label.setText(f"任务失败: {error_message}")
        self.status_label.setStyleSheet(f"color: {theme_manager.ERROR}; font-size: {sp(12)}px; font-weight: bold;")

        self.setWindowTitle(f"{self.task_name} - 失败")

        if self.can_cancel:
            self.cancel_button.setEnabled(False)

        self.close_button.setEnabled(True)

        self._log(f"任务执行失败: {error_message}")
        if error_details:
            self._log(f"错误详情: {error_details}")

        logger.error(f"任务 {self.task_id} 失败: {error_message}")

        # 发出失败信号
        self.task_failed.emit(error_message)

    def _cancel_task(self):
        """取消任务"""
        if self._is_completed or self._is_cancelled:
            return

        try:
            self.status_label.setText("正在取消任务...")
            self.cancel_button.setEnabled(False)

            # 调用API取消任务
            result = self.api_client.cancel_task(self.task_id)

            if result.get('success'):
                self._is_cancelled = True
                self.status_label.setText("任务已取消")
                self.status_label.setStyleSheet(f"color: {theme_manager.WARNING}; font-size: {sp(12)}px;")
                self.close_button.setEnabled(True)

                self._log("任务已被用户取消")
                logger.info(f"任务 {self.task_id} 已取消")

                # 停止监控
                if self._monitor:
                    self.monitor_manager.stop_monitoring(self.task_id)

                self.accept()
            else:
                self.status_label.setText("取消任务失败")
                self.cancel_button.setEnabled(True)
                self._log(f"取消任务失败: {result.get('message', '未知错误')}")

        except Exception as e:
            logger.exception(f"取消任务 {self.task_id} 时出错: {e}")
            self.status_label.setText(f"取消任务出错: {str(e)}")
            self.cancel_button.setEnabled(True)
            self._log(f"取消任务出错: {str(e)}")

    def _toggle_log(self):
        """切换日志显示"""
        is_visible = self.log_text.isVisible()
        self.log_text.setVisible(not is_visible)

        if is_visible:
            self.toggle_log_button.setText("显示详情")
            self.setMinimumHeight(dp(250))
        else:
            self.toggle_log_button.setText("隐藏详情")
            self.setMinimumHeight(dp(400))

    def _log(self, message: str):
        """添加日志"""
        self.log_text.append(message)

    def closeEvent(self, event):
        """关闭事件"""
        # 如果任务还在运行，阻止关闭
        if not self._is_completed and not self._is_cancelled:
            event.ignore()
            return

        # 停止监控
        if self._monitor:
            self.monitor_manager.stop_monitoring(self.task_id)

        event.accept()
