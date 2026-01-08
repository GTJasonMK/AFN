"""
版本管理Mixin

处理版本相关的所有方法，包括：
- 选择版本
- 重试生成版本
"""

import logging

from PyQt6.QtCore import QTimer

from api.manager import APIClientManager
from components.dialogs import TextInputDialog
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService, confirm

logger = logging.getLogger(__name__)


class VersionManagementMixin:
    """版本管理相关方法的Mixin"""

    # 重新生成状态提示消息列表
    _RETRY_STATUS_MESSAGES = [
        "正在准备生成上下文...",
        "正在检索相关内容...",
        "正在构建提示词...",
        "正在调用AI生成内容...",
        "AI正在创作中，请耐心等待...",
        "内容生成中，即将完成...",
    ]

    def _ensure_retry_timer_initialized(self):
        """确保重新生成状态定时器已初始化"""
        if not hasattr(self, '_retry_status_timer'):
            self._retry_status_timer = None
            self._retry_status_step = 0

    def onSelectVersion(self, version_index):
        """选择版本"""
        if self.selected_chapter_number is None:
            MessageService.show_warning(self, "请先选择一个章节")
            return

        logger.info(
            f"版本切换请求: project_id={self.project_id}, chapter={self.selected_chapter_number}, version_index={version_index}"
        )

        # 设置版本切换状态，禁用保存按钮防止冲突
        self.workspace.setVersionSwitching(True)

        self.show_loading("正在切换版本...")

        def do_select():
            client = APIClientManager.get_client()
            return client.select_chapter_version(
                self.project_id,
                self.selected_chapter_number,
                version_index,
            )

        worker = AsyncAPIWorker(do_select)
        worker.success.connect(lambda result: self.onSelectVersionSuccess(result, version_index))
        worker.error.connect(self.onSelectVersionError)
        self.worker_manager.start(worker, 'select_version')

    def onSelectVersionSuccess(self, result, version_index):
        """选择版本成功回调"""
        self.hide_loading()

        logger.info(f"版本切换成功: version_index={version_index}, 正在刷新界面")

        # 失效缓存 - 版本已切换，章节内容变更
        from utils.chapter_cache import get_chapter_cache
        if self.selected_chapter_number:
            get_chapter_cache().invalidate(self.project_id, self.selected_chapter_number)

        # 刷新workspace显示（displayChapter会清除版本切换状态）
        self.workspace.refreshCurrentChapter()

        # Bug 34 修复: 版本切换后刷新漫画数据，因为不同版本可能对应不同的图片
        if hasattr(self.workspace, '_loadMangaDataAsync'):
            self.workspace._loadMangaDataAsync()

        # 重新加载项目数据以刷新侧边栏
        self.loadProject()

        # 注意：版本切换状态会在 displayChapter 中清除
        # 这里不需要显式调用 setVersionSwitching(False)，因为 displayChapter 会处理

        MessageService.show_success(self, f"已切换到版本{version_index + 1}")

    def onSelectVersionError(self, error_msg):
        """选择版本失败回调"""
        self.hide_loading()

        # 清除版本切换状态，重新启用保存按钮
        self.workspace.setVersionSwitching(False)

        MessageService.show_error(self, f"切换版本失败：{error_msg}")

    def onRetryVersion(self, version_index):
        """重新生成指定版本"""
        if self.selected_chapter_number is None:
            MessageService.show_warning(self, "请先选择一个章节")
            return

        if not confirm(
            self,
            f"确定要重新生成第{self.selected_chapter_number}章的版本{version_index + 1}吗？\n\n这将替换当前版本的内容。",
            "确认重新生成"
        ):
            return

        # 询问用户输入优化提示词
        custom_prompt, ok = TextInputDialog.getTextStatic(
            parent=self,
            title="优化方向",
            label=f"请输入第{self.selected_chapter_number}章版本{version_index + 1}的优化方向：\n\n"
                  "（可选，留空则按原设定重新生成）",
            placeholder="示例：增加对话、加强冲突、优化节奏..."
        )

        if not ok:
            return

        # 显示初始加载状态
        self.show_loading("正在准备重新生成...")

        # 设置版本切换状态，禁用保存按钮防止冲突
        self.workspace.setVersionSwitching(True)

        # 启动状态更新定时器
        self._start_retry_status_timer()

        def do_retry():
            client = APIClientManager.get_client()
            return client.retry_chapter_version(
                self.project_id,
                self.selected_chapter_number,
                version_index,
                custom_prompt=custom_prompt.strip() if custom_prompt else None,
            )

        worker = AsyncAPIWorker(do_retry)
        worker.success.connect(lambda result: self.onRetrySuccess(result, version_index))
        worker.error.connect(self.onRetryError)
        self.worker_manager.start(worker, 'retry_version')

    def _start_retry_status_timer(self):
        """启动重新生成状态更新定时器"""
        self._ensure_retry_timer_initialized()
        self._retry_status_step = 0

        if self._retry_status_timer is None:
            self._retry_status_timer = QTimer(self)
            self._retry_status_timer.timeout.connect(self._update_retry_status)

        self._retry_status_timer.start(3000)  # 每3秒更新一次状态

    def _stop_retry_status_timer(self):
        """停止重新生成状态更新定时器"""
        self._ensure_retry_timer_initialized()
        if self._retry_status_timer:
            self._retry_status_timer.stop()
        self._retry_status_step = 0

    def _update_retry_status(self):
        """更新重新生成状态提示"""
        messages = self._RETRY_STATUS_MESSAGES
        if self._retry_status_step < len(messages):
            message = messages[self._retry_status_step]
            self.show_loading(message)
            self._retry_status_step += 1
        else:
            # 循环显示最后几条消息
            loop_messages = messages[-2:]
            idx = (self._retry_status_step - len(messages)) % len(loop_messages)
            self.show_loading(loop_messages[idx])
            self._retry_status_step += 1

    def onRetrySuccess(self, result, version_index):
        """重新生成成功回调"""
        # 停止状态更新定时器
        self._stop_retry_status_timer()

        self.hide_loading()

        # 失效缓存 - 版本已重新生成
        from utils.chapter_cache import get_chapter_cache
        if self.selected_chapter_number:
            get_chapter_cache().invalidate(self.project_id, self.selected_chapter_number)

        # 刷新workspace显示（displayChapter会清除版本切换状态）
        self.workspace.refreshCurrentChapter()

        # 刷新漫画数据（重新生成的版本可能需要重新生成漫画分镜）
        if hasattr(self.workspace, '_loadMangaDataAsync'):
            self.workspace._loadMangaDataAsync()

        # 重新加载项目数据以刷新侧边栏
        self.loadProject()

        # 注意：版本切换状态会在 displayChapter 中清除
        # 这里不需要显式调用 setVersionSwitching(False)，因为 displayChapter 会处理

        MessageService.show_success(self, f"版本{version_index + 1}已重新生成")

    def onRetryError(self, error_msg):
        """重新生成失败回调"""
        # 停止状态更新定时器
        self._stop_retry_status_timer()

        self.hide_loading()

        # 清除版本切换状态，重新启用保存按钮
        self.workspace.setVersionSwitching(False)

        MessageService.show_error(self, f"重新生成失败：{error_msg}")
