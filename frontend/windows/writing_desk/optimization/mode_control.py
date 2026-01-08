"""
模式控制Mixin

处理优化模式选择和后端会话控制。
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .content import OptimizationContent

logger = logging.getLogger(__name__)


class ModeControlMixin:
    """
    模式控制Mixin

    负责：
    - 模式选择
    - 后端会话控制（暂停/继续/取消）
    """

    def _get_selected_mode(self: "OptimizationContent"):
        """获取当前选择的优化模式"""
        from .models import OptimizationMode

        if self.mode_group:
            checked_id = self.mode_group.checkedId()
            if checked_id == 0:
                return OptimizationMode.REVIEW
            elif checked_id == 1:
                return OptimizationMode.AUTO
            elif checked_id == 2:
                return OptimizationMode.PLAN
        return OptimizationMode.REVIEW

    def _resume_backend_analysis(self: "OptimizationContent"):
        """通知后端继续分析"""
        from api.client import AFNAPIClient

        if not self.session_id:
            logger.warning("无法继续分析：session_id 为空")
            return

        self.current_suggestion_card = None

        # 调用后端 continue API
        try:
            client = AFNAPIClient()
            result = client.continue_optimization_session(self.session_id)
            logger.info("继续分析: %s", result)
        except Exception as e:
            logger.error("调用 continue API 失败: %s", e)
            self._update_status(f"继续分析失败: {e}")

    def _continue_analysis(self: "OptimizationContent"):
        """继续分析（用户点击继续按钮）"""
        # 如果有当前建议卡片且未处理，自动忽略
        if self.current_suggestion_card and not self.current_suggestion_card.is_applied:
            if not self.current_suggestion_card.is_ignored:
                self.current_suggestion_card._on_ignore()
                return  # _on_ignore 会触发 _on_suggestion_ignored，进而调用 _resume_backend_analysis

        # 直接调用后端继续
        self._resume_backend_analysis()

    def _stop_optimization(self: "OptimizationContent"):
        """停止优化"""
        from api.client import AFNAPIClient

        logger.info("停止优化: is_optimizing=%s, session_id=%s, sse_worker=%s",
                    self.is_optimizing, self.session_id, self.sse_worker is not None)

        # 先停止SSE连接（这是最重要的，会中断数据流）
        if self.sse_worker:
            try:
                logger.info("正在停止SSE Worker...")
                self.sse_worker.stop()
                logger.info("SSE Worker已停止")
            except RuntimeError as e:
                # C++对象已被删除
                logger.warning("停止SSE Worker时对象已被删除: %s", e)
            except Exception as e:
                logger.error("停止SSE Worker时发生错误: %s", e)
            finally:
                self.sse_worker = None

        # 取消后端会话（如果有的话）
        if self.session_id:
            try:
                client = AFNAPIClient()
                result = client.cancel_optimization_session(self.session_id)
                logger.info("已取消后端会话: %s, 结果: %s", self.session_id, result)
            except Exception as e:
                logger.warning("取消后端会话失败: %s", e)

        # 更新状态
        self.is_optimizing = False
        self.session_id = None

        # 更新UI
        if self.continue_btn:
            self.continue_btn.setVisible(False)
        if self.apply_plan_btn:
            self.apply_plan_btn.setVisible(False)

        # 更新思考流状态
        if hasattr(self, 'thinking_stream') and self.thinking_stream:
            self.thinking_stream.set_status("error")
            self.thinking_stream.add_progress("已停止分析")

        self._update_status("已停止")
        logger.info("优化已停止")


__all__ = [
    "ModeControlMixin",
]
