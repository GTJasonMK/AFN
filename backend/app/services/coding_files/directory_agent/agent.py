"""
目录规划Agent

使用ReAct循环实现智能目录结构规划。
Agent根据项目信息，通过思考-行动-观察循环，逐步构建完整的目录结构。
"""

import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from app.core.config import settings

from .tools import (
    ToolCall,
    ToolCategory,
    BatchToolCallParseResult,
    get_tools_prompt,
    get_tool,
    parse_tool_calls,
)
from .tool_executor import AgentState, ToolExecutor

logger = logging.getLogger(__name__)


# 提示词Key
DIRECTORY_PLANNING_AGENT_PROMPT_KEY = "directory_planning_agent"

# 默认提示词（当数据库中没有时使用）
DEFAULT_SYSTEM_PROMPT = """你是一个专业的软件架构师Agent，负责为编程项目设计最优的目录结构。

## 你的目标

根据项目信息（需求、蓝图、系统划分、模块设计），为项目规划一个**完美的目录结构**：
1. 每个代码文件的位置都放对（综合考虑用户需求、架构设计、复用性、扩展性）
2. 对每个文件的功能进行详细解释（为什么要设置这个文件、要实现什么）
3. 明确每个文件的依赖关系（依赖哪些模块、为什么需要这些依赖）

## 工作方式

你通过**思考-行动-观察**循环来完成任务：
1. **思考(Thinking)**: 分析当前状态，决定下一步做什么
2. **行动(Action)**: 调用工具获取信息或执行操作
3. **观察(Observation)**: 查看工具执行结果
4. 循环直到完成所有模块的规划

{tools_prompt}

## 响应格式

每次响应必须包含以下两部分：

1. **思考过程**（用<thinking>标签包裹）：
<thinking>
分析当前情况...
我需要做什么...
为什么选择这个工具...
</thinking>

2. **工具调用**（用<tool_call>标签包裹）：
<tool_call>
{
    "tool": "工具名称",
    "parameters": {参数},
    "reasoning": "选择理由"
}
</tool_call>

## 规划策略

1. **第一步**：了解项目
   - 获取项目概览，了解整体情况
   - 获取蓝图详情，了解技术要求
   - 获取所有系统，了解系统划分

2. **第二步**：分析依赖
   - 获取依赖关系图
   - 分析共享模块候选
   - 识别高依赖模块

3. **第三步**：规划结构
   - 先创建顶层目录结构（src/, tests/, etc.）
   - 为每个系统/功能创建对应目录
   - 为每个模块创建文件，详细说明功能和依赖

4. **第四步**：验证完善
   - 检查未覆盖的模块
   - 评估结构质量
   - 修复问题并完成规划

## 关键原则

1. **完整性**：确保所有模块都被覆盖，没有遗漏
2. **合理性**：目录结构要符合架构设计原则（高内聚、低耦合）
3. **清晰性**：每个文件的描述要清楚说明其职责
4. **可维护性**：依赖关系要合理，避免循环依赖
5. **实用性**：为后续编程Agent提供有价值的指导信息

## 注意事项

- 创建文件时，description字段要详细描述功能，不能泛泛而谈
- purpose字段要解释为什么需要这个文件
- dependencies字段要列出依赖的模块编号
- dependency_reasons字段要解释为什么需要这些依赖
- implementation_notes字段要给出实现建议

现在开始规划，首先获取项目信息。
"""


class DirectoryPlanningAgent:
    """
    目录规划Agent

    使用ReAct循环实现智能目录结构规划。
    """

    MAX_ITERATIONS = 100  # 最大迭代次数
    MAX_CONSECUTIVE_ERRORS = 3  # 最大连续错误次数

    def __init__(
        self,
        llm_service,
        prompt_service,
        user_id: int = 1,
    ):
        """
        初始化Agent

        Args:
            llm_service: LLM服务
            prompt_service: 提示词服务
            user_id: 用户ID
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.user_id = user_id

        # 对话历史
        self._conversation_history: List[Dict[str, str]] = []

        # 上下文增长追踪（用于动态预测压缩）
        self._context_deltas: List[int] = []  # 每次迭代的字符增长量
        self._prev_context_chars: int = 0  # 上一次的上下文字符数

    async def run(
        self,
        state: AgentState,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        运行Agent

        Args:
            state: Agent状态

        Yields:
            SSE事件
        """
        logger.info("启动目录规划Agent: project_id=%s", state.project_id)

        # 创建LLM调用函数（用于评估器）
        async def llm_caller(system_prompt: str, user_prompt: str) -> str:
            conversation = [{"role": "user", "content": user_prompt}]
            return await self.llm_service.get_llm_response(
                system_prompt=system_prompt,
                conversation_history=conversation,
                user_id=self.user_id,
            )

        # 创建工具执行器
        executor = ToolExecutor(state, llm_caller=llm_caller)

        # 构建系统提示词
        system_prompt = await self._build_system_prompt()

        # 初始化对话历史
        self._conversation_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._build_initial_message(state)},
        ]

        yield {
            "event": "agent_start",
            "data": {
                "project_id": state.project_id,
                "total_modules": len(state.modules),
                "total_systems": len(state.systems),
            }
        }

        iteration = 0
        consecutive_errors = 0

        while not state.is_complete and iteration < self.MAX_ITERATIONS:
            iteration += 1

            yield {
                "event": "iteration_start",
                "data": {
                    "iteration": iteration,
                    "covered_modules": len(state.covered_modules),
                    "total_modules": len(state.modules),
                }
            }

            # 1. 获取Agent响应
            try:
                response = await self._get_agent_response()
            except Exception as e:
                logger.error("获取Agent响应失败: %s", e)
                consecutive_errors += 1
                if consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                    yield {
                        "event": "error",
                        "data": {"message": f"连续错误超过限制: {e}"}
                    }
                    break
                continue

            # 2. 解析响应（支持批量工具调用）
            thinking, batch_result = self._parse_response(response)

            # 发送思考过程
            if thinking:
                yield {
                    "event": "thinking",
                    "data": {
                        "iteration": iteration,
                        "content": thinking,
                    }
                }

            # 3. 检查工具调用
            if not batch_result.success:
                logger.warning("工具调用解析失败: %s", batch_result.errors)
                consecutive_errors += 1

                # 给Agent一个修正机会
                error_message = f"工具调用格式错误: {'; '.join(batch_result.errors)}\n请重新按正确格式调用工具。"
                self._conversation_history.append({
                    "role": "assistant",
                    "content": response
                })
                self._conversation_history.append({
                    "role": "user",
                    "content": error_message
                })

                if consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                    yield {
                        "event": "error",
                        "data": {"message": "连续解析错误超过限制"}
                    }
                    break
                continue

            # 重置错误计数
            consecutive_errors = 0
            tool_calls = batch_result.tool_calls

            # 发送动作事件（每个工具调用单独发送）
            for tool_call in tool_calls:
                yield {
                    "event": "action",
                    "data": {
                        "iteration": iteration,
                        "tool": tool_call.tool,
                        "parameters": tool_call.parameters,
                        "reasoning": tool_call.reasoning,
                    }
                }

            # 4. 批量执行工具
            tool_results = await executor.execute_batch(tool_calls)

            # 发送观察结果（每个工具结果单独发送）
            for tool_call, tool_result in zip(tool_calls, tool_results):
                yield {
                    "event": "observation",
                    "data": {
                        "iteration": iteration,
                        "tool": tool_call.tool,
                        "success": tool_result.success,
                        "result": tool_result.result if tool_result.success else None,
                        "error": tool_result.error if not tool_result.success else None,
                    }
                }

            # 5. 检查是否有ACTION工具成功执行，如果有则推送目录结构更新
            has_structure_change = False
            for tool_call, tool_result in zip(tool_calls, tool_results):
                if tool_result.success:
                    tool_def = get_tool(tool_call.tool)
                    if tool_def and tool_def.category == ToolCategory.ACTION:
                        has_structure_change = True
                        break

            if has_structure_change:
                yield {
                    "event": "structure_update",
                    "data": {
                        "iteration": iteration,
                        "directories": [
                            {
                                "path": d.path,
                                "description": d.description,
                                "purpose": d.purpose,
                            }
                            for d in state.directories
                        ],
                        "files": [
                            {
                                "path": f.path,
                                "filename": f.filename,
                                "module_number": f.module_number,
                                "description": f.description[:100] if f.description else "",
                                "quality_ok": f.is_quality_ok(),
                            }
                            for f in state.files
                        ],
                        "stats": {
                            "total_directories": len(state.directories),
                            "total_files": len(state.files),
                            "covered_modules": len(state.covered_modules),
                            "total_modules": len(state.modules),
                        }
                    }
                }

            # 6. 更新对话历史（合并所有工具结果）
            tool_messages = [result.to_message() for result in tool_results]
            combined_tool_message = "\n\n".join(tool_messages)
            self._conversation_history.append({
                "role": "assistant",
                "content": response
            })
            self._conversation_history.append({
                "role": "user",
                "content": combined_tool_message
            })

            # 7. 动态预测压缩：计算增长量，预测是否需要压缩
            current_chars = sum(len(m.get("content", "")) for m in self._conversation_history)
            if self._prev_context_chars > 0:
                delta = current_chars - self._prev_context_chars
                self._context_deltas.append(delta)

            logger.debug(
                "[上下文追踪] iteration=%d, chars=%d, delta=%d, avg_delta=%.0f",
                iteration, current_chars,
                self._context_deltas[-1] if self._context_deltas else 0,
                sum(self._context_deltas) / len(self._context_deltas) if self._context_deltas else 0
            )

            # 预测下次是否会超限，如果是则调用LLM压缩
            if await self._should_compress(current_chars):
                yield {
                    "event": "context_compression",
                    "data": {"current_chars": current_chars, "reason": "predicted_overflow"}
                }
                await self._compress_with_llm()

            self._prev_context_chars = sum(len(m.get("content", "")) for m in self._conversation_history)

            # 8. 检查是否完成
            if state.is_complete:
                yield {
                    "event": "planning_complete",
                    "data": {
                        "iterations": iteration,
                        "total_directories": len(state.directories),
                        "total_files": len(state.files),
                        "covered_modules": len(state.covered_modules),
                        "summary": state.finish_summary,
                    }
                }
                break

            # 发送进度更新
            if iteration % 5 == 0:
                yield {
                    "event": "progress",
                    "data": {
                        "iteration": iteration,
                        "directories": len(state.directories),
                        "files": len(state.files),
                        "coverage": len(state.covered_modules) / len(state.modules) if state.modules else 0,
                    }
                }

        # 如果达到最大迭代次数但未完成
        if not state.is_complete and iteration >= self.MAX_ITERATIONS:
            yield {
                "event": "warning",
                "data": {
                    "message": f"达到最大迭代次数({self.MAX_ITERATIONS})，规划可能不完整",
                    "covered_modules": len(state.covered_modules),
                    "total_modules": len(state.modules),
                }
            }

        logger.info(
            "目录规划Agent结束: iterations=%d, dirs=%d, files=%d, complete=%s",
            iteration,
            len(state.directories),
            len(state.files),
            state.is_complete,
        )

    async def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        # 尝试从数据库获取
        prompt = None
        if self.prompt_service:
            try:
                prompt = await self.prompt_service.get_prompt(DIRECTORY_PLANNING_AGENT_PROMPT_KEY)
            except Exception as e:
                logger.warning("获取提示词失败: %s", e)

        if not prompt:
            prompt = DEFAULT_SYSTEM_PROMPT

        # 替换工具列表
        tools_prompt = get_tools_prompt()
        prompt = prompt.replace("{tools_prompt}", tools_prompt)

        return prompt

    def _build_initial_message(self, state: AgentState) -> str:
        """构建初始消息"""
        lines = [
            "请开始为以下项目规划目录结构：",
            "",
            f"**项目**: {state.project_data.get('title', '未命名项目')}",
            f"**系统数**: {len(state.systems)}",
            f"**模块数**: {len(state.modules)}",
            "",
            "请先获取项目概览信息，了解项目的整体情况。",
        ]
        return "\n".join(lines)

    async def _get_agent_response(self) -> str:
        """获取Agent响应"""
        # 构建消息列表
        messages = self._conversation_history.copy()

        # 调用LLM - 使用正确的参数格式
        # system_prompt 是第一条消息，conversation_history 是后续消息
        response = await self.llm_service.get_llm_response(
            system_prompt=messages[0]["content"],
            conversation_history=messages[1:],
            user_id=self.user_id,
        )

        return response

    def _format_messages_for_llm(self, messages: List[Dict[str, str]]) -> str:
        """格式化消息列表为LLM输入"""
        lines = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                lines.append(f"[User]\n{content}\n")
            elif role == "assistant":
                lines.append(f"[Assistant]\n{content}\n")
        return "\n".join(lines)

    def _parse_response(self, response: str) -> Tuple[str, BatchToolCallParseResult]:
        """
        解析Agent响应（支持批量工具调用）

        Args:
            response: Agent响应文本

        Returns:
            (思考内容, 批量工具调用解析结果)
        """
        # 提取思考内容
        thinking = ""
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
        if thinking_match:
            thinking = thinking_match.group(1).strip()

        # 解析工具调用（支持单个或多个）
        batch_result = parse_tool_calls(response)

        return thinking, batch_result

    async def _should_compress(self, current_chars: int) -> bool:
        """
        预测下次迭代是否会超过上下文限制

        基于历史增长均值预测，提前触发压缩
        """
        if len(self._context_deltas) < 3:
            # 数据不足，不预测
            return False

        max_chars = settings.agent_context_max_chars
        avg_delta = sum(self._context_deltas) / len(self._context_deltas)
        predicted_next = current_chars + avg_delta

        # 预留10%安全边际
        threshold = max_chars * 0.9

        should_compress = predicted_next > threshold
        if should_compress:
            logger.info(
                "[压缩预测] 触发压缩: current=%d, avg_delta=%.0f, predicted=%d, threshold=%d",
                current_chars, avg_delta, predicted_next, threshold
            )

        return should_compress

    async def _compress_with_llm(self) -> None:
        """
        使用LLM压缩对话历史

        将历史对话发送给LLM，生成压缩摘要，然后重置上下文
        """
        if len(self._conversation_history) <= 2:
            return

        # 保留系统提示词
        system_message = self._conversation_history[0]

        # 从PromptService加载压缩提示词
        compress_prompt_template = await self.prompt_service.get_prompt("context_compression")
        history_text = self._format_history_for_compression()
        compress_prompt = compress_prompt_template.replace("{history}", history_text)

        try:
            compressed_summary = await self.llm_service.get_llm_response(
                system_prompt="你是一个专业的对话压缩助手，负责将冗长的Agent对话历史压缩为简洁的摘要。",
                conversation_history=[{"role": "user", "content": compress_prompt}],
                user_id=self.user_id,
            )

            # 重置对话历史
            self._conversation_history = [
                system_message,
                {
                    "role": "user",
                    "content": f"[历史摘要]\n{compressed_summary}\n\n请继续完成目录规划任务。"
                }
            ]

            # 重置增长追踪
            self._context_deltas = []
            self._prev_context_chars = 0

            new_chars = sum(len(m.get("content", "")) for m in self._conversation_history)
            logger.info("[LLM压缩] 压缩完成: new_chars=%d", new_chars)

        except Exception as e:
            logger.error("[LLM压缩] 压缩失败: %s", e)
            raise

    def _format_history_for_compression(self) -> str:
        """格式化对话历史用于压缩"""
        lines = []
        for msg in self._conversation_history[1:]:  # 跳过system
            role = msg.get("role", "")
            content = msg.get("content", "")
            lines.append(f"[{role}] {content}")
        return "\n\n".join(lines)


async def run_directory_planning_agent(
    project_id: str,
    project_data: Dict[str, Any],
    blueprint_data: Dict[str, Any],
    systems: List[Dict[str, Any]],
    modules: List[Dict[str, Any]],
    llm_service,
    prompt_service,
    user_id: int = 1,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    运行目录规划Agent的便捷函数

    Args:
        project_id: 项目ID
        project_data: 项目数据
        blueprint_data: 蓝图数据
        systems: 系统列表
        modules: 模块列表
        llm_service: LLM服务
        prompt_service: 提示词服务
        user_id: 用户ID

    Yields:
        SSE事件
    """
    # 创建状态
    state = AgentState(
        project_id=project_id,
        project_data=project_data,
        blueprint_data=blueprint_data,
        systems=systems,
        modules=modules,
    )

    # 创建Agent
    agent = DirectoryPlanningAgent(
        llm_service=llm_service,
        prompt_service=prompt_service,
        user_id=user_id,
    )

    # 运行
    async for event in agent.run(state):
        yield event

    # 返回最终状态（通过特殊事件）
    yield {
        "event": "final_state",
        "data": {
            "directories": [
                {
                    "path": d.path,
                    "description": d.description,
                    "purpose": d.purpose,
                }
                for d in state.directories
            ],
            "files": [
                {
                    "path": f.path,
                    "filename": f.filename,
                    "description": f.description,
                    "purpose": f.purpose,
                    "module_number": f.module_number,
                    "file_type": f.file_type,
                    "language": f.language,
                    "priority": f.priority,
                    "dependencies": f.dependencies,
                    "dependency_reasons": f.dependency_reasons,
                    "implementation_notes": f.implementation_notes,
                }
                for f in state.files
            ],
        }
    }
