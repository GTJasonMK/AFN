"""
正文优化Agent核心

实现思考-决策-行动-观察的Agent循环。
Agent根据当前状态和观察结果自主决定下一步行动。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from .tools import (
    ToolName,
    ToolCall,
    ToolResult,
    get_tools_prompt,
    parse_tool_call,
    format_tool_result,
)
from .tool_executor import ToolExecutor, AgentState
from .schemas import OptimizationEventType, OptimizationMode
from .session_manager import OptimizationSession, get_session_manager
from ..llm_service import LLMService
from ...utils.sse_helpers import sse_event

logger = logging.getLogger(__name__)


# Agent最大循环次数限制（防止无限循环）
MAX_ITERATIONS = 100
# 单个段落最大迭代次数
MAX_PARAGRAPH_ITERATIONS = 15


class ContentOptimizationAgent:
    """正文优化Agent"""

    def __init__(
        self,
        llm_service: LLMService,
        tool_executor: ToolExecutor,
        user_id: str,
        optimization_session: Optional[OptimizationSession] = None,
        optimization_mode: OptimizationMode = OptimizationMode.AUTO,
    ):
        self.llm_service = llm_service
        self.tool_executor = tool_executor
        self.user_id = user_id
        self.optimization_session = optimization_session
        self.optimization_mode = optimization_mode
        self.session_manager = get_session_manager()

        # Agent对话历史（用于维持上下文）
        self.conversation_history: List[Dict[str, str]] = []

    async def run(
        self,
        state: AgentState,
        dimensions: List[str],
    ) -> AsyncGenerator[str, None]:
        """
        运行Agent主循环

        Args:
            state: Agent状态
            dimensions: 检查维度

        Yields:
            SSE事件流
        """
        logger.info(
            "Agent开始运行: 项目=%s, 章节=%d, 段落数=%d",
            state.project_id,
            state.chapter_number,
            len(state.paragraphs),
        )

        # 发送工作流开始事件
        session_id = self.optimization_session.session_id if self.optimization_session else ""
        yield sse_event(OptimizationEventType.WORKFLOW_START, {
            "session_id": session_id,
            "total_paragraphs": len(state.paragraphs),
            "dimensions": dimensions,
            "mode": self.optimization_mode.value if isinstance(self.optimization_mode, OptimizationMode) else self.optimization_mode,
        })

        # 初始化Agent
        system_prompt = self._build_system_prompt(dimensions)
        self.conversation_history = []

        # 发送初始任务描述
        initial_message = self._build_initial_message(state, dimensions)
        self.conversation_history.append({"role": "user", "content": initial_message})

        iteration = 0
        paragraph_iteration = 0

        while not state.is_complete and iteration < MAX_ITERATIONS:
            iteration += 1
            paragraph_iteration += 1

            # 防止单个段落陷入循环
            if paragraph_iteration > MAX_PARAGRAPH_ITERATIONS:
                logger.warning("段落 %d 迭代次数过多，强制移动到下一段", state.current_index)
                if state.has_more_paragraphs():
                    state.move_to_next()
                    paragraph_iteration = 0
                    # 通知Agent段落切换
                    self.conversation_history.append({
                        "role": "user",
                        "content": f"已自动移动到下一段（第{state.current_index + 1}段），请继续分析。",
                    })
                else:
                    state.is_complete = True
                    break

            try:
                # 调用LLM获取下一步行动
                response = await self._get_agent_response(system_prompt)

                if not response:
                    logger.warning("Agent响应为空")
                    continue

                # 解析思考过程和工具调用
                thinking, tool_call = self._parse_response(response)

                # 发送思考事件
                if thinking:
                    yield sse_event(OptimizationEventType.THINKING, {
                        "paragraph_index": state.current_index,
                        "content": thinking,
                        "step": f"iteration_{iteration}",
                    })

                # 如果没有工具调用，提示Agent选择工具
                if not tool_call:
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response,
                    })
                    self.conversation_history.append({
                        "role": "user",
                        "content": "请使用<tool_call>标签选择一个工具来执行。",
                    })
                    continue

                # 发送动作事件
                yield sse_event(OptimizationEventType.ACTION, {
                    "paragraph_index": state.current_index,
                    "action": tool_call.tool_name.value,
                    "description": tool_call.reasoning or f"调用 {tool_call.tool_name.value}",
                })

                # 执行工具
                result = await self.tool_executor.execute(tool_call, state)

                # 发送观察事件
                yield sse_event(OptimizationEventType.OBSERVATION, {
                    "paragraph_index": state.current_index,
                    "action": tool_call.tool_name.value,
                    "result": self._summarize_result(result),
                    "success": result.success,
                })

                # 处理特殊工具
                if tool_call.tool_name == ToolName.GENERATE_SUGGESTION and result.success:
                    # 发送建议事件
                    if state.suggestions:
                        latest_suggestion = state.suggestions[-1]
                        yield sse_event(OptimizationEventType.SUGGESTION, latest_suggestion)

                        # Review模式下，发送建议后暂停等待用户确认
                        if self.optimization_mode == OptimizationMode.REVIEW and self.optimization_session:
                            # 发送暂停事件
                            yield sse_event(OptimizationEventType.WORKFLOW_PAUSED, {
                                "session_id": self.optimization_session.session_id,
                                "message": "等待用户处理建议",
                            })

                            # 暂停会话
                            self.session_manager.pause_session(self.optimization_session.session_id)

                            # 等待用户操作（继续或取消）
                            can_continue = await self.session_manager.wait_if_paused(
                                self.optimization_session.session_id,
                                timeout=300.0,  # 5分钟超时
                            )

                            if not can_continue:
                                # 会话被取消或超时
                                logger.info("会话被取消或超时: %s", self.optimization_session.session_id)
                                state.is_complete = True
                                yield sse_event(OptimizationEventType.ERROR, {
                                    "message": "用户取消或等待超时",
                                })
                                break

                            # 发送恢复事件
                            yield sse_event(OptimizationEventType.WORKFLOW_RESUMED, {
                                "session_id": self.optimization_session.session_id,
                            })

                elif tool_call.tool_name == ToolName.NEXT_PARAGRAPH:
                    paragraph_iteration = 0
                    if result.success:
                        yield sse_event(OptimizationEventType.PARAGRAPH_START, {
                            "index": state.current_index,
                            "text_preview": state.current_paragraph[:100] if state.current_paragraph else "",
                        })

                elif tool_call.tool_name == ToolName.FINISH_ANALYSIS:
                    yield sse_event(OptimizationEventType.PARAGRAPH_COMPLETE, {
                        "index": state.current_index,
                        "suggestions_count": len([
                            s for s in state.suggestions
                            if s["paragraph_index"] == state.current_index
                        ]),
                    })
                    paragraph_iteration = 0

                elif tool_call.tool_name == ToolName.COMPLETE_WORKFLOW:
                    state.is_complete = True

                # 更新对话历史
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response,
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": format_tool_result(result),
                })

            except Exception as e:
                logger.error("Agent循环错误: %s", e, exc_info=True)
                yield sse_event(OptimizationEventType.ERROR, {
                    "message": f"Agent执行错误: {str(e)}",
                })
                # 继续尝试下一次迭代
                self.conversation_history.append({
                    "role": "user",
                    "content": f"发生错误: {str(e)}。请继续分析或选择其他工具。",
                })

        # 发送工作流完成事件
        yield sse_event(OptimizationEventType.WORKFLOW_COMPLETE, {
            "total_suggestions": len(state.suggestions),
            "total_paragraphs_analyzed": state.current_index + 1,
            "summary": state.summary or f"分析完成，共发现 {len(state.suggestions)} 个问题",
        })

        logger.info(
            "Agent完成运行: 迭代次数=%d, 建议数=%d",
            iteration,
            len(state.suggestions),
        )

    def _build_system_prompt(self, dimensions: List[str]) -> str:
        """构建系统提示词"""
        dimension_names = {
            "coherence": "逻辑连贯性",
            "character": "角色一致性",
            "foreshadow": "伏笔呼应",
            "timeline": "时间线一致性",
            "style": "风格一致性",
            "scene": "场景描写",
        }

        dim_desc = "、".join([dimension_names.get(d, d) for d in dimensions])

        return f"""你是一个专业的小说编辑Agent，负责分析和优化小说章节内容。

## 你的任务
逐段分析章节内容，检查以下维度：{dim_desc}
发现问题时生成具体的修改建议。

## 工作方式
你通过调用工具来完成任务。每次响应时，你需要：
1. 先思考当前状态和下一步计划（在<thinking>标签中）
2. 然后选择一个工具执行（在<tool_call>标签中）

## 可用工具
{get_tools_prompt()}

## 响应格式
<thinking>
你的思考过程...分析当前段落，决定需要检查什么，以及下一步行动。
</thinking>

<tool_call>
{{
    "tool": "工具名称",
    "parameters": {{...}},
    "reasoning": "为什么选择这个工具"
}}
</tool_call>

## 重要规则
1. 每次只调用一个工具
2. 根据工具返回结果决定下一步行动
3. 只在确认存在问题时才生成建议，避免过度修改
4. 完成一个段落的分析后使用finish_analysis，然后用next_paragraph移动到下一段
5. 所有段落分析完成后使用complete_workflow结束

## 分析策略
1. 先用analyze_paragraph了解段落内容
2. 根据段落内容决定需要检查的维度
3. 使用信息获取工具（如rag_retrieve、get_character_state）获取上下文
4. 使用检查工具验证一致性
5. 发现问题时用generate_suggestion生成建议
6. 没有问题或已处理完当前段落后，用finish_analysis标记完成
"""

    def _build_initial_message(self, state: AgentState, dimensions: List[str]) -> str:
        """构建初始消息"""
        paragraph = state.current_paragraph or ""
        preview = paragraph[:300] + "..." if len(paragraph) > 300 else paragraph

        return f"""开始分析章节内容。

章节信息：
- 项目ID: {state.project_id}
- 章节号: {state.chapter_number}
- 总段落数: {len(state.paragraphs)}
- 检查维度: {', '.join(dimensions)}

当前段落（第1段）：
{preview}

请开始分析。首先使用analyze_paragraph工具分析当前段落的内容。"""

    async def _get_agent_response(self, system_prompt: str) -> str:
        """调用LLM获取Agent响应"""
        # 构建对话消息（conversation_history 是消息列表，不包含 system 消息）
        messages = self.conversation_history.copy()

        # 调用LLM（非流式，因为需要完整响应来解析工具调用）
        response = await self.llm_service.get_llm_response(
            system_prompt=system_prompt,
            conversation_history=messages,
            user_id=self.user_id,
            response_format=None,  # Agent响应不需要JSON格式
        )

        return response

    def _parse_response(self, response: str) -> tuple[str, Optional[ToolCall]]:
        """解析Agent响应，提取思考过程和工具调用"""
        import re

        thinking = ""
        tool_call = None

        # 提取thinking
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
        if thinking_match:
            thinking = thinking_match.group(1).strip()

        # 解析工具调用
        tool_call = parse_tool_call(response)

        return thinking, tool_call

    def _summarize_result(self, result: ToolResult) -> str:
        """总结工具执行结果，用于SSE事件"""
        if not result.success:
            return f"执行失败: {result.error}"

        if isinstance(result.result, dict):
            # 提取关键信息
            if "results" in result.result:
                count = result.result.get("results_count", len(result.result["results"]))
                return f"找到 {count} 条相关结果"
            elif "issues" in result.result:
                count = result.result.get("issues_found", 0)
                if count > 0:
                    return f"发现 {count} 个潜在问题"
                return "未发现问题"
            elif "recorded" in result.result:
                return "已记录"
            elif "success" in result.result:
                return "操作成功" if result.result["success"] else "操作失败"
            elif "completed" in result.result:
                return result.result.get("summary", "完成")
            else:
                # 默认返回简短摘要
                return str(result.result)[:100]

        return str(result.result)[:100] if result.result else "完成"
