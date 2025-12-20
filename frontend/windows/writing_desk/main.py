"""
写作台主类

集成Header、Sidebar、Workspace，提供完整的章节写作功能
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QSizePolicy
)
from pages.base_page import BasePage
from api.manager import APIClientManager
from components.dialogs import LoadingDialog
from utils.async_worker import AsyncAPIWorker
from utils.sse_worker import SSEWorker
from utils.constants import WorkerTimeouts
from utils.worker_manager import WorkerManager
from utils.error_handler import handle_errors
from utils.message_service import MessageService, confirm
from utils.dpi_utils import dp, sp
from utils.chapter_error_formatter import format_chapter_error
from themes.theme_manager import theme_manager

from .header import WDHeader
from .sidebar import WDSidebar
from .workspace import WDWorkspace
from .assistant_panel import AssistantPanel
from .prompt_preview_dialog import PromptPreviewDialog

logger = logging.getLogger(__name__)


class WritingDesk(BasePage):
    """写作台页面 - 禅意风格"""

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id

        self.api_client = APIClientManager.get_client()
        self.project = None
        self.selected_chapter_number = None
        self.generating_chapter = None

        # 异步任务管理 - 使用 WorkerManager 统一管理
        self.worker_manager = WorkerManager(self)
        self._sse_worker = None  # SSE Worker 单独管理（需要特殊的 stop 方法）
        self._progress_dialog = None  # 进度对话框

        self.setupUI()
        self.loadProject()

    def setupUI(self):
        """初始化UI"""
        logger.info("WritingDesk.setupUI 被调用")
        # 如果布局不存在，创建UI结构
        if not self.layout():
            logger.info("布局不存在，调用 _create_ui_structure")
            self._create_ui_structure()
        else:
            logger.info("布局已存在，跳过 _create_ui_structure")
        # 总是应用主题样式
        logger.info("应用主题样式")
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        logger.info("WritingDesk._create_ui_structure 开始执行")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self.header = WDHeader()
        main_layout.addWidget(self.header)

        # 主内容区
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        content_layout.setSpacing(dp(12))

        # Sidebar（固定宽度）
        self.sidebar = WDSidebar()
        content_layout.addWidget(self.sidebar)

        # Workspace（占据剩余空间）
        self.workspace = WDWorkspace()
        self.workspace.setProjectId(self.project_id)
        # 不设置最小宽度，让 Qt 布局系统自动分配空间
        # 设置 Workspace 水平方向可扩展
        self.workspace.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout.addWidget(self.workspace, stretch=1)

        # RAG Assistant Panel（固定宽度，初始隐藏）
        self.assistant_panel = AssistantPanel(self.project_id)
        # 使用 setFixedWidth 确保宽度固定（内部同时设置 min 和 max）
        # 320dp 宽度确保在大多数窗口尺寸下不会与 workspace 重叠
        self.assistant_panel.setFixedWidth(dp(320))
        self.assistant_panel.setVisible(False)
        content_layout.addWidget(self.assistant_panel, stretch=0)

        main_layout.addWidget(self.content_widget, stretch=1)

        # 统一连接所有信号
        self._connect_signals()

    def _connect_signals(self):
        """统一管理所有信号连接

        将所有信号连接集中在此方法中，便于追踪和维护。
        按组件分类组织，提高可读性。
        """
        # Header 信号
        self.header.goBackClicked.connect(self.goBackToWorkspace)
        self.header.viewDetailClicked.connect(self.openProjectDetail)
        self.header.exportClicked.connect(self.exportNovel)
        self.header.toggleAssistantClicked.connect(self.toggleAssistant)

        # Sidebar 信号
        self.sidebar.chapterSelected.connect(self.onChapterSelected)
        self.sidebar.generateChapter.connect(self.onGenerateChapter)
        self.sidebar.generateOutline.connect(self.onGenerateOutline)

        # Workspace 信号
        self.workspace.generateChapterRequested.connect(self.onGenerateChapter)
        self.workspace.previewPromptRequested.connect(self.onPreviewPrompt)
        self.workspace.saveContentRequested.connect(self.onSaveContent)
        self.workspace.ragIngestRequested.connect(self.onRagIngest)
        self.workspace.selectVersion.connect(self.onSelectVersion)
        self.workspace.evaluateChapter.connect(self.onEvaluateChapter)
        self.workspace.retryVersion.connect(self.onRetryVersion)
        self.workspace.editContent.connect(self.onEditContent)
        self.workspace.chapterContentLoaded.connect(self.onChapterContentLoaded)

        # Assistant Panel 信号
        self.assistant_panel.suggestion_applied.connect(self.onSuggestionApplied)

    def toggleAssistant(self, show: bool):
        """切换RAG助手显示状态"""
        self.assistant_panel.setVisible(show)
        # 由于assistant_panel使用固定宽度，splitter会自动处理布局

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格"""
        # 使用 theme_manager 的书香风格便捷方法，而非硬编码颜色
        bg_color = theme_manager.book_bg_primary()

        # 主窗口背景
        self.setStyleSheet(f"""
            WritingDesk {{
                background-color: {bg_color};
            }}
        """)

        if hasattr(self, 'content_widget'):
            self.content_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: transparent;
                }}
            """)

    def loadProject(self):
        """加载项目数据（异步非阻塞）"""
        logger.info(f"WritingDesk.loadProject被调用, project_id={self.project_id}")

        # 使用异步worker加载项目，避免阻塞UI线程
        worker = AsyncAPIWorker(self.api_client.get_novel, self.project_id)
        worker.success.connect(self._onProjectLoaded)
        worker.error.connect(self._onProjectLoadError)

        # 使用 WorkerManager 启动
        self.worker_manager.start(worker, 'load_project')

    def _onProjectLoaded(self, project_data):
        """项目数据加载成功回调"""
        self.project = project_data

        logger.info("项目数据加载成功")
        logger.info(f"项目键: {list(self.project.keys()) if isinstance(self.project, dict) else 'NOT A DICT'}")

        blueprint = self.project.get('blueprint', {})
        if blueprint:
            chapter_outline = blueprint.get('chapter_outline', [])
            logger.info(f"blueprint.chapter_outline数量: {len(chapter_outline)}")
        else:
            logger.warning("blueprint不存在")

        logger.info("调用 header.setProject")
        self.header.setProject(self.project)

        logger.info("调用 sidebar.setProject")
        self.sidebar.setProject(self.project)

    def _onProjectLoadError(self, error_msg):
        """项目数据加载失败回调"""
        logger.error(f"项目加载失败: {error_msg}")
        MessageService.show_error(self, f"加载项目失败：\n\n{error_msg}", "错误")

    def onChapterSelected(self, chapter_number):
        """章节被选中"""
        self.selected_chapter_number = chapter_number
        self.workspace.loadChapter(chapter_number)

    def onChapterContentLoaded(self, chapter_number: int, content: str):
        """章节内容加载完成 - 更新优化面板"""
        if self.assistant_panel:
            self.assistant_panel.set_chapter_for_optimization(chapter_number, content)

    def onSuggestionApplied(self, suggestion: dict):
        """处理修改建议被应用 - 在正文编辑器中高亮显示修改"""
        if self.workspace:
            self.workspace.applySuggestion(suggestion)

    def onGenerateChapter(self, chapter_number):
        """生成章节 - 使用SSE流式进度显示"""
        # 防止快速点击导致多个生成任务同时运行
        if self.generating_chapter is not None:
            MessageService.show_warning(
                self,
                f"正在生成第{self.generating_chapter}章，请等待完成后再生成其他章节",
                "提示"
            )
            return

        if not confirm(
            self,
            f"确定要生成第{chapter_number}章吗？\n\n生成过程可能需要 1-3 分钟。",
            "确认生成"
        ):
            return

        # 询问用户输入写作提示词（可选）
        from components.dialogs import TextInputDialog
        writing_notes, ok = TextInputDialog.getTextStatic(
            parent=self,
            title="写作指导",
            label=f"请输入第{chapter_number}章的写作指导（可选）：\n\n"
                  "留空则按大纲设定生成，填写后会影响RAG检索和生成内容。",
            placeholder="示例：注重环境描写、加强悬疑氛围、增加角色对话、突出心理变化..."
        )

        if not ok:
            return

        # 标记正在生成的章节
        self.generating_chapter = chapter_number
        self.sidebar.setGeneratingChapter(chapter_number)

        # 显示进度对话框
        progress_title = f"生成第{chapter_number}章"
        self._progress_dialog = LoadingDialog(
            parent=self,
            title=progress_title,
            message="正在初始化...",
            cancelable=True
        )
        self._progress_dialog.rejected.connect(self._on_chapter_gen_cancelled)
        self._progress_dialog.show()

        # 使用SSEWorker连接流式端点
        url = f"{self.api_client.base_url}/api/writer/novels/{self.project_id}/chapters/generate-stream"
        payload = {"chapter_number": chapter_number}
        # 添加写作提示词（如果有）
        if writing_notes and writing_notes.strip():
            payload["writing_notes"] = writing_notes.strip()

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.progress_received.connect(self._on_chapter_gen_progress)
        self._sse_worker.complete.connect(self._on_chapter_gen_complete)
        self._sse_worker.cancelled.connect(self._on_chapter_gen_cancelled_by_server)
        self._sse_worker.error.connect(self._on_chapter_gen_error)
        self._sse_worker.start()

    def _on_chapter_gen_progress(self, data: dict):
        """处理章节生成进度更新"""
        if not self._progress_dialog:
            return

        stage = data.get('stage', '')
        message = data.get('message', '')
        current = data.get('current', 0)
        total = data.get('total', 0)

        # 根据阶段显示不同的进度信息
        stage_labels = {
            'initializing': '初始化',
            'collecting_context': '收集上下文',
            'preparing_prompt': '准备提示词',
            'generating': '生成内容',
            'saving': '保存结果'
        }

        stage_label = stage_labels.get(stage, stage)
        if total > 0:
            progress_text = f"[{stage_label}] {message}"
        else:
            progress_text = f"[{stage_label}] {message}"

        self._progress_dialog.setMessage(progress_text)

    def _on_chapter_gen_complete(self, data: dict):
        """章节生成完成"""
        chapter_number = self.generating_chapter
        self._cleanup_chapter_gen_sse()

        message = data.get('message', '生成完成')
        version_count = data.get('version_count', 0)

        logger.info(f"章节生成完成: {message}, 版本数: {version_count}")
        MessageService.show_operation_success(self, message)

        # 重新加载项目数据
        self.loadProject()

        # 如果当前正停留在该章节，刷新显示
        if self.selected_chapter_number == chapter_number:
            self.workspace.loadChapter(chapter_number)

    def _on_chapter_gen_error(self, error_msg: str):
        """章节生成错误

        根据错误消息内容提供更有用的用户反馈。
        """
        chapter_number = self.generating_chapter
        self._cleanup_chapter_gen_sse()
        logger.error(f"章节生成失败: {error_msg}")

        # 使用工具函数格式化错误消息
        title, message = format_chapter_error(error_msg, chapter_number)
        MessageService.show_error(self, message, title)

    def _on_chapter_gen_cancelled(self):
        """用户取消章节生成（点击取消按钮）"""
        logger.info("用户取消章节生成")
        self._cleanup_chapter_gen_sse()

    def _on_chapter_gen_cancelled_by_server(self, data: dict):
        """服务器确认章节生成已取消"""
        logger.info("服务器确认章节生成已取消: %s", data.get('message', ''))
        self._cleanup_chapter_gen_sse()

    def _cleanup_chapter_gen_sse(self):
        """清理章节生成SSE相关资源"""
        self.generating_chapter = None
        self.sidebar.clearGeneratingState()

        if self._sse_worker:
            # SSEWorker.stop() 已经断开信号并关闭连接，无需 blockSignals
            self._sse_worker.stop()
            if self._sse_worker.isRunning():
                self._sse_worker.quit()
                self._sse_worker.wait(WorkerTimeouts.DEFAULT_MS)
            self._sse_worker = None

        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def onPreviewPrompt(self, chapter_number):
        """预览章节生成的提示词（用于测试RAG效果）"""
        from components.dialogs import TextInputDialog
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QButtonGroup, QPushButton, QTextEdit
        from themes.theme_manager import theme_manager
        from themes import ButtonStyles

        # 创建选项对话框
        options_dialog = QDialog(self)
        options_dialog.setWindowTitle("预览提示词选项")
        options_dialog.setMinimumWidth(dp(450))

        # 设置对话框背景色
        options_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(options_dialog)
        layout.setSpacing(dp(16))
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))

        # 模式选择
        ui_font = theme_manager.ui_font()
        mode_label = QLabel("选择预览模式：")
        mode_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        layout.addWidget(mode_label)

        mode_group = QButtonGroup(options_dialog)

        # 单选按钮样式
        radio_style = f"""
            QRadioButton {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_PRIMARY};
                spacing: {dp(8)}px;
            }}
            QRadioButton::indicator {{
                width: {dp(18)}px;
                height: {dp(18)}px;
                border: 2px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(9)}px;
                background-color: {theme_manager.BG_SECONDARY};
            }}
            QRadioButton::indicator:checked {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY};
            }}
        """

        first_gen_radio = QRadioButton("首次生成 - 完整提示词（包含分层前情摘要）")
        first_gen_radio.setChecked(True)
        first_gen_radio.setStyleSheet(radio_style)
        mode_group.addButton(first_gen_radio, 0)
        layout.addWidget(first_gen_radio)

        retry_radio = QRadioButton("重新生成 - 简化提示词（不含完整前情摘要）")
        retry_radio.setStyleSheet(radio_style)
        mode_group.addButton(retry_radio, 1)
        layout.addWidget(retry_radio)

        # 写作备注/优化方向
        notes_label = QLabel("写作备注/优化方向（可选）：")
        notes_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(14)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
            margin-top: {dp(8)}px;
        """)
        layout.addWidget(notes_label)

        notes_hint = QLabel("留空则使用默认设置，填写后会影响RAG查询和提示词内容")
        notes_hint.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(12)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(notes_hint)

        notes_input = QTextEdit()
        notes_input.setPlaceholderText("示例：增加心理描写、加快节奏、强化角色冲突...")
        notes_input.setMaximumHeight(dp(80))
        notes_input.setStyleSheet(f"""
            QTextEdit {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px;
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            QTextEdit:focus {{
                border-color: {theme_manager.PRIMARY};
            }}
        """)
        layout.addWidget(notes_input)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(ButtonStyles.secondary())
        cancel_btn.clicked.connect(options_dialog.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("预览提示词")
        confirm_btn.setStyleSheet(ButtonStyles.primary())
        confirm_btn.clicked.connect(options_dialog.accept)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

        # 显示对话框
        if options_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # 获取选项
        is_retry = mode_group.checkedId() == 1
        writing_notes = notes_input.toPlainText().strip() or None

        # 显示加载动画
        mode_text = "重新生成" if is_retry else "首次生成"
        self.show_loading(f"正在构建第{chapter_number}章的提示词（{mode_text}模式）...")

        # 创建异步工作线程并通过 WorkerManager 管理
        worker = AsyncAPIWorker(
            self.api_client.preview_chapter_prompt,
            self.project_id,
            chapter_number,
            writing_notes,
            is_retry
        )
        worker.success.connect(
            lambda result: self.onPreviewPromptSuccess(result, chapter_number, is_retry)
        )
        worker.error.connect(self.onPreviewPromptError)

        # 使用 WorkerManager 启动（自动管理生命周期）
        self.worker_manager.start(worker, 'preview')

    def onPreviewPromptSuccess(self, result, chapter_number, is_retry=False):
        """提示词预览成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        # 显示预览对话框
        dialog = PromptPreviewDialog(result, chapter_number, is_retry=is_retry, parent=self)
        dialog.exec()

    def onPreviewPromptError(self, error_msg):
        """提示词预览失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_error(self, f"预览提示词失败：\n\n{error_msg}", "错误")

    def onGenerateOutline(self):
        """跳转到项目详情的章节大纲页面"""
        self.navigateTo('DETAIL', project_id=self.project_id, section='chapter_outline')

    def onSaveContent(self, chapter_number, content):
        """保存章节内容到后端（异步非阻塞）"""
        # 显示保存中提示
        self.show_loading(f"正在保存第{chapter_number}章内容...")

        # 创建异步工作线程并通过 WorkerManager 管理
        worker = AsyncAPIWorker(
            self.api_client.update_chapter,
            self.project_id,
            chapter_number,
            content
        )
        worker.success.connect(
            lambda r: self.onSaveContentSuccess(chapter_number)
        )
        worker.error.connect(self.onSaveContentError)

        # 使用 WorkerManager 启动
        self.worker_manager.start(worker, 'save_content')

    def onSaveContentSuccess(self, chapter_number):
        """保存成功回调"""
        self.hide_loading()

        # 使用对话框显示保存成功（更明显）
        from components.dialogs import AlertDialog
        dialog = AlertDialog(
            parent=self,
            title="保存成功",
            message=f"第{chapter_number}章内容已成功保存",
            button_text="确定",
            dialog_type="success"
        )
        dialog.exec()

    def onSaveContentError(self, error_msg):
        """保存失败回调"""
        self.hide_loading()

        # 使用对话框显示保存失败
        from components.dialogs import AlertDialog
        dialog = AlertDialog(
            parent=self,
            title="保存失败",
            message=f"保存章节内容时出错：{error_msg}",
            button_text="确定",
            dialog_type="error"
        )
        dialog.exec()

    def onRagIngest(self, chapter_number, content):
        """RAG入库 - 保存章节内容并执行完整RAG处理（异步非阻塞）

        RAG处理包括：生成摘要、分析角色状态和伏笔、更新索引、向量入库
        """
        # 显示处理中提示
        self.show_loading(f"正在处理第{chapter_number}章RAG入库...\n（包括摘要生成、分析、索引、向量入库）")

        # 创建异步工作线程并通过 WorkerManager 管理
        worker = AsyncAPIWorker(
            self.api_client.update_chapter,
            self.project_id,
            chapter_number,
            content,
            trigger_rag=True  # 触发RAG处理
        )
        worker.success.connect(
            lambda r: self.onRagIngestSuccess(chapter_number)
        )
        worker.error.connect(self.onRagIngestError)

        # 使用 WorkerManager 启动
        self.worker_manager.start(worker, 'rag_ingest')

    def onRagIngestSuccess(self, chapter_number):
        """RAG入库成功回调"""
        self.hide_loading()

        # 使用对话框显示成功
        from components.dialogs import AlertDialog
        dialog = AlertDialog(
            parent=self,
            title="RAG入库完成",
            message=f"第{chapter_number}章已完成RAG处理：\n\n"
                    "- 章节内容已保存\n"
                    "- 摘要已生成\n"
                    "- 角色状态和伏笔已分析\n"
                    "- 索引已更新\n"
                    "- 向量库已同步",
            button_text="确定",
            dialog_type="success"
        )
        dialog.exec()

        # 重新加载项目数据以更新显示
        self.loadProject()

    def onRagIngestError(self, error_msg):
        """RAG入库失败回调"""
        self.hide_loading()

        # 使用对话框显示失败
        from components.dialogs import AlertDialog
        dialog = AlertDialog(
            parent=self,
            title="RAG入库失败",
            message=f"处理第{self.selected_chapter_number}章RAG入库时出错：\n\n{error_msg}",
            button_text="确定",
            dialog_type="error"
        )
        dialog.exec()

    def onSelectVersion(self, version_index):
        """选择版本（异步非阻塞版本）"""
        if self.selected_chapter_number is None:
            return

        # 显示加载动画
        self.show_loading(f"正在确认第{self.selected_chapter_number}章版本{version_index + 1}...")

        # 创建异步工作线程并通过 WorkerManager 管理
        worker = AsyncAPIWorker(
            self.api_client.select_chapter_version,
            self.project_id,
            self.selected_chapter_number,
            version_index
        )
        worker.success.connect(lambda r: self.onSelectVersionSuccess(r, version_index))
        worker.error.connect(self.onSelectVersionError)

        # 使用 WorkerManager 启动
        self.worker_manager.start(worker, 'select_version')

    def onSelectVersionSuccess(self, result, version_index):
        """版本选择成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_success(self, "版本已确认！")

        # 重新加载
        self.loadProject()
        if self.selected_chapter_number:
            self.workspace.loadChapter(self.selected_chapter_number)

    def onSelectVersionError(self, error_msg):
        """版本选择失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_error(self, f"选择版本失败：\n\n{error_msg}", "错误")

    def onEvaluateChapter(self):
        """评审章节（异步非阻塞版本）"""
        if self.selected_chapter_number is None:
            return

        # 显示加载动画
        self.show_loading(f"正在评审第{self.selected_chapter_number}章...")

        # 创建异步工作线程并通过 WorkerManager 管理
        worker = AsyncAPIWorker(
            self.api_client.evaluate_chapter,
            self.project_id,
            self.selected_chapter_number
        )
        worker.success.connect(self.onEvaluateSuccess)
        worker.error.connect(self.onEvaluateError)

        # 使用 WorkerManager 启动
        self.worker_manager.start(worker, 'evaluate')

    def onEvaluateSuccess(self, result):
        """章节评审成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_success(self, "评审完成！")

        # 重新加载
        self.loadProject()
        if self.selected_chapter_number:
            self.workspace.loadChapter(self.selected_chapter_number)

    def onEvaluateError(self, error_msg):
        """章节评审失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_error(self, f"评审失败：\n\n{error_msg}", "错误")

    def onEditContent(self, new_content):
        """编辑章节内容（异步非阻塞版本）"""
        if self.selected_chapter_number is None:
            return

        # 显示加载动画
        self.show_loading(f"正在保存第{self.selected_chapter_number}章内容...")

        # 创建异步工作线程并通过 WorkerManager 管理
        worker = AsyncAPIWorker(
            self.api_client.update_chapter,
            self.project_id,
            self.selected_chapter_number,
            new_content
        )
        worker.success.connect(self.onEditContentSuccess)
        worker.error.connect(self.onEditContentError)

        # 使用 WorkerManager 启动
        self.worker_manager.start(worker, 'edit_content')

    def onEditContentSuccess(self, result):
        """编辑内容成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_success(self, "内容已保存！")

        # 重新加载
        self.loadProject()
        if self.selected_chapter_number:
            self.workspace.loadChapter(self.selected_chapter_number)

    def onEditContentError(self, error_msg):
        """编辑内容失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_error(self, f"保存失败：\n\n{error_msg}", "错误")

    def onRetryVersion(self, version_index):
        """重试章节版本（异步非阻塞版本）"""
        if self.selected_chapter_number is None:
            return

        if not confirm(
            self,
            f"确定要重新生成第{self.selected_chapter_number}章的版本{version_index + 1}吗？\n\n这将替换当前版本的内容。",
            "确认重新生成"
        ):
            return

        # 询问用户输入优化提示词
        from components.dialogs import TextInputDialog
        custom_prompt, ok = TextInputDialog.getTextStatic(
            parent=self,
            title="优化方向",
            label=f"请输入第{self.selected_chapter_number}章版本{version_index + 1}的优化方向：\n\n"
                  "（可选，留空则按原设定重新生成）",
            placeholder="示例：增加心理描写、加快节奏、强化角色冲突、增加悬念感"
        )

        if not ok:
            return

        # 显示加载动画
        loading_msg = f"正在重新生成第{self.selected_chapter_number}章版本{version_index + 1}..."
        if custom_prompt.strip():
            loading_msg += f"\n优化方向：{custom_prompt[:50]}..."
        self.show_loading(loading_msg)

        # 创建异步工作线程并通过 WorkerManager 管理
        worker = AsyncAPIWorker(
            self.api_client.retry_chapter_version,
            self.project_id,
            self.selected_chapter_number,
            version_index,
            custom_prompt.strip() if custom_prompt.strip() else None
        )
        worker.success.connect(lambda r: self.onRetrySuccess(r, version_index))
        worker.error.connect(self.onRetryError)

        # 使用 WorkerManager 启动
        self.worker_manager.start(worker, 'retry')

    def onRetrySuccess(self, result, version_index):
        """版本重试成功回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_operation_success(
            self,
            f"第{self.selected_chapter_number}章版本{version_index + 1}重新生成"
        )

        # 重新加载项目并刷新显示
        self.loadProject()
        if self.selected_chapter_number:
            self.workspace.loadChapter(self.selected_chapter_number)

    def onRetryError(self, error_msg):
        """版本重试失败回调"""
        # 隐藏加载动画
        self.hide_loading()

        MessageService.show_error(self, f"重新生成失败：\n\n{error_msg}", "错误")

    def openProjectDetail(self):
        """打开项目详情页"""
        self.navigateTo('DETAIL', project_id=self.project_id)

    def goBackToWorkspace(self):
        """返回首页"""
        self.navigateTo('HOME')

    def exportNovel(self, format_type):
        """导出小说"""
        @handle_errors("导出小说")
        def _export():
            content = self.api_client.export_novel(self.project_id, format_type)

            title = self.project.get('title', '小说')
            ext = 'md' if format_type == 'markdown' else 'txt'
            default_name = f"{title}.{ext}"

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存导出文件",
                default_name,
                f"{'Markdown' if format_type == 'markdown' else '文本'}文件 (*.{ext})"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                MessageService.show_operation_success(self, "导出", f"已导出到：{file_path}")

        _export()

    def onHide(self):
        """页面隐藏时清理资源"""
        # 停止所有正在运行的workers，防止信号发射到已删除的页面
        self._cleanup_workers()

    def _cleanup_workers(self):
        """清理所有异步工作线程"""
        # 使用 WorkerManager 统一清理所有托管的 Worker
        self.worker_manager.cleanup_all()

        # 清理SSE worker（章节生成流式，单独管理）
        self._cleanup_chapter_gen_sse()

        # 清理助手面板的Worker
        if hasattr(self, 'assistant_panel') and self.assistant_panel:
            try:
                self.assistant_panel.cleanup()
            except RuntimeError:
                pass  # 面板已被删除

        # 隐藏加载动画（如果有）
        self.hide_loading()

    def __del__(self):
        """析构函数，确保资源被释放"""
        try:
            self._cleanup_workers()
            # 注意：api_client 现在由 APIClientManager 单例管理，不在此处关闭
        except (RuntimeError, AttributeError, TypeError):
            # 析构时可能的异常：对象已删除、属性不存在、类型错误
            pass

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.onHide()
        super().closeEvent(event)

    def refresh(self, **params):
        """页面刷新"""
        if 'project_id' in params:
            self.project_id = params['project_id']
            if hasattr(self, 'workspace'):
                self.workspace.setProjectId(self.project_id)
            self.loadProject()
