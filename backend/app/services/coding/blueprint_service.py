"""
Coding蓝图服务

负责Coding项目蓝图的生成和管理。
"""

from __future__ import annotations

import logging
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...exceptions import ResourceNotFoundError
from ...models.coding import CodingBlueprint
from ...repositories.coding_repository import (
    CodingProjectRepository,
    CodingBlueprintRepository,
    CodingSystemRepository,
    CodingModuleRepository,
)
from ...schemas.coding import (
    CodingBlueprint as CodingBlueprintSchema,
    CodingBlueprintPatch,
)
from ..blueprint_base import BlueprintServiceBase
from .project_service import CodingProjectService

logger = logging.getLogger(__name__)


class CodingBlueprintService(BlueprintServiceBase):
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
        super().__init__(session)
        self.session = session
        self.project_repo = CodingProjectRepository(session)
        self.blueprint_repo = CodingBlueprintRepository(session)
        self.system_repo = CodingSystemRepository(session)
        self.module_repo = CodingModuleRepository(session)
        self._project_service = CodingProjectService(session)
        self._patch_field_map = {
            "title": "title",
            "one_sentence_summary": "one_sentence_summary",
            "architecture_synopsis": "architecture_synopsis",
            "tech_stack": "tech_stack",
        }
        self._generated_field_map = {
            "title": ("title", ""),
            "target_audience": ("target_audience", ""),
            "project_type_desc": ("project_type_desc", ""),
            "tech_style": ("tech_style", ""),
            "project_tone": ("project_tone", ""),
            "one_sentence_summary": ("one_sentence_summary", ""),
            "architecture_synopsis": ("architecture_synopsis", ""),
            "tech_stack": ("tech_stack", {}),
            "system_suggestions": ("system_suggestions", []),
            "core_requirements": ("core_requirements", []),
            "technical_challenges": ("technical_challenges", []),
            "non_functional_requirements": ("non_functional_requirements", None),
            "risks": ("risks", []),
            "milestones": ("milestones", []),
            "dependencies": ("dependencies", []),
            "total_systems": ("total_systems", 0),
            "total_modules": ("total_modules", 0),
            "needs_phased_design": ("needs_phased_design", False),
        }

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

        update_data = await self.apply_patch_update(
            project_id,
            updates.model_dump(exclude_unset=True),
            self._patch_field_map,
            allow_none=False,
            blueprint=blueprint,
            transform=self._transform_patch_update,
        )

        if "title" in update_data:
            project.title = update_data["title"]

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

        self._apply_generated_mapping(blueprint, blueprint_data, self._generated_field_map)

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
        await self.cleanup_blueprint_data(project_id, user_id=user_id)

    async def _ensure_project_owner(self, project_id: str, user_id: int) -> None:
        """校验项目归属"""
        await self._project_service.ensure_project_owner(project_id, user_id)

    async def _apply_update_data(
        self,
        project_id: str,
        update_data: dict,
        blueprint: Optional[CodingBlueprint] = None,
    ) -> None:
        """应用蓝图字段更新"""
        if not blueprint:
            blueprint = await self.blueprint_repo.get_by_project(project_id)
        if not blueprint:
            raise ResourceNotFoundError("Coding蓝图", project_id)
        await self.blueprint_repo.update_fields(blueprint, **update_data)

    async def _cleanup_dependents(
        self,
        project_id: str,
        *,
        project: Optional[Any] = None,
        llm_service: Optional[Any] = None,
    ) -> None:
        """清理蓝图关联数据"""
        await self.system_repo.delete_by_project_id(project_id)
        await self.module_repo.delete_by_project_id(project_id)

    async def _reset_blueprint_state(self, project_id: str) -> None:
        """重置蓝图聚合字段"""
        blueprint = await self.blueprint_repo.get_by_project(project_id)
        if blueprint:
            blueprint.systems = []
            blueprint.modules = []
            blueprint.total_systems = 0
            blueprint.total_modules = 0

    @staticmethod
    def _transform_patch_update(
        update_data: dict,
        patch_data: dict,
        blueprint: Optional[CodingBlueprint],
    ) -> dict:
        """处理补丁字段转换"""
        if "tech_stack" in update_data and update_data["tech_stack"] is not None:
            update_data["tech_stack"] = update_data["tech_stack"].model_dump()
        return update_data
