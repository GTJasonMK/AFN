"""主角档案系统Repository层

包含主角档案、属性变更、行为记录、删除标记的数据访问类。
"""
from typing import Any, Iterable, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.protagonist import (
    ProtagonistProfile,
    ProtagonistAttributeChange,
    ProtagonistBehaviorRecord,
    ProtagonistDeletionMark,
)
from .base import BaseRepository


class ProtagonistProfileRepository(BaseRepository[ProtagonistProfile]):
    """主角档案Repository"""

    model = ProtagonistProfile

    async def get_by_project_and_name(
        self,
        project_id: str,
        character_name: str
    ) -> Optional[ProtagonistProfile]:
        """根据项目ID和角色名获取档案"""
        return await self.get(project_id=project_id, character_name=character_name)

    async def get_by_id(self, profile_id: int) -> Optional[ProtagonistProfile]:
        """根据ID获取档案"""
        return await self.get(id=profile_id)

    async def list_by_project_id(self, project_id: str) -> Iterable[ProtagonistProfile]:
        """获取项目下所有主角档案"""
        return await self.list(
            filters={"project_id": project_id},
            order_by="created_at",
            order_desc=False
        )


class ProtagonistAttributeChangeRepository(BaseRepository[ProtagonistAttributeChange]):
    """属性变更历史Repository"""

    model = ProtagonistAttributeChange

    async def list_by_profile(
        self,
        profile_id: int,
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None,
        category: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ProtagonistAttributeChange]:
        """获取档案的变更历史

        Args:
            profile_id: 档案ID
            start_chapter: 起始章节（可选）
            end_chapter: 结束章节（可选）
            category: 属性类别过滤（可选）
            order_desc: 是否降序

        Returns:
            变更记录列表
        """
        stmt = select(self.model).where(self.model.profile_id == profile_id)

        if start_chapter is not None:
            stmt = stmt.where(self.model.chapter_number >= start_chapter)
        if end_chapter is not None:
            stmt = stmt.where(self.model.chapter_number <= end_chapter)
        if category:
            stmt = stmt.where(self.model.attribute_category == category)

        if order_desc:
            stmt = stmt.order_by(self.model.chapter_number.desc(), self.model.id.desc())
        else:
            stmt = stmt.order_by(self.model.chapter_number, self.model.id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_attribute(
        self,
        profile_id: int,
        category: str,
        attribute_key: str
    ) -> List[ProtagonistAttributeChange]:
        """获取特定属性的所有变更记录"""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.profile_id == profile_id,
                    self.model.attribute_category == category,
                    self.model.attribute_key == attribute_key
                )
            )
            .order_by(self.model.chapter_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ProtagonistBehaviorRecordRepository(BaseRepository[ProtagonistBehaviorRecord]):
    """行为记录Repository"""

    model = ProtagonistBehaviorRecord

    async def list_by_profile(
        self,
        profile_id: int,
        chapter: Optional[int] = None,
        limit: Optional[int] = None,
        order_desc: bool = True
    ) -> List[ProtagonistBehaviorRecord]:
        """获取档案的行为记录

        Args:
            profile_id: 档案ID
            chapter: 指定章节（可选）
            limit: 返回数量限制（可选）
            order_desc: 是否降序（默认True，最新的在前）

        Returns:
            行为记录列表
        """
        stmt = select(self.model).where(self.model.profile_id == profile_id)

        if chapter is not None:
            stmt = stmt.where(self.model.chapter_number == chapter)

        if order_desc:
            stmt = stmt.order_by(self.model.chapter_number.desc(), self.model.id.desc())
        else:
            stmt = stmt.order_by(self.model.chapter_number, self.model.id)

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent_by_profile(
        self,
        profile_id: int,
        limit: int = 20
    ) -> List[ProtagonistBehaviorRecord]:
        """获取最近的行为记录"""
        return await self.list_by_profile(profile_id, limit=limit, order_desc=True)

    async def get_classification_stats(
        self,
        profile_id: int,
        attribute_key: str,
        window_chapters: int = 10
    ) -> dict:
        """获取隐性属性的分类统计

        统计最近N章内某属性的符合/不符合次数。

        Args:
            profile_id: 档案ID
            attribute_key: 属性键名
            window_chapters: 统计窗口大小（章节数）

        Returns:
            统计结果: {total, conform_count, non_conform_count, records}
        """
        # 获取最近的行为记录
        stmt = (
            select(self.model)
            .where(self.model.profile_id == profile_id)
            .order_by(self.model.chapter_number.desc())
        )
        result = await self.session.execute(stmt)
        all_records = list(result.scalars().all())

        # 筛选包含目标属性分类的记录
        relevant_records = []
        conform_count = 0
        non_conform_count = 0
        chapters_seen = set()

        for record in all_records:
            if len(chapters_seen) >= window_chapters:
                break

            classifications = record.classification_results or {}
            if attribute_key in classifications:
                relevant_records.append(record)
                chapters_seen.add(record.chapter_number)

                if classifications[attribute_key] == "conform":
                    conform_count += 1
                elif classifications[attribute_key] == "non-conform":
                    non_conform_count += 1

        return {
            "total": len(relevant_records),
            "conform_count": conform_count,
            "non_conform_count": non_conform_count,
            "records": relevant_records
        }


class ProtagonistDeletionMarkRepository(BaseRepository[ProtagonistDeletionMark]):
    """删除标记Repository"""

    model = ProtagonistDeletionMark

    async def get_mark(
        self,
        profile_id: int,
        category: str,
        attribute_key: str
    ) -> Optional[ProtagonistDeletionMark]:
        """获取特定属性的删除标记"""
        return await self.get(
            profile_id=profile_id,
            attribute_category=category,
            attribute_key=attribute_key
        )

    async def list_by_profile(
        self,
        profile_id: int,
        category: Optional[str] = None,
        executed: Optional[bool] = None
    ) -> List[ProtagonistDeletionMark]:
        """获取档案的删除标记

        Args:
            profile_id: 档案ID
            category: 属性类别过滤（可选）
            executed: 是否已执行过滤（可选）

        Returns:
            删除标记列表
        """
        stmt = select(self.model).where(self.model.profile_id == profile_id)

        if category:
            stmt = stmt.where(self.model.attribute_category == category)
        if executed is not None:
            stmt = stmt.where(self.model.is_executed == executed)

        stmt = stmt.order_by(self.model.chapter_number)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_marks(self, profile_id: int) -> List[ProtagonistDeletionMark]:
        """获取所有未执行的删除标记"""
        return await self.list_by_profile(profile_id, executed=False)

    async def list_ready_for_deletion(
        self,
        profile_id: int,
        threshold: int = 5
    ) -> List[ProtagonistDeletionMark]:
        """获取达到删除阈值的标记

        Args:
            profile_id: 档案ID
            threshold: 连续标记阈值（默认5）

        Returns:
            达到阈值的删除标记列表
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.profile_id == profile_id,
                    self.model.is_executed == False,
                    self.model.consecutive_count >= threshold
                )
            )
            .order_by(self.model.chapter_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
