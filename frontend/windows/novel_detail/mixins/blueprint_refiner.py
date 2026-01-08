"""
蓝图优化Mixin

负责蓝图优化功能。
"""

import logging
from typing import TYPE_CHECKING

from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService, confirm
from utils.constants import WorkerTimeouts

if TYPE_CHECKING:
    from ..main import NovelDetail

logger = logging.getLogger(__name__)


class BlueprintRefinerMixin:
    """
    蓝图优化Mixin

    负责：
    - 处理蓝图优化请求
    - 显示优化对话框
    - 异步执行优化
    - 处理优化冲突（已有章节大纲时）
    """

    def onRefineBlueprint(self: "NovelDetail"):
        """优化蓝图"""
        from ..dialogs import RefineDialog

        # 检查是否有蓝图 - 使用 _safe_get_blueprint 支持两种项目类型
        blueprint = self._safe_get_blueprint()
        if not self.project_data or not blueprint:
            MessageService.show_warning(self, "请先生成蓝图后再进行优化", "提示")
            return

        # 显示优化对话框
        dialog = RefineDialog(self)
        if dialog.exec() != RefineDialog.DialogCode.Accepted:
            return

        instruction = dialog.getValue()
        if not instruction:
            MessageService.show_warning(self, "请输入优化指令", "提示")
            return

        # 执行优化
        self._doRefineBlueprint(instruction)

    def _doRefineBlueprint(self: "NovelDetail", instruction, force=False):
        """执行蓝图优化(异步方式, 不阻塞UI)

        Args:
            instruction: 优化指令
            force: 是否强制优化(将删除所有章节大纲, 部分大纲, 章节内容)
        """
        from components.dialogs import LoadingDialog

        # 创建加载提示对话框
        loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在优化蓝图...",
            cancelable=True
        )
        loading_dialog.show()

        # 禁用优化按钮，防止重复点击
        if hasattr(self, 'refine_btn') and self.refine_btn:
            self.refine_btn.setEnabled(False)

        # 清理之前的worker（如果有）
        if hasattr(self, 'refine_worker') and self.refine_worker is not None:
            try:
                if self.refine_worker.isRunning():
                    self.refine_worker.cancel()
                    self.refine_worker.quit()
                    self.refine_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                # Worker已被删除，忽略
                pass
            self.refine_worker = None

        # 创建异步worker（传递force参数）
        self.refine_worker = AsyncAPIWorker(
            self.api_client.refine_blueprint,
            self.project_id,
            instruction,
            force=force
        )

        # 成功回调
        def on_success(result):
            loading_dialog.close()
            # 恢复按钮状态
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setEnabled(True)
            # 显示成功消息
            ai_message = result.get('ai_message', '蓝图优化完成')
            MessageService.show_success(self, ai_message)
            # 刷新页面
            self.refreshProject()

        # 错误回调
        def on_error(error_msg):
            loading_dialog.close()
            # 恢复按钮状态
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setEnabled(True)

            # 检查是否是冲突错误（已有章节大纲）
            if "已有" in error_msg and "章节大纲" in error_msg:
                # 显示确认对话框，明确告知会删除所有数据
                if confirm(
                    self,
                    "检测到项目已有章节大纲。\n\n"
                    "优化蓝图将会删除以下所有数据：\n"
                    "- 所有章节大纲\n"
                    "- 所有部分大纲（如有）\n"
                    "- 所有已生成的章节内容\n"
                    "- 所有章节版本\n"
                    "- 向量库数据\n\n"
                    "此操作不可恢复，确定要继续吗？",
                    "确认优化蓝图"
                ):
                    # 用户确认，强制优化
                    self._doRefineBlueprint(instruction, force=True)
            else:
                # 其他错误，直接显示
                MessageService.show_api_error(self, error_msg, "优化蓝图")

        # 取消回调
        def on_cancel():
            try:
                if self.refine_worker and self.refine_worker.isRunning():
                    self.refine_worker.cancel()
                    self.refine_worker.quit()
                    self.refine_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                pass  # C++ 对象已被删除，忽略
            # 恢复按钮状态
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setEnabled(True)

        self.refine_worker.success.connect(on_success)
        self.refine_worker.error.connect(on_error)
        loading_dialog.rejected.connect(on_cancel)
        self.refine_worker.start()


__all__ = [
    "BlueprintRefinerMixin",
]
