"""章节大纲数据访问层"""

from typing import Iterable, List, Optional

from sqlalchemy import delete, func, select

from .base import BaseRepository
from ..models.novel import ChapterOutline


class ChapterOutlineRepository(BaseRepository[ChapterOutline]):
    """章节大纲Repository"""

    model = ChapterOutline

    async def get_by_project_and_number(
        self,
        project_id: str,
        chapter_number: int
    ) -> Optional[ChapterOutline]:
        """
        根据项目ID和章节号获取大纲

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            大纲实例，不存在返回None
        """
        stmt = select(ChapterOutline).where(
            ChapterOutline.project_id == project_id,
            ChapterOutline.chapter_number == chapter_number
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_project(self, project_id: str) -> Iterable[ChapterOutline]:
        """
        获取项目的所有章节大纲

        Args:
            project_id: 项目ID

        Returns:
            大纲列表
        """
        stmt = (
            select(ChapterOutline)
            .where(ChapterOutline.project_id == project_id)
            .order_by(ChapterOutline.chapter_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_project(self, project_id: str) -> int:
        """
        统计项目的章节大纲数量

        Args:
            project_id: 项目ID

        Returns:
            大纲数量
        """
        stmt = (
            select(func.count(ChapterOutline.id))
            .where(ChapterOutline.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def delete_by_project(self, project_id: str) -> None:
        """
        删除项目的所有章节大纲

        Args:
            project_id: 项目ID
        """
        await self.session.execute(
            delete(ChapterOutline).where(ChapterOutline.project_id == project_id)
        )

    async def delete_from_chapter(self, project_id: str, from_chapter: int) -> int:
        """
        删除指定章节号及之后的所有章节大纲

        用于串行生成原则下的级联删除：重新生成某章时，删除该章及之后的所有大纲。

        Args:
            project_id: 项目ID
            from_chapter: 起始章节号（包含）

        Returns:
            int: 删除的大纲数量
        """
        # 先统计要删除的数量
        count_stmt = (
            select(func.count(ChapterOutline.id))
            .where(ChapterOutline.project_id == project_id)
            .where(ChapterOutline.chapter_number >= from_chapter)
        )
        result = await self.session.execute(count_stmt)
        delete_count = result.scalar() or 0

        # 执行删除
        await self.session.execute(
            delete(ChapterOutline)
            .where(ChapterOutline.project_id == project_id)
            .where(ChapterOutline.chapter_number >= from_chapter)
        )

        return delete_count

    async def bulk_create(
        self,
        project_id: str,
        outlines: List[dict]
    ) -> None:
        """
        批量创建章节大纲（先删除旧数据）

        Args:
            project_id: 项目ID
            outlines: 大纲数据列表
        """
        await self.delete_by_project(project_id)

        # 使用批量创建而非循环
        outline_models = [
            ChapterOutline(
                project_id=project_id,
                chapter_number=outline_data.get("chapter_number"),
                title=outline_data.get("title", ""),
                summary=outline_data.get("summary"),
            )
            for outline_data in outlines
        ]

        if outline_models:
            self.session.add_all(outline_models)
        await self.session.flush()

    async def upsert_outline(
        self,
        project_id: str,
        chapter_number: int,
        title: str,
        summary: str
    ) -> ChapterOutline:
        """
        更新或创建章节大纲（upsert）

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            title: 章节标题
            summary: 章节摘要

        Returns:
            创建或更新的大纲实例
        """
        existing = await self.get_by_project_and_number(project_id, chapter_number)
        if existing:
            # 更新现有大纲
            existing.title = title
            existing.summary = summary
            await self.session.flush()
            return existing
        else:
            # 创建新大纲
            outline = ChapterOutline(
                project_id=project_id,
                chapter_number=chapter_number,
                title=title,
                summary=summary,
            )
            self.session.add(outline)
            await self.session.flush()
            return outline
