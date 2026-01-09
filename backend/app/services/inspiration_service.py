"""
灵感对话服务

封装灵感对话的核心业务逻辑，解决Router层代码重复问题。
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.constants import NovelConstants, LLMConstants
from ..models.novel import NovelConversation
from ..models.coding import CodingConversation
from ..services.conversation_service import ConversationService, ConversationRecord
from ..services.llm_service import LLMService
from ..services.llm_wrappers import call_llm, LLMProfile
from ..services.prompt_service import PromptService
from ..utils.json_utils import (
    parse_llm_json_or_fail,
    remove_think_tags,
    unwrap_markdown_json,
)
from ..utils.prompt_helpers import ensure_prompt
from .project_factory import ProjectTypeConfig, ProjectStage

logger = logging.getLogger(__name__)


@dataclass
class InspirationResult:
    """灵感对话处理结果"""
    parsed_response: Dict[str, Any]
    normalized_json: str
    is_complete: bool
    ready_for_blueprint: bool
    conversation_turns: int


class InspirationService:
    """
    灵感对话服务

    封装灵感对话的核心业务逻辑，包括：
    - 构建对话上下文
    - 调用LLM获取响应
    - 解析和处理响应
    - 计算对话完成状态

    遵循单一职责原则，将业务逻辑从Router层分离。
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        prompt_service: PromptService,
    ):
        """
        初始化InspirationService

        Args:
            session: 数据库会话
            llm_service: LLM服务
            prompt_service: 提示词服务
        """
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        # 对话服务会根据项目类型动态创建
        self._conversation_services: Dict[str, ConversationService] = {}

    def _get_conversation_service(self, project_type: str = "novel") -> ConversationService:
        """
        获取对应项目类型的对话服务

        Args:
            project_type: 项目类型 (novel/coding)

        Returns:
            ConversationService: 对话服务实例
        """
        if project_type not in self._conversation_services:
            self._conversation_services[project_type] = ConversationService(
                self.session, project_type=project_type
            )
        return self._conversation_services[project_type]

    async def get_system_prompt(self, project_type: str = "novel") -> str:
        """
        获取灵感对话/需求分析的系统提示词

        Args:
            project_type: 项目类型 (novel/coding)

        Returns:
            str: 系统提示词内容
        """
        # 根据项目类型获取对应的提示词名称
        prompt_name = ProjectTypeConfig.get_prompt_name(project_type, ProjectStage.INSPIRATION)
        system_prompt = await self.prompt_service.get_prompt(prompt_name)
        return ensure_prompt(system_prompt, prompt_name)

    async def build_conversation_context(
        self,
        project_id: str,
        user_input: Dict[str, Any],
        project_type: str = "novel",
    ) -> tuple[List[Dict[str, str]], List[ConversationRecord]]:
        """
        构建对话上下文

        Args:
            project_id: 项目ID
            user_input: 用户输入
            project_type: 项目类型 (novel/coding)

        Returns:
            tuple: (conversation_history, history_records)
        """
        conversation_service = self._get_conversation_service(project_type)
        history_records = await conversation_service.list_conversations(project_id)

        conversation_history = [
            {"role": record.role, "content": record.content}
            for record in history_records
        ]

        user_content = json.dumps(user_input, ensure_ascii=False)
        conversation_history.append({"role": "user", "content": user_content})

        return conversation_history, history_records

    def calculate_completion_status(
        self,
        parsed: Dict[str, Any],
        history_records: List[ConversationRecord],
        project_id: str,
    ) -> tuple[bool, bool, int]:
        """
        计算对话完成状态

        判断对话是否完成的逻辑：
        - LLM明确标记完成 OR 对话轮次达到阈值

        Args:
            parsed: LLM解析后的响应
            history_records: 历史对话记录
            project_id: 项目ID（用于日志）

        Returns:
            tuple: (is_complete, ready_for_blueprint, conversation_turns)
        """
        # 计算对话轮次（刚添加了2条新记录：user + assistant）
        total_messages = len(history_records) + 2
        conversation_turns = total_messages // 2

        llm_says_complete = parsed.get("is_complete", False)
        turns_threshold_met = conversation_turns >= NovelConstants.CONVERSATION_ROUNDS_SHORT

        is_complete = llm_says_complete or turns_threshold_met
        ready_for_blueprint = is_complete

        # 记录完成原因（用于调试）
        if is_complete:
            if turns_threshold_met and not llm_says_complete:
                logger.info(
                    "项目 %s 对话已达到%d轮（阈值%d轮），自动标记为可生成蓝图",
                    project_id, conversation_turns, NovelConstants.CONVERSATION_ROUNDS_SHORT
                )
            else:
                logger.info("项目 %s LLM标记对话完成，is_complete=true", project_id)
        else:
            logger.info(
                "项目 %s 灵感对话进行中，当前%d轮（阈值%d轮），is_complete=%s",
                project_id, conversation_turns, NovelConstants.CONVERSATION_ROUNDS_SHORT, llm_says_complete
            )

        return is_complete, ready_for_blueprint, conversation_turns

    def parse_llm_response(self, llm_response: str, project_id: str) -> tuple[Dict[str, Any], str]:
        """
        解析LLM响应

        Args:
            llm_response: LLM原始响应
            project_id: 项目ID（用于错误信息）

        Returns:
            tuple: (parsed_dict, normalized_json)

        Raises:
            JSONParseError: 解析失败
        """
        cleaned = remove_think_tags(llm_response)
        normalized = unwrap_markdown_json(cleaned)
        parsed = parse_llm_json_or_fail(
            llm_response,
            f"项目{project_id}的灵感对话响应解析失败"
        )
        return parsed, normalized

    async def process_conversation(
        self,
        project_id: str,
        user_input: Dict[str, Any],
        user_id: int,
        project_type: str = "novel",
    ) -> InspirationResult:
        """
        处理灵感对话/需求分析（非流式）

        完整的对话处理流程：
        1. 构建对话上下文
        2. 获取系统提示词
        3. 调用LLM
        4. 解析响应
        5. 保存对话历史
        6. 计算完成状态

        Args:
            project_id: 项目ID
            user_input: 用户输入
            user_id: 用户ID
            project_type: 项目类型 (novel/coding)

        Returns:
            InspirationResult: 处理结果
        """
        # 1. 构建对话上下文
        conversation_history, history_records = await self.build_conversation_context(
            project_id, user_input, project_type
        )
        user_content = conversation_history[-1]["content"]

        logger.info(
            "项目 %s 灵感对话请求，用户 %s，历史记录 %s 条，项目类型 %s",
            project_id, user_id, len(history_records), project_type,
        )

        # 2. 获取系统提示词（根据项目类型）
        system_prompt = await self.get_system_prompt(project_type)

        # 3. 调用LLM
        llm_response = await call_llm(
            self.llm_service,
            LLMProfile.INSPIRATION,
            system_prompt=system_prompt,
            user_content=user_content,
            user_id=user_id,
            extra_messages=conversation_history[:-1] if len(conversation_history) > 1 else None,
        )

        # 4. 解析响应
        parsed, normalized = self.parse_llm_response(llm_response, project_id)

        # 5. 保存对话历史
        conversation_service = self._get_conversation_service(project_type)
        await conversation_service.append_conversation(project_id, "user", user_content)
        await conversation_service.append_conversation(project_id, "assistant", normalized)

        # 6. 计算完成状态
        is_complete, ready_for_blueprint, conversation_turns = self.calculate_completion_status(
            parsed, history_records, project_id
        )

        # 更新解析结果
        if is_complete:
            parsed["is_complete"] = True
            parsed["ready_for_blueprint"] = True

        parsed.setdefault("conversation_state", parsed.get("conversation_state", {}))

        return InspirationResult(
            parsed_response=parsed,
            normalized_json=normalized,
            is_complete=is_complete,
            ready_for_blueprint=ready_for_blueprint,
            conversation_turns=conversation_turns,
        )

    async def process_conversation_stream(
        self,
        project_id: str,
        user_input: Dict[str, Any],
        user_id: int,
        project_type: str = "novel",
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        处理灵感对话/需求分析（流式）

        流式对话处理流程，通过yield返回事件：
        - streaming_start: 开始流式输出
        - llm_chunk: LLM响应片段（用于收集完整响应）
        - parsed_result: 解析完成的结果
        - error: 错误信息

        Args:
            project_id: 项目ID
            user_input: 用户输入
            user_id: 用户ID
            project_type: 项目类型 (novel/coding)

        Yields:
            Dict[str, Any]: 事件数据
        """
        # 1. 构建对话上下文
        conversation_history, history_records = await self.build_conversation_context(
            project_id, user_input, project_type
        )
        user_content = conversation_history[-1]["content"]

        logger.info(
            "项目 %s 灵感对话流式请求，用户 %s，历史记录 %s 条，项目类型 %s",
            project_id, user_id, len(history_records), project_type,
        )

        # 2. 获取系统提示词（根据项目类型）
        system_prompt = await self.get_system_prompt(project_type)

        # 3. 发送开始事件
        yield {"event": "streaming_start", "data": {"status": "started"}}

        # 4. 流式调用LLM，收集完整响应
        full_response = []
        async for chunk in self.llm_service.stream_llm_response(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            temperature=settings.llm_temp_inspiration,
            user_id=user_id,
            timeout=LLMConstants.INSPIRATION_TIMEOUT,
        ):
            content = chunk.get("content")
            if content:
                full_response.append(content)
                yield {"event": "llm_chunk", "data": {"content": content}}

        # 5. 解析完整JSON响应
        llm_response = "".join(full_response)
        parsed, normalized = self.parse_llm_response(llm_response, project_id)

        # 6. 保存对话历史并立即提交
        # 注意：在流式响应中，对话保存是关键操作，应该尽快持久化
        # 避免在生成器外部commit，防止客户端断开导致事务状态不确定
        conversation_service = self._get_conversation_service(project_type)
        await conversation_service.append_conversation(project_id, "user", user_content)
        await conversation_service.append_conversation(project_id, "assistant", normalized)
        await self.session.commit()

        # 自动入库：灵感对话（仅编程项目）
        if project_type == "coding":
            try:
                from .coding_rag import schedule_ingestion, CodingDataType
                from ..core.dependencies import get_vector_store

                vector_store = await get_vector_store()
                if vector_store:
                    schedule_ingestion(
                        project_id=project_id,
                        user_id=user_id,
                        data_type=CodingDataType.INSPIRATION,
                        vector_store=vector_store,
                        llm_service=self.llm_service,
                    )
                    logger.info("项目 %s 灵感对话已调度RAG入库", project_id)
            except Exception as rag_exc:
                logger.warning("项目 %s 灵感对话RAG入库调度失败: %s", project_id, str(rag_exc))

        # 7. 计算完成状态
        is_complete, ready_for_blueprint, conversation_turns = self.calculate_completion_status(
            parsed, history_records, project_id
        )

        if is_complete:
            parsed["is_complete"] = True
            parsed["ready_for_blueprint"] = True

        parsed.setdefault("conversation_state", parsed.get("conversation_state", {}))

        # 8. 返回解析结果
        yield {
            "event": "parsed_result",
            "data": {
                "parsed": parsed,
                "is_complete": is_complete,
                "ready_for_blueprint": ready_for_blueprint,
                "conversation_turns": conversation_turns,
            }
        }

        logger.info("项目 %s 灵感对话流式响应完成", project_id)
