"""
Coding项目Repository

提供Coding项目相关的数据访问操作。
"""

from typing import Iterable, Optional, List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository, RelationOptionsMixin, SequenceRepositoryMixin
from ..models.coding import (
    CodingProject,
    CodingConversation,
    CodingBlueprint,
    CodingSystem,
    CodingModule,
)


class CodingProjectRepository(RelationOptionsMixin, BaseRepository[CodingProject]):
    """Coding项目仓储"""

    model = CodingProject

    def _detail_load_options(self):
        return [
            selectinload(CodingProject.blueprint),
            selectinload(CodingProject.conversations),
            selectinload(CodingProject.systems),
            selectinload(CodingProject.modules),
        ]

    def _summary_load_options(self):
        return [
            selectinload(CodingProject.blueprint),
        ]

    async def get_by_id(self, project_id: str) -> Optional[CodingProject]:
        """根据ID获取项目"""
        return await self.get(id=project_id)

    async def get_with_relations(self, project_id: str) -> Optional[CodingProject]:
        """获取项目及其所有关联数据"""
        stmt = (
            select(CodingProject)
            .where(CodingProject.id == project_id)
        )
        stmt = self._apply_load_options(stmt, self._detail_load_options())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_user(
        self,
        user_id: int,
        order_by: str = "updated_at",
        order_desc: bool = True,
    ) -> Iterable[CodingProject]:
        """获取用户的所有项目"""
        return await self.list(
            filters={"user_id": user_id},
            order_by=order_by,
            order_desc=order_desc,
        )

    async def get_by_user_with_relations(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        order_by: str = "updated_at",
        order_desc: bool = True,
    ) -> Tuple[List[CodingProject], int]:
        """分页获取用户的项目（包含关联数据）"""
        count_stmt = select(func.count(CodingProject.id)).where(CodingProject.user_id == user_id)
        stmt = (
            select(CodingProject)
            .where(CodingProject.user_id == user_id)
        )
        stmt = self._apply_load_options(stmt, self._summary_load_options())

        if order_by:
            field = getattr(CodingProject, order_by, None)
            if field is not None:
                stmt = stmt.order_by(field.desc() if order_desc else field)

        return await self.paginate(
            stmt,
            count_stmt,
            page=page,
            page_size=page_size,
            max_page_size=100,
        )


class CodingConversationRepository(SequenceRepositoryMixin, BaseRepository[CodingConversation]):
    """Coding对话仓储"""

    model = CodingConversation
    sequence_field = "seq"

    async def get_max_seq(self, project_id: str) -> int:
        """获取项目的最大对话序号"""
        return await self.get_max_number(project_id)


class CodingBlueprintRepository(BaseRepository[CodingBlueprint]):
    """Coding蓝图仓储"""

    model = CodingBlueprint

    async def get_by_project(self, project_id: str) -> Optional[CodingBlueprint]:
        """根据项目ID获取蓝图"""
        return await self.get(project_id=project_id)


class CodingSystemRepository(SequenceRepositoryMixin, BaseRepository[CodingSystem]):
    """Coding系统仓储"""

    model = CodingSystem
    sequence_field = "system_number"

    async def get_by_project_and_number(
        self,
        project_id: str,
        system_number: int,
    ) -> Optional[CodingSystem]:
        """根据项目ID和系统编号获取系统"""
        return await self.get(project_id=project_id, system_number=system_number)


class CodingModuleRepository(SequenceRepositoryMixin, BaseRepository[CodingModule]):
    """Coding模块仓储"""

    model = CodingModule
    sequence_field = "module_number"

    async def get_by_project_and_number(
        self,
        project_id: str,
        module_number: int,
    ) -> Optional[CodingModule]:
        """根据项目ID和模块编号获取模块"""
        return await self.get(project_id=project_id, module_number=module_number)

    async def get_by_system(
        self,
        project_id: str,
        system_number: int,
    ) -> List[CodingModule]:
        """获取系统下的所有模块"""
        stmt = (
            select(CodingModule)
            .where(CodingModule.project_id == project_id)
            .where(CodingModule.system_number == system_number)
            .order_by(CodingModule.module_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

