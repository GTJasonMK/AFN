"""
编程项目 Prompt 优化 - ReAct Agent 核心

实现思考-决策-行动-观察循环的 Agent。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..content_optimization.session_manager import get_session_manager
from .schemas import (
    OptimizationContext,
    OptimizationEventType,
    OptimizationMode,
    PromptType,
    StructuredThinking,
    DIMENSION_DISPLAY_NAMES,
    REVIEW_DIMENSION_DISPLAY_NAMES,
    get_all_dimension_names,
)
from .tools import (
    ToolName,
    get_tools_prompt,
    parse_thinking,
    parse_tool_call,
)
from .tool_executor import AgentState, ToolExecutor

logger = logging.getLogger(__name__)

# Agent 限制常量
MAX_ITERATIONS = 50                     # 最大迭代次数
MAX_CONSECUTIVE_PARSE_ERRORS = 3        # 连续解析错误容限
MAX_CONVERSATION_HISTORY_ROUNDS = 15    # 对话历史窗口大小


def sse_event(event_type: str, data: Any) -> str:
    """生成 SSE 事件"""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"


class PromptOptimizationAgent:
    """
    Prompt 优化 Agent

    使用 ReAct（推理+行动）模式对编程项目的功能 Prompt 进行质量检查和优化。
    """

    def __init__(
        self,
        llm_service: Any,
        tool_executor: ToolExecutor,
        optimization_mode: OptimizationMode = OptimizationMode.AUTO,
        session_id: Optional[str] = None,
        prompt_type: PromptType = PromptType.IMPLEMENTATION,
    ):
        self.llm_service = llm_service
        self.tool_executor = tool_executor
        self.optimization_mode = optimization_mode
        self.session_id = session_id
        self.prompt_type = prompt_type
        self.session_manager = get_session_manager()

    async def run(
        self,
        state: AgentState,
        dimensions: List[str],
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        运行 Agent

        Args:
            state: Agent 状态
            dimensions: 要检查的维度列表
            user_id: 用户 ID

        Yields:
            SSE 事件字符串
        """
        # 发送工作流开始事件
        dimension_names_map = get_all_dimension_names(self.prompt_type)
        yield sse_event(OptimizationEventType.WORKFLOW_START, {
            "session_id": self.session_id,
            "feature_id": state.feature_id,
            "feature_name": state.context.feature.feature_name,
            "dimensions": dimensions,
            "dimension_names": [dimension_names_map.get(d, d) for d in dimensions],
            "mode": self.optimization_mode.value,
            "prompt_type": self.prompt_type.value,
            "prompt_length": len(state.prompt_content),
        })

        # 构建系统提示词
        system_prompt = self._build_system_prompt(dimensions)

        # 初始化对话历史
        conversation_history: List[Dict[str, str]] = []

        # 构建初始用户消息
        initial_message = self._build_initial_message(state, dimensions)
        conversation_history.append({"role": "user", "content": initial_message})

        # Agent 循环
        iteration = 0
        consecutive_parse_errors = 0

        while iteration < MAX_ITERATIONS and not state.is_complete:
            iteration += 1
            logger.info("Agent 迭代 %d/%d", iteration, MAX_ITERATIONS)

            try:
                # 调用 LLM
                response = await self._get_agent_response(
                    system_prompt=system_prompt,
                    conversation_history=conversation_history,
                    user_id=user_id,
                )

                if not response:
                    logger.warning("LLM 返回空响应")
                    continue

                # 解析思考过程
                thinking_text = parse_thinking(response)
                if thinking_text:
                    structured_thinking = StructuredThinking.parse_from_text(thinking_text)
                    yield sse_event(OptimizationEventType.THINKING, {
                        "iteration": iteration,
                        "raw_content": thinking_text,
                        "steps": [
                            {
                                "step_type": step.step_type.value,
                                "content": step.content,
                                "confidence": step.confidence,
                                "related_dimension": step.related_dimension,
                            }
                            for step in structured_thinking.steps
                        ],
                        "summary": structured_thinking.summary,
                    })

                # 解析工具调用
                parse_result = parse_tool_call(response)

                if not parse_result.success:
                    if parse_result.is_parse_error:
                        consecutive_parse_errors += 1
                        logger.warning(
                            "工具调用解析错误 (%d/%d): %s",
                            consecutive_parse_errors,
                            MAX_CONSECUTIVE_PARSE_ERRORS,
                            parse_result.error,
                        )

                        if consecutive_parse_errors >= MAX_CONSECUTIVE_PARSE_ERRORS:
                            # 放弃重试，提示 Agent 并继续
                            conversation_history.append({
                                "role": "assistant",
                                "content": response,
                            })
                            conversation_history.append({
                                "role": "user",
                                "content": f"工具调用格式错误，请使用正确的格式。错误: {parse_result.error}",
                            })
                            consecutive_parse_errors = 0
                        else:
                            # 回退迭代计数，给 LLM 修正机会
                            iteration -= 1
                            conversation_history.append({
                                "role": "assistant",
                                "content": response,
                            })
                            conversation_history.append({
                                "role": "user",
                                "content": f"工具调用格式不正确: {parse_result.error}。请重新调用工具。",
                            })
                    else:
                        # 没有找到工具调用标签
                        conversation_history.append({
                            "role": "assistant",
                            "content": response,
                        })
                        conversation_history.append({
                            "role": "user",
                            "content": "请使用工具继续分析，或调用 complete_workflow 完成分析。",
                        })
                    continue

                # 重置解析错误计数
                consecutive_parse_errors = 0

                tool_call = parse_result.tool_call

                # 发送动作事件
                yield sse_event(OptimizationEventType.ACTION, {
                    "iteration": iteration,
                    "tool": tool_call.tool_name.value,
                    "parameters": tool_call.parameters,
                    "reasoning": tool_call.reasoning,
                })

                # 执行工具
                result = await self.tool_executor.execute(
                    tool_name=tool_call.tool_name,
                    parameters=tool_call.parameters,
                    state=state,
                )

                # 发送观察事件
                yield sse_event(OptimizationEventType.OBSERVATION, {
                    "iteration": iteration,
                    "tool": tool_call.tool_name.value,
                    "success": result.success,
                    "summary": result.summary,
                    "error": result.error,
                })

                # 处理特殊工具
                if tool_call.tool_name == ToolName.GENERATE_SUGGESTION and result.success:
                    suggestion = result.data.get("suggestion", {})
                    yield sse_event(OptimizationEventType.SUGGESTION, suggestion)

                    # Review 模式：每个建议后暂停
                    if self.optimization_mode == OptimizationMode.REVIEW and self.session_id:
                        yield sse_event(OptimizationEventType.WORKFLOW_PAUSED, {
                            "session_id": self.session_id,
                            "reason": "review_suggestion",
                            "suggestion": suggestion,
                        })

                        self.session_manager.pause_session(self.session_id)
                        can_continue = await self.session_manager.wait_if_paused(
                            self.session_id,
                            timeout=300.0,
                        )

                        if not can_continue:
                            state.is_complete = True
                            yield sse_event(OptimizationEventType.ERROR, {
                                "error": "会话已取消或超时",
                            })
                            break

                        yield sse_event(OptimizationEventType.WORKFLOW_RESUMED, {
                            "session_id": self.session_id,
                        })

                elif tool_call.tool_name == ToolName.COMPLETE_WORKFLOW:
                    # 工作流完成
                    state.is_complete = True

                # 更新对话历史
                conversation_history.append({
                    "role": "assistant",
                    "content": response,
                })

                # 构建观察反馈
                observation_content = self._format_observation(tool_call.tool_name, result)
                conversation_history.append({
                    "role": "user",
                    "content": observation_content,
                })

                # 裁剪对话历史
                self._trim_conversation_history(conversation_history)

            except Exception as e:
                logger.error("Agent 迭代异常: %s", e, exc_info=True)
                yield sse_event(OptimizationEventType.ERROR, {
                    "error": f"Agent 异常: {str(e)}",
                    "iteration": iteration,
                })
                break

        # Plan 模式：完成分析后发送所有建议
        if self.optimization_mode == OptimizationMode.PLAN and state.suggestions:
            # 按严重程度分类
            by_severity = {"high": 0, "medium": 0, "low": 0}
            by_dimension = {}
            for s in state.suggestions:
                sev = s.get("severity", "medium")
                by_severity[sev] = by_severity.get(sev, 0) + 1
                dim = s.get("dimension", "unknown")
                by_dimension[dim] = by_dimension.get(dim, 0) + 1

            yield sse_event(OptimizationEventType.PLAN_READY, {
                "session_id": self.session_id,
                "suggestions": state.suggestions,
                "suggestions_by_severity": by_severity,
                "suggestions_by_dimension": by_dimension,
                "observations": state.observations,
                "summary": state.summary,
                "overall_quality": state.overall_quality,
            })

            # 暂停等待用户确认
            if self.session_id:
                self.session_manager.pause_session(self.session_id)
                can_continue = await self.session_manager.wait_if_paused(
                    self.session_id,
                    timeout=600.0,
                )

                if not can_continue:
                    yield sse_event(OptimizationEventType.ERROR, {
                        "error": "会话已取消或超时",
                    })

        # 发送完成事件
        yield sse_event(OptimizationEventType.WORKFLOW_COMPLETE, {
            "session_id": self.session_id,
            "total_iterations": iteration,
            "total_suggestions": len(state.suggestions),
            "total_observations": len(state.observations),
            "summary": state.summary,
            "overall_quality": state.overall_quality,
        })

    def _build_system_prompt(self, dimensions: List[str]) -> str:
        """构建系统提示词"""
        dimension_names_map = get_all_dimension_names(self.prompt_type)
        dimension_list = "\n".join([
            f"- {dim}: {dimension_names_map.get(dim, dim)}"
            for dim in dimensions
        ])

        tools_prompt = get_tools_prompt()

        # 根据 Prompt 类型生成不同的任务描述
        if self.prompt_type == PromptType.REVIEW:
            prompt_type_desc = "审查 Prompt"
            task_desc = """分析提供的功能审查 Prompt，检查以下维度的质量：
- 审查 Prompt 用于指导代码审查和测试验收
- 应包含完整的测试覆盖要求、验收标准、边界条件等"""
            check_focus = """1. 首先使用 get_feature_context 获取功能的完整上下文
2. 根据需要使用 rag_retrieve 检索相关的测试规范、验收标准等信息
3. 检查审查 Prompt 是否包含：
   - 测试用例覆盖要求
   - 明确的验收标准
   - 边界条件和异常场景
   - 安全检查项
   - 性能检查要求
   - 代码质量标准
4. 对于发现的每个问题，使用 generate_suggestion 生成具体的优化建议
5. 完成所有检查后，使用 complete_workflow 结束分析"""
        else:
            prompt_type_desc = "实现 Prompt"
            task_desc = """分析提供的功能实现 Prompt，检查以下维度的质量：
- 实现 Prompt 用于指导代码实现
- 应包含完整的功能描述、接口定义、实现步骤等"""
            check_focus = """1. 首先使用 get_feature_context 获取功能的完整上下文
2. 根据需要使用 rag_retrieve 检索相关的架构设计、需求等信息
3. 使用各种检查工具（check_completeness, check_interface, check_dependency）进行快速检查
4. 如果快速检查发现问题或需要深入分析，使用 deep_check 进行 LLM 深度检查
5. 对于发现的每个问题，使用 generate_suggestion 生成具体的优化建议
6. 完成所有检查后，使用 complete_workflow 结束分析"""

        return f"""你是一位资深的软件工程师和代码审查专家，正在对一个编程项目的功能 {prompt_type_desc} 进行质量分析和优化。

## 你的任务

{task_desc}
{dimension_list}

## 工作流程

{check_focus}

## 响应格式

每次响应必须包含思考过程和工具调用：

<thinking>
你的分析思考过程...
- 当前在分析什么
- 发现了什么问题或特点
- 下一步打算做什么
</thinking>

<tool_call>
{{
    "tool": "工具名称",
    "parameters": {{"参数名": "参数值"}},
    "reasoning": "为什么调用这个工具"
}}
</tool_call>

{tools_prompt}

## 重要提示

1. 每次只调用一个工具
2. 仔细分析工具返回的结果，根据结果决定下一步
3. 生成建议时必须提供具体的原始文本和建议修改
4. 不要遗漏任何维度的检查
5. 完成后必须调用 complete_workflow 结束分析"""

    def _build_initial_message(
        self,
        state: AgentState,
        dimensions: List[str],
    ) -> str:
        """构建初始用户消息"""
        feature = state.context.feature
        dimension_names_map = get_all_dimension_names(self.prompt_type)

        # 根据 Prompt 类型生成不同的任务描述
        if self.prompt_type == PromptType.REVIEW:
            prompt_type_name = "审查 Prompt"
            analysis_hint = "请分析此审查 Prompt 是否包含完整的测试要求、验收标准和边界条件检查。"
        else:
            prompt_type_name = "实现 Prompt"
            analysis_hint = "请开始分析，首先获取功能上下文。"

        return f"""请分析以下功能 {prompt_type_name} 的质量：

## 功能信息
- 功能编号: {feature.feature_number}
- 功能名称: {feature.feature_name}
- 功能描述: {feature.feature_description or '无'}
- 输入: {feature.inputs or '无'}
- 输出: {feature.outputs or '无'}
- 所属系统: {feature.system_name or '无'}
- 所属模块: {feature.module_name or '无'}

## 待分析的 {prompt_type_name} 内容

```
{state.prompt_content}
```

## 检查维度
{', '.join([dimension_names_map.get(d, d) for d in dimensions])}

{analysis_hint}"""

    async def _get_agent_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        user_id: str,
    ) -> str:
        """调用 LLM 获取 Agent 响应"""
        try:
            # 构建消息列表
            messages = []
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

            response = await self.llm_service.get_llm_response(
                user_id=user_id,
                system_prompt=system_prompt,
                user_prompt=messages[-1]["content"] if messages else "",
                conversation_history=messages[:-1] if len(messages) > 1 else [],
                max_tokens=4000,
                timeout=120,
            )

            return response

        except Exception as e:
            logger.error("LLM 调用失败: %s", e)
            raise

    def _format_observation(self, tool_name: ToolName, result) -> str:
        """格式化观察反馈"""
        if not result.success:
            return f"工具 {tool_name.value} 执行失败: {result.error}"

        return f"[观察] {result.summary}\n\n详细数据:\n```json\n{json.dumps(result.data, ensure_ascii=False, indent=2)[:1000]}\n```"

    def _trim_conversation_history(
        self,
        history: List[Dict[str, str]],
    ) -> None:
        """裁剪对话历史，保持在窗口大小内"""
        max_messages = MAX_CONVERSATION_HISTORY_ROUNDS * 2  # 每轮包含 user 和 assistant

        while len(history) > max_messages:
            # 保留第一条消息（初始任务描述）
            history.pop(1)
            if len(history) > max_messages:
                history.pop(1)


__all__ = [
    "PromptOptimizationAgent",
    "sse_event",
]
