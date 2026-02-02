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
                        logger.info(
                            "[结构变更] ACTION工具执行成功: tool=%s, 将发送structure_update事件",
                            tool_call.tool
                        )
                        break

            if has_structure_change:
                logger.info(
                    "[结构变更] 发送structure_update事件: dirs=%d, files=%d",
                    len(state.directories), len(state.files)
                )
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
        """构建系统提示词

        P0修复: 遵循CLAUDE.md规范，提示词加载失败时直接报错，不使用硬编码回退
        """
        if not self.prompt_service:
            raise ValueError(
                "目录规划Agent需要PromptService，但未提供。"
                "请确保正确注入依赖。"
            )

        prompt = await self.prompt_service.get_prompt(DIRECTORY_PLANNING_AGENT_PROMPT_KEY)
        if not prompt:
            raise ValueError(
                f"未找到提示词 '{DIRECTORY_PLANNING_AGENT_PROMPT_KEY}'。"
                "请检查 backend/prompts/coding/ 目录下是否存在对应的 .md 文件，"
                "并确保已在 _registry.yaml 中注册。"
            )

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
            response_format=None,
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
                response_format=None,
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
