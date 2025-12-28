"""
导入分析进度对话框

显示导入分析的进度状态，包含阶段进度和取消功能。
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncAPIWorker

from ..base import BaseDialog
from ..styles import DialogStyles


class ImportProgressDialog(BaseDialog):
    """导入分析进度对话框

    使用方式：
        dialog = ImportProgressDialog(
            parent=self,
            project_id=project_id,
            api_client=client
        )
        dialog.analysis_completed.connect(on_complete)
        dialog.analysis_cancelled.connect(on_cancel)
        dialog.exec()
    """

    # 阶段显示名称（按新的执行顺序）
    STAGE_NAMES = {
        'generating_analysis_data': '生成分析数据',  # 阶段1：最重要，作为后续步骤基础
        'analyzing_chapters': '生成章节摘要',        # 阶段2：利用analysis_data
        'generating_outlines': '更新章节大纲',       # 阶段3
        'generating_part_outlines': '生成分部大纲',  # 阶段4（仅长篇）
        'extracting_blueprint': '反推蓝图信息',      # 阶段5：利用analysis_data
    }

    def __init__(self, parent=None, project_id: str = "", api_client=None):
        import logging
        import traceback
        logger = logging.getLogger(__name__)

        logger.info("=== ImportProgressDialog.__init__ 开始 ===")
        print("=== DEBUG: ImportProgressDialog.__init__ 开始 ===")

        try:
            self.project_id = project_id
            self.api_client = api_client
            self._cancelled = False
            self._completed = False
            self._poll_timer = None
            self._cancel_worker = None

            # UI组件引用
            self.container = None
            self.title_label = None
            self.stage_label = None
            self.progress_bar = None
            self.message_label = None
            self.cancel_btn = None
            self.spinner = None

            logger.info("调用 super().__init__...")
            print("DEBUG: 调用 super().__init__...")
            super().__init__(parent)
            logger.info("super().__init__ 完成")
            print("DEBUG: super().__init__ 完成")

            logger.info("调用 _setup_ui...")
            print("DEBUG: 调用 _setup_ui...")
            self._setup_ui()
            logger.info("_setup_ui 完成")
            print("DEBUG: _setup_ui 完成")

            logger.info("调用 _apply_theme...")
            print("DEBUG: 调用 _apply_theme...")
            self._apply_theme()
            logger.info("_apply_theme 完成")
            print("DEBUG: _apply_theme 完成")

            logger.info("调用 _start_polling...")
            print("DEBUG: 调用 _start_polling...")
            self._start_polling()
            logger.info("_start_polling 完成")
            print("DEBUG: _start_polling 完成")

            logger.info("=== ImportProgressDialog.__init__ 完成 ===")
            print("=== DEBUG: ImportProgressDialog.__init__ 完成 ===")

        except Exception as e:
            logger.error(f"ImportProgressDialog.__init__ 异常: {e}")
            logger.error(traceback.format_exc())
            print(f"DEBUG ERROR: ImportProgressDialog.__init__ 异常: {e}")
            print(traceback.format_exc())
            raise

    def _setup_ui(self):
        """创建UI"""
        import logging
        import traceback
        logger = logging.getLogger(__name__)

        logger.info("_setup_ui 开始")
        print("DEBUG: _setup_ui 开始")

        try:
            logger.info("导入 CircularSpinner...")
            print("DEBUG: 导入 CircularSpinner...")
            from components.loading_spinner import CircularSpinner
            logger.info("CircularSpinner 导入成功")
            print("DEBUG: CircularSpinner 导入成功")

            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)

            # 容器
            self.container = QFrame()
            self.container.setObjectName("import_progress_container")
            container_layout = QVBoxLayout(self.container)
            container_layout.setContentsMargins(dp(32), dp(28), dp(32), dp(28))
            container_layout.setSpacing(dp(16))

            # 标题
            self.title_label = QLabel("正在分析导入的小说")
            self.title_label.setObjectName("import_progress_title")
            self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(self.title_label)

            # 加载动画
            logger.info("创建 CircularSpinner...")
            print("DEBUG: 创建 CircularSpinner...")
            spinner_container = QHBoxLayout()
            spinner_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.spinner = CircularSpinner(size=dp(40))
            spinner_container.addWidget(self.spinner)
            container_layout.addLayout(spinner_container)
            logger.info("CircularSpinner 创建成功")
            print("DEBUG: CircularSpinner 创建成功")

            # 当前阶段标签
            self.stage_label = QLabel("准备中...")
            self.stage_label.setObjectName("import_stage_label")
            self.stage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(self.stage_label)

            # 进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setObjectName("import_progress_bar")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFixedHeight(dp(8))
            self.progress_bar.setTextVisible(False)
            container_layout.addWidget(self.progress_bar)

            # 详细消息
            self.message_label = QLabel("正在初始化分析任务...")
            self.message_label.setObjectName("import_message_label")
            self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.message_label.setWordWrap(True)
            container_layout.addWidget(self.message_label)

            # 取消按钮
            button_layout = QHBoxLayout()
            button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.cancel_btn = QPushButton("取消分析")
            self.cancel_btn.setObjectName("import_cancel_btn")
            self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.cancel_btn.setFixedHeight(dp(36))
            self.cancel_btn.setMinimumWidth(dp(120))
            self.cancel_btn.clicked.connect(self._on_cancel)
            button_layout.addWidget(self.cancel_btn)

            container_layout.addLayout(button_layout)

            layout.addWidget(self.container)

            # 设置对话框大小
            self.setFixedWidth(dp(400))

            logger.info("_setup_ui 完成")
            print("DEBUG: _setup_ui 完成")

        except Exception as e:
            logger.error(f"_setup_ui 异常: {e}")
            logger.error(traceback.format_exc())
            print(f"DEBUG ERROR: _setup_ui 异常: {e}")
            print(traceback.format_exc())
            raise

    def _apply_theme(self):
        """应用主题样式"""
        ui_font = theme_manager.ui_font()

        # 容器样式
        self.container.setStyleSheet(DialogStyles.container("import_progress_container"))

        # 标题样式
        self.title_label.setStyleSheet(f"""
            #import_progress_title {{
                font-family: {ui_font};
                font-size: {sp(18)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)

        # 阶段标签样式
        self.stage_label.setStyleSheet(f"""
            #import_stage_label {{
                font-family: {ui_font};
                font-size: {sp(15)}px;
                font-weight: 500;
                color: {theme_manager.PRIMARY};
            }}
        """)

        # 进度条样式
        self.progress_bar.setStyleSheet(f"""
            #import_progress_bar {{
                background-color: {theme_manager.BG_TERTIARY};
                border-radius: {dp(4)}px;
                border: none;
            }}
            #import_progress_bar::chunk {{
                background-color: {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
            }}
        """)

        # 消息标签样式
        self.message_label.setStyleSheet(f"""
            #import_message_label {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
            }}
        """)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("import_cancel_btn"))

    def _start_polling(self):
        """开始轮询进度"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("_start_polling 开始")
        print("DEBUG: _start_polling 开始")

        # 保存 worker 引用，避免被垃圾回收
        self._poll_workers = []

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start(2000)  # 每2秒轮询一次

        logger.info("定时器已启动，立即执行一次轮询")
        print("DEBUG: 定时器已启动，立即执行一次轮询")

        # 立即执行一次
        self._poll_status()

        logger.info("_start_polling 完成")
        print("DEBUG: _start_polling 完成")

    def _poll_status(self):
        """轮询分析状态"""
        import logging
        import traceback
        logger = logging.getLogger(__name__)

        logger.info("_poll_status 开始")
        print("DEBUG: _poll_status 开始")

        if self._cancelled or self._completed or not self.api_client:
            logger.info(f"跳过轮询: cancelled={self._cancelled}, completed={self._completed}, api_client={self.api_client is not None}")
            print(f"DEBUG: 跳过轮询: cancelled={self._cancelled}, completed={self._completed}")
            return

        try:
            def fetch_status():
                logger.info("fetch_status 被调用")
                print("DEBUG: fetch_status 被调用")
                result = self.api_client.get_import_analysis_status(self.project_id)
                logger.info(f"fetch_status 返回: {result}")
                print(f"DEBUG: fetch_status 返回: {result}")
                return result

            worker = AsyncAPIWorker(fetch_status)
            worker.success.connect(self._on_status_received)
            worker.error.connect(self._on_status_error)

            # 先启动 worker
            logger.info("启动轮询 worker...")
            print("DEBUG: 启动轮询 worker...")
            worker.start()
            logger.info("轮询 worker 已启动")
            print("DEBUG: 轮询 worker 已启动")

            # 保存 worker 引用，避免被垃圾回收（在 start 之后）
            self._poll_workers.append(worker)

            # 清理已完成的 worker（安全地检查，捕获已删除对象的异常）
            if len(self._poll_workers) > 5:
                active_workers = []
                for w in self._poll_workers:
                    try:
                        if w.isRunning() or w == worker:
                            active_workers.append(w)
                    except RuntimeError:
                        # C++ 对象已被删除，跳过
                        pass
                self._poll_workers = active_workers

        except Exception as e:
            logger.error(f"_poll_status 异常: {e}")
            logger.error(traceback.format_exc())
            print(f"DEBUG ERROR: _poll_status 异常: {e}")
            print(traceback.format_exc())

    def _on_status_received(self, data: dict):
        """处理状态响应"""
        status = data.get('status', 'pending')
        progress = data.get('progress', {})

        if status == 'completed':
            self._completed = True
            self._stop_polling()
            self.stage_label.setText("分析完成")
            self.message_label.setText("分析已完成，正在关闭...")
            self.progress_bar.setValue(100)
            # 延迟关闭
            QTimer.singleShot(1000, self.accept)
            return

        if status == 'failed':
            self._stop_polling()
            error = progress.get('error', '未知错误')
            self.stage_label.setText("分析失败")
            self.message_label.setText(f"错误: {error}")
            self.cancel_btn.setText("关闭")
            return

        if status == 'cancelled':
            self._cancelled = True
            self._stop_polling()
            self.stage_label.setText("分析已取消")
            self.message_label.setText("分析任务已被取消")
            self.cancel_btn.setText("关闭")
            return

        # 更新进度
        current_stage = progress.get('current_stage', '')
        message = progress.get('message', '处理中...')
        overall_progress = progress.get('overall_progress', 0)

        # 获取阶段显示名称
        stage_name = self.STAGE_NAMES.get(current_stage, current_stage)
        if stage_name:
            self.stage_label.setText(stage_name)
        else:
            self.stage_label.setText("正在准备...")

        # 如果消息为空或是默认消息，显示更友好的提示
        if not message or message == '处理中...':
            if status == 'analyzing':
                message = "正在调用AI分析，请耐心等待..."
            else:
                message = "正在初始化分析任务..."
        self.message_label.setText(message)
        self.progress_bar.setValue(overall_progress)

    def _on_status_error(self, error_msg: str):
        """处理状态查询错误"""
        # 静默处理错误，继续轮询
        pass

    def _on_cancel(self):
        """取消按钮点击"""
        if self._completed or self._cancelled:
            self.reject()
            return

        self._cancelled = True
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("正在取消...")
        self.message_label.setText("正在取消分析任务...")

        def cancel_analysis():
            return self.api_client.cancel_import_analysis(self.project_id)

        self._cancel_worker = AsyncAPIWorker(cancel_analysis)
        self._cancel_worker.success.connect(self._on_cancel_success)
        self._cancel_worker.error.connect(self._on_cancel_error)
        self._cancel_worker.start()

    def _on_cancel_success(self, data: dict):
        """取消成功"""
        self._stop_polling()
        self.stage_label.setText("分析已取消")
        self.message_label.setText("分析任务已被取消")
        self.cancel_btn.setText("关闭")
        self.cancel_btn.setEnabled(True)

    def _on_cancel_error(self, error_msg: str):
        """取消失败"""
        self.message_label.setText(f"取消失败: {error_msg}")
        self.cancel_btn.setText("关闭")
        self.cancel_btn.setEnabled(True)

    def _stop_polling(self):
        """停止轮询"""
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None

    def show(self):
        """显示对话框"""
        super().show()
        if self.spinner:
            self.spinner.start()

    def close(self):
        """关闭对话框"""
        self._stop_polling()
        if self.spinner:
            self.spinner.stop()
        super().close()

    def accept(self):
        """接受并关闭"""
        self._stop_polling()
        if self.spinner:
            self.spinner.stop()
        super().accept()

    def reject(self):
        """拒绝并关闭"""
        self._stop_polling()
        if self.spinner:
            self.spinner.stop()
        super().reject()

    def was_completed(self) -> bool:
        """是否完成"""
        return self._completed

    def was_cancelled(self) -> bool:
        """是否被取消"""
        return self._cancelled
