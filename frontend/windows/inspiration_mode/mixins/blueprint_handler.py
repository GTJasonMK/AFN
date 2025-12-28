"""
蓝图处理Mixin

负责蓝图的生成、优化和确认流程。
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import InspirationMode

logger = logging.getLogger(__name__)


class BlueprintHandlerMixin:
    """
    蓝图处理Mixin

    负责：
    - 蓝图生成请求和回调
    - 蓝图优化请求和回调
    - Worker清理
    """

    def onGenerateBlueprint(self: "InspirationMode"):
        """生成蓝图"""
        from utils.message_service import MessageService, confirm

        if not self._state.project_id:
            MessageService.show_warning(self, "请先进行对话", "提示")
            return

        # 检查对话是否完成
        if not self._state.is_complete:
            if not confirm(
                self,
                "AI表示还需要更多信息来生成蓝图。\n\n"
                "确定要继续生成吗？将使用「随机生成」模式，AI会自动补全缺失的设定。",
                "对话未完成"
            ):
                return
            # 用户确认使用随机生成模式
            self._do_generate_blueprint(allow_incomplete=True)
            return

        if not confirm(self, "确定要根据当前对话生成蓝图吗？", "确认生成"):
            return

        self._do_generate_blueprint()

    def _do_generate_blueprint(
        self: "InspirationMode",
        force_regenerate: bool = False,
        allow_incomplete: bool = False
    ):
        """执行蓝图生成（异步方式，不阻塞UI）

        Args:
            force_regenerate: 是否强制重新生成（将删除所有章节大纲、部分大纲、章节内容）
            allow_incomplete: 是否允许在灵感对话未完成时生成蓝图（随机生成模式）
        """
        from utils.message_service import MessageService
        from utils.async_worker import AsyncAPIWorker
        from components.dialogs import LoadingDialog

        # 防御性检查：确保项目ID存在
        if not self._state.project_id:
            MessageService.show_warning(self, "请先进行对话创建项目", "提示")
            return

        # 创建加载提示对话框
        self._blueprint_loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在生成蓝图...",
            cancelable=True
        )
        self._blueprint_loading_dialog.show()

        # 禁用生成按钮，防止重复点击
        if hasattr(self, 'generate_btn') and self.generate_btn:
            try:
                self.generate_btn.setEnabled(False)
            except RuntimeError:
                pass

        # 清理之前的worker（如果有）
        self._cleanup_blueprint_worker()

        # 创建异步worker（传递force_regenerate和allow_incomplete参数）
        self.blueprint_worker = AsyncAPIWorker(
            self.api_client.generate_blueprint,
            self._state.project_id,
            force_regenerate=force_regenerate,
            allow_incomplete=allow_incomplete
        )

        self.blueprint_worker.success.connect(self._on_blueprint_success)
        self.blueprint_worker.error.connect(self._on_blueprint_error)
        self._blueprint_loading_dialog.rejected.connect(self._on_blueprint_cancelled)
        self.blueprint_worker.start()

    def _close_blueprint_loading_dialog(self: "InspirationMode"):
        """安全关闭蓝图加载对话框"""
        try:
            if hasattr(self, '_blueprint_loading_dialog') and self._blueprint_loading_dialog:
                if self._blueprint_loading_dialog.isVisible():
                    self._blueprint_loading_dialog.close()
        except RuntimeError:
            pass
        self._blueprint_loading_dialog = None

    def _restore_generate_button(self: "InspirationMode"):
        """恢复生成按钮状态"""
        if hasattr(self, 'generate_btn') and self.generate_btn:
            try:
                self.generate_btn.setEnabled(True)
            except RuntimeError:
                pass

    def _on_blueprint_success(self: "InspirationMode", response):
        """蓝图生成成功回调"""
        from utils.message_service import MessageService

        logger.info("Blueprint generation success")
        self._close_blueprint_loading_dialog()
        self._restore_generate_button()

        try:
            # 验证响应是字典
            if not isinstance(response, dict):
                logger.error("响应数据类型错误，期望dict，实际为%s", type(response).__name__)
                MessageService.show_error(self, "蓝图生成失败：API响应格式错误", "生成蓝图失败")
                return

            # 验证蓝图数据
            self._state.blueprint = response.get('blueprint', {})

            if not isinstance(self._state.blueprint, dict):
                logger.error("蓝图数据类型错误，期望dict，实际为%s", type(self._state.blueprint).__name__)
                MessageService.show_error(self, "蓝图生成失败：蓝图数据格式错误", "生成蓝图失败")
                self._state.blueprint = {}
                return

            if not self._state.blueprint:
                MessageService.show_error(self, "蓝图生成失败：蓝图数据为空", "生成蓝图失败")
                return

            # 验证蓝图必需字段
            required_fields = ['world_setting', 'characters']
            missing_fields = [f for f in required_fields if not self._state.blueprint.get(f)]
            if missing_fields:
                MessageService.show_error(
                    self,
                    f"蓝图数据不完整，缺少字段：{', '.join(missing_fields)}",
                    "生成蓝图失败"
                )
                return

            # 更新蓝图数据并切换页面
            if hasattr(self, 'confirmation_page') and self.confirmation_page:
                self.confirmation_page.setBlueprint(self._state.blueprint)

            self._show_confirmation_page()
            logger.info("Blueprint generation completed successfully")

        except Exception as e:
            logger.error("处理蓝图数据失败: %s", str(e), exc_info=True)
            MessageService.show_error(self, f"处理蓝图数据失败：{str(e)}", "生成蓝图失败")

    def _on_blueprint_error(self: "InspirationMode", error_msg):
        """蓝图生成错误回调"""
        from utils.message_service import MessageService, confirm

        logger.info("Blueprint generation error: %s", error_msg[:100] if error_msg else "empty")
        self._close_blueprint_loading_dialog()
        self._restore_generate_button()

        # 检查是否是冲突错误（已有章节大纲）
        if "已有" in error_msg and "章节大纲" in error_msg:
            # 显示确认对话框，明确告知会删除所有数据
            if confirm(
                self,
                "检测到项目已有章节大纲。\n\n"
                "重新生成蓝图将会删除以下所有数据：\n"
                "* 所有章节大纲\n"
                "* 所有部分大纲（如有）\n"
                "* 所有已生成的章节内容\n"
                "* 所有章节版本\n"
                "* 向量库数据\n\n"
                "此操作不可恢复，确定要继续吗？",
                "确认重新生成蓝图"
            ):
                # 用户确认，强制重新生成
                self._do_generate_blueprint(force_regenerate=True)
        else:
            # 其他错误，直接显示
            MessageService.show_error(self, f"生成蓝图失败：{error_msg}", "生成蓝图失败")

    def _on_blueprint_cancelled(self: "InspirationMode"):
        """蓝图生成取消回调"""
        self._cleanup_blueprint_worker()
        self._restore_generate_button()

    def _cleanup_blueprint_worker(self: "InspirationMode"):
        """清理蓝图生成worker"""
        from utils.constants import WorkerTimeouts

        if self.blueprint_worker:
            try:
                # 断开信号连接
                try:
                    self.blueprint_worker.success.disconnect()
                    self.blueprint_worker.error.disconnect()
                except (TypeError, RuntimeError):
                    pass  # 信号可能已经断开或对象已删除

                if self.blueprint_worker.isRunning():
                    self.blueprint_worker.cancel()
                    self.blueprint_worker.quit()
                    self.blueprint_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                pass  # C++ 对象可能已被删除
            finally:
                self.blueprint_worker = None

    def onBlueprintConfirmed(self: "InspirationMode"):
        """蓝图确认"""
        # 使用navigateReplace跳转到项目详情页
        # 这样返回时会跳过灵感对话页面，直接返回首页
        self.navigateReplace('DETAIL', project_id=self._state.project_id)

    def onBlueprintRejected(self: "InspirationMode"):
        """重新生成蓝图 - 使用refine API直接优化"""
        from components.dialogs import TextInputDialog

        # 显示输入对话框获取优化方向
        optimization_prompt, ok = TextInputDialog.getTextStatic(
            parent=self,
            title="重新生成蓝图",
            label="请输入您希望的优化方向：\n\n"
                  "（可选，留空则按原设定重新生成）",
            placeholder="示例：增加更多悬念、调整角色关系、修改结局走向、深化世界观设定"
        )

        if not ok:
            return  # 用户取消

        # 如果用户输入了优化方向，使用refine API直接优化
        if optimization_prompt.strip():
            self._do_refine_blueprint(optimization_prompt.strip())
        else:
            # 没有输入优化方向，直接重新生成
            self._do_generate_blueprint(force_regenerate=True)

    def _do_refine_blueprint(self: "InspirationMode", refinement_instruction: str):
        """使用refine API优化蓝图

        Args:
            refinement_instruction: 用户输入的优化方向
        """
        from components.dialogs import LoadingDialog
        from utils.async_worker import AsyncAPIWorker

        # 创建加载对话框
        self._refine_loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在优化蓝图...",
            cancelable=True
        )
        self._refine_loading_dialog.show()

        # 禁用按钮
        if hasattr(self, 'generate_btn') and self.generate_btn:
            try:
                self.generate_btn.setEnabled(False)
            except RuntimeError:
                pass

        # 清理之前的worker（如果有）
        self._cleanup_refine_worker()

        # 创建异步worker
        self._refine_worker = AsyncAPIWorker(
            self.api_client.refine_blueprint,
            self._state.project_id,
            refinement_instruction,
            force=True  # 强制优化，允许删除已有数据
        )

        self._refine_worker.success.connect(self._on_refine_success)
        self._refine_worker.error.connect(self._on_refine_error)
        self._refine_loading_dialog.rejected.connect(self._on_refine_cancelled)
        self._refine_worker.start()

    def _close_refine_loading_dialog(self: "InspirationMode"):
        """安全关闭优化蓝图加载对话框"""
        try:
            if hasattr(self, '_refine_loading_dialog') and self._refine_loading_dialog:
                if self._refine_loading_dialog.isVisible():
                    self._refine_loading_dialog.close()
        except RuntimeError:
            pass
        self._refine_loading_dialog = None

    def _cleanup_refine_worker(self: "InspirationMode"):
        """清理优化蓝图worker"""
        from utils.constants import WorkerTimeouts

        if hasattr(self, '_refine_worker') and self._refine_worker:
            try:
                try:
                    self._refine_worker.success.disconnect()
                    self._refine_worker.error.disconnect()
                except (TypeError, RuntimeError):
                    pass

                if self._refine_worker.isRunning():
                    self._refine_worker.cancel()
                    self._refine_worker.quit()
                    self._refine_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                pass
            finally:
                self._refine_worker = None

    def _on_refine_success(self: "InspirationMode", response):
        """蓝图优化成功回调"""
        from utils.message_service import MessageService

        logger.info("Blueprint refine success")
        self._close_refine_loading_dialog()
        self._restore_generate_button()

        try:
            # 获取优化后的蓝图
            self._state.blueprint = response.get('blueprint', {})
            if not self._state.blueprint:
                MessageService.show_error(self, "蓝图优化失败：蓝图数据为空", "优化失败")
                return

            # 更新确认页面并显示
            if hasattr(self, 'confirmation_page') and self.confirmation_page:
                self.confirmation_page.setBlueprint(self._state.blueprint)
            self._show_confirmation_page()

            # 显示成功消息
            ai_message = response.get('ai_message', '')
            if ai_message:
                MessageService.show_success(self, ai_message)

        except Exception as e:
            logger.error("处理优化蓝图数据失败: %s", str(e), exc_info=True)
            MessageService.show_error(self, f"处理蓝图数据失败：{str(e)}", "优化失败")

    def _on_refine_error(self: "InspirationMode", error_msg):
        """蓝图优化错误回调"""
        from utils.message_service import MessageService

        logger.error("Blueprint refine error: %s", error_msg[:100] if error_msg else "empty")
        self._close_refine_loading_dialog()
        self._restore_generate_button()
        MessageService.show_error(self, f"蓝图优化失败：{error_msg}", "优化失败")

    def _on_refine_cancelled(self: "InspirationMode"):
        """蓝图优化取消回调"""
        self._cleanup_refine_worker()
        self._restore_generate_button()


__all__ = [
    "BlueprintHandlerMixin",
]
