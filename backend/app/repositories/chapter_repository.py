"""
章节数据访问层

本文件包含ChapterRepository，并为向后兼容导出其他章节相关Repository。

重构说明：
    原chapter_repository.py包含4个Repository类，现已拆分为独立文件：
    - chapter_repository.py: ChapterRepository
    - chapter_version_repository.py: ChapterVersionRepository
    - chapter_evaluation_repository.py: ChapterEvaluationRepository
    - chapter_outline_repository.py: ChapterOutlineRepository

    为保持向后兼容性，本文件仍导出所有4个Repository类。
    新代码建议直接从各自文件导入。
"""

from typing import Iterable, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.novel import Chapter, ChapterVersion, ChapterEvaluation, ChapterOutline

# 向后兼容导出（新代码建议直接从各自模块导入）
from .chapter_version_repository import ChapterVersionRepository
from .chapter_evaluation_repository import ChapterEvaluationRepository
from .chapter_outline_repository import ChapterOutlineRepository


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
                selectinload(Chapter.manga_prompt),
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
        return await self.count_by_field("project_id", project_id)

    async def delete_by_project(self, project_id: str) -> int:
        """
        删除项目的所有章节

        Args:
            project_id: 项目ID

        Returns:
            删除的记录数
        """
        return await self.delete_by_project_id(project_id)

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


# 模块级导出（向后兼容）
__all__ = [
    "ChapterRepository",
    "ChapterVersionRepository",
    "ChapterEvaluationRepository",
    "ChapterOutlineRepository",
]
