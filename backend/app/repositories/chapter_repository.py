"""章节数据访问层"""

from typing import Iterable, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.novel import Chapter, ChapterVersion, ChapterEvaluation, ChapterOutline


class ChapterRepository(BaseRepository[Chapter]):
    """章节Repository，封装章节相关的数据库操作"""

    model = Chapter

    async def get_by_id(self, chapter_id: int) -> Optional[Chapter]:
        """
        根据ID获取章节（预加载关联数据）

        Args:
            chapter_id: 章节ID

        Returns:
            章节实例，不存在返回None
        """
        stmt = (
            select(Chapter)
            .where(Chapter.id == chapter_id)
            .options(
                selectinload(Chapter.versions),
                selectinload(Chapter.selected_version),
                selectinload(Chapter.evaluations),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_project_and_number(
        self,
        project_id: str,
        chapter_number: int
    ) -> Optional[Chapter]:
        """
        根据项目ID和章节号获取章节

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            章节实例，不存在返回None
        """
        stmt = (
            select(Chapter)
            .where(
                Chapter.project_id == project_id,
                Chapter.chapter_number == chapter_number
            )
            .options(
                selectinload(Chapter.versions),
                selectinload(Chapter.selected_version),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_project_and_numbers(
        self,
        project_id: str,
        chapter_numbers: List[int]
    ) -> List[Chapter]:
        """
        批量获取指定章节号的章节（优化版本，避免N+1查询）

        Args:
            project_id: 项目ID
            chapter_numbers: 章节号列表

        Returns:
            章节列表
        """
        if not chapter_numbers:
            return []

        stmt = (
            select(Chapter)
            .where(
                Chapter.project_id == project_id,
                Chapter.chapter_number.in_(chapter_numbers)
            )
            .options(
                selectinload(Chapter.selected_version),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_project(self, project_id: str) -> Iterable[Chapter]:
        """
        获取项目的所有章节

        Args:
            project_id: 项目ID

        Returns:
            章节列表
        """
        stmt = (
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.chapter_number)
            .options(
                selectinload(Chapter.selected_version),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_project(self, project_id: str) -> int:
        """
        统计项目的章节数量

        Args:
            project_id: 项目ID

        Returns:
            章节数量
        """
        from sqlalchemy import func
        stmt = (
            select(func.count(Chapter.id))
            .where(Chapter.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def delete_by_project(self, project_id: str) -> None:
        """
        删除项目的所有章节

        Args:
            project_id: 项目ID
        """
        await self.session.execute(
            delete(Chapter).where(Chapter.project_id == project_id)
        )

    async def get_or_create(
        self,
        project_id: str,
        chapter_number: int
    ) -> Chapter:
        """
        获取或创建章节（如果不存在）

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            章节实例
        """
        chapter = await self.get_by_project_and_number(project_id, chapter_number)
        if chapter:
            return chapter

        # 创建新章节
        chapter = Chapter(project_id=project_id, chapter_number=chapter_number)
        self.session.add(chapter)
        await self.session.flush()
        await self.session.refresh(chapter)
        return chapter


class ChapterVersionRepository(BaseRepository[ChapterVersion]):
    """章节版本Repository"""

    model = ChapterVersion

    async def list_by_chapter(self, chapter_id: int) -> Iterable[ChapterVersion]:
        """
        获取章节的所有版本

        Args:
            chapter_id: 章节ID

        Returns:
            版本列表
        """
        stmt = (
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == chapter_id)
            .order_by(ChapterVersion.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_chapter(self, chapter_id: int) -> None:
        """
        删除章节的所有版本

        Args:
            chapter_id: 章节ID
        """
        await self.session.execute(
            delete(ChapterVersion).where(ChapterVersion.chapter_id == chapter_id)
        )

    async def replace_all(
        self,
        chapter_id: int,
        versions_data: List[dict]
    ) -> List[ChapterVersion]:
        """
        替换章节的所有版本（先删除再创建）

        Args:
            chapter_id: 章节ID
            versions_data: 版本数据列表，每个dict包含content, metadata, version_label

        Returns:
            创建的版本列表
        """
        # 先删除所有旧版本
        await self.delete_by_chapter(chapter_id)

        # 使用批量创建而非循环
        versions = [
            ChapterVersion(
                chapter_id=chapter_id,
                content=data.get("content", ""),
                metadata=data.get("metadata"),
                version_label=data.get("version_label", ""),
            )
            for data in versions_data
        ]

        if versions:
            self.session.add_all(versions)
        await self.session.flush()
        return versions


class ChapterEvaluationRepository(BaseRepository[ChapterEvaluation]):
    """章节评价Repository"""

    model = ChapterEvaluation

    async def list_by_chapter(self, chapter_id: int) -> Iterable[ChapterEvaluation]:
        """
        获取章节的所有评价

        Args:
            chapter_id: 章节ID

        Returns:
            评价列表
        """
        stmt = (
            select(ChapterEvaluation)
            .where(ChapterEvaluation.chapter_id == chapter_id)
            .order_by(ChapterEvaluation.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


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
        from sqlalchemy import func
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
        from sqlalchemy import func
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
