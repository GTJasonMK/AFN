"""
Coding项目服务

负责Coding项目级别的CRUD、状态机管理和数据查询。
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.state_machine import ProjectStatus, ProjectStateMachine
from ...exceptions import ResourceNotFoundError, PermissionDeniedError
from ...models.coding import CodingProject, CodingBlueprint
from ...repositories.coding_repository import (
    CodingProjectRepository,
    CodingConversationRepository,
    CodingBlueprintRepository,
    CodingSystemRepository,
    CodingModuleRepository,
    CodingFeatureRepository,
)
from ...serializers.coding_serializer import CodingSerializer
from ...schemas.coding import (
    CodingProjectResponse,
    CodingProjectSummary,
)

logger = logging.getLogger(__name__)


class CodingProjectService:
    """
    Coding项目服务

    负责：
    - 项目CRUD（创建、查询、删除）
    - 状态机管理（状态转换）
    - 权限验证（确保项目归属）
    - 数据查询（项目Schema）
    """

    def __init__(self, session: AsyncSession):
        """
        初始化CodingProjectService

        Args:
            session: 数据库会话
        """
        self.session = session
        self.project_repo = CodingProjectRepository(session)
        self.conversation_repo = CodingConversationRepository(session)
        self.blueprint_repo = CodingBlueprintRepository(session)
        self.system_repo = CodingSystemRepository(session)
        self.module_repo = CodingModuleRepository(session)
        self.feature_repo = CodingFeatureRepository(session)

    # ------------------------------------------------------------------
    # 状态机管理
    # ------------------------------------------------------------------

    async def transition_project_status(
        self,
        project: CodingProject,
        new_status: str,
        force: bool = False
    ) -> None:
        """
        安全地转换项目状态

        Args:
            project: 项目实例
            new_status: 目标状态
            force: 是否强制转换（跳过验证）
        """
        logger.info(
            "Coding项目状态转换: project_id=%s %s -> %s%s",
            project.id,
            project.status,
            new_status,
            " (force=True)" if force else ""
        )

        state_machine = ProjectStateMachine(project.status)
        project.status = state_machine.transition_to(new_status, force=force)
        await self.session.commit()

        logger.info(
            "Coding项目状态转换成功: project_id=%s 新状态=%s",
            project.id,
            project.status
        )

    # ------------------------------------------------------------------
    # 项目CRUD
    # ------------------------------------------------------------------

    async def create_project(
        self,
        user_id: int,
        title: str,
        initial_prompt: str = "",
        skip_conversation: bool = False,
    ) -> CodingProject:
        """
        创建新Coding项目

        Args:
            user_id: 用户ID
            title: 项目标题
            initial_prompt: 需求分析的初始提示词
            skip_conversation: 是否跳过需求对话（直接进入蓝图状态）

        Returns:
            CodingProject: 创建的项目

        注意：此方法不commit，调用方需要在适当时候commit
        """
        initial_status = (
            ProjectStatus.BLUEPRINT_READY.value
            if skip_conversation
            else ProjectStatus.DRAFT.value
        )

        project = CodingProject(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            initial_prompt=initial_prompt,
            status=initial_status,
        )

        # 创建空蓝图
        blueprint = CodingBlueprint(project_id=project.id)

        self.session.add(project)
        self.session.add(blueprint)
        await self.session.flush()
        await self.session.refresh(project)

        return project

    async def delete_project(
        self,
        project_id: str,
        user_id: int,
    ) -> None:
        """
        删除Coding项目

        Args:
            project_id: 项目ID
            user_id: 用户ID（用于权限验证）

        注意：此方法不commit，调用方需要在适当时候commit
        """
        project = await self.ensure_project_owner(project_id, user_id)
        await self.project_repo.delete(project)

    async def delete_projects(
        self,
        project_ids: List[str],
        user_id: int,
    ) -> None:
        """
        批量删除Coding项目

        Args:
            project_ids: 项目ID列表
            user_id: 用户ID（用于权限验证）

        注意：此方法不commit，调用方需要在适当时候commit
        """
        from sqlalchemy import delete

        for pid in project_ids:
            await self.ensure_project_owner(pid, user_id)

        await self.session.execute(
            delete(CodingProject).where(CodingProject.id.in_(project_ids))
        )

    # ------------------------------------------------------------------
    # 权限验证
    # ------------------------------------------------------------------

    async def ensure_project_owner(self, project_id: str, user_id: int) -> CodingProject:
        """确保项目归属于指定用户（带关系加载）"""
        project = await self.project_repo.get_with_relations(project_id)
        if not project:
            raise ResourceNotFoundError("Coding项目", project_id)
        if project.user_id != user_id:
            raise PermissionDeniedError("无权访问该项目")
        return project

    async def ensure_blueprint_ready(
        self,
        project_id: str,
        user_id: int,
    ) -> Tuple[CodingProject, CodingProjectResponse]:
        """确保项目蓝图已就绪"""
        from ...exceptions import BlueprintNotReadyError

        project = await self.project_repo.get_with_relations(project_id)
        if not project:
            raise ResourceNotFoundError("Coding项目", project_id)
        if project.user_id != user_id:
            raise PermissionDeniedError("无权访问该项目")

        project_schema = await CodingSerializer.serialize_project(project)

        if not project_schema.blueprint:
            raise BlueprintNotReadyError(project_id)

        return project, project_schema

    # ------------------------------------------------------------------
    # 数据查询
    # ------------------------------------------------------------------

    async def get_project(self, project_id: str, user_id: Optional[int] = None) -> CodingProject:
        """获取项目ORM实例"""
        if user_id is not None:
            return await self.ensure_project_owner(project_id, user_id)

        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ResourceNotFoundError("Coding项目", project_id)
        return project

    async def get_project_schema(
        self,
        project_id: str,
        user_id: Optional[int] = None
    ) -> CodingProjectResponse:
        """获取项目Schema"""
        if user_id is not None:
            project = await self.project_repo.get_with_relations(project_id)
            if not project:
                raise ResourceNotFoundError("Coding项目", project_id)
            if project.user_id != user_id:
                raise PermissionDeniedError("无权访问该项目")
        else:
            project = await self.project_repo.get_with_relations(project_id)
            if not project:
                raise ResourceNotFoundError("Coding项目", project_id)

        return await CodingSerializer.serialize_project(project)

    async def list_projects_for_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[CodingProjectSummary], int]:
        """
        分页获取用户的项目摘要列表

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量

        Returns:
            (项目摘要列表, 总数)
        """
        projects = await self.project_repo.get_by_user_with_relations(user_id)

        # 计算分页
        total = len(projects)
        start = (page - 1) * page_size
        end = start + page_size
        paged_projects = projects[start:end]

        summaries = [
            CodingSerializer.serialize_project_summary(project)
            for project in paged_projects
        ]

        return summaries, total

    # ------------------------------------------------------------------
    # 项目更新
    # ------------------------------------------------------------------

    async def update_project(
        self,
        project_id: str,
        user_id: int,
        title: Optional[str] = None,
    ) -> CodingProject:
        """
        更新项目基本信息

        Args:
            project_id: 项目ID
            user_id: 用户ID
            title: 新标题（可选）

        Returns:
            更新后的项目
        """
        project = await self.ensure_project_owner(project_id, user_id)

        if title is not None:
            project.title = title

        await self.session.flush()
        return project
