"""
RAG管理Mixin

负责小说项目RAG数据的同步和管理。
"""

import logging
from typing import TYPE_CHECKING

from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService

if TYPE_CHECKING:
    from ..main import NovelDetail

logger = logging.getLogger(__name__)


class RAGManagerMixin:
    """
    RAG管理Mixin

    负责：
    - 检查RAG完整性
    - 同步/入库RAG数据
    - 显示同步进度和结果
    """

    def onSyncRAG(self: "NovelDetail"):
        """RAG同步按钮点击处理"""
        if not self.project_id:
            MessageService.show_warning(self, "请先选择项目")
            return

        # 禁用按钮，显示加载状态
        if hasattr(self, 'rag_sync_btn') and self.rag_sync_btn:
            self.rag_sync_btn.setEnabled(False)
            self.rag_sync_btn.setText("同步中...")

        # 先检查完整性，然后根据结果决定是否需要入库
        self._check_and_sync_rag()

    def _check_and_sync_rag(self: "NovelDetail"):
        """检查完整性并同步"""
        self._rag_worker = AsyncAPIWorker(
            self.api_client.check_rag_completeness,
            self.project_id
        )
        self._rag_worker.success.connect(self._on_completeness_check_done)
        self._rag_worker.error.connect(self._on_rag_error)
        self._rag_worker.start()

    def _on_completeness_check_done(self: "NovelDetail", result: dict):
        """完整性检查完成"""
        is_complete = result.get('complete', False)
        has_changes = result.get('has_changes', False)

        if is_complete and not has_changes:
            # RAG数据已完整，无需同步
            MessageService.show_success(self, "RAG数据已完整，无需同步")
            self._restore_rag_button()
            return

        # 需要同步，显示详情并开始入库
        type_details = result.get('type_details', {})
        changes_summary = self._format_changes_summary(type_details)

        logger.info("RAG需要同步: %s", changes_summary)

        # 开始入库
        self._do_rag_ingest()

    def _format_changes_summary(self, type_details: dict) -> str:
        """格式化变更摘要"""
        new_count = 0
        modified_count = 0

        for type_name, details in type_details.items():
            if isinstance(details, dict):
                new_count += details.get('new_count', 0)
                modified_count += details.get('modified_count', 0)

        parts = []
        if new_count > 0:
            parts.append(f"新增{new_count}条")
        if modified_count > 0:
            parts.append(f"更新{modified_count}条")

        return ", ".join(parts) if parts else "需要同步"

    def _do_rag_ingest(self: "NovelDetail"):
        """执行RAG入库"""
        self._rag_worker = AsyncAPIWorker(
            self.api_client.ingest_all_rag,
            self.project_id,
            False  # force=False, 只入库缺失的数据
        )
        self._rag_worker.success.connect(self._on_rag_ingest_done)
        self._rag_worker.error.connect(self._on_rag_error)
        self._rag_worker.start()

    def _on_rag_ingest_done(self: "NovelDetail", result: dict):
        """RAG入库完成"""
        self._restore_rag_button()

        # 统计入库结果
        total_added = 0
        total_updated = 0
        total_failed = 0

        results = result.get('results', {})
        for type_name, type_result in results.items():
            if isinstance(type_result, dict):
                total_added += type_result.get('added_count', 0)
                total_updated += type_result.get('updated_count', 0)
                total_failed += type_result.get('failed_count', 0)

        # 刷新项目数据（分析数据已更新）
        self.loadProjectBasicInfo()

        # 显示结果
        if total_failed > 0:
            MessageService.show_warning(
                self,
                f"RAG同步完成，但有{total_failed}条记录失败\n"
                f"成功: 新增{total_added}条，更新{total_updated}条"
            )
        elif total_added > 0 or total_updated > 0:
            MessageService.show_success(
                self,
                f"RAG同步成功\n新增{total_added}条，更新{total_updated}条"
            )
        else:
            MessageService.show_success(self, "RAG数据已是最新")

    def _on_rag_error(self: "NovelDetail", error_msg: str):
        """RAG操作错误"""
        self._restore_rag_button()
        MessageService.show_error(self, f"RAG同步失败: {error_msg}")
        logger.error("RAG同步失败: %s", error_msg)

    def _restore_rag_button(self: "NovelDetail"):
        """恢复RAG按钮状态"""
        if hasattr(self, 'rag_sync_btn') and self.rag_sync_btn:
            self.rag_sync_btn.setEnabled(True)
            self.rag_sync_btn.setText("RAG同步")


__all__ = [
    "RAGManagerMixin",
]
