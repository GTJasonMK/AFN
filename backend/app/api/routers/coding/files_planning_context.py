"""
Coding 文件相关路由：目录规划上下文构建

拆分自 `backend/app/api/routers/coding/files.py`（plan-v2 / plan-agent 共享的上下文构建逻辑）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class DirectoryPlanningContext:
    """目录规划所需上下文（路由层序列化后的 dict 结构）"""

    project_data: Dict[str, Any]
    blueprint_data: Dict[str, Any]
    systems: List[Dict[str, Any]]
    modules: List[Dict[str, Any]]


def _dump_dict_or_model(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def _dump_list(items: Any) -> List[Any]:
    return [i.model_dump() if hasattr(i, "model_dump") else i for i in (items or [])]


async def load_directory_planning_context(
    session: AsyncSession,
    project_id: str,
    user_id: int,
) -> DirectoryPlanningContext:
    """加载目录规划所需上下文（项目/蓝图/系统/模块）"""
    from ....repositories.coding_repository import CodingModuleRepository, CodingSystemRepository
    from ....serializers.coding_serializer import CodingSerializer
    from ....services.coding import CodingProjectService

    project_service = CodingProjectService(session)
    project = await project_service.ensure_project_owner(project_id, user_id)

    blueprint_schema = CodingSerializer.build_blueprint_schema(project)

    system_repo = CodingSystemRepository(session)
    systems = await system_repo.get_by_project_ordered(project_id)

    module_repo = CodingModuleRepository(session)
    modules = await module_repo.get_by_project_ordered(project_id)

    module_dicts = [
        {
            "module_number": m.module_number,
            "system_number": m.system_number,
            "name": m.name,
            "module_type": m.module_type,
            "description": m.description,
            "interface": m.interface,
            "dependencies": m.dependencies or [],
        }
        for m in modules
    ]

    project_data = {
        "id": project.id,
        "title": project.title,
        "initial_prompt": project.initial_prompt,
        "status": project.status,
    }

    blueprint_data: Dict[str, Any] = {}
    if blueprint_schema:
        nfr_dict = _dump_dict_or_model(blueprint_schema.non_functional_requirements)

        blueprint_data = {
            "title": blueprint_schema.title,
            "target_audience": blueprint_schema.target_audience,
            "project_type_desc": blueprint_schema.project_type_desc,
            "tech_style": blueprint_schema.tech_style,
            "project_tone": blueprint_schema.project_tone,
            "one_sentence_summary": blueprint_schema.one_sentence_summary,
            "architecture_synopsis": blueprint_schema.architecture_synopsis,
            "tech_stack": _dump_dict_or_model(blueprint_schema.tech_stack),
            "system_suggestions": _dump_list(blueprint_schema.system_suggestions),
            "core_requirements": _dump_list(blueprint_schema.core_requirements),
            "technical_challenges": _dump_list(blueprint_schema.technical_challenges),
            "non_functional_requirements": nfr_dict,
            "risks": _dump_list(blueprint_schema.risks),
            "milestones": _dump_list(blueprint_schema.milestones),
            "dependencies": _dump_list(blueprint_schema.dependencies),
        }

    system_dicts = [
        {
            "system_number": s.system_number,
            "name": s.name,
            "description": s.description,
            "responsibilities": s.responsibilities or [],
            "tech_requirements": s.tech_requirements,
            "module_count": s.module_count,
            "feature_count": s.feature_count,
        }
        for s in systems
    ]

    return DirectoryPlanningContext(
        project_data=project_data,
        blueprint_data=blueprint_data,
        systems=system_dicts,
        modules=module_dicts,
    )


__all__ = ["DirectoryPlanningContext", "load_directory_planning_context"]

