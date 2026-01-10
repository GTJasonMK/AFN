"""
SSE事件处理Mixin

处理正文优化过程中的SSE流式事件。
"""

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .content import OptimizationContent

logger = logging.getLogger(__name__)


class SSEHandlerMixin:
    """
    SSE事件处理Mixin

    处理后端发送的各种SSE事件：
    - workflow_start: 工作流开始
    - workflow_paused: 工作流暂停（审核模式）
    - workflow_resumed: 工作流恢复
    - paragraph_start: 开始分析段落
    - thinking: 思考过程
    - action: 执行动作
    - observation: 观察结果
    - suggestion: 建议
    - workflow_complete: 工作流完成
    - error: 错误
    """

    def _on_sse_event(self: "OptimizationContent", event_type: str, data: dict):
        """处理SSE事件"""
        # 后端现在负责暂停控制，直接处理所有事件
        self._process_sse_event(event_type, data)

    def _process_sse_event(self: "OptimizationContent", event_type: str, data: dict):
        """实际处理SSE事件"""
        if event_type == "workflow_start":
            self._handle_workflow_start(data)

        elif event_type == "workflow_paused":
            self._handle_workflow_paused()

        elif event_type == "workflow_resumed":
            self._handle_workflow_resumed()

        elif event_type == "paragraph_start":
            self._handle_paragraph_start(data)

        elif event_type == "thinking":
            self._handle_thinking(data)

        elif event_type == "action":
            self._handle_action(data)

        elif event_type == "observation":
            self._handle_observation(data)

        elif event_type == "suggestion":
            self._handle_suggestion(data)

        elif event_type == "paragraph_complete":
            self._handle_paragraph_complete(data)

        elif event_type == "workflow_complete":
            self._handle_workflow_complete(data)

        elif event_type == "error":
            self._handle_error(data)

    def _handle_workflow_start(self: "OptimizationContent", data: dict):
        """处理工作流开始事件"""
        # 保存会话ID用于暂停/继续控制
        self.session_id = data.get("session_id", "")
        total = data.get("total_paragraphs", 0)
        dimensions = data.get("dimensions", [])
        mode = data.get("mode", "auto")

        if self.thinking_stream:
            self.thinking_stream.on_workflow_start(total, dimensions)

        # 根据模式显示不同提示
        mode_names = {"auto": "自动模式", "review": "审核模式"}
        mode_name = mode_names.get(mode, mode)
        self._update_status(f"正在分析（{mode_name}）...")

    def _handle_workflow_paused(self: "OptimizationContent"):
        """处理工作流暂停事件"""
        self._update_status("等待处理建议...")
        if self.thinking_stream:
            self.thinking_stream.on_workflow_paused()
        # 显示继续分析按钮
        if self.continue_btn:
            self.continue_btn.setVisible(True)

    def _handle_workflow_resumed(self: "OptimizationContent"):
        """处理工作流恢复事件"""
        self._update_status("正在分析...")
        if self.thinking_stream:
            self.thinking_stream.on_workflow_resumed()
        # 隐藏继续分析按钮
        if self.continue_btn:
            self.continue_btn.setVisible(False)

    def _handle_paragraph_start(self: "OptimizationContent", data: dict):
        """处理段落开始事件"""
        index = data.get("index", 0)
        preview = data.get("text_preview", "")
        if self.thinking_stream:
            self.thinking_stream.set_current_paragraph(index, preview)

    def _handle_paragraph_complete(self: "OptimizationContent", data: dict):
        """处理段落完成事件"""
        index = data.get("index", 0)
        suggestion_count = data.get("suggestions_count", 0)
        if self.thinking_stream:
            self.thinking_stream.add_progress(
                f"第 {index + 1} 段分析完成，发现 {suggestion_count} 条建议"
            )

    def _handle_thinking(self: "OptimizationContent", data: dict):
        """处理思考事件"""
        content = data.get("content", "")
        step = data.get("step", "")
        # 获取结构化信息
        structured = data.get("structured")
        primary_dimension = data.get("primary_dimension")

        if self.thinking_stream:
            # 如果有结构化数据，可以提取更多细节
            details = []
            if structured and structured.get("steps"):
                for s in structured["steps"][:3]:  # 只显示前3个步骤
                    step_content = s.get("content", "")[:50]
                    if step_content:
                        details.append(step_content)

            self.thinking_stream.add_thinking(content, step, details=details if details else None)

    def _handle_action(self: "OptimizationContent", data: dict):
        """处理动作事件"""
        action = data.get("action", "")
        description = data.get("description", "")
        if self.thinking_stream:
            self.thinking_stream.add_action(action, description)

    def _handle_observation(self: "OptimizationContent", data: dict):
        """处理观察事件"""
        result = data.get("result", "")
        success = data.get("success", True)
        if self.thinking_stream:
            if success:
                self.thinking_stream.add_observation(result)
            else:
                self.thinking_stream.add_error(f"观察失败: {result}")

    def _handle_workflow_complete(self: "OptimizationContent", data: dict):
        """处理工作流完成事件"""
        total = data.get("total_suggestions", 0)
        summary = data.get("summary", "")
        if self.thinking_stream:
            self.thinking_stream.on_workflow_complete(total, summary)
        self._on_workflow_complete(total, summary)

    def _handle_error(self: "OptimizationContent", data: dict):
        """处理错误事件"""
        message = data.get("message", "未知错误")
        self._update_status(f"错误: {message}")
        if self.thinking_stream:
            self.thinking_stream.add_error(message)
        logger.error("优化错误: %s", message)

    def _on_sse_error(self: "OptimizationContent", error_msg: str):
        """处理SSE错误"""
        self.is_optimizing = False
        self._update_status(f"连接错误: {error_msg}")
        if self.thinking_stream:
            self.thinking_stream.add_error(error_msg)
        logger.error("SSE错误: %s", error_msg)

    def _on_sse_complete(self: "OptimizationContent"):
        """SSE完成"""
        self.is_optimizing = False
        self.sse_worker = None

        # 启用应用按钮
        if self.suggestions:
            if self.apply_all_btn:
                self.apply_all_btn.setEnabled(True)
            high_count = sum(1 for s in self.suggestions if s.get("priority") == "high")
            if high_count > 0 and self.apply_high_btn:
                self.apply_high_btn.setEnabled(True)

        # 隐藏继续按钮
        if self.continue_btn:
            self.continue_btn.setVisible(False)

    def _on_workflow_complete(self: "OptimizationContent", total_suggestions: int, summary: str):
        """工作流完成回调"""
        self._update_status(summary)

        # 隐藏控制按钮
        if self.continue_btn:
            self.continue_btn.setVisible(False)


__all__ = [
    "SSEHandlerMixin",
]
