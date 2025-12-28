"""
章节大纲处理Mixin

负责章节大纲的生成、继续生成、编辑、重新生成和删除操作。
"""

import logging
from typing import TYPE_CHECKING

from components.dialogs import IntInputDialog, InputDialog, LoadingDialog
from utils.message_service import MessageService, confirm
from utils.sse_worker import SSEWorker
from utils.constants import WorkerTimeouts

if TYPE_CHECKING:
    from ..main import ChapterOutlineSection

logger = logging.getLogger(__name__)


class ChapterOutlineHandlerMixin:
    """
    章节大纲处理Mixin

    负责：
    - 手动新增章节大纲
    - 首次生成章节大纲（SSE流式）
    - 继续生成章节大纲
    - 章节大纲编辑
    - 重新生成最新N个章节大纲
    - 删除最新N个章节大纲
    """

    def _on_add_chapter_outline(self: "ChapterOutlineSection"):
        """手动新增章节大纲"""
        from ..dialogs import ChapterOutlineEditDialog
        from PyQt6.QtWidgets import QDialog

        # 计算下一个章节编号
        current_max = 0
        for outline in self.outline:
            chapter_num = outline.get('chapter_number', 0)
            if chapter_num > current_max:
                current_max = chapter_num
        next_chapter_number = current_max + 1

        # 检查是否超出限制（长篇模式下不能超过部分大纲覆盖范围）
        needs_part_outlines = self.blueprint.get('needs_part_outlines', False)
        if needs_part_outlines and self._max_covered_chapter > 0:
            if next_chapter_number > self._max_covered_chapter:
                MessageService.show_warning(
                    self,
                    f"当前部分大纲仅覆盖到第{self._max_covered_chapter}章，\n"
                    f"无法新增第{next_chapter_number}章。\n\n"
                    f"请先生成更多部分大纲以覆盖后续章节。",
                    "提示"
                )
                return

        # 打开新增对话框
        dialog = ChapterOutlineEditDialog(
            chapter_number=next_chapter_number,
            is_new=True,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_title, new_summary = dialog.get_values()

            self.async_helper.execute(
                self.api_client.update_chapter_outline,
                self.project_id,
                next_chapter_number,
                new_title,
                new_summary,
                loading_message=f"正在添加第{next_chapter_number}章大纲...",
                success_message=f"第{next_chapter_number}章大纲已添加",
                error_context="添加章节大纲",
                on_success=lambda r: self.refreshRequested.emit()
            )

    def _on_generate_chapter_outlines(self: "ChapterOutlineSection"):
        """生成章节大纲"""
        total_chapters = self.blueprint.get('total_chapters')
        if not total_chapters:
            self._prompt_total_chapters_then_generate()
            return

        self._do_generate_chapter_outlines()

    def _prompt_total_chapters_then_generate(self: "ChapterOutlineSection"):
        """提示用户输入总章节数，然后生成大纲"""
        dialog = IntInputDialog(
            parent=self,
            title="设置章节数量",
            label="请输入计划的总章节数：",
            value=20,
            min_value=1,
            max_value=500
        )

        if dialog.exec():
            total_chapters = dialog.getValue()
            if total_chapters > 0:
                self._save_total_chapters_then_generate(total_chapters)

    def _save_total_chapters_then_generate(self: "ChapterOutlineSection", total_chapters: int):
        """保存总章节数后生成大纲"""
        self.async_helper.execute(
            self.api_client.update_blueprint,
            self.project_id,
            {'total_chapters': total_chapters},
            loading_message="正在保存章节数量...",
            success_message=None,
            error_context="保存章节数量",
            on_success=lambda r: self._on_total_chapters_saved(total_chapters)
        )

    def _on_total_chapters_saved(self: "ChapterOutlineSection", total_chapters: int):
        """总章节数保存成功后继续生成"""
        self.blueprint['total_chapters'] = total_chapters
        self._do_generate_chapter_outlines()

    def _do_generate_chapter_outlines(self: "ChapterOutlineSection"):
        """执行生成章节大纲（使用SSE流式进度）"""
        total_chapters = self.blueprint.get('total_chapters', 0)
        logger.info(f"开始生成全部章节大纲（共{total_chapters}章，使用SSE流式进度）")

        self._progress_dialog = LoadingDialog(
            parent=self,
            title="生成章节大纲",
            message=f"正在准备生成 {total_chapters} 个章节大纲...",
            cancelable=True
        )
        self._progress_dialog.rejected.connect(self._on_chapter_outline_sse_cancelled)
        self._progress_dialog.show()

        url = f"{self.api_client.base_url}/api/novels/{self.project_id}/chapter-outlines/generate-stream"
        payload = {}

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.progress_received.connect(self._on_chapter_outline_progress)
        self._sse_worker.complete.connect(self._on_chapter_outline_complete)
        self._sse_worker.error_data.connect(self._on_chapter_outline_error)
        self._sse_worker.start()

    def _on_chapter_outlines_generated(self: "ChapterOutlineSection", result):
        """章节大纲生成完成"""
        total = result.get('total_chapters', 0)
        MessageService.show_operation_success(self, f"章节大纲生成完成，共{total}章")
        self.refreshRequested.emit()

    def _on_chapter_edit_requested(self: "ChapterOutlineSection", chapter_data: dict):
        """处理章节大纲编辑请求"""
        from ..dialogs import ChapterOutlineEditDialog
        from PyQt6.QtWidgets import QDialog

        chapter_number = chapter_data.get('chapter_number', 0)
        title = chapter_data.get('title', '')
        summary = chapter_data.get('summary', '')

        dialog = ChapterOutlineEditDialog(
            chapter_number=chapter_number,
            title=title,
            summary=summary,
            is_new=False,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_title, new_summary = dialog.get_values()
            self.editRequested.emit(
                f"chapter_outline:{chapter_number}",
                f"第{chapter_number}章大纲",
                {
                    'chapter_number': chapter_number,
                    'original_title': title,
                    'original_summary': summary,
                    'new_title': new_title,
                    'new_summary': new_summary
                }
            )

            # 更新本地数据显示
            for i, outline in enumerate(self.outline):
                if outline.get('chapter_number') == chapter_number:
                    self.outline[i]['title'] = new_title
                    self.outline[i]['summary'] = new_summary
                    break

            if self._chapter_list:
                self._chapter_list.update_data(self.outline)

    def _on_continue_generate_chapters(self: "ChapterOutlineSection"):
        """继续生成N个章节大纲"""
        current_count = len(self.outline)

        # 长篇模式下，检查部分大纲覆盖范围
        needs_part_outlines = self.blueprint.get('needs_part_outlines', False)
        if needs_part_outlines:
            part_outlines = self.blueprint.get('part_outlines', [])
            max_covered_chapter = 0
            for part in part_outlines:
                end_chapter = part.get('end_chapter', 0)
                if end_chapter > max_covered_chapter:
                    max_covered_chapter = end_chapter

            remaining = max_covered_chapter - current_count
            if remaining <= 0:
                if max_covered_chapter < self.blueprint.get('total_chapters', 0):
                    MessageService.show_warning(
                        self,
                        f"当前部分大纲仅覆盖到第{max_covered_chapter}章，\n"
                        f"已生成{current_count}章，无法继续生成。\n\n"
                        f"请先生成更多部分大纲以覆盖后续章节。",
                        "提示"
                    )
                else:
                    MessageService.show_warning(self, "所有章节大纲已生成完成", "提示")
                return

            max_generate = min(remaining, 100)
            label_text = (
                f"当前已生成 {current_count} 章，部分大纲覆盖到第 {max_covered_chapter} 章\n"
                f"还可生成 {remaining} 章\n\n"
                f"请输入要生成的章节数量："
            )
        else:
            total_chapters = self.blueprint.get('total_chapters', 0) or len(self.outline)
            remaining = total_chapters - current_count if total_chapters > 0 else 100
            max_generate = min(remaining, 100) if remaining > 0 else 100
            label_text = "请输入要生成的章节数量："

        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="继续生成章节大纲",
            label=label_text,
            value=min(5, max_generate),
            min_value=1,
            max_value=max_generate
        )
        if not ok:
            return

        logger.info(f"开始继续生成 {count} 个章节大纲（使用SSE流式进度）")

        self._progress_dialog = LoadingDialog(
            parent=self,
            title="生成章节大纲",
            message=f"正在准备生成 {count} 个章节大纲...",
            cancelable=True
        )
        self._progress_dialog.rejected.connect(self._on_chapter_outline_sse_cancelled)
        self._progress_dialog.show()

        url = f"{self.api_client.base_url}/api/writer/novels/{self.project_id}/chapter-outlines/generate-by-count"
        payload = {"count": count}

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.progress_received.connect(self._on_chapter_outline_progress)
        self._sse_worker.complete.connect(self._on_chapter_outline_complete)
        self._sse_worker.error_data.connect(self._on_chapter_outline_error)
        self._sse_worker.start()

    def _on_chapter_outline_progress(self: "ChapterOutlineSection", data: dict):
        """处理章节大纲生成进度更新"""
        if not self._progress_dialog:
            return

        status = data.get('status', '')
        current_batch = data.get('current_batch', 0)
        total_batches = data.get('total_batches', 0)
        generated_count = data.get('generated_count', 0)
        total_count = data.get('total_count', 0)
        current_range = data.get('current_range', '')

        if status == 'starting':
            message = f"正在准备生成...\n{current_range}"
        elif status == 'generating':
            message = f"批次进度: {current_batch}/{total_batches}\n{current_range}\n已完成: {generated_count}/{total_count} 章"
        elif status == 'batch_done':
            message = f"批次进度: {current_batch}/{total_batches}\n{current_range}\n已完成: {generated_count}/{total_count} 章"
        else:
            message = current_range

        self._progress_dialog.setMessage(message)

    def _on_chapter_outline_complete(self: "ChapterOutlineSection", data: dict):
        """章节大纲生成完成"""
        self._cleanup_chapter_outline_sse()

        message = data.get('message', '生成完成')
        generated_chapters = data.get('generated_chapters', [])

        logger.info(f"章节大纲生成完成: {message}, 共{len(generated_chapters)}章")
        MessageService.show_operation_success(self, message)
        self.refreshRequested.emit()

    def _on_chapter_outline_error(self: "ChapterOutlineSection", error_data: dict):
        """章节大纲生成错误"""
        self._cleanup_chapter_outline_sse()

        error_msg = error_data.get('message', '未知错误')
        saved_count = error_data.get('saved_count', 0)
        saved_chapters = error_data.get('saved_chapters', [])

        logger.error(f"章节大纲生成失败: {error_msg}, 已保存 {saved_count} 章")

        if saved_count > 0:
            saved_info = f"\n\n已成功保存 {saved_count} 章大纲（第{min(saved_chapters)}-{max(saved_chapters)}章）。\n刷新页面可查看已保存的内容。"
            MessageService.show_api_error(self, f"{error_msg}{saved_info}", "生成章节大纲")
            self.refreshRequested.emit()
        else:
            MessageService.show_api_error(self, error_msg, "生成章节大纲")

    def _on_chapter_outline_sse_cancelled(self: "ChapterOutlineSection"):
        """用户取消章节大纲生成"""
        logger.info("用户取消章节大纲生成")
        self._cleanup_chapter_outline_sse()

    def _cleanup_chapter_outline_sse(self: "ChapterOutlineSection"):
        """清理章节大纲SSE相关资源"""
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

    def _on_regenerate_latest_chapters(self: "ChapterOutlineSection"):
        """重新生成最新N个章节大纲"""
        if not self.outline:
            MessageService.show_warning(self, "没有章节大纲可以重新生成", "提示")
            return

        max_count = len(self.outline)
        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="重新生成最新N个章节大纲",
            label=f"共有 {max_count} 个章节大纲\n请输入要重新生成的数量（从最后开始）：",
            value=1,
            min_value=1,
            max_value=max_count
        )
        if not ok:
            return

        start_chapter = max_count - count + 1

        if not confirm(
            self,
            f"将重新生成最后 {count} 个章节大纲（第{start_chapter}-{max_count}章）。\n\n"
            f"确定要继续吗？",
            "确认重新生成"
        ):
            return

        prompt, ok = InputDialog.getTextStatic(
            parent=self,
            title="优化提示词（可选）",
            label=f"请输入优化提示词，用于引导AI重新生成章节大纲：",
            placeholder="留空则使用默认生成方式"
        )
        if not ok:
            return

        self.async_helper.execute(
            self.api_client.regenerate_chapter_outline,
            self.project_id, start_chapter,
            prompt=prompt if prompt else None,
            cascade_delete=True,
            loading_message=f"正在重新生成第{start_chapter}章及之后的章节大纲...",
            success_message=f"章节大纲重新生成",
            error_context="重新生成章节大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )

    def _on_delete_latest_chapters(self: "ChapterOutlineSection"):
        """删除最新N个章节大纲"""
        if not self.outline:
            MessageService.show_warning(self, "没有章节大纲可以删除", "提示")
            return

        max_count = len(self.outline)
        count, ok = IntInputDialog.getIntStatic(
            parent=self,
            title="删除最新N个章节大纲",
            label=f"共有 {max_count} 个章节大纲\n请输入要删除的数量（从最后开始）：",
            value=1,
            min_value=1,
            max_value=max_count
        )
        if not ok:
            return

        if not confirm(
            self,
            f"确定要删除最后 {count} 个章节大纲吗？\n\n此操作不可恢复！",
            "确认删除"
        ):
            return

        self.async_helper.execute(
            self.api_client.delete_chapter_outlines,
            self.project_id, count,
            loading_message=f"正在删除 {count} 个章节大纲...",
            success_message=f"删除 {count} 个章节大纲",
            error_context="删除章节大纲",
            on_success=lambda r: self.refreshRequested.emit()
        )


__all__ = [
    "ChapterOutlineHandlerMixin",
]
