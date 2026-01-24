"""
项目服务通用基类

提供项目权限校验与状态机流转的通用能力。
"""

from __future__ import annotations

import logging
from typing import Optional

from ..core.state_machine import ProjectStateMachine
from ..exceptions import ResourceNotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)


class ProjectServiceBase:
    """项目服务通用基类"""

    def __init__(
        self,
        session,
        repo,
        *,
        resource_name: str,
        log_label: str,
        use_relations: bool = False,
    ) -> None:
        self.session = session
        self.repo = repo
        self.resource_name = resource_name
        self.log_label = log_label
        self.use_relations = use_relations

    async def _get_project_by_id(
        self,
        project_id: str,
        *,
        with_relations: Optional[bool] = None,
    ):
        use_relations = self.use_relations if with_relations is None else with_relations
        if use_relations and hasattr(self.repo, "get_with_relations"):
            return await self.repo.get_with_relations(project_id)
        return await self.repo.get_by_id(project_id)

    async def ensure_project_owner(self, project_id: str, user_id: int):
        """确保项目归属于指定用户"""
        project = await self._get_project_by_id(project_id)
        if not project:
            raise ResourceNotFoundError(self.resource_name, project_id)
        if project.user_id != user_id:
            raise PermissionDeniedError("无权访问该项目")
        return project

    def _is_backward_transition(self, current_status: str, new_status: str) -> bool:
        """判断是否为回退转换（使用状态机统一定义）"""
        return ProjectStateMachine.check_backward_transition(current_status, new_status)

    async def _handle_backward_transition(self, project, new_status: str) -> None:
        """处理回退转换的清理逻辑（子类可覆盖）"""
        return None

    def _log_transition_start(self, project, new_status: str, force: bool) -> None:
        logger.info(
            "%s状态转换: project_id=%s %s -> %s%s",
            self.log_label,
            project.id,
            project.status,
            new_status,
            " (force=True)" if force else "",
        )

    def _log_transition_complete(self, project) -> None:
        logger.info(
            "%s状态转换成功: project_id=%s 新状态=%s",
            self.log_label,
            project.id,
            project.status,
        )

    async def transition_project_status(self, project, new_status: str, force: bool = False) -> None:
        """安全地转换项目状态"""
        self._log_transition_start(project, new_status, force)

        if self._is_backward_transition(project.status, new_status):
            logger.warning(
                "检测到状态回退: %s -> %s，开始清理相关数据",
                project.status,
                new_status,
            )
            await self._handle_backward_transition(project, new_status)

        state_machine = ProjectStateMachine(project.status)
        project.status = state_machine.transition_to(new_status, force=force)
        await self.session.commit()

        self._log_transition_complete(project)


__all__ = [
    "ProjectServiceBase",
]
