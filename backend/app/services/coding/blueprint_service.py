"""
Coding蓝图服务

负责Coding项目蓝图的生成和管理。
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.state_machine import ProjectStatus
from ...exceptions import ResourceNotFoundError
from ...models.coding import CodingProject, CodingBlueprint
from ...repositories.coding_repository import (
    CodingProjectRepository,
    CodingBlueprintRepository,
    CodingSystemRepository,
    CodingModuleRepository,
    CodingFeatureRepository,
)
from ...schemas.coding import (
    CodingBlueprint as CodingBlueprintSchema,
    CodingBlueprintPatch,
)
from .project_service import CodingProjectService

logger = logging.getLogger(__name__)


class CodingBlueprintService:
    """
    Coding蓝图服务

    负责：
    - 蓝图更新
    - 蓝图数据序列化
    - 系统/模块/功能结构管理
    """

    def __init__(self, session: AsyncSession):
        """
        初始化CodingBlueprintService

        Args:
            session: 数据库会话
        """
        self.session = session
        self.project_repo = CodingProjectRepository(session)
        self.blueprint_repo = CodingBlueprintRepository(session)
        self.system_repo = CodingSystemRepository(session)
        self.module_repo = CodingModuleRepository(session)
        self.feature_repo = CodingFeatureRepository(session)
        self._project_service = CodingProjectService(session)

    async def get_blueprint(
        self,
        project_id: str,
        user_id: int,
    ) -> Optional[CodingBlueprintSchema]:
        """
        获取项目蓝图

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            蓝图Schema，如果不存在则返回None
        """
        project = await self._project_service.ensure_project_owner(project_id, user_id)
        project_with_relations = await self.project_repo.get_with_relations(project_id)

        from ...serializers.coding_serializer import CodingSerializer
        return CodingSerializer.build_blueprint_schema(project_with_relations)

    async def update_blueprint(
        self,
        project_id: str,
        user_id: int,
        updates: CodingBlueprintPatch,
    ) -> CodingBlueprint:
        """
        更新项目蓝图

        Args:
            project_id: 项目ID
            user_id: 用户ID
            updates: 更新数据

        Returns:
            更新后的蓝图
        """
        project = await self._project_service.ensure_project_owner(project_id, user_id)
        blueprint = await self.blueprint_repo.get_by_project(project_id)

        if not blueprint:
            raise ResourceNotFoundError("Coding蓝图", project_id)

        # 更新字段
        if updates.title is not None:
            blueprint.title = updates.title
            project.title = updates.title  # 同步更新项目标题

        if updates.one_sentence_summary is not None:
            blueprint.one_sentence_summary = updates.one_sentence_summary

        if updates.architecture_synopsis is not None:
            blueprint.architecture_synopsis = updates.architecture_synopsis

        if updates.tech_stack is not None:
            blueprint.tech_stack = updates.tech_stack.model_dump()

        await self.session.flush()
        return blueprint

    async def save_generated_blueprint(
        self,
        project_id: str,
        blueprint_data: dict,
    ) -> CodingBlueprint:
        """
        保存LLM生成的蓝图数据

        Args:
            project_id: 项目ID
            blueprint_data: LLM生成的蓝图数据（字典格式）

        Returns:
            保存后的蓝图
        """
        blueprint = await self.blueprint_repo.get_by_project(project_id)
        project = await self.project_repo.get_by_id(project_id)

        if not blueprint:
            blueprint = CodingBlueprint(project_id=project_id)
            self.session.add(blueprint)

        # 更新蓝图字段
        blueprint.title = blueprint_data.get("title", "")
        blueprint.target_audience = blueprint_data.get("target_audience", "")
        blueprint.project_type_desc = blueprint_data.get("project_type_desc", "")
        blueprint.tech_style = blueprint_data.get("tech_style", "")
        blueprint.project_tone = blueprint_data.get("project_tone", "")
        blueprint.one_sentence_summary = blueprint_data.get("one_sentence_summary", "")
        blueprint.architecture_synopsis = blueprint_data.get("architecture_synopsis", "")

        # 技术栈
        blueprint.tech_stack = blueprint_data.get("tech_stack", {})

        # 架构辅助信息
        blueprint.system_suggestions = blueprint_data.get("system_suggestions", [])
        blueprint.core_requirements = blueprint_data.get("core_requirements", [])
        blueprint.technical_challenges = blueprint_data.get("technical_challenges", [])
        blueprint.non_functional_requirements = blueprint_data.get("non_functional_requirements")
        blueprint.risks = blueprint_data.get("risks", [])
        blueprint.milestones = blueprint_data.get("milestones", [])

        # 依赖关系
        blueprint.dependencies = blueprint_data.get("dependencies", [])

        # 统计信息
        blueprint.total_systems = blueprint_data.get("total_systems", 0)
        blueprint.total_modules = blueprint_data.get("total_modules", 0)
        blueprint.total_features = blueprint_data.get("total_features", 0)
        blueprint.needs_phased_design = blueprint_data.get("needs_phased_design", False)

        # 同步更新项目标题
        if project and blueprint.title:
            project.title = blueprint.title

        await self.session.flush()
        return blueprint

    async def clear_blueprint_data(
        self,
        project_id: str,
        user_id: int,
    ) -> None:
        """
        清理蓝图数据（用于重新生成）

        Args:
            project_id: 项目ID
            user_id: 用户ID
        """
        await self._project_service.ensure_project_owner(project_id, user_id)

        # 删除所有系统、模块、功能
        await self.system_repo.delete_by_project_id(project_id)
        await self.module_repo.delete_by_project_id(project_id)
        await self.feature_repo.delete_by_project_id(project_id)

        # 重置蓝图数据
        blueprint = await self.blueprint_repo.get_by_project(project_id)
        if blueprint:
            blueprint.systems = []
            blueprint.modules = []
            blueprint.features = []
            blueprint.total_systems = 0
            blueprint.total_modules = 0
            blueprint.total_features = 0

        await self.session.flush()
