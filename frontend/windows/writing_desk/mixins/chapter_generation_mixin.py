"""
章节生成Mixin

处理章节生成相关的所有方法，包括：
- 生成章节
- SSE流式处理
- 提示词预览
"""

import logging
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QButtonGroup, QPushButton, QTextEdit

from api.manager import APIClientManager
from components.dialogs import TextInputDialog
from utils.async_worker import AsyncAPIWorker
from utils.sse_worker import SSEWorker
from utils.message_service import MessageService, confirm
from utils.dpi_utils import dp
from utils.chapter_error_formatter import format_chapter_error
from themes.theme_manager import theme_manager
from themes import ButtonStyles

from ..dialogs import PromptPreviewDialog

logger = logging.getLogger(__name__)


class ChapterGenerationMixin:
    """章节生成相关方法的Mixin"""

    # 章节生成初始阶段状态提示消息列表
    _GENERATION_INIT_MESSAGES = [
        "正在连接AI服务...",
        "正在收集前文摘要...",
        "正在检索相关内容...",
        "正在构建RAG上下文...",
        "正在准备写作提示词...",
        "正在启动创作引擎...",
        "AI正在构思章节内容...",
    ]

    def _ensure_gen_timer_initialized(self):
        """确保生成状态定时器已初始化"""
        if not hasattr(self, '_gen_status_timer'):
            self._gen_status_timer = None
            self._gen_status_step = 0
            self._gen_first_content_received = False

    def _start_gen_status_timer(self):
        """启动生成状态更新定时器（初始阶段使用）"""
        self._ensure_gen_timer_initialized()
        self._gen_status_step = 0
        self._gen_first_content_received = False

        if self._gen_status_timer is None:
            self._gen_status_timer = QTimer(self)
            self._gen_status_timer.timeout.connect(self._update_gen_status)

        self._gen_status_timer.start(2000)  # 每2秒更新一次状态

    def _stop_gen_status_timer(self):
        """停止生成状态更新定时器"""
        self._ensure_gen_timer_initialized()
        if self._gen_status_timer:
            self._gen_status_timer.stop()
        self._gen_status_step = 0

    def _update_gen_status(self):
        """更新生成状态提示（初始阶段）"""
        # 如果已经收到内容，不再更新初始状态
        if self._gen_first_content_received:
            self._stop_gen_status_timer()
            return

        messages = self._GENERATION_INIT_MESSAGES
        if self._gen_status_step < len(messages):
            message = messages[self._gen_status_step]
            # 同时更新workspace状态和loading overlay
            self.workspace.setGenerationStatus(message)
            if hasattr(self, 'show_loading'):
                self.show_loading(message)
            self._gen_status_step += 1
        else:
            # 循环显示最后两条消息
            loop_messages = messages[-2:]
            idx = (self._gen_status_step - len(messages)) % len(loop_messages)
            message = loop_messages[idx]
            self.workspace.setGenerationStatus(message)
            if hasattr(self, 'show_loading'):
                self.show_loading(message)
            self._gen_status_step += 1

    def onGenerateChapter(self, chapter_number):
        """生成章节"""
        if not confirm(
            self,
            f"确定要生成第{chapter_number}章吗？\n\n生成过程可能需要 1-3 分钟。",
            "确认生成"
        ):
            return

        # 询问用户输入写作提示词（可选）
        writing_notes, ok = TextInputDialog.getTextStatic(
            parent=self,
            title="写作指导",
            label=f"请输入第{chapter_number}章的写作指导（可选）：\n\n"
                  "留空则按大纲设定生成，填写后会影响RAG检索和生成内容。",
            placeholder="示例：注重环境描写、加强悬疑氛围、增加角色对话、突出心理变化..."
        )

        if not ok:
            return

        # 清理旧的SSE
        self._cleanup_chapter_gen_sse()

        # 记录正在生成的章节
        self.generating_chapter = chapter_number

        # 通知workspace准备生成
        self.workspace.prepareForGeneration(chapter_number)

        # 显示初始加载状态并启动状态更新定时器
        self.show_loading("正在准备生成章节...")
        self._start_gen_status_timer()

        # 创建SSE Worker
        # 后端路径: /api/writer/novels/{project_id}/chapters/generate-stream
        url = f"{self.api_client.base_url}/api/writer/novels/{self.project_id}/chapters/generate-stream"
        payload = {
            "chapter_number": chapter_number,
            "writing_notes": writing_notes.strip() if writing_notes else None,
        }

        self._sse_worker = SSEWorker(url, payload)
        # token_received 信号发射的是字符串，直接追加到内容
        self._sse_worker.token_received.connect(self._on_chapter_gen_token)
        # progress_received 信号发射的是dict，包含状态信息
        self._sse_worker.progress_received.connect(self._on_chapter_gen_progress)
        self._sse_worker.complete.connect(self._on_chapter_gen_complete)
        self._sse_worker.error.connect(self._on_chapter_gen_error)
        self._sse_worker.cancelled.connect(self._on_chapter_gen_cancelled)
        self._sse_worker.start()

        # 更新侧边栏状态
        self.sidebar.setChapterGenerating(chapter_number, True)

        logger.info(f"开始生成第{chapter_number}章")

    def _on_chapter_gen_token(self, token: str):
        """处理章节生成的token（流式文本）"""
        # 第一次收到内容时，停止初始状态定时器并隐藏loading
        self._ensure_gen_timer_initialized()
        if not self._gen_first_content_received:
            self._gen_first_content_received = True
            self._stop_gen_status_timer()
            self.hide_loading()

        self.workspace.appendGeneratedContent(token)

    def _on_chapter_gen_progress(self, data: dict):
        """处理章节生成进度（状态更新、UI控制等）"""
        if "status" in data:
            status = data.get("status", "")
            message = data.get("message", "")
            if status == "preparing":
                self.workspace.setGenerationStatus(f"准备中: {message}")
            elif status == "generating":
                self.workspace.setGenerationStatus(f"生成中: {message}")
            elif status == "processing":
                self.workspace.setGenerationStatus(f"处理中: {message}")
        elif "ui_control" in data:
            ui_control = data.get("ui_control", {})
            if ui_control.get("show_evaluation_section"):
                self.workspace.showEvaluationSection()
            if ui_control.get("can_regenerate"):
                self.workspace.enableRegenerate()

    def _on_chapter_gen_complete(self, data: dict):
        """处理章节生成完成"""
        chapter_number = self.generating_chapter
        self.generating_chapter = None

        # 停止状态定时器并隐藏loading
        self._stop_gen_status_timer()
        self.hide_loading()

        # 清理SSE
        self._cleanup_chapter_gen_sse()

        # 失效缓存 - 章节已生成新版本
        if chapter_number:
            from utils.chapter_cache import get_chapter_cache
            get_chapter_cache().invalidate(self.project_id, chapter_number)

        # 更新侧边栏状态
        if chapter_number:
            self.sidebar.setChapterGenerating(chapter_number, False)

        # 通知workspace完成
        self.workspace.onGenerationComplete(data)

        # 刷新侧边栏以显示新版本
        self._refresh_sidebar()

        logger.info(f"第{chapter_number}章生成完成")

    def _on_chapter_gen_error(self, error_msg: str):
        """处理章节生成错误"""
        chapter_number = self.generating_chapter
        self.generating_chapter = None

        # 停止状态定时器并隐藏loading
        self._stop_gen_status_timer()
        self.hide_loading()

        self._cleanup_chapter_gen_sse()

        if chapter_number:
            self.sidebar.setChapterGenerating(chapter_number, False)

        # format_chapter_error 返回 (title, message) 元组
        error_title, error_message = format_chapter_error(error_msg, chapter_number or 0)
        self.workspace.onGenerationError(error_title, error_message)
        logger.error(f"章节生成失败: {error_msg}")

    def _on_chapter_gen_cancelled(self, data: dict = None):
        """处理生成取消（用户取消或服务器取消）"""
        chapter_number = self.generating_chapter
        self.generating_chapter = None

        # 停止状态定时器并隐藏loading
        self._stop_gen_status_timer()
        self.hide_loading()

        self._cleanup_chapter_gen_sse()

        if chapter_number:
            self.sidebar.setChapterGenerating(chapter_number, False)
            self.workspace.onGenerationCancelled()

        logger.info("章节生成已取消")

    def _cleanup_chapter_gen_sse(self):
        """清理章节生成的SSE连接"""
        if self._sse_worker:
            try:
                self._sse_worker.stop()
                self._sse_worker.deleteLater()
            except RuntimeError:
                pass
            self._sse_worker = None

        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def _refresh_sidebar(self):
        """刷新侧边栏数据"""
        if hasattr(self, 'loadProject'):
            # 重新加载项目数据会自动更新侧边栏
            self.loadProject()

    def onPreviewPrompt(self, chapter_number):
        """预览章节生成的提示词（用于测试RAG效果）"""

        # 创建选项对话框
        options_dialog = QDialog(self)
        options_dialog.setWindowTitle("预览提示词选项")
        options_dialog.setMinimumWidth(dp(450))

        # 设置对话框背景色
        options_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
            QLabel {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
            }}
            QRadioButton {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(14)}px;
                spacing: {dp(8)}px;
            }}
            QRadioButton::indicator {{
                width: {dp(18)}px;
                height: {dp(18)}px;
            }}
            QTextEdit {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px;
                font-size: {dp(13)}px;
            }}
        """)

        layout = QVBoxLayout(options_dialog)
        layout.setSpacing(dp(16))
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))

        # 说明标签
        desc_label = QLabel("选择预览选项：")
        layout.addWidget(desc_label)

        # RAG选项
        rag_group = QButtonGroup(options_dialog)
        rag_enabled = QRadioButton("启用RAG检索（完整上下文）")
        rag_disabled = QRadioButton("禁用RAG检索（仅基础上下文）")
        rag_enabled.setChecked(True)
        rag_group.addButton(rag_enabled, 1)
        rag_group.addButton(rag_disabled, 0)
        layout.addWidget(rag_enabled)
        layout.addWidget(rag_disabled)

        # 写作备注输入
        notes_label = QLabel("\n写作指导（可选）：")
        layout.addWidget(notes_label)
        notes_edit = QTextEdit()
        notes_edit.setPlaceholderText("输入写作指导，测试RAG检索效果...")
        notes_edit.setMaximumHeight(dp(80))
        layout.addWidget(notes_edit)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(ButtonStyles.secondary())
        cancel_btn.clicked.connect(options_dialog.reject)
        preview_btn = QPushButton("预览")
        preview_btn.setStyleSheet(ButtonStyles.primary())
        preview_btn.clicked.connect(options_dialog.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(preview_btn)
        layout.addLayout(btn_layout)

        if options_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # 获取选项
        use_rag = rag_group.checkedId() == 1
        writing_notes = notes_edit.toPlainText().strip() or None

        # 显示加载
        self.show_loading("正在生成提示词预览...")

        def do_preview():
            client = APIClientManager.get_client()
            return client.preview_chapter_prompt(
                self.project_id,
                chapter_number,
                use_rag=use_rag,
                writing_notes=writing_notes,
            )

        worker = AsyncAPIWorker(do_preview)
        worker.success.connect(lambda result: self.onPreviewPromptSuccess(result, chapter_number))
        worker.error.connect(self.onPreviewPromptError)
        self.worker_manager.start(worker, 'preview_prompt')

    def onPreviewPromptSuccess(self, result, chapter_number, is_retry=False):
        """提示词预览成功回调"""
        self.hide_loading()

        # 打开提示词预览对话框
        dialog = PromptPreviewDialog(result, chapter_number, self)
        dialog.exec()

    def onPreviewPromptError(self, error_msg):
        """提示词预览失败回调"""
        self.hide_loading()
        MessageService.show_error(self, f"预览提示词失败：{error_msg}")
