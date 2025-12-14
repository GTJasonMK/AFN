"""
正文优化服务模块

使用Agent驱动的方式进行章节内容分析和优化：
- Agent自主决定调用哪些工具
- 根据环境反馈决定下一步行动
- 支持多种检查维度：逻辑连贯性、角色一致性、伏笔呼应等

架构：
- Agent: 核心决策循环
- Tools: 可调用的工具集
- ToolExecutor: 工具执行器
- Workflow: 工作流协调
"""

from .service import ContentOptimizationService
from .workflow import ContentOptimizationWorkflow, LegacyContentOptimizationWorkflow
from .agent import ContentOptimizationAgent
from .tools import ToolName, ToolCall, ToolResult, get_tools_prompt
from .tool_executor import ToolExecutor, AgentState
from .schemas import (
    OptimizeContentRequest,
    CheckDimension,
    AnalysisScope,
    OptimizationEventType,
)

__all__ = [
    # 服务入口
    "ContentOptimizationService",
    # 工作流
    "ContentOptimizationWorkflow",
    "LegacyContentOptimizationWorkflow",
    # Agent核心
    "ContentOptimizationAgent",
    "ToolExecutor",
    "AgentState",
    # 工具
    "ToolName",
    "ToolCall",
    "ToolResult",
    "get_tools_prompt",
    # 数据模型
    "OptimizeContentRequest",
    "CheckDimension",
    "AnalysisScope",
    "OptimizationEventType",
]
