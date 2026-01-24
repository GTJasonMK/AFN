"""
内容管理Mixin

处理内容相关的所有方法，包括：
- 保存内容
- RAG入库
- 编辑内容
"""

import logging

from PyQt6.QtCore import QTimer

from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker, run_async_action
from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class ContentManagementMixin:
    """内容管理相关方法的Mixin"""

    # RAG入库状态提示消息列表
    _RAG_STATUS_MESSAGES = [
        "正在保存章节内容...",
        "正在检查已有摘要和分析...",
        "正在生成章节摘要...",
        "正在进行章节分析...",
        "正在提取角色状态...",
        "正在建立伏笔索引...",
        "正在向量化入库...",
        "正在更新检索索引...",
        "处理即将完成，请稍候...",
    ]

    def _ensure_rag_timer_initialized(self):
        """确保RAG状态定时器已初始化"""
        if not hasattr(self, '_rag_status_timer'):
            self._rag_status_timer = None
            self._rag_status_step = 0

    def _start_rag_status_timer(self):
        """启动RAG入库状态更新定时器"""
        self._ensure_rag_timer_initialized()
        self._rag_status_step = 0

        if self._rag_status_timer is None:
            self._rag_status_timer = QTimer(self)
            self._rag_status_timer.timeout.connect(self._update_rag_status)

        self._rag_status_timer.start(2500)  # 每2.5秒更新一次状态

    def _stop_rag_status_timer(self):
        """停止RAG入库状态更新定时器"""
        self._ensure_rag_timer_initialized()
        if self._rag_status_timer:
            self._rag_status_timer.stop()
        self._rag_status_step = 0

    def _update_rag_status(self):
        """更新RAG入库状态提示"""
        messages = self._RAG_STATUS_MESSAGES
        if self._rag_status_step < len(messages):
            message = messages[self._rag_status_step]
            self.show_loading(message)
            self._rag_status_step += 1
        else:
            # 循环显示最后几条消息
            loop_messages = messages[-2:]
            idx = (self._rag_status_step - len(messages)) % len(loop_messages)
            self.show_loading(loop_messages[idx])
            self._rag_status_step += 1

    def onSaveContent(self, chapter_number, content):
        """保存章节内容"""
        self.show_loading("正在保存...")

        def do_save():
            client = APIClientManager.get_client()
            return client.update_chapter(
                self.project_id,
                chapter_number,
                content,
                trigger_rag=False,
            )

        run_async_action(
            self.worker_manager,
            do_save,
            task_name='save_content',
            on_success=lambda _: self.onSaveContentSuccess(chapter_number),
            on_error=self.onSaveContentError,
        )

    def onSaveContentSuccess(self, chapter_number):
        """保存成功回调"""
        self.hide_loading()

        # 失效缓存 - 内容已变更
        from utils.chapter_cache import get_chapter_cache
        get_chapter_cache().invalidate_and_refresh(self.project_id, chapter_number)

        MessageService.show_success(
            self,
            f"第{chapter_number}章内容已成功保存",
            title="保存成功"
        )

    def onSaveContentError(self, error_msg):
        """保存失败回调"""
        self.hide_loading()

        MessageService.show_error(
            self,
            f"保存章节内容时出错：{error_msg}",
            title="保存失败"
        )

    def onRagIngest(self, chapter_number, content):
        """RAG入库"""
        # 显示初始加载状态
        self.show_loading("正在准备RAG入库...")

        # 启动状态更新定时器
        self._start_rag_status_timer()

        def do_ingest():
            client = APIClientManager.get_client()
            return client.update_chapter(
                self.project_id,
                chapter_number,
                content,
                trigger_rag=True,
            )
        run_async_action(
            self.worker_manager,
            do_ingest,
            task_name='rag_ingest',
            on_success=lambda _: self.onRagIngestSuccess(chapter_number),
            on_error=self.onRagIngestError,
        )

    def onRagIngestSuccess(self, chapter_number):
        """RAG入库成功回调"""
        # 停止状态更新定时器
        self._stop_rag_status_timer()

        self.hide_loading()

        # 失效缓存 - 内容和分析数据已变更
        from utils.chapter_cache import get_chapter_cache
        get_chapter_cache().invalidate_and_refresh(self.project_id, chapter_number)

        MessageService.show_success(
            self,
            f"第{chapter_number}章已完成RAG处理：\n\n"
            "- 章节内容已保存\n"
            "- 摘要已生成\n"
            "- 文本已向量化入库\n"
            "- 角色状态已更新\n"
            "- 伏笔索引已建立",
            title="RAG入库完成"
        )

        # 刷新章节数据以显示更新后的摘要和分析
        # 使用 refreshCurrentChapter() 而不是 loadChapter()
        # 因为 loadChapter() 会被 _last_loaded_chapter 检查阻止
        if hasattr(self, 'workspace') and self.workspace:
            self.workspace.refreshCurrentChapter()

            # 刷新漫画数据（分析数据变更可能影响漫画）
            if hasattr(self.workspace, '_loadMangaDataAsync'):
                self.workspace._loadMangaDataAsync()

        # 重新加载项目数据以刷新侧边栏
        self.loadProject()

    def onRagIngestError(self, error_msg):
        """RAG入库失败回调"""
        # 停止状态更新定时器
        self._stop_rag_status_timer()

        self.hide_loading()

        MessageService.show_error(
            self,
            f"处理第{self.selected_chapter_number}章RAG入库时出错：\n\n{error_msg}",
            title="RAG入库失败"
        )

    def onEditContent(self, new_content):
        """编辑当前版本内容"""
        if self.selected_chapter_number is None:
            MessageService.show_warning(self, "请先选择一个章节")
            return

        self.show_loading("正在保存编辑...")

        def do_edit():
            client = APIClientManager.get_client()
            return client.update_chapter(
                self.project_id,
                self.selected_chapter_number,
                new_content,
                trigger_rag=False,
            )

        worker = AsyncAPIWorker(do_edit)
        worker.success.connect(self.onEditContentSuccess)
        worker.error.connect(self.onEditContentError)
        self.worker_manager.start(worker, 'edit_content')

    def onEditContentSuccess(self, result):
        """编辑成功回调"""
        self.hide_loading()

        # 失效缓存 - 内容已变更
        from utils.chapter_cache import get_chapter_cache
        if self.selected_chapter_number:
            get_chapter_cache().invalidate_and_refresh(
                self.project_id,
                self.selected_chapter_number
            )

        # 刷新workspace显示
        self.workspace.refreshCurrentChapter()

        # 刷新漫画数据（编辑后内容变化，漫画分镜可能需要更新）
        if hasattr(self.workspace, '_loadMangaDataAsync'):
            self.workspace._loadMangaDataAsync()

        # 重新加载项目数据以刷新侧边栏
        self.loadProject()

        MessageService.show_success(self, "内容已保存")

    def onEditContentError(self, error_msg):
        """编辑失败回调"""
        self.hide_loading()
        MessageService.show_error(self, f"保存失败：{error_msg}")
