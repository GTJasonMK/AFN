"""
部分大纲处理Mixin

负责部分大纲的生成、继续生成、重新生成和删除操作。
"""

import logging
import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer

from components.dialogs import IntInputDialog, InputDialog, LoadingDialog
from utils.message_service import MessageService, confirm
from utils.sse_worker import SSEWorker
from utils.constants import WorkerTimeouts

if TYPE_CHECKING:
    from ..main import ChapterOutlineSection

logger = logging.getLogger(__name__)


class PartOutlineHandlerMixin:
    """
    部分大纲处理Mixin

    负责：
    - 首次生成部分大纲（SSE流式）
    - 继续生成部分大纲（增量模式）
    - 重新生成最新N个部分大纲
    - 删除最新N个部分大纲
    - 进度轮询（兼容旧模式）
    """

    def _on_generate_part_outlines(self: "ChapterOutlineSection"):
        """生成部分大纲"""
        total_chapters = self.blueprint.get('total_chapters', 0)
        if total_chapters == 0:
            MessageService.show_warning(self, "无法获取总章节数，请先生成蓝图", "提示")
            return

        # 使用新的配置对话框（支持指定生成范围）
        from components.dialogs import PartOutlineConfigDialog
        result = PartOutlineConfigDialog.getConfigStatic(
            parent=self,
            total_chapters=total_chapters
        )
        if not result:
            return

        generate_chapters, chapters_per_part = result

        # 计算预计生成的部分数
        estimated_parts = math.ceil(generate_chapters / chapters_per_part)

        logger.info(f"开始生成部分大纲（使用SSE流式进度）: {generate_chapters}章, 每部分{chapters_per_part}章, 预计{estimated_parts}部分")

        # 显示带进度的加载对话框
        if generate_chapters < total_chapters:
            message = f"正在生成第1-{generate_chapters}章的部分大纲...\n预计生成 {estimated_parts} 个部分"
        else:
            message = f"正在准备生成 {estimated_parts} 个部分大纲..."

        self._progress_dialog = LoadingDialog(
            parent=self,
            title="生成部分大纲",
            message=message,
            cancelable=True
        )
        self._progress_dialog.rejected.connect(self._on_part_outline_sse_cancelled)
        self._progress_dialog.show()

        # 使用SSE流式端点
        url = f"{self.api_client.base_url}/api/writer/novels/{self.project_id}/parts/generate-stream"
        payload = {
            "total_chapters": generate_chapters,
            "chapters_per_part": chapters_per_part
        }

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.progress_received.connect(self._on_part_outline_progress)
        self._sse_worker.complete.connect(self._on_part_outline_complete)
        self._sse_worker.error_data.connect(self._on_part_outline_error)
        self._sse_worker.start()

    def _on_part_outline_progress(self: "ChapterOutlineSection", data: dict):
        """处理部分大纲生成进度更新"""
        if not self._progress_dialog:
            return

        status = data.get('status', '')
        current_part = data.get('current_part', 0)
        total_parts = data.get('total_parts', 0)
        message = data.get('message', '')

        if status == 'starting':
            progress_text = f"{message}\n预计生成 {total_parts} 个部分"
        elif status == 'generating':
            progress_text = f"正在生成第 {current_part}/{total_parts} 部分..."
        else:
            progress_text = message

        self._progress_dialog.setMessage(progress_text)

    def _on_part_outline_complete(self: "ChapterOutlineSection", data: dict):
        """部分大纲生成完成"""
        self._cleanup_part_outline_sse()

        message = data.get('message', '生成完成')
        total_parts = data.get('total_parts', 0)

        logger.info(f"部分大纲生成完成: {message}, 共{total_parts}部分")
        MessageService.show_operation_success(self, message)
        self.refreshRequested.emit()

    def _on_part_outline_error(self: "ChapterOutlineSection", error_data: dict):
        """部分大纲生成错误"""
        self._cleanup_part_outline_sse()

        error_msg = error_data.get('message', '未知错误')
        saved_count = error_data.get('saved_count', 0)

        logger.error(f"部分大纲生成失败: {error_msg}, 已保存 {saved_count} 部分")

        if saved_count > 0:
            saved_info = f"\n\n已成功保存 {saved_count} 个部分大纲。\n刷新页面可查看已保存的内容。"
            MessageService.show_api_error(self, f"{error_msg}{saved_info}", "生成部分大纲")
            self.refreshRequested.emit()
        else:
            MessageService.show_api_error(self, error_msg, "生成部分大纲")

    def _on_part_outline_sse_cancelled(self: "ChapterOutlineSection"):
        """用户取消部分大纲生成"""
        logger.info("用户取消部分大纲生成")
        self._cleanup_part_outline_sse()

    def _cleanup_part_outline_sse(self: "ChapterOutlineSection"):
        """清理部分大纲SSE相关资源"""
        if self._sse_worker:
            try:
                self._sse_worker.stop()
                if self._sse_worker.isRunning():
                    self._sse_worker.quit()
                    self._sse_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                pass
            self._sse_worker = None

        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def _on_continue_generate_parts(self: "ChapterOutlineSection"):
        """继续生成部分大纲（增量模式）"""
        total_chapters = self.blueprint.get('total_chapters', 0)
        if total_chapters == 0:
            MessageService.show_warning(self, "无法获取总章节数，请先生成蓝图", "提示")
            return

        # 获取当前已覆盖的章节范围
        part_outlines = self.blueprint.get('part_outlines', [])
        if not part_outlines:
            self._on_generate_part_outlines()
            return

        # 计算当前已覆盖到第几章
        current_covered_chapter = max(p.get('end_chapter', 0) for p in part_outlines)
        current_parts = len(part_outlines)
        chapters_per_part = self.blueprint.get('chapters_per_part', 25)

        if current_covered_chapter >= total_chapters:
            MessageService.show_warning(
                self,
                f"已生成所有部分大纲（覆盖到第{current_covered_chapter}章），无需继续生成",
                "提示"
            )
            return

        # 使用专用的继续生成配置对话框
        from components.dialogs import PartOutlineConfigDialog
        result = PartOutlineConfigDialog.getContinueConfigStatic(
            parent=self,
            total_chapters=total_chapters,
            current_covered_chapter=current_covered_chapter,
            current_parts=current_parts,
            chapters_per_part=chapters_per_part
        )
        if not result:
            return

        generate_chapters, chapters_per_part = result

        # 计算预计新增的部分数
        estimated_parts = math.ceil(generate_chapters / chapters_per_part)
        new_parts = estimated_parts - current_parts

        logger.info(
            f"继续生成部分大纲（SSE增量模式）: "
            f"当前{current_parts}部分(覆盖到第{current_covered_chapter}章), "
            f"目标覆盖到第{generate_chapters}章, 预计新增{new_parts}部分"
        )

        # 显示进度对话框
        message = f"从第{current_covered_chapter + 1}章开始继续生成...\n目标覆盖到第{generate_chapters}章"

        self._progress_dialog = LoadingDialog(
            parent=self,
            title="继续生成部分大纲",
            message=message,
            cancelable=True
        )
        self._progress_dialog.rejected.connect(self._on_part_outline_sse_cancelled)
        self._progress_dialog.show()

        # 使用SSE增量生成端点
        url = f"{self.api_client.base_url}/api/writer/novels/{self.project_id}/parts/continue-stream"
        payload = {
            "total_chapters": generate_chapters,
            "chapters_per_part": chapters_per_part
        }

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.progress_received.connect(self._on_part_outline_progress)
        self._sse_worker.complete.connect(self._on_part_outline_complete)
        self._sse_worker.error_data.connect(self._on_part_outline_error)
        self._sse_worker.start()

    def _on_regenerate_latest_parts(self: "ChapterOutlineSection"):
        """重新生成最新N个部分大纲"""
        part_outlines = self.blueprint.get('part_outlines', [])
        if not part_outlines:
            MessageService.show_warning(self, "没有部分大纲可以重新生成", "提示")
            return

        max_count = len(part_outlines)
        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="重新生成最新N个部分大纲",
            label=f"共有 {max_count} 个部分大纲\n请输入要重新生成的数量（从最后开始）：",
            value=1,
            min_value=1,
            max_value=max_count
        )
        if not ok:
            return

        # 确认级联删除
        start_part = max_count - count + 1
        if not confirm(
            self,
            f"将重新生成最后 {count} 个部分大纲（第{start_part}-{max_count}部分）。\n\n"
            f"根据串行生成原则：\n"
            f"* 这些部分对应的所有章节大纲也会被删除\n\n"
            f"确定要继续吗？",
            "确认重新生成"
        ):
            return

        # 获取优化提示词
        prompt, ok = InputDialog.getTextStatic(
            parent=self,
            title="优化提示词（可选）",
            label="请输入优化提示词，用于引导AI生成更符合预期的部分大纲：",
            placeholder="留空则使用默认生成方式"
        )
        if not ok:
            return

        # 从第start_part部分开始重新生成（级联删除后续所有）
        self._run_async_action(
            self.api_client.regenerate_specific_part_outline,
            self.project_id,
            start_part,
            prompt=prompt if prompt else None,
            cascade_delete=True,
            loading_message=f"正在重新生成第{start_part}部分及之后的部分大纲...",
            success_message=f"部分大纲重新生成",
            error_context="重新生成部分大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def _on_delete_latest_parts(self: "ChapterOutlineSection"):
        """删除最新N个部分大纲"""
        part_outlines = self.blueprint.get('part_outlines', [])
        if not part_outlines:
            MessageService.show_warning(self, "没有部分大纲可以删除", "提示")
            return

        max_count = len(part_outlines)
        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="删除最新N个部分大纲",
            label=f"共有 {max_count} 个部分大纲\n请输入要删除的数量（从最后开始）：",
            value=1,
            min_value=1,
            max_value=max_count
        )
        if not ok:
            return

        start_part = max_count - count + 1
        if not confirm(
            self,
            f"确定要删除最后 {count} 个部分大纲（第{start_part}-{max_count}部分）吗？\n\n"
            f"这些部分对应的章节大纲也会被一起删除。\n\n"
            f"此操作不可恢复！",
            "确认删除"
        ):
            return

        self._run_async_action(
            self.api_client.delete_part_outlines,
            self.project_id,
            count,
            loading_message=f"正在删除 {count} 个部分大纲...",
            success_message=f"删除 {count} 个部分大纲",
            error_context="删除部分大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    # ========== 进度轮询（兼容旧模式） ==========

    def _on_generate_completed(self: "ChapterOutlineSection", result):
        """生成任务完成（旧版轮询模式，保留兼容）"""
        self._stop_progress_polling()
        total_parts = result.get('total_parts', 0)
        logger.info(f"部分大纲生成完成: {result}")
        MessageService.show_operation_success(self, f"部分大纲生成完成，共 {total_parts} 个部分")
        self.refreshRequested.emit()

    def _on_generate_started(self: "ChapterOutlineSection", result):
        """生成任务启动成功，开始轮询进度（已弃用，保留兼容）"""
        logger.info(f"部分大纲生成任务已启动: {result}")
        self._start_progress_polling()

    def _on_generate_error(self: "ChapterOutlineSection", error_msg):
        """生成任务启动失败（旧版轮询模式，保留兼容）"""
        self._stop_progress_polling()
        MessageService.show_api_error(self, error_msg, "启动生成任务")

    def _start_progress_polling(self: "ChapterOutlineSection"):
        """开始轮询进度"""
        if self._progress_timer:
            self._progress_timer.stop()

        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._poll_progress)
        self._progress_timer.start(2000)

    def _stop_progress_polling(self: "ChapterOutlineSection"):
        """停止进度轮询"""
        if self._progress_timer:
            self._progress_timer.stop()
            self._progress_timer = None

        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def _poll_progress(self: "ChapterOutlineSection"):
        """轮询生成进度"""
        try:
            status_data = self.api_client.get_part_outline_generation_status(self.project_id)
            status = status_data.get('status', 'pending')
            completed_parts = status_data.get('completed_parts', 0)
            total_parts = status_data.get('total_parts', 0)
            parts = status_data.get('parts', [])

            logger.info(f"部分大纲生成进度: {completed_parts}/{total_parts}, 状态: {status}")

            if self._progress_dialog:
                progress_text = f"正在生成部分大纲...\n已完成: {completed_parts} / {total_parts}"

                generating_part = None
                for part in parts:
                    if part.get('generation_status') == 'generating':
                        generating_part = part.get('part_number', 0)
                        break

                if generating_part:
                    progress_text += f"\n当前正在生成: 第 {generating_part} 部分"

                self._progress_dialog.setMessage(progress_text)

            if status == 'completed' or completed_parts >= total_parts:
                self._stop_progress_polling()
                MessageService.show_operation_success(self, f"部分大纲生成完成，共 {total_parts} 个部分")
                self.refreshRequested.emit()
            elif status == 'failed':
                self._stop_progress_polling()
                MessageService.show_error(self, "部分大纲生成失败，请重试", "生成失败")

        except Exception as e:
            logger.error(f"轮询进度失败: {e}")


__all__ = [
    "PartOutlineHandlerMixin",
]
