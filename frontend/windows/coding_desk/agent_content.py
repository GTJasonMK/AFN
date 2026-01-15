"""
Agent规划内容组件

从directory.py中提取的Agent目录规划功能，用于在助手面板中展示。
"""

import logging
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTextEdit, QCheckBox, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from utils.async_worker import AsyncAPIWorker
from utils.sse_worker import SSEWorker
from api.manager import APIClientManager
from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class AgentPlanningContent(ThemeAwareFrame):
    """Agent目录规划内容组件

    提供目录结构规划功能，包括：
    - 启动Agent规划
    - 显示Agent思考过程
    - 实时更新目录结构
    - 暂停/继续规划
    """

    # 信号
    structureUpdated = pyqtSignal(list, list)  # (directories, files) - 结构更新信号
    planningCompleted = pyqtSignal()  # 规划完成信号
    planningStarted = pyqtSignal()  # 规划开始信号
    refreshTreeRequested = pyqtSignal()  # 请求刷新目录树

    def __init__(self, project_id: str, parent=None):
        self.project_id = project_id
        self.api_client = APIClientManager.get_client()

        # 状态
        self._has_paused_state = False
        self._paused_state_info = {}
        self._detailed_mode = False
        self._is_running = False

        # Worker引用
        self._sse_worker: Optional[SSEWorker] = None
        self._workers: List[AsyncAPIWorker] = []

        # UI组件引用
        self.status_label = None
        self.output_text = None
        self.plan_btn = None
        self.optimize_btn = None
        self.continue_btn = None
        self.discard_btn = None
        self.stop_btn = None
        self.detailed_checkbox = None

        super().__init__(parent)
        self.setupUI()

        # 检查Agent状态
        if self.project_id:
            QTimer.singleShot(300, self._check_agent_state)

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(12))

        # 标题栏
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        title = QLabel("Agent 目录规划")
        title.setObjectName("agent_title")
        header.addWidget(title)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("status_label")
        header.addWidget(self.status_label)

        header.addStretch()

        # 详细模式开关
        self.detailed_checkbox = QCheckBox("详细模式")
        self.detailed_checkbox.setObjectName("detailed_checkbox")
        self.detailed_checkbox.setChecked(self._detailed_mode)
        self.detailed_checkbox.toggled.connect(self._on_detailed_mode_toggled)
        header.addWidget(self.detailed_checkbox)

        layout.addLayout(header)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(8))

        # Agent规划按钮
        self.plan_btn = QPushButton("规划整个项目")
        self.plan_btn.setObjectName("plan_btn")
        self.plan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plan_btn.clicked.connect(self._on_agent_plan)
        btn_layout.addWidget(self.plan_btn)

        # 仅优化目录按钮
        self.optimize_btn = QPushButton("仅优化目录")
        self.optimize_btn.setObjectName("optimize_btn")
        self.optimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.optimize_btn.clicked.connect(self._on_agent_optimize)
        self.optimize_btn.setVisible(False)
        btn_layout.addWidget(self.optimize_btn)

        # 继续规划按钮（有暂停状态时显示）
        self.continue_btn = QPushButton("继续规划")
        self.continue_btn.setObjectName("continue_btn")
        self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.continue_btn.clicked.connect(self._on_agent_continue)
        self.continue_btn.setVisible(False)
        btn_layout.addWidget(self.continue_btn)

        # 放弃按钮
        self.discard_btn = QPushButton("重新开始")
        self.discard_btn.setObjectName("discard_btn")
        self.discard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.discard_btn.clicked.connect(self._on_agent_discard)
        self.discard_btn.setVisible(False)
        btn_layout.addWidget(self.discard_btn)

        btn_layout.addStretch()

        # 停止按钮
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._on_agent_stop)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        # 输出区域
        self.output_text = QTextEdit()
        self.output_text.setObjectName("output_text")
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(dp(200))
        layout.addWidget(self.output_text, stretch=1)

        # 初始提示
        self._show_welcome_message()

    def _apply_theme(self):
        """应用主题"""
        bg_color = theme_manager.book_bg_secondary()

        self.setStyleSheet(f"""
            AgentPlanningContent {{
                background-color: {bg_color};
            }}
        """)

        # 标题
        title = self.findChild(QLabel, "agent_title")
        if title:
            title.setStyleSheet(f"""
                font-size: {dp(14)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            """)

        # 状态标签
        if self.status_label:
            self.status_label.setStyleSheet(f"""
                font-size: {dp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
                margin-left: {dp(8)}px;
            """)

        # 详细模式复选框
        if self.detailed_checkbox:
            self.detailed_checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {theme_manager.TEXT_SECONDARY};
                    font-size: {dp(11)}px;
                }}
                QCheckBox::indicator {{
                    width: {dp(14)}px;
                    height: {dp(14)}px;
                }}
                QCheckBox::indicator:unchecked {{
                    border: 1px solid {theme_manager.TEXT_TERTIARY};
                    border-radius: {dp(3)}px;
                    background-color: transparent;
                }}
                QCheckBox::indicator:checked {{
                    border: 1px solid {theme_manager.PRIMARY};
                    border-radius: {dp(3)}px;
                    background-color: {theme_manager.PRIMARY};
                }}
            """)

        # 按钮样式
        btn_style_primary = f"""
            QPushButton {{
                background-color: {theme_manager.SUCCESS};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(14)}px;
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.SUCCESS}DD;
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
        """

        btn_style_secondary = f"""
            QPushButton {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(14)}px;
                font-size: {dp(12)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY}DD;
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
        """

        btn_style_outline = f"""
            QPushButton {{
                background-color: transparent;
                color: {theme_manager.WARNING};
                border: 1px solid {theme_manager.WARNING};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.WARNING}10;
            }}
        """

        btn_style_stop = f"""
            QPushButton {{
                background-color: {theme_manager.WARNING};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(10)}px;
                font-size: {dp(11)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.WARNING}DD;
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.TEXT_TERTIARY};
            }}
        """

        if self.plan_btn:
            self.plan_btn.setStyleSheet(btn_style_primary)
        if self.optimize_btn:
            self.optimize_btn.setStyleSheet(btn_style_secondary)
        if self.continue_btn:
            self.continue_btn.setStyleSheet(btn_style_secondary)
        if self.discard_btn:
            self.discard_btn.setStyleSheet(btn_style_outline)
        if self.stop_btn:
            self.stop_btn.setStyleSheet(btn_style_stop)

        # 输出文本框
        if self.output_text:
            self.output_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {theme_manager.BG_PRIMARY};
                    color: {theme_manager.TEXT_PRIMARY};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(4)}px;
                    font-family: Consolas, 'Microsoft YaHei', monospace;
                    font-size: {dp(11)}px;
                    padding: {dp(8)}px;
                }}
            """)

    def _show_welcome_message(self):
        """显示欢迎信息"""
        self.output_text.clear()
        self._append_output(
            "[系统] Agent目录规划助手\n\n"
            "功能说明：\n"
            "- 规划整个项目：根据架构设计生成完整的目录结构\n"
            "- 仅优化目录：在现有目录基础上优化和完善\n\n"
            "规划过程中可以随时停止，进度会自动保存。\n",
            "info"
        )

    def _on_detailed_mode_toggled(self, checked: bool):
        """详细模式切换"""
        self._detailed_mode = checked
        mode_text = "详细模式已开启，将显示完整的思考和观察内容" if checked else "详细模式已关闭，内容将被截断显示"
        self._append_output(f"[系统] {mode_text}\n", "info")

    def _on_agent_plan(self):
        """开始Agent规划"""
        if not self.project_id:
            MessageService.show_warning(self, "请先保存项目")
            return

        logger.info(f"开始Agent规划: project_id={self.project_id}")

        # 启动规划
        self.output_text.clear()
        self.status_label.setText("正在连接...")
        self.plan_btn.setEnabled(False)
        self.optimize_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._is_running = True
        self.planningStarted.emit()

        # 启动SSE连接
        url = self.api_client.get_directory_plan_agent_url(self.project_id)
        self._sse_worker = SSEWorker(url, {"clear_existing": True})
        self._connect_sse_signals()
        self._sse_worker.start()

    def _on_agent_optimize(self):
        """仅优化现有目录结构"""
        if not self.project_id:
            MessageService.show_warning(self, "请先保存项目")
            return

        logger.info(f"开始优化目录结构: project_id={self.project_id}")

        self.output_text.clear()
        self.status_label.setText("正在连接...")
        self.plan_btn.setEnabled(False)
        self.optimize_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._is_running = True
        self.planningStarted.emit()

        self._append_output("[系统] 从现有目录结构开始优化...\n", "info")

        url = self.api_client.get_directory_plan_agent_url(self.project_id)
        self._sse_worker = SSEWorker(url, {"clear_existing": False})
        self._connect_sse_signals()
        self._sse_worker.start()

    def _on_agent_continue(self):
        """继续规划"""
        if not self.project_id:
            return

        logger.info(f"继续Agent规划: project_id={self.project_id}")

        self.output_text.clear()
        self.status_label.setText("正在恢复...")
        self.continue_btn.setEnabled(False)
        self.discard_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._is_running = True
        self.planningStarted.emit()

        self._append_output("[系统] 正在从上次中断处继续...\n", "info")

        url = self.api_client.get_directory_plan_agent_url(self.project_id)
        self._sse_worker = SSEWorker(url, {"resume": True})
        self._connect_sse_signals()
        self._sse_worker.start()

    def _on_agent_stop(self):
        """停止Agent"""
        if not self.project_id:
            return

        self._append_output("\n[系统] 正在保存进度...\n", "info")
        self.stop_btn.setEnabled(False)

        worker = AsyncAPIWorker(
            self.api_client.pause_directory_agent,
            self.project_id,
            "用户手动停止"
        )
        worker.success.connect(self._on_agent_pause_success)
        worker.error.connect(self._on_agent_pause_error)
        self._workers.append(worker)
        worker.start()

    def _on_agent_pause_success(self, result):
        """暂停成功"""
        if self._sse_worker:
            self._sse_worker.stop()
            self._sse_worker = None

        self.status_label.setText("已暂停")
        self._is_running = False

        total_dirs = result.get('total_directories', 0)
        total_files = result.get('total_files', 0)
        phase = result.get('current_phase', '')

        self._append_output(
            f"\n[系统] 进度已保存 ({total_dirs}目录/{total_files}文件)\n",
            "success"
        )
        self._append_output("[系统] 可以稍后点击「继续规划」继续\n", "info")

        self._enable_buttons()

        self._has_paused_state = True
        self._paused_state_info = {
            'has_paused_state': True,
            'current_phase': phase,
            'total_directories': total_dirs,
            'total_files': total_files,
        }
        self._update_buttons_for_state()

    def _on_agent_pause_error(self, error_msg: str):
        """暂停失败"""
        logger.warning(f"暂停Agent失败: {error_msg}")

        if self._sse_worker:
            self._sse_worker.stop()
            self._sse_worker = None

        self.status_label.setText("已停止(未保存)")
        self._is_running = False
        self._append_output(f"\n[警告] 保存进度失败: {error_msg}\n", "warning")
        self._append_output("[系统] 连接已断开，进度可能丢失\n", "warning")

        self._enable_buttons()
        QTimer.singleShot(500, self._check_agent_state)

    def _on_agent_discard(self):
        """放弃暂停状态，重新开始"""
        from PyQt6.QtWidgets import QDialog
        from components.dialogs import ConfirmDialog

        dialog = ConfirmDialog(
            self,
            title="放弃已有进度",
            message="确定要放弃已有的规划进度吗？\n\n这将删除保存的状态，您需要重新开始规划。",
            confirm_text="确定放弃",
            cancel_text="取消"
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        logger.info(f"放弃Agent状态: project_id={self.project_id}")

        worker = AsyncAPIWorker(
            self.api_client.clear_directory_agent_state,
            self.project_id
        )
        worker.success.connect(self._on_agent_state_cleared)
        worker.error.connect(lambda e: MessageService.show_error(self, f"清除状态失败: {e}"))
        self._workers.append(worker)
        worker.start()

    def _on_agent_state_cleared(self, result):
        """Agent状态已清除"""
        logger.info("Agent状态已清除")
        self._has_paused_state = False
        self._paused_state_info = {}
        self._update_buttons_for_state()
        MessageService.show_success(self, "已清除保存的进度，可以重新开始规划")

    def _connect_sse_signals(self):
        """连接SSE信号"""
        if not self._sse_worker:
            return
        self._sse_worker.progress_received.connect(self._on_progress_received)
        self._sse_worker.complete.connect(self._on_complete_received)
        self._sse_worker.event_received.connect(self._on_agent_event)
        self._sse_worker.error.connect(self._on_agent_error)
        self._sse_worker.finished.connect(self._on_agent_finished)

    def _on_progress_received(self, data: dict):
        """处理progress信号"""
        self._on_agent_event("progress", data)

    def _on_complete_received(self, data: dict):
        """处理complete信号"""
        self._on_agent_event("complete", data)

    def _on_agent_event(self, event_type: str, data: dict):
        """处理Agent事件"""
        logger.debug("[Agent事件] type=%s, keys=%s", event_type, list(data.keys()) if data else [])

        # 阶段变化
        if event_type == "phase":
            phase = data.get("phase", "")
            message = data.get("message", "")
            phase_names = {
                "gathering": "信息收集",
                "analyzing": "结构分析",
                "optimizing": "优化中",
                "finalizing": "最终验证",
            }
            phase_name = phase_names.get(phase, phase)
            self.status_label.setText(phase_name)
            self._append_output(f"\n{'='*40}\n", "phase")
            self._append_output(f"[阶段] {message}\n", "phase")

        # Agent思考过程
        elif event_type == "thought":
            iteration = data.get("iteration", 0)
            thought = data.get("thought", "")
            thought_type = data.get("type", "reasoning")

            if thought_type == "reasoning":
                if self._detailed_mode:
                    display_thought = thought
                else:
                    display_thought = thought[:300] + "..." if len(thought) > 300 else thought
                self._append_output(f"[思考#{iteration}] {display_thought}\n", "thinking")
            elif thought_type == "conclusion":
                self._append_output(f"[结论] {thought}\n", "success")

        # Agent反思
        elif event_type == "reflection":
            iteration = data.get("iteration", 0)
            message = data.get("message", "")
            self._append_output(f"\n[反思#{iteration}] {message}\n", "warning")

        # 信息收集
        elif event_type == "info_gathered":
            tool = data.get("tool", "")
            reason = data.get("reason", "")
            success = data.get("success", False)
            round_num = data.get("round", 1)

            status = "成功" if success else "失败"
            tool_display = tool.replace("get_", "").replace("_", " ").title()
            self._append_output(f"[收集#{round_num}] {tool_display}: {status}\n", "info")
            if reason and self._detailed_mode:
                self._append_output(f"  原因: {reason}\n", "thinking")

        # 信息收集完成
        elif event_type == "gathering_complete":
            items = data.get("items_collected", 0)
            types = data.get("collected_types", [])
            self._append_output(f"[收集完成] 共收集 {items} 项信息\n", "success")
            if types and self._detailed_mode:
                type_list = ", ".join([t.replace("get_", "") for t in types])
                self._append_output(f"  类型: {type_list}\n", "info")

        # 分析结果
        elif event_type == "analysis":
            coverage = data.get("coverage_rate", 0) * 100
            issues = data.get("total_issues", 0)
            missing = data.get("missing_modules", [])
            self._append_output(f"[分析结果] 覆盖率: {coverage:.1f}%, 问题数: {issues}\n", "info")
            if missing:
                self._append_output(f"[分析结果] 未覆盖模块: {missing[:10]}\n", "warning")

        # 工具执行
        elif event_type == "action":
            iteration = data.get("iteration", 0)
            tool = data.get("tool", "")
            reasoning = data.get("reasoning", "")

            tool_display = tool.replace("_", " ").title()
            self._append_output(f"[动作#{iteration}] {tool_display}\n", "action")
            if reasoning and self._detailed_mode:
                self._append_output(f"  理由: {reasoning}\n", "info")

        # 进度
        elif event_type == "progress":
            stage = data.get("stage", "")
            message = data.get("message", "")

            stage_names = {
                "phase1": "第一阶段：生成目录结构",
                "phase1_complete": "第一阶段完成",
                "phase2": "第二阶段：优化结构",
                "phase2_complete": "第二阶段完成",
                "saving": "保存到数据库",
                "resuming": "正在恢复",
            }
            stage_name = stage_names.get(stage, stage)
            self.status_label.setText(stage_name)
            self._append_output(f"[进度] {message}\n", "phase")

            if "coverage_rate" in data:
                coverage = data.get("coverage_rate", 0) * 100
                self._append_output(f"[统计] 模块覆盖率: {coverage:.1f}%\n", "info")
            if "total_directories" in data:
                dirs = data.get("total_directories", 0)
                files = data.get("total_files", 0)
                self._append_output(f"[统计] 目录: {dirs}, 文件: {files}\n", "info")

        # 状态已保存
        elif event_type == "state_saved":
            message = data.get("message", "状态已保存")
            self._append_output(f"[保存] {message}\n", "success")

        # 结构生成完成
        elif event_type == "structure":
            dirs = len(data.get("directories", []))
            files = len(data.get("files", []))
            shared = data.get("shared_modules", [])
            self._append_output(f"\n[结构] 生成了 {dirs} 个目录和 {files} 个文件\n", "success")
            if shared:
                self._append_output(f"[结构] 共享模块: {', '.join(shared)}\n", "info")
            self.refreshTreeRequested.emit()

        # 实时结构更新
        elif event_type == "structure_update":
            logger.info("[Agent事件] 处理structure_update事件")

            directories = data.get("directories", [])
            files = data.get("files", [])
            stats = data.get("stats", {})

            dirs_count = stats.get("total_directories", len(directories))
            files_count = stats.get("total_files", len(files))
            covered = stats.get("covered_modules", 0)
            total = stats.get("total_modules", 0)

            coverage_pct = (covered / total * 100) if total > 0 else 0
            self._append_output(
                f"[结构更新] 目录: {dirs_count}, 文件: {files_count}, 覆盖率: {coverage_pct:.0f}%\n",
                "info"
            )

            # 发送结构更新信号
            self.structureUpdated.emit(directories, files)

        # 完成
        elif event_type == "complete":
            self.status_label.setText("规划完成")
            dirs = data.get("directories_created", 0)
            files = data.get("files_created", 0)
            coverage = data.get("coverage_rate", 0) * 100
            message = data.get("message", "")
            self._append_output(f"\n[完成] {message}\n", "success")
            self._append_output(f"[统计] 保存了 {dirs} 个目录和 {files} 个文件，覆盖率 {coverage:.1f}%\n", "success")
            self.stop_btn.setEnabled(False)
            self.refreshTreeRequested.emit()
            self.planningCompleted.emit()

        # 错误
        elif event_type == "error":
            error_msg = data.get("message", "未知错误")
            stage = data.get("stage", "")
            self.status_label.setText("发生错误")
            self._append_output(f"\n[错误] {error_msg}\n", "error")
            if stage:
                self._append_output(f"[错误] 发生在: {stage}\n", "error")
            self.stop_btn.setEnabled(False)

    def _on_agent_error(self, error_msg: str):
        """Agent错误处理"""
        logger.error(f"Agent SSE错误: {error_msg}")
        self.status_label.setText("连接错误")
        self._append_output(f"\n[错误] 连接失败: {error_msg}\n", "error")
        self._enable_buttons()
        self._is_running = False

    def _on_agent_finished(self):
        """Agent完成处理"""
        logger.info("Agent规划流程结束")
        self._enable_buttons()
        self._is_running = False
        self.refreshTreeRequested.emit()
        self._check_agent_state()

    def _enable_buttons(self):
        """重新启用按钮"""
        self.plan_btn.setEnabled(True)
        self.optimize_btn.setEnabled(True)
        self.continue_btn.setEnabled(True)
        self.discard_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _check_agent_state(self):
        """检查是否有暂停的Agent状态"""
        if not self.project_id:
            self._has_paused_state = False
            self._paused_state_info = {}
            self._update_buttons_for_state()
            return

        worker = AsyncAPIWorker(
            self.api_client.get_directory_agent_state,
            self.project_id
        )
        worker.success.connect(self._on_agent_state_loaded)
        worker.error.connect(lambda e: logger.warning(f"检查Agent状态失败: {e}"))
        self._workers.append(worker)
        worker.start()

    def _on_agent_state_loaded(self, result):
        """Agent状态加载完成"""
        self._has_paused_state = result.get('has_paused_state', False)
        self._paused_state_info = result

        if self._has_paused_state:
            logger.info(
                "检测到暂停的Agent状态: phase=%s, dirs=%d, files=%d",
                result.get('current_phase', ''),
                result.get('total_directories', 0),
                result.get('total_files', 0)
            )

        self._update_buttons_for_state()

    def _update_buttons_for_state(self):
        """根据Agent状态更新按钮显示"""
        if self._has_paused_state:
            self.continue_btn.setVisible(True)
            self.discard_btn.setVisible(True)
            self.plan_btn.setVisible(False)
            self.optimize_btn.setVisible(False)

            dirs = self._paused_state_info.get('total_directories', 0)
            files = self._paused_state_info.get('total_files', 0)
            if dirs > 0 or files > 0:
                self.continue_btn.setText(f"继续规划 ({dirs}目录/{files}文件)")
            else:
                self.continue_btn.setText("继续规划")
        else:
            self.continue_btn.setVisible(False)
            self.discard_btn.setVisible(False)
            self.plan_btn.setVisible(True)
            self.optimize_btn.setVisible(True)

    def set_has_directories(self, has_directories: bool):
        """设置是否有目录结构（用于显示优化按钮）"""
        if not self._has_paused_state:
            self.optimize_btn.setVisible(has_directories)

    def _append_output(self, text: str, style: str = "normal"):
        """追加输出，带样式"""
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        color_map = {
            "info": theme_manager.TEXT_SECONDARY,
            "phase": theme_manager.PRIMARY,
            "thinking": theme_manager.TEXT_TERTIARY,
            "action": theme_manager.WARNING,
            "observation": theme_manager.TEXT_SECONDARY,
            "directory": theme_manager.SUCCESS,
            "file": theme_manager.SUCCESS,
            "success": theme_manager.SUCCESS,
            "warning": theme_manager.WARNING,
            "error": theme_manager.ERROR,
            "normal": theme_manager.TEXT_PRIMARY,
        }
        color = color_map.get(style, theme_manager.TEXT_PRIMARY)

        html_text = text.replace('\n', '<br>')
        cursor.insertHtml(f'<span style="color: {color};">{html_text}</span>')

        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum()
        )

    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running

    def cleanup(self):
        """清理资源"""
        if self._sse_worker:
            try:
                self._sse_worker.stop()
            except Exception:
                pass
            self._sse_worker = None

        for worker in self._workers:
            try:
                if worker.isRunning():
                    worker.cancel()
            except Exception:
                pass
        self._workers.clear()


__all__ = ["AgentPlanningContent"]
