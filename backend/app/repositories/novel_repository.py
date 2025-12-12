from typing import Iterable, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, load_only

from .base import BaseRepository
from ..models import Chapter, NovelProject
from ..models.novel import NovelBlueprint


class NovelRepository(BaseRepository[NovelProject]):
    model = NovelProject

    async def count_all(self) -> int:
        """统计所有项目数量"""
        result = await self.session.execute(select(func.count(NovelProject.id)))
        return result.scalar_one()

    async def count_by_user(self, user_id: int) -> int:
        """统计指定用户的项目数量"""
        result = await self.session.execute(
            select(func.count(NovelProject.id)).where(NovelProject.user_id == user_id)
        )
        return result.scalar_one()

    async def get_by_id(self, project_id: str) -> Optional[NovelProject]:
        stmt = (
            select(NovelProject)
            .where(NovelProject.id == project_id)
            .options(
                selectinload(NovelProject.blueprint),
                selectinload(NovelProject.characters),
                selectinload(NovelProject.relationships_),
                selectinload(NovelProject.outlines),
                selectinload(NovelProject.conversations),
                selectinload(NovelProject.part_outlines),
                selectinload(NovelProject.chapters).selectinload(Chapter.versions),
                selectinload(NovelProject.chapters).selectinload(Chapter.evaluations),
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
            )
        )
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
        page_size = min(page_size, 100)  # 限制最大每页数量
        offset = (page - 1) * page_size

        # 先获取总数
        total = await self.count_by_user(user_id)

        # 分页查询
        result = await self.session.execute(
            select(NovelProject)
            .where(NovelProject.user_id == user_id)
            .order_by(NovelProject.updated_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(
                # 只加载blueprint的genre字段，避免加载world_setting等大字段
                selectinload(NovelProject.blueprint).load_only(NovelBlueprint.genre),
                selectinload(NovelProject.outlines),
                selectinload(NovelProject.part_outlines),
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
            )
        )
        return result.scalars().all(), total

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
        page_size = min(page_size, 100)  # 限制最大每页数量
        offset = (page - 1) * page_size

        # 先获取总数
        total = await self.count_all()

        # 分页查询
        result = await self.session.execute(
            select(NovelProject)
            .order_by(NovelProject.updated_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(
                selectinload(NovelProject.owner),
                # 只加载blueprint的genre字段，避免加载world_setting等大字段
                selectinload(NovelProject.blueprint).load_only(NovelBlueprint.genre),
                selectinload(NovelProject.outlines),
                selectinload(NovelProject.part_outlines),
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
            )
        )
        return result.scalars().all(), total
