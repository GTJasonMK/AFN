"""对话记录数据访问层"""

from typing import List

from sqlalchemy import select, func

from .base import BaseRepository
from ..models.novel import NovelConversation
from ..models.coding import CodingConversation


class NovelConversationRepository(BaseRepository[NovelConversation]):
    """小说项目对话记录Repository"""

    model = NovelConversation

    async def list_by_project(self, project_id: str) -> List[NovelConversation]:
        """获取项目的所有对话记录（按序号升序）"""
        stmt = (
            select(NovelConversation)
            .where(NovelConversation.project_id == project_id)
            .order_by(NovelConversation.seq.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def get_next_seq(self, project_id: str) -> int:
        """获取项目的下一个对话序号"""
        result = await self.session.execute(
            select(func.max(NovelConversation.seq)).where(
                NovelConversation.project_id == project_id
            )
        )
        current_max = result.scalar()
        return (current_max or 0) + 1

    async def append(
        self,
        project_id: str,
        role: str,
        content: str,
        metadata: dict = None
    ) -> NovelConversation:
        """追加对话记录（自动分配序号）"""
        next_seq = await self.get_next_seq(project_id)
        conversation = NovelConversation(
            project_id=project_id,
            seq=next_seq,
            role=role,
            content=content,
            metadata=metadata,
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation


class CodingConversationRepository(BaseRepository[CodingConversation]):
    """编程项目对话记录Repository"""

    model = CodingConversation

    async def list_by_project(self, project_id: str) -> List[CodingConversation]:
        """获取项目的所有对话记录（按序号升序）"""
        stmt = (
            select(CodingConversation)
            .where(CodingConversation.project_id == project_id)
            .order_by(CodingConversation.seq.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def get_next_seq(self, project_id: str) -> int:
        """获取项目的下一个对话序号"""
        result = await self.session.execute(
            select(func.max(CodingConversation.seq)).where(
                CodingConversation.project_id == project_id
            )
        )
        current_max = result.scalar()
        return (current_max or 0) + 1

    async def append(
        self,
        project_id: str,
        role: str,
        content: str,
        metadata: dict = None
    ) -> CodingConversation:
        """追加对话记录（自动分配序号）"""
        next_seq = await self.get_next_seq(project_id)
        conversation = CodingConversation(
            project_id=project_id,
            seq=next_seq,
            role=role,
            content=content,
            metadata_json=metadata,
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation
