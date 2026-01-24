"""
蓝图服务基类

提供蓝图更新与清理的通用模板方法，减少跨模块重复实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Mapping, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.field_mapping import build_update_data, apply_mapping_with_defaults


PatchTransform = Callable[[Dict[str, Any], Mapping[str, Any], Optional[Any]], Dict[str, Any]]


class BlueprintServiceBase(ABC):
    """蓝图服务基类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _build_update_data(
        self,
        source: Mapping[str, Any],
        field_map: Mapping[str, str],
        *,
        allow_none: bool,
    ) -> Dict[str, Any]:
        """构建更新字段字典"""
        return build_update_data(source, field_map, allow_none=allow_none)

    def _apply_generated_mapping(
        self,
        target: Any,
        source: Mapping[str, Any],
        field_map: Mapping[str, tuple[str, Any]],
    ) -> None:
        """应用生成字段映射"""
        apply_mapping_with_defaults(target, source, field_map)

    async def apply_patch_update(
        self,
        project_id: str,
        patch_data: Mapping[str, Any],
        field_map: Mapping[str, str],
        *,
        allow_none: bool,
        blueprint: Optional[Any] = None,
        transform: Optional[PatchTransform] = None,
    ) -> Dict[str, Any]:
        """构建并应用蓝图更新"""
        update_data = self._build_update_data(
            patch_data,
            field_map,
            allow_none=allow_none,
        )
        if transform:
            update_data = transform(update_data, patch_data, blueprint)

        if update_data:
            await self._apply_update_data(project_id, update_data, blueprint)

        return update_data

    async def cleanup_blueprint_data(
        self,
        project_id: str,
        *,
        project: Optional[Any] = None,
        user_id: Optional[int] = None,
        llm_service: Optional[Any] = None,
    ) -> None:
        """清理蓝图相关数据的统一入口"""
        if user_id is not None:
            await self._ensure_project_owner(project_id, user_id)

        await self._cleanup_dependents(project_id, project=project, llm_service=llm_service)
        await self._reset_blueprint_state(project_id)
        await self._post_cleanup(project_id, project=project)
        await self.session.flush()

    async def _ensure_project_owner(self, project_id: str, user_id: int) -> None:
        """校验项目归属（默认不处理）"""
        return None

    @abstractmethod
    async def _apply_update_data(
        self,
        project_id: str,
        update_data: Dict[str, Any],
        blueprint: Optional[Any] = None,
    ) -> None:
        """应用更新数据（子类实现）"""

    @abstractmethod
    async def _cleanup_dependents(
        self,
        project_id: str,
        *,
        project: Optional[Any] = None,
        llm_service: Optional[Any] = None,
    ) -> None:
        """清理蓝图关联数据（子类实现）"""

    async def _reset_blueprint_state(self, project_id: str) -> None:
        """重置蓝图聚合字段（可选覆盖）"""
        return None

    async def _post_cleanup(self, project_id: str, *, project: Optional[Any] = None) -> None:
        """清理后处理（可选覆盖）"""
        return None


__all__ = ["BlueprintServiceBase"]
