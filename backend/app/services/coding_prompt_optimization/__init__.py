"""
编程项目 Prompt 优化服务

基于 ReAct Agent 模式的 Prompt 质量分析和优化系统。

主要组件：
- PromptOptimizationWorkflow: 工作流协调器，主入口
- PromptOptimizationAgent: ReAct Agent 核心
- ToolExecutor: 工具执行器
- PromptChecker: LLM 深度检查器

使用方式：
    workflow = PromptOptimizationWorkflow(
        session=db_session,
        llm_service=llm_service,
        vector_store=vector_store,
        user_id=user_id,
    )

    async for event in workflow.start_optimization(
        feature_id=feature_id,
        dimensions=["completeness", "interface"],
        mode=OptimizationMode.AUTO,
    ):
        # 处理 SSE 事件
        pass
"""

from .agent import PromptOptimizationAgent, sse_event
from .prompt_checker import PromptChecker
from .schemas import (
    DEFAULT_DIMENSIONS,
    DEFAULT_REVIEW_DIMENSIONS,
    DIMENSION_DISPLAY_NAMES,
    DIMENSION_KEYWORDS,
    DIMENSION_WEIGHTS,
    FeatureContext,
    OptimizationContext,
    OptimizationEventType,
    OptimizationMode,
    OptimizationSessionInfo,
    OptimizePromptRequest,
    ProjectContext,
    PromptDimension,
    PromptType,
    ReviewDimension,
    REVIEW_DIMENSION_DISPLAY_NAMES,
    REVIEW_DIMENSION_KEYWORDS,
    REVIEW_DIMENSION_WEIGHTS,
    StructuredThinking,
    Suggestion,
    SuggestionSeverity,
    ThinkingStep,
    ThinkingStepType,
    detect_dimension_from_text,
    get_all_dimension_names,
    get_default_dimensions,
    get_dimension_display_name,
    get_dimension_weight,
)
from .tool_executor import AgentState, ToolExecutor
from .tools import (
    TOOL_DEFINITIONS,
    ToolCall,
    ToolCallParseResult,
    ToolDefinition,
    ToolName,
    ToolResult,
    get_tools_prompt,
    parse_thinking,
    parse_tool_call,
)
from .workflow import PromptOptimizationWorkflow

__all__ = [
    # 工作流
    "PromptOptimizationWorkflow",
    # Agent
    "PromptOptimizationAgent",
    "sse_event",
    # 工具
    "ToolExecutor",
    "AgentState",
    "ToolName",
    "ToolDefinition",
    "TOOL_DEFINITIONS",
    "ToolCall",
    "ToolCallParseResult",
    "ToolResult",
    "get_tools_prompt",
    "parse_tool_call",
    "parse_thinking",
    # 检查器
    "PromptChecker",
    # 数据模型
    "PromptType",
    "PromptDimension",
    "ReviewDimension",
    "DIMENSION_DISPLAY_NAMES",
    "DIMENSION_WEIGHTS",
    "DIMENSION_KEYWORDS",
    "DEFAULT_DIMENSIONS",
    "REVIEW_DIMENSION_DISPLAY_NAMES",
    "REVIEW_DIMENSION_WEIGHTS",
    "REVIEW_DIMENSION_KEYWORDS",
    "DEFAULT_REVIEW_DIMENSIONS",
    "get_dimension_weight",
    "get_dimension_display_name",
    "get_default_dimensions",
    "get_all_dimension_names",
    "detect_dimension_from_text",
    "OptimizationMode",
    "OptimizationEventType",
    "FeatureContext",
    "ProjectContext",
    "OptimizationContext",
    "SuggestionSeverity",
    "Suggestion",
    "ThinkingStepType",
    "ThinkingStep",
    "StructuredThinking",
    "OptimizePromptRequest",
    "OptimizationSessionInfo",
]
