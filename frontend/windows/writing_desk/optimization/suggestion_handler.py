"""
建议处理Mixin

处理正文优化建议的应用、忽略等操作。

新模式（v2）：
- 建议产生时立即发送预览信号，在正文中显示预览
- 用户点击"应用"时确认预览
- 用户点击"忽略"时撤销预览
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .content import OptimizationContent
    from ..components.suggestion_card import SuggestionCard

logger = logging.getLogger(__name__)


class SuggestionHandlerMixin:
    """
    建议处理Mixin

    负责：
    - 处理新建议
    - 应用/忽略建议
    - 批量应用建议
    - 预览信号发送（新模式）
    """

    def _handle_suggestion(self: "OptimizationContent", suggestion: dict):
        """处理建议事件 - 根据模式采取不同行为"""
        from .models import OptimizationMode
        from ..components.suggestion_card import SuggestionCard

        self.suggestions.append(suggestion)

        # 更新统计信息
        self._update_suggestion_stats()

        # 创建建议卡片
        card = SuggestionCard(suggestion, parent=self.suggestions_container)
        card.applied.connect(self._on_suggestion_applied)
        card.ignored.connect(self._on_suggestion_ignored)

        # 插入到stretch之前
        if self.suggestions_layout:
            self.suggestions_layout.insertWidget(
                self.suggestions_layout.count() - 1,
                card
            )

        # 在思考流中添加建议提示
        reason = suggestion.get("reason", "发现问题")
        priority = suggestion.get("priority", "medium")
        if self.thinking_stream:
            self.thinking_stream.add_suggestion_hint(reason, priority=priority)

        # 新模式：建议产生时立即发送预览信号
        # 预览信号会触发正文编辑器显示修改预览
        logger.info("SuggestionHandlerMixin: 发送预览信号, 段落=%s", suggestion.get("paragraph_index", -1))
        self.suggestion_preview_requested.emit(suggestion)

        # 根据模式处理
        if self.optimization_mode == OptimizationMode.AUTO:
            # 自动模式：自动应用建议（预览已显示，直接确认）
            card._on_apply()

        elif self.optimization_mode == OptimizationMode.REVIEW:
            # 审核模式：记录当前建议卡片，等待用户确认
            # 后端会发送 workflow_paused 事件来更新UI状态
            self.current_suggestion_card = card

    def _on_suggestion_applied(self: "OptimizationContent", suggestion: dict):
        """建议被应用 - 确认预览"""
        from .models import OptimizationMode

        self.suggestion_applied.emit(suggestion)
        logger.info("应用建议: 段落%d", suggestion.get("paragraph_index", -1))

        # 审核模式下，调用后端继续分析
        if self.optimization_mode == OptimizationMode.REVIEW:
            self._resume_backend_analysis()

    def _on_suggestion_ignored(self: "OptimizationContent", suggestion: dict):
        """建议被忽略 - 撤销预览"""
        from .models import OptimizationMode

        # 发送忽略信号，触发撤销预览
        self.suggestion_ignored.emit(suggestion)
        logger.info("忽略建议: 段落%d", suggestion.get("paragraph_index", -1))

        # 审核模式下，调用后端继续分析
        if self.optimization_mode == OptimizationMode.REVIEW:
            self._resume_backend_analysis()

    def _apply_all(self: "OptimizationContent"):
        """应用全部建议"""
        from ..components.suggestion_card import SuggestionCard

        for i in range(self.suggestions_layout.count() - 1):  # -1 排除stretch
            item = self.suggestions_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, SuggestionCard) and not card.is_applied and not card.is_ignored:
                    card._on_apply()

    def _apply_high_priority(self: "OptimizationContent"):
        """应用高优先级建议"""
        from ..components.suggestion_card import SuggestionCard

        for i in range(self.suggestions_layout.count() - 1):
            item = self.suggestions_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, SuggestionCard) and card.is_high_priority():
                    if not card.is_applied and not card.is_ignored:
                        card._on_apply()


__all__ = [
    "SuggestionHandlerMixin",
]
