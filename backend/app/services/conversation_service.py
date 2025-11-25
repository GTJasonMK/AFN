"""
对话管理服务

负责小说项目的灵感对话历史管理和格式化。
"""

from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.novel import NovelConversation
from ..repositories.conversation_repository import NovelConversationRepository
from ..utils.json_utils import parse_llm_json_safe
from ..exceptions import ConversationExtractionError


class ConversationService:
    """
    对话管理服务

    负责对话记录的增删查改和格式化处理。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化ConversationService

        Args:
            session: 数据库会话
        """
        self.session = session
        self.conversation_repo = NovelConversationRepository(session)

    async def list_conversations(self, project_id: str) -> List[NovelConversation]:
        """
        获取项目的所有对话记录

        Args:
            project_id: 项目ID

        Returns:
            List[NovelConversation]: 对话记录列表
        """
        return await self.conversation_repo.list_by_project(project_id)

    async def append_conversation(
        self,
        project_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        追加对话记录

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            project_id: 项目ID
            role: 角色（user/assistant）
            content: 对话内容
            metadata: 元数据（可选）
        """
        await self.conversation_repo.append(project_id, role, content, metadata)

    def format_conversation_history(self, history_records: List[NovelConversation]) -> List[Dict[str, str]]:
        """
        格式化对话历史为LLM输入格式

        此方法将数据库中的对话记录转换为LLM API所需的消息格式。
        处理JSON解析、字段提取等复杂逻辑。

        Args:
            history_records: 原始对话记录列表

        Returns:
            List[Dict[str, str]]: 格式化后的对话历史

        Raises:
            ConversationExtractionError: 如果无法提取有效内容

        Example:
            >>> records = await conversation_service.list_conversations(project_id)
            >>> formatted = conversation_service.format_conversation_history(records)
            >>> # 可直接传给LLM API
            >>> llm_response = await llm_service.get_llm_response(..., formatted)
        """
        formatted_history: List[Dict[str, str]] = []

        for record in history_records:
            role = record.role
            content = record.content
            if not role or not content:
                continue

            # 使用安全解析（失败时跳过）
            data = parse_llm_json_safe(content)
            if not data:
                continue

            if role == "user":
                # 提取用户消息 - 兼容多种字段格式
                # 优先级：value > message > 整个data
                user_value = data.get("value") or data.get("message") or data

                if isinstance(user_value, str):
                    formatted_history.append({"role": "user", "content": user_value})
                elif isinstance(user_value, dict):
                    # 如果是dict，尝试提取message字段（兼容旧格式）
                    msg = user_value.get("message")
                    if msg and isinstance(msg, str):
                        formatted_history.append({"role": "user", "content": msg})
            elif role == "assistant":
                # 提取AI消息
                ai_message = data.get("ai_message") if isinstance(data, dict) else None
                if ai_message:
                    formatted_history.append({"role": "assistant", "content": ai_message})

        if not formatted_history:
            # 从记录中提取project_id用于错误信息
            project_id = history_records[0].project_id if history_records else "unknown"
            raise ConversationExtractionError(
                project_id=project_id,
                reason="对话记录存在但格式无效，无法提取有效内容"
            )

        return formatted_history
