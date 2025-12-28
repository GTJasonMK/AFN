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

        # 取消后端会话
        if self.session_id:
            try:
                client = AFNAPIClient()
                client.cancel_optimization_session(self.session_id)
                logger.info("已取消后端会话: %s", self.session_id)
            except Exception as e:
                logger.warning("取消后端会话失败: %s", e)

        # 停止SSE连接
        if self.sse_worker:
            try:
                self.sse_worker.stop()
            except RuntimeError:
                # C++对象已被删除
                pass
            self.sse_worker = None

        self.is_optimizing = False
        self.session_id = None
        if self.continue_btn:
            self.continue_btn.setVisible(False)
        self._update_status("已停止")


__all__ = [
    "ModeControlMixin",
]
