"""
Coding项目Repository

提供Coding项目相关的数据访问操作。
"""

from typing import Iterable, Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.coding import (
    CodingProject,
    CodingConversation,
    CodingBlueprint,
    CodingSystem,
    CodingModule,
    CodingFeature,
    CodingFeatureVersion,
)


class CodingProjectRepository(BaseRepository[CodingProject]):
    """Coding项目仓储"""

    model = CodingProject

    async def get_by_id(self, project_id: str) -> Optional[CodingProject]:
        """根据ID获取项目"""
        return await self.get(id=project_id)

    async def get_with_relations(self, project_id: str) -> Optional[CodingProject]:
        """获取项目及其所有关联数据"""
        stmt = (
            select(CodingProject)
            .where(CodingProject.id == project_id)
            .options(
                selectinload(CodingProject.blueprint),
                selectinload(CodingProject.conversations),
                selectinload(CodingProject.systems),
                selectinload(CodingProject.modules),
                selectinload(CodingProject.features).selectinload(CodingFeature.versions),
            )
        )
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
        order_by: str = "updated_at",
        order_desc: bool = True,
    ) -> List[CodingProject]:
        """获取用户的所有项目（包含关联数据）"""
        stmt = (
            select(CodingProject)
            .where(CodingProject.user_id == user_id)
            .options(
                selectinload(CodingProject.blueprint),
                selectinload(CodingProject.features),
            )
        )

        if order_by:
            field = getattr(CodingProject, order_by, None)
            if field is not None:
                stmt = stmt.order_by(field.desc() if order_desc else field)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class CodingConversationRepository(BaseRepository[CodingConversation]):
    """Coding对话仓储"""

    model = CodingConversation

    async def get_max_seq(self, project_id: str) -> int:
        """获取项目的最大对话序号"""
        from sqlalchemy import func
        stmt = (
            select(func.max(CodingConversation.seq))
            .where(CodingConversation.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_by_project_ordered(self, project_id: str) -> List[CodingConversation]:
        """获取项目的对话列表（按序号排序）"""
        conversations = await self.list(
            filters={"project_id": project_id},
            order_by="seq",
            order_desc=False,
        )
        return list(conversations)


class CodingBlueprintRepository(BaseRepository[CodingBlueprint]):
    """Coding蓝图仓储"""

    model = CodingBlueprint

    async def get_by_project(self, project_id: str) -> Optional[CodingBlueprint]:
        """根据项目ID获取蓝图"""
        return await self.get(project_id=project_id)


class CodingSystemRepository(BaseRepository[CodingSystem]):
    """Coding系统仓储"""

    model = CodingSystem

    async def get_by_project_and_number(
        self,
        project_id: str,
        system_number: int,
    ) -> Optional[CodingSystem]:
        """根据项目ID和系统编号获取系统"""
        return await self.get(project_id=project_id, system_number=system_number)

    async def get_by_project_ordered(self, project_id: str) -> List[CodingSystem]:
        """获取项目的系统列表（按编号排序）"""
        systems = await self.list(
            filters={"project_id": project_id},
            order_by="system_number",
            order_desc=False,
        )
        return list(systems)

    async def get_max_number(self, project_id: str) -> int:
        """获取项目的最大系统编号"""
        from sqlalchemy import func
        stmt = (
            select(func.max(CodingSystem.system_number))
            .where(CodingSystem.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class CodingModuleRepository(BaseRepository[CodingModule]):
    """Coding模块仓储"""

    model = CodingModule

    async def get_by_project_and_number(
        self,
        project_id: str,
        module_number: int,
    ) -> Optional[CodingModule]:
        """根据项目ID和模块编号获取模块"""
        return await self.get(project_id=project_id, module_number=module_number)

    async def get_by_project_ordered(self, project_id: str) -> List[CodingModule]:
        """获取项目的模块列表（按编号排序）"""
        modules = await self.list(
            filters={"project_id": project_id},
            order_by="module_number",
            order_desc=False,
        )
        return list(modules)

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

    async def get_max_number(self, project_id: str) -> int:
        """获取项目的最大模块编号"""
        from sqlalchemy import func
        stmt = (
            select(func.max(CodingModule.module_number))
            .where(CodingModule.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class CodingFeatureRepository(BaseRepository[CodingFeature]):
    """Coding功能仓储"""

    model = CodingFeature

    async def get_by_project_and_number(
        self,
        project_id: str,
        feature_number: int,
    ) -> Optional[CodingFeature]:
        """根据项目ID和功能编号获取功能"""
        return await self.get(project_id=project_id, feature_number=feature_number)

    async def get_with_versions(
        self,
        project_id: str,
        feature_number: int,
    ) -> Optional[CodingFeature]:
        """获取功能及其版本列表"""
        stmt = (
            select(CodingFeature)
            .where(CodingFeature.project_id == project_id)
            .where(CodingFeature.feature_number == feature_number)
            .options(selectinload(CodingFeature.versions))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_project_ordered(self, project_id: str) -> List[CodingFeature]:
        """获取项目的功能列表（按编号排序）"""
        features = await self.list(
            filters={"project_id": project_id},
            order_by="feature_number",
            order_desc=False,
        )
        return list(features)

    async def get_by_module(
        self,
        project_id: str,
        module_number: int,
    ) -> List[CodingFeature]:
        """获取模块下的所有功能"""
        stmt = (
            select(CodingFeature)
            .where(CodingFeature.project_id == project_id)
            .where(CodingFeature.module_number == module_number)
            .order_by(CodingFeature.feature_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_system(
        self,
        project_id: str,
        system_number: int,
    ) -> List[CodingFeature]:
        """获取系统下的所有功能"""
        stmt = (
            select(CodingFeature)
            .where(CodingFeature.project_id == project_id)
            .where(CodingFeature.system_number == system_number)
            .order_by(CodingFeature.feature_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_max_number(self, project_id: str) -> int:
        """获取项目的最大功能编号"""
        from sqlalchemy import func
        stmt = (
            select(func.max(CodingFeature.feature_number))
            .where(CodingFeature.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class CodingFeatureVersionRepository(BaseRepository[CodingFeatureVersion]):
    """Coding功能版本仓储"""

    model = CodingFeatureVersion

    async def get_by_feature(self, feature_id: int) -> List[CodingFeatureVersion]:
        """获取功能的所有版本"""
        versions = await self.list(
            filters={"feature_id": feature_id},
            order_by="created_at",
            order_desc=False,
        )
        return list(versions)

    async def get_latest(self, feature_id: int) -> Optional[CodingFeatureVersion]:
        """获取功能的最新版本"""
        versions = await self.list(
            filters={"feature_id": feature_id},
            order_by="created_at",
            order_desc=True,
        )
        versions_list = list(versions)
        return versions_list[0] if versions_list else None
