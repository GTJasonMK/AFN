from typing import Iterable, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, load_only

from .base import BaseRepository, RelationOptionsMixin
from ..models import Chapter, ChapterOutline, NovelProject
from ..models.novel import NovelBlueprint


class NovelRepository(RelationOptionsMixin, BaseRepository[NovelProject]):
    model = NovelProject

    def _detail_load_options(self):
        return [
            selectinload(NovelProject.blueprint),
            selectinload(NovelProject.characters),
            selectinload(NovelProject.relationships_),
            selectinload(NovelProject.outlines),
            selectinload(NovelProject.conversations),
            selectinload(NovelProject.part_outlines),
            selectinload(NovelProject.chapters).selectinload(Chapter.versions),
            selectinload(NovelProject.chapters).selectinload(Chapter.evaluations),
            selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
        ]

    def _summary_load_options(self):
        return [
            # 只加载blueprint的genre字段，避免加载world_setting等大字段
            selectinload(NovelProject.blueprint).load_only(NovelBlueprint.genre),
            # 大纲只需要章节号用于计数
            selectinload(NovelProject.outlines).load_only(ChapterOutline.chapter_number),
            selectinload(NovelProject.part_outlines),
            # 章节只需要selected_version_id用于判断完成状态，不需要加载完整的版本对象
            selectinload(NovelProject.chapters).load_only(
                Chapter.chapter_number,
                Chapter.selected_version_id,
            ),
        ]

    async def count_all(self) -> int:
        """统计所有项目数量"""
        result = await self.session.execute(select(func.count(NovelProject.id)))
        return result.scalar_one()

    async def count_by_user(self, user_id: int) -> int:
        """统计指定用户的项目数量

        Args:
            user_id: 用户ID
        """
        stmt = select(func.count(NovelProject.id)).where(NovelProject.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, project_id: str) -> Optional[NovelProject]:
        stmt = (
            select(NovelProject)
            .where(NovelProject.id == project_id)
        )
        stmt = self._apply_load_options(stmt, self._detail_load_options())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[Iterable[NovelProject], int]:
        """
        分页获取指定用户的项目列表

        Args:
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页数量（默认20，最大100）

        Returns:
            Tuple[Iterable[NovelProject], int]: (项目列表, 总数)
        """
        count_stmt = select(func.count(NovelProject.id)).where(NovelProject.user_id == user_id)

        stmt = (
            select(NovelProject)
            .where(NovelProject.user_id == user_id)
        )

        stmt = stmt.order_by(NovelProject.updated_at.desc())
        stmt = self._apply_load_options(stmt, self._summary_load_options())
        return await self.paginate(
            stmt,
            count_stmt,
            page=page,
            page_size=page_size,
            max_page_size=100,
        )

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[Iterable[NovelProject], int]:
        """
        分页获取所有项目列表

        Args:
            page: 页码（从1开始）
            page_size: 每页数量（默认20，最大100）

        Returns:
            Tuple[Iterable[NovelProject], int]: (项目列表, 总数)

        注意:
            此方法用于管理视图，生产环境应限制访问。
            内存安全：使用分页避免一次性加载大量数据。
        """
        count_stmt = select(func.count(NovelProject.id))

        stmt = (
            select(NovelProject)
            .order_by(NovelProject.updated_at.desc())
            .options(selectinload(NovelProject.owner))
        )
        stmt = self._apply_load_options(stmt, self._summary_load_options())
        return await self.paginate(
            stmt,
            count_stmt,
            page=page,
            page_size=page_size,
            max_page_size=100,
        )
