from typing import Iterable, Optional

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

    async def list_by_user(self, user_id: int) -> Iterable[NovelProject]:
        result = await self.session.execute(
            select(NovelProject)
            .where(NovelProject.user_id == user_id)
            .order_by(NovelProject.updated_at.desc())
            .options(
                # 只加载blueprint的genre字段，避免加载world_setting等大字段
                selectinload(NovelProject.blueprint).load_only(NovelBlueprint.genre),
                selectinload(NovelProject.outlines),
                selectinload(NovelProject.part_outlines),
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
            )
        )
        return result.scalars().all()

    async def list_all(self) -> Iterable[NovelProject]:
        result = await self.session.execute(
            select(NovelProject)
            .order_by(NovelProject.updated_at.desc())
            .options(
                selectinload(NovelProject.owner),
                # 只加载blueprint的genre字段，避免加载world_setting等大字段
                selectinload(NovelProject.blueprint).load_only(NovelBlueprint.genre),
                selectinload(NovelProject.outlines),
                selectinload(NovelProject.part_outlines),
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
            )
        )
        return result.scalars().all()
