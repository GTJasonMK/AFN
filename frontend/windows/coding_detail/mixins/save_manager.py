"""
保存管理Mixin

负责编程项目详情页的保存功能。
"""

import logging
from typing import TYPE_CHECKING

from themes.theme_manager import theme_manager
from utils.message_service import MessageService
from utils.async_worker import AsyncAPIWorker
from utils.dpi_utils import dp

if TYPE_CHECKING:
    from ..main import CodingDetail

logger = logging.getLogger(__name__)


class SaveManagerMixin:
    """保存管理Mixin

    负责：
    - 保存修改
    - 检查未保存的修改
    - 更新保存按钮状态
    """

    def onSaveAll(self: "CodingDetail"):
        """保存所有修改"""
        if not self.dirty_tracker.is_dirty():
            MessageService.show_info(self, "没有需要保存的修改", "提示")
            return

        dirty_data = self.dirty_tracker.get_dirty_data()
        summary = self.dirty_tracker.get_dirty_summary()

        logger.info(f"保存修改: {summary}")

        # 准备更新数据
        blueprint_updates = dirty_data.get('blueprint_updates', {})

        if not blueprint_updates:
            MessageService.show_info(self, "没有需要保存的修改", "提示")
            return

        # 调用API保存 - 使用batch_update_blueprint
        self.show_loading("正在保存...")

        try:
            # 使用现有的batch_update_blueprint方法，传入coding_blueprint_updates
            worker = AsyncAPIWorker(
                self.api_client.batch_update_blueprint,
                self.project_id,
                blueprint_updates,  # 会被解析为coding_blueprint更新
                None  # chapter_outline_updates
            )
            worker.success.connect(self._onSaveSuccess)
            worker.error.connect(self._onSaveError)

            self._workers.append(worker)
            worker.start()
        except Exception as e:
            self.hide_loading()
            logger.error(f"保存失败: {e}")
            MessageService.show_error(self, f"保存功能暂未完全实现：{e}", "提示")

    def _onSaveSuccess(self: "CodingDetail", response):
        """保存成功"""
        self.hide_loading()
        self.dirty_tracker.reset()
        self._updateSaveButtonStyle()
        MessageService.show_success(self, "保存成功", "提示")
        logger.info("保存成功")

        # 刷新项目数据
        self.refreshProject()

    def _onSaveError(self: "CodingDetail", error_msg):
        """保存失败"""
        self.hide_loading()
        logger.error(f"保存失败: {error_msg}")
        MessageService.show_error(self, f"保存失败：{error_msg}", "错误")

    def _updateSaveButtonStyle(self: "CodingDetail"):
        """更新保存按钮样式"""
        if not hasattr(self, 'save_btn') or not self.save_btn:
            return

        is_dirty = self.dirty_tracker.is_dirty()

        if is_dirty:
            # 有未保存修改，高亮显示
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.WARNING};
                    color: white;
                    border: none;
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {dp(13)}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.WARNING}DD;
                }}
            """)
            summary = self.dirty_tracker.get_dirty_summary()
            self.save_btn.setToolTip(f"有未保存的修改：{summary}")
        else:
            # 无修改，普通样式
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.book_bg_secondary()};
                    color: {theme_manager.TEXT_PRIMARY};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {dp(13)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.PRIMARY}20;
                    border-color: {theme_manager.PRIMARY};
                }}
            """)
            self.save_btn.setToolTip("保存修改")


__all__ = ["SaveManagerMixin"]
