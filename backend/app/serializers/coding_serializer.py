"""
Coding项目序列化器

负责将Coding ORM模型转换为Pydantic Schema，分离序列化逻辑和业务逻辑。
"""

import json
import logging
from typing import Dict, List, Optional

from ..models.coding import (
    CodingProject,
    CodingBlueprint as CodingBlueprintModel,
    CodingSystem as CodingSystemModel,
    CodingModule as CodingModuleModel,
)
from ..schemas.coding import (
    CodingBlueprint,
    CodingModule,
    CodingProjectResponse,
    CodingProjectSummary,
    CodingSystem,
    CodingSystemStatus,
    ModuleDependency,
    TechStack,
    TechComponent,
    TechDomain,
    SystemSuggestion,
    CoreRequirement,
    TechnicalChallenge,
    NonFunctionalRequirements,
    Risk,
    Milestone,
)

logger = logging.getLogger(__name__)


class CodingSerializer:
    """
    Coding项目序列化器

    提供统一的序列化接口，将ORM模型转换为API响应的Pydantic Schema。
    """

    @staticmethod
    async def serialize_project(project: CodingProject) -> CodingProjectResponse:
        """
        序列化完整Coding项目

        Args:
            project: 项目ORM模型（需预加载所有关联数据）

        Returns:
            CodingProjectResponse: 完整的项目Schema
        """
        # 序列化对话历史
        conversations = [
            {"role": convo.role, "content": convo.content}
            for convo in sorted(project.conversations, key=lambda c: c.seq)
        ]

        # 构建蓝图Schema
        blueprint_schema = CodingSerializer.build_blueprint_schema(project)

        return CodingProjectResponse(
            id=project.id,
            user_id=project.user_id,
            title=project.title,
            initial_prompt=project.initial_prompt or "",
            status=project.status,
            conversation_history=conversations,
            blueprint=blueprint_schema,
        )

    @staticmethod
    def serialize_project_summary(project: CodingProject) -> CodingProjectSummary:
        """
        序列化项目摘要（用于列表展示）

        Args:
            project: 项目ORM模型

        Returns:
            CodingProjectSummary: 项目摘要
        """
        # 获取项目类型描述
        project_type_desc = ""
        if project.blueprint:
            project_type_desc = project.blueprint.project_type_desc or ""

        return CodingProjectSummary(
            id=project.id,
            title=project.title,
            project_type_desc=project_type_desc,
            last_edited=project.updated_at.isoformat() if project.updated_at else "",
            status=project.status,
        )

    @staticmethod
    def build_blueprint_schema(project: CodingProject) -> Optional[CodingBlueprint]:
        """
        构建蓝图Schema

        Args:
            project: 项目ORM模型

        Returns:
            CodingBlueprint: 蓝图Schema，如果不存在则返回None
        """
        blueprint_obj = project.blueprint
        if not blueprint_obj:
            return None

        # 反序列化技术栈配置
        tech_stack_data = blueprint_obj.tech_stack or {}
        tech_stack = TechStack(
            core_constraints=tech_stack_data.get("core_constraints", ""),
            components=[
                TechComponent(
                    name=comp.get("name", ""),
                    description=comp.get("description", "")
                )
                for comp in tech_stack_data.get("components", [])
            ],
            domains=[
                TechDomain(
                    name=dom.get("name", ""),
                    description=dom.get("description", "")
                )
                for dom in tech_stack_data.get("domains", [])
            ],
        )

        # 反序列化架构设计辅助信息
        system_suggestions = [
            SystemSuggestion(
                name=s.get("name", ""),
                description=s.get("description", ""),
                priority=s.get("priority", "medium"),
                estimated_modules=s.get("estimated_modules", 0),
            )
            for s in (blueprint_obj.system_suggestions or [])
        ]

        core_requirements = [
            CoreRequirement(
                category=r.get("category", "功能"),
                requirement=r.get("requirement", ""),
                priority=r.get("priority", "should-have"),
            )
            for r in (blueprint_obj.core_requirements or [])
        ]

        technical_challenges = [
            TechnicalChallenge(
                challenge=c.get("challenge", ""),
                impact=c.get("impact", "medium"),
                solution_direction=c.get("solution_direction", ""),
            )
            for c in (blueprint_obj.technical_challenges or [])
        ]

        nfr_data = blueprint_obj.non_functional_requirements or {}
        non_functional_requirements = NonFunctionalRequirements(
            performance=nfr_data.get("performance", ""),
            security=nfr_data.get("security", ""),
            scalability=nfr_data.get("scalability", ""),
            reliability=nfr_data.get("reliability", ""),
            maintainability=nfr_data.get("maintainability", ""),
        ) if nfr_data else None

        risks = [
            Risk(
                risk=r.get("risk", ""),
                probability=r.get("probability", "medium"),
                mitigation=r.get("mitigation", ""),
            )
            for r in (blueprint_obj.risks or [])
        ]

        milestones = [
            Milestone(
                phase=m.get("phase", ""),
                goals=m.get("goals", []),
                key_deliverables=m.get("key_deliverables", []),
            )
            for m in (blueprint_obj.milestones or [])
        ]

        # 从关联关系构建系统列表
        systems = [
            CodingSerializer.build_system_schema(system)
            for system in sorted(project.systems, key=lambda s: s.system_number)
        ]

        # 从关联关系构建模块列表
        modules = [
            CodingSerializer.build_module_schema(module)
            for module in sorted(project.modules, key=lambda m: m.module_number)
        ]

        # 从模块的dependencies字段动态提取依赖关系
        # 每个模块的dependencies存储了它依赖的其他模块名称列表
        dependencies = []
        for module in project.modules:
            module_deps = module.dependencies or []
            for dep_name in module_deps:
                dependencies.append(
                    ModuleDependency(
                        from_module=module.name,
                        to_module=dep_name,
                        description=f"{module.name} 依赖 {dep_name}",
                    )
                )

        return CodingBlueprint(
            title=blueprint_obj.title or "",
            target_audience=blueprint_obj.target_audience or "",
            project_type_desc=blueprint_obj.project_type_desc or "",
            tech_style=blueprint_obj.tech_style or "",
            project_tone=blueprint_obj.project_tone or "",
            one_sentence_summary=blueprint_obj.one_sentence_summary or "",
            architecture_synopsis=blueprint_obj.architecture_synopsis or "",
            tech_stack=tech_stack,
            system_suggestions=system_suggestions,
            core_requirements=core_requirements,
            technical_challenges=technical_challenges,
            non_functional_requirements=non_functional_requirements,
            risks=risks,
            milestones=milestones,
            systems=systems,
            modules=modules,
            dependencies=dependencies,
            total_systems=blueprint_obj.total_systems or len(systems),
            total_modules=blueprint_obj.total_modules or len(modules),
            needs_phased_design=blueprint_obj.needs_phased_design or False,
        )

    @staticmethod
    def build_system_schema(system: CodingSystemModel) -> CodingSystem:
        """
        构建系统Schema

        Args:
            system: 系统ORM模型

        Returns:
            CodingSystem: 系统Schema
        """
        try:
            gen_status = CodingSystemStatus(system.generation_status) if system.generation_status else CodingSystemStatus.PENDING
        except ValueError:
            gen_status = CodingSystemStatus.PENDING

        return CodingSystem(
            system_number=system.system_number,
            name=system.name,
            description=system.description or "",
            responsibilities=system.responsibilities or [],
            tech_requirements=system.tech_requirements or "",
            module_count=system.module_count or 0,
            generation_status=gen_status,
            progress=system.progress or 0,
        )

    @staticmethod
    def build_module_schema(module: CodingModuleModel) -> CodingModule:
        """
        构建模块Schema

        Args:
            module: 模块ORM模型

        Returns:
            CodingModule: 模块Schema
        """
        try:
            gen_status = CodingSystemStatus(module.generation_status) if module.generation_status else CodingSystemStatus.PENDING
        except ValueError:
            gen_status = CodingSystemStatus.PENDING

        return CodingModule(
            module_number=module.module_number,
            system_number=module.system_number,
            name=module.name,
            type=module.module_type or "",
            description=module.description or "",
            interface=module.interface or "",
            dependencies=module.dependencies or [],
            generation_status=gen_status,
        )
