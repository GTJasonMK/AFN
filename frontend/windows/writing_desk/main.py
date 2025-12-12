"""
写作台主类

集成Header、Sidebar、Workspace，提供完整的章节写作功能
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog
)
from PyQt6.QtCore import Qt
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
        self.header.goBackClicked.connect(self.goBackToWorkspace)
        self.header.viewDetailClicked.connect(self.openProjectDetail)
        self.header.exportClicked.connect(self.exportNovel)
        main_layout.addWidget(self.header)

        # 主内容区 - 紧凑布局
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)  # 从24减少到16
        content_layout.setSpacing(16)  # 从24减少到16

        # Sidebar
        self.sidebar = WDSidebar()
        self.sidebar.chapterSelected.connect(self.onChapterSelected)
        self.sidebar.generateChapter.connect(self.onGenerateChapter)
        self.sidebar.generateOutline.connect(self.onGenerateOutline)
        content_layout.addWidget(self.sidebar)

        # Workspace
        self.workspace = WDWorkspace()
        self.workspace.generateChapterRequested.connect(self.onGenerateChapter)
        self.workspace.previewPromptRequested.connect(self.onPreviewPrompt)
        self.workspace.saveContentRequested.connect(self.onSaveContent)
        self.workspace.selectVersion.connect(self.onSelectVersion)
        self.workspace.evaluateChapter.connect(self.onEvaluateChapter)
        self.workspace.retryVersion.connect(self.onRetryVersion)
        self.workspace.editContent.connect(self.onEditContent)
        self.workspace.setProjectId(self.project_id)
        content_layout.addWidget(self.workspace, stretch=1)
        
        # Assistant Panel (Initially hidden)
        self.assistant_panel = AssistantPanel(self.project_id)
        self.assistant_panel.setVisible(False)
        self.assistant_panel.setFixedWidth(dp(350)) # 固定宽度
        content_layout.addWidget(self.assistant_panel)
        
        # Connect Header Signal
        self.header.toggleAssistantClicked.connect(self.toggleAssistant)

        main_layout.addWidget(self.content_widget, stretch=1)

    def toggleAssistant(self, show: bool):
        """切换AI助手显示状态"""
        self.assistant_panel.setVisible(show)

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

    @handle_errors("加载项目")
    def loadProject(self):
        """加载项目数据"""
        logger.info(f"WritingDesk.loadProject被调用, project_id={self.project_id}")
        self.project = self.api_client.get_novel(self.project_id)

        logger.info(f"项目数据加载成功")
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

    def onChapterSelected(self, chapter_number):
        """章节被选中"""
        self.selected_chapter_number = chapter_number
        self.workspace.loadChapter(chapter_number)

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

        # 标记正在生成的章节
        self.generating_chapter = chapter_number
        self.sidebar.setGeneratingChapter(chapter_number)

        # 显示进度对话框
        self._progress_dialog = LoadingDialog(
            parent=self,
            title=f"生成第{chapter_number}章",
            message="正在初始化...",
            cancelable=True
        )
        self._progress_dialog.rejected.connect(self._on_chapter_gen_cancelled)
        self._progress_dialog.show()

        # 使用SSEWorker连接流式端点
        url = f"{self.api_client.base_url}/api/writer/novels/{self.project_id}/chapters/generate-stream"
        payload = {"chapter_number": chapter_number}

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.progress_received.connect(self._on_chapter_gen_progress)
        self._sse_worker.complete.connect(self._on_chapter_gen_complete)
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

        # 根据错误消息内容生成更友好的提示
        title, message = self._format_generation_error(error_msg, chapter_number)
        MessageService.show_error(self, message, title)

    def _format_generation_error(self, error_msg: str, chapter_number: int) -> tuple:
        """格式化章节生成错误消息

        根据错误内容识别错误类型，提供更有用的建议。

        Args:
            error_msg: 原始错误消息
            chapter_number: 章节号

        Returns:
            (title, message) 元组
        """
        error_lower = error_msg.lower() if error_msg else ""

        # LLM服务相关错误
        if any(kw in error_lower for kw in ["ai服务", "llm", "api key", "openai", "模型"]):
            title = "AI服务错误"
            message = (
                f"第{chapter_number}章生成失败：AI服务暂时不可用\n\n"
                "请检查：\n"
                "- LLM配置是否正确\n"
                "- API密钥是否有效\n"
                "- 网络连接是否正常"
            )
        # 超时错误
        elif any(kw in error_lower for kw in ["超时", "timeout", "timed out"]):
            title = "生成超时"
            message = (
                f"第{chapter_number}章生成超时\n\n"
                "这可能是因为：\n"
                "- 章节内容较长，需要更多生成时间\n"
                "- 服务器负载较高\n\n"
                "请稍后重试。"
            )
        # 连接错误
        elif any(kw in error_lower for kw in ["连接", "connection", "network"]):
            title = "连接失败"
            message = (
                f"第{chapter_number}章生成失败：网络连接问题\n\n"
                "请检查：\n"
                "- 后端服务是否已启动\n"
                "- 网络连接是否正常"
            )
        # JSON解析错误
        elif any(kw in error_lower for kw in ["json", "解析", "格式"]):
            title = "响应格式错误"
            message = (
                f"第{chapter_number}章生成失败：AI响应格式异常\n\n"
                "这可能是由于AI模型返回了非预期的内容。\n"
                "请重试生成。"
            )
        # 章节大纲相关
        elif "大纲" in error_msg:
            title = "大纲错误"
            message = (
                f"第{chapter_number}章生成失败：章节大纲问题\n\n"
                f"{error_msg}\n\n"
                "请检查章节大纲是否已正确生成。"
            )
        # 默认错误
        else:
            title = "生成失败"
            message = f"第{chapter_number}章生成失败\n\n{error_msg}"

        return title, message

    def _on_chapter_gen_cancelled(self):
        """用户取消章节生成"""
        logger.info("用户取消章节生成")
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

        layout = QVBoxLayout(options_dialog)
        layout.setSpacing(dp(16))
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))

        # 模式选择
        mode_label = QLabel("选择预览模式：")
        mode_label.setStyleSheet(f"font-weight: bold; color: {theme_manager.TEXT_PRIMARY};")
        layout.addWidget(mode_label)

        mode_group = QButtonGroup(options_dialog)

        first_gen_radio = QRadioButton("首次生成 - 完整提示词（包含分层前情摘要）")
        first_gen_radio.setChecked(True)
        first_gen_radio.setStyleSheet(f"color: {theme_manager.TEXT_PRIMARY};")
        mode_group.addButton(first_gen_radio, 0)
        layout.addWidget(first_gen_radio)

        retry_radio = QRadioButton("重新生成 - 简化提示词（不含完整前情摘要）")
        retry_radio.setStyleSheet(f"color: {theme_manager.TEXT_PRIMARY};")
        mode_group.addButton(retry_radio, 1)
        layout.addWidget(retry_radio)

        # 写作备注/优化方向
        notes_label = QLabel("写作备注/优化方向（可选）：")
        notes_label.setStyleSheet(f"font-weight: bold; color: {theme_manager.TEXT_PRIMARY}; margin-top: {dp(8)}px;")
        layout.addWidget(notes_label)

        notes_hint = QLabel("留空则使用默认设置，填写后会影响RAG查询和提示词内容")
        notes_hint.setStyleSheet(f"font-size: {sp(12)}px; color: {theme_manager.TEXT_SECONDARY};")
        layout.addWidget(notes_hint)

        notes_input = QTextEdit()
        notes_input.setPlaceholderText("示例：增加心理描写、加快节奏、强化角色冲突...")
        notes_input.setMaximumHeight(dp(80))
        notes_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme_manager.BG_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
                color: {theme_manager.TEXT_PRIMARY};
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
