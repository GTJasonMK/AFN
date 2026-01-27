"""
目录结构生成服务

负责根据模块信息生成目录结构和源文件列表。
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ...exceptions import InvalidParameterError, ResourceNotFoundError
from ...models.coding import CodingModule
from ...models.coding_files import CodingDirectoryNode, CodingSourceFile
from ...repositories.coding_repository import (
    CodingModuleRepository,
)
from ...repositories.coding_files_repository import (
    CodingDirectoryNodeRepository,
    CodingSourceFileRepository,
)
from ...schemas.coding_files import (
    DirectoryNodeResponse,
    DirectoryTreeResponse,
    LLMDirectoryStructureOutput,
    SourceFileResponse,
)
from ...serializers.coding_files_serializer import build_directory_node_response
from ...serializers.coding_files_serializer import build_source_file_response
from ...services.coding import CodingProjectService

logger = logging.getLogger(__name__)


class DirectoryStructureService:
    """
    目录结构服务

    负责：
    - 目录结构的CRUD操作
    - 按模块生成目录结构（调用LLM）
    - 目录树的查询和序列化
    - 文件-功能映射管理
    """

    def __init__(self, session: AsyncSession):
        """
        初始化DirectoryStructureService

        Args:
            session: 数据库会话
        """
        self.session = session
        self.dir_repo = CodingDirectoryNodeRepository(session)
        self.file_repo = CodingSourceFileRepository(session)
        self.module_repo = CodingModuleRepository(session)
        self._project_service = CodingProjectService(session)

    # ------------------------------------------------------------------
    # 目录树查询
    # ------------------------------------------------------------------

    async def get_directory_tree(
        self,
        project_id: str,
        user_id: int,
    ) -> DirectoryTreeResponse:
        """
        获取项目的完整目录树

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            目录树响应
        """
        await self._project_service.ensure_project_owner(project_id, user_id)

        # 获取根节点（包含完整树结构）
        root_nodes = await self.dir_repo.get_root_nodes_with_tree(project_id)

        # 统计
        total_dirs = await self.dir_repo.count_by_project(project_id)
        total_files = await self.file_repo.count_by_project(project_id)

        # 序列化
        root_nodes_response = [
            await self._serialize_node_with_children(node)
            for node in root_nodes
        ]

        return DirectoryTreeResponse(
            project_id=project_id,
            root_nodes=root_nodes_response,
            total_directories=total_dirs,
            total_files=total_files,
        )

    async def _serialize_node_with_children(
        self,
        node: CodingDirectoryNode,
    ) -> DirectoryNodeResponse:
        """递归序列化目录节点及其子节点"""
        # 获取该目录下的文件
        files = await self.file_repo.get_by_directory(node.id)
        file_count = len(files)

        # 序列化文件列表
        files_response = [build_source_file_response(f, version_count=0) for f in files]

        # 递归序列化子节点（使用_children_list，避免触发SQLAlchemy懒加载）
        children = []
        children_list = getattr(node, '_children_list', [])
        for child in children_list:
            child_response = await self._serialize_node_with_children(child)
            children.append(child_response)

        return build_directory_node_response(
            node,
            file_count=file_count,
            files=files_response,
            children=children,
        )

    # ------------------------------------------------------------------
    # 目录结构生成
    # ------------------------------------------------------------------

    async def generate_for_module(
        self,
        project_id: str,
        user_id: int,
        module_number: int,
        preference: Optional[str] = None,
        clear_existing: bool = True,
        llm_service=None,
        prompt_service=None,
    ) -> Tuple[int, int, str]:
        """
        为指定模块生成目录结构

        Args:
            project_id: 项目ID
            user_id: 用户ID
            module_number: 模块编号
            preference: 生成偏好
            clear_existing: 是否清除该模块的现有文件（保留可复用的目录）
            llm_service: LLM服务
            prompt_service: 提示词服务

        Returns:
            (创建的目录数, 创建的文件数, 根目录路径)
        """
        # 验证项目和模块
        project = await self._project_service.ensure_project_owner(project_id, user_id)
        module = await self.module_repo.get_by_project_and_number(project_id, module_number)

        if not module:
            raise ResourceNotFoundError("模块", str(module_number))

        # 清除现有数据：只清除该模块的文件，保留可复用的目录结构
        if clear_existing:
            await self.file_repo.delete_by_module(project_id, module_number)
            await self.session.flush()

        # 构建LLM提示并生成
        if llm_service and prompt_service:
            result = await self._generate_with_llm(
                project=project,
                module=module,
                preference=preference,
                llm_service=llm_service,
                prompt_service=prompt_service,
            )
        else:
            # 无LLM时使用默认模板
            result = self._generate_default_structure(module)

        # 保存到数据库（支持目录复用）
        dirs_created, files_created = await self._save_structure(
            project_id=project_id,
            module_number=module_number,
            structure=result,
        )

        return dirs_created, files_created, result.root_path

    async def _generate_with_llm(
        self,
        project,
        module: CodingModule,
        preference: Optional[str],
        llm_service,
        prompt_service,
    ) -> LLMDirectoryStructureOutput:
        """使用LLM生成目录结构"""
        from ...serializers.coding_serializer import CodingSerializer
        from ...utils.json_utils import parse_llm_json_or_fail
        from ...core.config import settings

        # 获取蓝图信息
        blueprint_schema = CodingSerializer.build_blueprint_schema(project)

        # 构建提示词
        system_prompt = await self._build_system_prompt(prompt_service)
        user_prompt = self._build_user_prompt(
            blueprint=blueprint_schema.model_dump() if blueprint_schema else {},
            module=module,
            preference=preference,
        )

        # 调用LLM - 目录结构JSON可能较大，使用coding_prompt的max_tokens
        response = await llm_service.get_llm_response(
            system_prompt=system_prompt,
            conversation_history=[{"role": "user", "content": user_prompt}],
            user_id=project.user_id,
            max_tokens=settings.llm_max_tokens_coding_prompt,
            response_format={"type": "json_object"},
        )

        # 解析响应
        data = parse_llm_json_or_fail(response, "目录结构生成失败")
        return LLMDirectoryStructureOutput(**data)

    def _generate_default_structure(
        self,
        module: CodingModule,
    ) -> LLMDirectoryStructureOutput:
        """生成默认目录结构（无LLM时使用）"""
        from ...schemas.coding_files import LLMDirectoryNode, LLMSourceFile

        # 根据模块类型生成不同结构
        module_type = module.module_type or "service"
        module_name = module.name.lower().replace(" ", "_")

        root_path = f"src/{module_name}"

        # 默认目录结构
        directories = [
            LLMDirectoryNode(
                name=module_name,
                path=root_path,
                node_type="directory",
                description=module.description or f"{module.name}模块",
                files=[
                    LLMSourceFile(
                        filename=f"{module_name}.py",
                        file_type="source",
                        language="python",
                        description=f"{module.name}主文件",
                        purpose="模块核心实现",
                        priority="high",
                    ),
                    LLMSourceFile(
                        filename="__init__.py",
                        file_type="source",
                        language="python",
                        description="模块初始化",
                        purpose="导出模块接口",
                        priority="medium",
                    ),
                ],
                children=[],
            ),
        ]

        return LLMDirectoryStructureOutput(
            root_path=root_path,
            directories=directories,
            summary=f"为{module.name}模块生成的默认目录结构",
        )

    async def _save_structure(
        self,
        project_id: str,
        module_number: int,
        structure: LLMDirectoryStructureOutput,
    ) -> Tuple[int, int]:
        """保存目录结构到数据库"""
        dirs_created = 0
        files_created = 0

        # 递归保存目录和文件
        for dir_node in structure.directories:
            # 确保父目录存在，并获取正确的parent_id
            parent_id = await self._ensure_parent_directories(
                project_id=project_id,
                module_number=module_number,
                path=dir_node.path,
            )

            d, f = await self._save_directory_node(
                project_id=project_id,
                module_number=module_number,
                node_data=dir_node,
                parent_id=parent_id,
            )
            dirs_created += d
            files_created += f

        await self.session.flush()
        return dirs_created, files_created

    async def _ensure_parent_directories(
        self,
        project_id: str,
        module_number: int,
        path: str,
    ) -> Optional[int]:
        """
        确保路径中的所有父目录都存在

        例如对于路径 "src/auth/handlers"，确保 "src" 和 "src/auth" 目录存在。

        Args:
            project_id: 项目ID
            module_number: 模块编号
            path: 目标目录的完整路径

        Returns:
            直接父目录的ID，如果是根目录则返回None
        """
        # 分解路径
        parts = path.strip("/").split("/")

        # 如果只有一层（如 "src"），则没有父目录
        if len(parts) <= 1:
            return None

        # 需要创建的父目录路径列表（不包含最后一级，因为最后一级是目标目录本身）
        parent_parts = parts[:-1]
        parent_id = None

        # 逐级创建父目录
        for i in range(len(parent_parts)):
            current_path = "/".join(parent_parts[:i + 1])
            current_name = parent_parts[i]

            # 检查该路径是否已存在
            existing_dir = await self.dir_repo.get_by_path(project_id, current_path)

            if existing_dir:
                # 目录已存在，更新parent_id为当前目录
                parent_id = existing_dir.id
                logger.debug(f"父目录已存在: {current_path} (id={parent_id})")
            else:
                # 创建新的父目录
                new_dir = CodingDirectoryNode(
                    project_id=project_id,
                    parent_id=parent_id,
                    name=current_name,
                    path=current_path,
                    node_type="directory",
                    description=f"自动创建的目录: {current_name}",
                    sort_order=0,
                    module_number=module_number,
                    generation_status="completed",
                    is_manual=False,
                )
                self.session.add(new_dir)
                await self.session.flush()
                parent_id = new_dir.id
                logger.debug(f"自动创建父目录: {current_path} (id={parent_id})")

        return parent_id

    async def _save_directory_node(
        self,
        project_id: str,
        module_number: int,
        node_data,
        parent_id: Optional[int],
        sort_order: int = 0,
    ) -> Tuple[int, int]:
        """递归保存目录节点（支持目录复用）"""
        dirs_created = 0
        files_created = 0

        # 优先使用node_data自身的module_number，否则使用传入的默认值
        effective_dir_module = getattr(node_data, 'module_number', None) or module_number

        # 检查该路径是否已存在目录
        existing_dir = await self.dir_repo.get_by_path(project_id, node_data.path)

        if existing_dir:
            # 目录已存在，复用它
            dir_node = existing_dir
            logger.debug(f"复用已存在的目录: {node_data.path}")
        else:
            # 创建新目录
            dir_node = CodingDirectoryNode(
                project_id=project_id,
                parent_id=parent_id,
                name=node_data.name,
                path=node_data.path,
                node_type=node_data.node_type,
                description=node_data.description,
                sort_order=sort_order,
                module_number=effective_dir_module,
                generation_status="completed",
                is_manual=False,
            )
            self.session.add(dir_node)
            await self.session.flush()
            dirs_created = 1
            logger.debug(f"创建新目录: {node_data.path} (module={effective_dir_module})")

        # 创建文件（优先使用文件自身的module_number）
        for idx, file_data in enumerate(node_data.files):
            file_path = f"{node_data.path}/{file_data.filename}"

            # 检查文件是否已存在
            existing_file = await self.file_repo.get_by_path(project_id, file_path)
            if existing_file:
                logger.debug(f"跳过已存在的文件: {file_path}")
                continue

            # 优先使用文件自身的module_number，其次目录的，最后使用传入的默认值
            effective_file_module = getattr(file_data, 'module_number', None) or effective_dir_module

            source_file = CodingSourceFile(
                project_id=project_id,
                directory_id=dir_node.id,
                filename=file_data.filename,
                file_path=file_path,
                file_type=file_data.file_type,
                language=file_data.language,
                description=file_data.description,
                purpose=file_data.purpose,
                priority=file_data.priority,
                module_number=effective_file_module,
                sort_order=idx,
                status="not_generated",
                is_manual=False,
            )
            self.session.add(source_file)
            await self.session.flush()
            files_created += 1

        # 递归处理子目录（传递默认module_number，但子节点会优先使用自身的）
        for idx, child in enumerate(node_data.children):
            d, f = await self._save_directory_node(
                project_id=project_id,
                module_number=module_number,  # 仍传递默认值，但子节点会优先使用自身的
                node_data=child,
                parent_id=dir_node.id,
                sort_order=idx,
            )
            dirs_created += d
            files_created += f

        return dirs_created, files_created

    # ------------------------------------------------------------------
    # 目录CRUD
    # ------------------------------------------------------------------

    async def create_directory(
        self,
        project_id: str,
        user_id: int,
        name: str,
        parent_id: Optional[int] = None,
        node_type: str = "directory",
        description: Optional[str] = None,
    ) -> CodingDirectoryNode:
        """手动创建目录"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        # 计算路径
        if parent_id:
            parent = await self.dir_repo.get_by_id(parent_id)
            if not parent or parent.project_id != project_id:
                raise ResourceNotFoundError("父目录", str(parent_id))
            path = f"{parent.path}/{name}"
        else:
            path = name

        # 检查路径唯一性
        existing = await self.dir_repo.get_by_path(project_id, path)
        if existing:
            raise InvalidParameterError(f"目录路径已存在: {path}", parameter="path")

        dir_node = CodingDirectoryNode(
            project_id=project_id,
            parent_id=parent_id,
            name=name,
            path=path,
            node_type=node_type,
            description=description,
            generation_status="completed",
            is_manual=True,
        )
        self.session.add(dir_node)
        await self.session.flush()

        return dir_node

    async def update_directory(
        self,
        project_id: str,
        user_id: int,
        node_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sort_order: Optional[int] = None,
    ) -> CodingDirectoryNode:
        """更新目录"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        node = await self.dir_repo.get_by_id(node_id)
        if not node or node.project_id != project_id:
            raise ResourceNotFoundError("目录", str(node_id))

        if name is not None and name != node.name:
            # 更新名称时需要更新路径
            if node.parent_id:
                parent = await self.dir_repo.get_by_id(node.parent_id)
                new_path = f"{parent.path}/{name}"
            else:
                new_path = name

            # 检查新路径唯一性
            existing = await self.dir_repo.get_by_path(project_id, new_path)
            if existing and existing.id != node_id:
                raise InvalidParameterError(f"目录路径已存在: {new_path}", parameter="name")

            node.name = name
            node.path = new_path

        if description is not None:
            node.description = description

        if sort_order is not None:
            node.sort_order = sort_order

        await self.session.flush()
        return node

    async def delete_directory(
        self,
        project_id: str,
        user_id: int,
        node_id: int,
    ) -> None:
        """删除目录（级联删除子目录和文件）"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        node = await self.dir_repo.get_by_id(node_id)
        if not node or node.project_id != project_id:
            raise ResourceNotFoundError("目录", str(node_id))

        await self.dir_repo.delete(node)
        await self.session.flush()

    # ------------------------------------------------------------------
    # 提示词构建
    # ------------------------------------------------------------------

    async def _build_system_prompt(self, prompt_service) -> str:
        """构建系统提示词"""
        try:
            prompt = await prompt_service.get_prompt("directory_structure_generation")
            if prompt:
                return prompt
        except Exception:
            pass

        return """你是一位资深软件架构师，擅长设计清晰、合理的项目目录结构。

根据模块信息，生成该模块的目录结构和源文件列表。

输出JSON格式：
{
    "root_path": "模块根目录路径",
    "directories": [
        {
            "name": "目录名",
            "path": "完整路径",
            "node_type": "directory或package",
            "description": "目录说明",
            "files": [
                {
                    "filename": "文件名",
                    "file_type": "source/config/test/doc",
                    "language": "python/typescript/go等",
                    "description": "文件描述",
                    "purpose": "文件用途",
                    "priority": "high/medium/low"
                }
            ],
            "children": [子目录...]
        }
    ],
    "summary": "目录结构说明"
}

设计原则：
1. 遵循语言和框架的最佳实践
2. 职责清晰，每个文件专注一个职责
3. 文件命名规范，易于理解
4. 合理的目录层级，不过深不过浅"""

    # ------------------------------------------------------------------
    # 数据修复
    # ------------------------------------------------------------------

    async def repair_parent_relationships(
        self,
        project_id: str,
        user_id: int,
    ) -> Dict[str, int]:
        """
        修复目录的parent_id关系

        遍历所有目录，根据路径重建正确的父子关系。

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            修复统计信息
        """
        await self._project_service.ensure_project_owner(project_id, user_id)

        stats = {
            "total_directories": 0,
            "fixed_directories": 0,
            "created_parents": 0,
        }

        # 获取项目所有目录，按路径长度排序（短路径先处理）
        all_dirs = await self.dir_repo.get_by_project(project_id)
        all_dirs_sorted = sorted(all_dirs, key=lambda d: len(d.path.split("/")))

        stats["total_directories"] = len(all_dirs_sorted)

        # 建立路径到目录的映射
        path_to_dir: Dict[str, CodingDirectoryNode] = {d.path: d for d in all_dirs_sorted}

        for dir_node in all_dirs_sorted:
            path_parts = dir_node.path.strip("/").split("/")

            # 如果只有一层（如 "src"），则parent_id应为None
            if len(path_parts) <= 1:
                if dir_node.parent_id is not None:
                    dir_node.parent_id = None
                    stats["fixed_directories"] += 1
                continue

            # 计算父目录路径
            parent_path = "/".join(path_parts[:-1])

            # 查找或创建父目录
            if parent_path in path_to_dir:
                parent_dir = path_to_dir[parent_path]
            else:
                # 父目录不存在，需要创建
                parent_name = path_parts[-2]
                # 递归确保所有祖先目录存在
                grandparent_id = None
                if len(path_parts) > 2:
                    grandparent_path = "/".join(path_parts[:-2])
                    if grandparent_path in path_to_dir:
                        grandparent_id = path_to_dir[grandparent_path].id

                parent_dir = CodingDirectoryNode(
                    project_id=project_id,
                    parent_id=grandparent_id,
                    name=parent_name,
                    path=parent_path,
                    node_type="directory",
                    description=f"自动修复创建: {parent_name}",
                    sort_order=0,
                    module_number=dir_node.module_number or 0,
                    generation_status="completed",
                    is_manual=False,
                )
                self.session.add(parent_dir)
                await self.session.flush()
                path_to_dir[parent_path] = parent_dir
                stats["created_parents"] += 1
                logger.info(f"修复创建父目录: {parent_path}")

            # 更新parent_id
            if dir_node.parent_id != parent_dir.id:
                dir_node.parent_id = parent_dir.id
                stats["fixed_directories"] += 1
                logger.debug(f"修复目录parent_id: {dir_node.path} -> parent={parent_path}")

        await self.session.flush()
        logger.info(
            f"目录关系修复完成: total={stats['total_directories']} "
            f"fixed={stats['fixed_directories']} created={stats['created_parents']}"
        )

        return stats

    async def clear_project_structure(
        self,
        project_id: str,
        user_id: int,
    ) -> Tuple[int, int]:
        """
        清除项目的所有目录结构

        先删除所有文件，再删除所有目录。

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            (删除的目录数, 删除的文件数)
        """
        await self._project_service.ensure_project_owner(project_id, user_id)

        # 先删除所有文件（因为文件依赖目录）
        files_deleted = await self.file_repo.delete_by_project(project_id)

        # 再删除所有目录
        dirs_deleted = await self.dir_repo.delete_by_project(project_id)

        await self.session.flush()

        logger.info(
            f"清除项目目录结构: project_id={project_id} "
            f"dirs_deleted={dirs_deleted} files_deleted={files_deleted}"
        )

        return dirs_deleted, files_deleted

    # ------------------------------------------------------------------
    # 提示词构建
    # ------------------------------------------------------------------

    def _build_user_prompt(
        self,
        blueprint: dict,
        module: CodingModule,
        preference: Optional[str],
    ) -> str:
        """构建用户提示词"""
        import json

        # 提取项目和技术栈信息
        tech_stack = blueprint.get("tech_stack", {})

        input_data = {
            "project": {
                "name": blueprint.get("title", ""),
                "tech_style": blueprint.get("tech_style", ""),
            },
            "tech_stack": {
                "constraints": tech_stack.get("core_constraints", "")[:500] if isinstance(tech_stack, dict) else "",
                "components": [c.get("name", "") for c in tech_stack.get("components", [])][:10] if isinstance(tech_stack, dict) else [],
            },
            "module": {
                "number": module.module_number,
                "name": module.name,
                "type": module.module_type or "service",
                "description": module.description or "",
                "interface": module.interface or "",
            },
        }

        if preference:
            input_data["preference"] = preference[:500]

        return f"""请为以下模块生成目录结构：

{json.dumps(input_data, ensure_ascii=False, indent=2)}

按照模块类型和技术栈，生成合理的目录结构和源文件列表。"""
