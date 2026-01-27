"""
文件 Prompt 子模块：提示词构建能力（PromptsMixin）

拆分自 `backend/app/services/coding_files/file_prompt_service.py`。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ....models.coding_files import CodingSourceFile
from ....utils.prompt_helpers import (
    build_prompt_block,
    build_prompt_section,
    format_prompt_json,
    join_prompt_lines,
)


class PromptsMixin:
    """system/user prompt 与 RAG section 构建能力"""

    async def _build_system_prompt(self, prompt_service) -> str:
        """构建系统提示词（文件 Prompt）"""
        if not prompt_service:
            raise ValueError(
                "文件Prompt生成需要PromptService，但未提供。"
                "请确保正确注入依赖。"
            )

        prompt = await prompt_service.get_prompt("file_prompt_generation")
        if not prompt:
            raise ValueError(
                "未找到提示词 'file_prompt_generation'。"
                "请检查 backend/prompts/ 目录下是否存在对应的 .md 文件，"
                "并确保已在 _registry.yaml 中注册。"
            )
        return prompt

    async def _build_review_system_prompt(self, prompt_service) -> str:
        """构建系统提示词（审查 Prompt）"""
        if not prompt_service:
            raise ValueError(
                "审查提示词生成需要PromptService，但未提供。"
                "请确保正确注入依赖。"
            )

        prompt = await prompt_service.get_prompt("file_review_generation")
        if not prompt:
            raise ValueError(
                "未找到提示词 'file_review_generation'。"
                "请检查 backend/prompts/ 目录下是否存在对应的 .md 文件，"
                "并确保已在 _registry.yaml 中注册。"
            )
        return prompt

    async def _build_prompt_input_data(
        self,
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str],
        include_module: bool,
        include_tech_constraints: bool,
    ) -> Dict[str, Any]:
        """构建用户提示词输入数据"""
        from ....serializers.coding_serializer import CodingSerializer

        blueprint_schema = CodingSerializer.build_blueprint_schema(project)
        blueprint = blueprint_schema.model_dump() if blueprint_schema else {}

        input_data = {
            "project": {
                "name": blueprint.get("title", ""),
                "tech_style": blueprint.get("tech_style", ""),
            },
            "file": {
                "filename": file.filename,
                "file_path": file.file_path,
                "file_type": file.file_type,
                "language": file.language or "",
                "description": file.description or "",
                "purpose": file.purpose or "",
            },
        }

        if include_tech_constraints:
            tech_stack = blueprint.get("tech_stack", {})
            input_data["tech_stack"] = {
                "constraints": tech_stack.get("core_constraints", "")[:500] if isinstance(tech_stack, dict) else "",
            }

        if include_module:
            module = None
            if file.module_number:
                module = await self.module_repo.get_by_project_and_number(file.project_id, file.module_number)
            input_data["module"] = {
                "name": module.name if module else "",
                "type": module.module_type if module else "",
                "description": (module.description or "")[:300] if module else "",
            }

        if writing_notes:
            input_data["extra_requirements"] = writing_notes[:500]

        return input_data

    def _build_rag_section(
        self,
        rag_context: Optional[Dict[str, Any]],
        title: str,
        include_architecture: bool,
        include_modules: bool,
        include_related_files: bool,
    ) -> str:
        """构建RAG上下文片段"""
        if not rag_context:
            return ""

        rag_parts = []

        if include_architecture and rag_context.get("architecture"):
            arch_content = join_prompt_lines([item["content"] for item in rag_context["architecture"]])
            if arch_content:
                rag_parts.append(build_prompt_section("架构设计参考", arch_content, level=3))

        if rag_context.get("tech_stack"):
            tech_content = join_prompt_lines([item["content"] for item in rag_context["tech_stack"]])
            if tech_content:
                rag_parts.append(build_prompt_section("技术栈参考", tech_content, level=3))

        if include_modules and rag_context.get("modules"):
            mod_content = join_prompt_lines([item["content"] for item in rag_context["modules"]])
            if mod_content:
                rag_parts.append(build_prompt_section("相关模块", mod_content, level=3))

        if rag_context.get("features"):
            feat_content = join_prompt_lines([item["content"] for item in rag_context["features"]])
            if feat_content:
                rag_parts.append(build_prompt_section("相关功能", feat_content, level=3))

        if include_related_files and rag_context.get("related_files"):
            file_parts = []
            for item in rag_context["related_files"][:2]:
                file_path = item.get("file_path", "")
                content = item.get("content", "")[:300]
                if file_path and content:
                    file_parts.append(f"**{file_path}**:\n{content}")
            if file_parts:
                rag_parts.append(build_prompt_section("相关文件参考", "\n\n".join(file_parts), level=3))

        if not rag_parts:
            return ""

        return build_prompt_block(title, rag_parts)

    async def _build_user_prompt(
        self,
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str] = None,
        rag_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建用户提示词（文件 Prompt，支持RAG上下文）"""
        input_data = await self._build_prompt_input_data(
            project=project,
            file=file,
            writing_notes=writing_notes,
            include_module=True,
            include_tech_constraints=True,
        )
        input_data["file"]["priority"] = file.priority

        rag_section = self._build_rag_section(
            rag_context,
            title="项目上下文（RAG检索）",
            include_architecture=True,
            include_modules=True,
            include_related_files=True,
        )

        return f"""请为以下源文件生成实现Prompt：

{format_prompt_json(input_data)}
{rag_section}

根据文件信息、关联功能和项目上下文，生成完整的实现Prompt。"""

    async def _build_review_user_prompt(
        self,
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str] = None,
        rag_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建审查Prompt的用户提示词"""
        input_data = await self._build_prompt_input_data(
            project=project,
            file=file,
            writing_notes=writing_notes,
            include_module=False,
            include_tech_constraints=False,
        )

        impl_section = ""
        if file.selected_version_id and file.selected_version:
            implementation_prompt = file.selected_version.content
            impl_section = f"\n\n## 文件实现Prompt（参考）\n\n{implementation_prompt[:2000]}"

        rag_section = self._build_rag_section(
            rag_context,
            title="项目上下文",
            include_architecture=False,
            include_modules=False,
            include_related_files=False,
        )

        return f"""请为以下源文件生成审查与测试Prompt：

{format_prompt_json(input_data)}
{impl_section}
{rag_section}

根据文件信息和实现Prompt，生成完整的审查与测试指南。"""


__all__ = ["PromptsMixin"]

