"""
Coding项目目录结构和文件Repository

提供目录节点、源文件、文件版本的数据访问操作。
"""

from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.coding_files import (
    CodingDirectoryNode,
    CodingSourceFile,
    CodingFileVersion,
    CodingAgentState,
)


class CodingDirectoryNodeRepository(BaseRepository[CodingDirectoryNode]):
    """目录节点仓储"""

    model = CodingDirectoryNode

    async def get_by_id(self, node_id: int) -> Optional[CodingDirectoryNode]:
        """根据ID获取目录节点"""
        return await self.get(id=node_id)

    async def get_with_children(self, node_id: int) -> Optional[CodingDirectoryNode]:
        """获取目录节点及其子节点"""
        stmt = (
            select(CodingDirectoryNode)
            .where(CodingDirectoryNode.id == node_id)
            .options(
                selectinload(CodingDirectoryNode.children),
                selectinload(CodingDirectoryNode.source_files),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_path(
        self,
        project_id: str,
        path: str,
    ) -> Optional[CodingDirectoryNode]:
        """根据路径获取目录节点"""
        return await self.get(project_id=project_id, path=path)

    async def get_root_nodes(self, project_id: str) -> List[CodingDirectoryNode]:
        """获取项目的根目录节点（parent_id为空）"""
        stmt = (
            select(CodingDirectoryNode)
            .where(CodingDirectoryNode.project_id == project_id)
            .where(CodingDirectoryNode.parent_id.is_(None))
            .order_by(CodingDirectoryNode.sort_order, CodingDirectoryNode.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_root_nodes_with_tree(self, project_id: str) -> List[CodingDirectoryNode]:
        """获取项目的完整目录树（递归加载所有子节点和文件）"""
        # 首先获取所有节点
        stmt = (
            select(CodingDirectoryNode)
            .where(CodingDirectoryNode.project_id == project_id)
            .options(
                selectinload(CodingDirectoryNode.source_files),
            )
            .order_by(CodingDirectoryNode.path)
        )
        result = await self.session.execute(stmt)
        all_nodes = list(result.scalars().all())

        # 构建树结构
        node_map = {node.id: node for node in all_nodes}
        root_nodes = []

        for node in all_nodes:
            if node.parent_id is None:
                root_nodes.append(node)
            else:
                parent = node_map.get(node.parent_id)
                if parent:
                    if not hasattr(parent, '_children_list'):
                        parent._children_list = []
                    parent._children_list.append(node)

        # 将_children_list排序（不赋值给children，避免触发SQLAlchemy懒加载）
        for node in all_nodes:
            if hasattr(node, '_children_list'):
                node._children_list = sorted(node._children_list, key=lambda x: (x.sort_order, x.name))
            else:
                node._children_list = []

        return sorted(root_nodes, key=lambda x: (x.sort_order, x.name))

    async def get_by_project(self, project_id: str) -> List[CodingDirectoryNode]:
        """获取项目的所有目录节点"""
        nodes = await self.list(
            filters={"project_id": project_id},
            order_by="path",
            order_desc=False,
        )
        return list(nodes)

    async def get_by_module(
        self,
        project_id: str,
        module_number: int,
    ) -> List[CodingDirectoryNode]:
        """获取模块关联的目录节点"""
        stmt = (
            select(CodingDirectoryNode)
            .where(CodingDirectoryNode.project_id == project_id)
            .where(CodingDirectoryNode.module_number == module_number)
            .order_by(CodingDirectoryNode.path)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_children(self, node_id: int) -> List[CodingDirectoryNode]:
        """获取目录的子节点"""
        stmt = (
            select(CodingDirectoryNode)
            .where(CodingDirectoryNode.parent_id == node_id)
            .order_by(CodingDirectoryNode.sort_order, CodingDirectoryNode.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_module(
        self,
        project_id: str,
        module_number: int,
    ) -> int:
        """删除模块关联的所有目录节点（级联删除文件）"""
        stmt = (
            delete(CodingDirectoryNode)
            .where(CodingDirectoryNode.project_id == project_id)
            .where(CodingDirectoryNode.module_number == module_number)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def count_by_project(self, project_id: str) -> int:
        """统计项目的目录数量"""
        stmt = (
            select(func.count(CodingDirectoryNode.id))
            .where(CodingDirectoryNode.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def delete_by_project(self, project_id: str) -> int:
        """删除项目的所有目录节点"""
        stmt = (
            delete(CodingDirectoryNode)
            .where(CodingDirectoryNode.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.rowcount


class CodingSourceFileRepository(BaseRepository[CodingSourceFile]):
    """源文件仓储"""

    model = CodingSourceFile

    async def get_by_id(self, file_id: int) -> Optional[CodingSourceFile]:
        """根据ID获取源文件"""
        return await self.get(id=file_id)

    async def get_with_versions(self, file_id: int) -> Optional[CodingSourceFile]:
        """获取源文件及其版本列表"""
        stmt = (
            select(CodingSourceFile)
            .where(CodingSourceFile.id == file_id)
            .options(
                selectinload(CodingSourceFile.versions),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_with_relations(self, file_id: int) -> Optional[CodingSourceFile]:
        """获取源文件及其所有关联数据"""
        stmt = (
            select(CodingSourceFile)
            .where(CodingSourceFile.id == file_id)
            .options(
                selectinload(CodingSourceFile.versions),
                selectinload(CodingSourceFile.directory),
                selectinload(CodingSourceFile.selected_version),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_path(
        self,
        project_id: str,
        file_path: str,
    ) -> Optional[CodingSourceFile]:
        """根据文件路径获取源文件"""
        return await self.get(project_id=project_id, file_path=file_path)

    async def get_by_project(self, project_id: str) -> List[CodingSourceFile]:
        """获取项目的所有源文件"""
        files = await self.list(
            filters={"project_id": project_id},
            order_by="file_path",
            order_desc=False,
        )
        return list(files)

    async def get_by_directory(self, directory_id: int) -> List[CodingSourceFile]:
        """获取目录下的所有源文件"""
        stmt = (
            select(CodingSourceFile)
            .where(CodingSourceFile.directory_id == directory_id)
            .order_by(CodingSourceFile.sort_order, CodingSourceFile.filename)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_module(
        self,
        project_id: str,
        module_number: int,
    ) -> List[CodingSourceFile]:
        """获取模块关联的源文件"""
        stmt = (
            select(CodingSourceFile)
            .where(CodingSourceFile.project_id == project_id)
            .where(CodingSourceFile.module_number == module_number)
            .order_by(CodingSourceFile.file_path)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_system(
        self,
        project_id: str,
        system_number: int,
    ) -> List[CodingSourceFile]:
        """获取系统关联的源文件"""
        stmt = (
            select(CodingSourceFile)
            .where(CodingSourceFile.project_id == project_id)
            .where(CodingSourceFile.system_number == system_number)
            .order_by(CodingSourceFile.file_path)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_not_generated(self, project_id: str) -> List[CodingSourceFile]:
        """获取未生成Prompt的源文件"""
        stmt = (
            select(CodingSourceFile)
            .where(CodingSourceFile.project_id == project_id)
            .where(CodingSourceFile.status == "not_generated")
            .order_by(
                CodingSourceFile.priority.desc(),
                CodingSourceFile.sort_order,
                CodingSourceFile.file_path
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_project(self, project_id: str) -> int:
        """统计项目的文件数量"""
        stmt = (
            select(func.count(CodingSourceFile.id))
            .where(CodingSourceFile.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_generated(self, project_id: str) -> Tuple[int, int]:
        """统计已生成/总数"""
        total_stmt = (
            select(func.count(CodingSourceFile.id))
            .where(CodingSourceFile.project_id == project_id)
        )
        generated_stmt = (
            select(func.count(CodingSourceFile.id))
            .where(CodingSourceFile.project_id == project_id)
            .where(CodingSourceFile.status == "generated")
        )

        total_result = await self.session.execute(total_stmt)
        generated_result = await self.session.execute(generated_stmt)

        return (generated_result.scalar() or 0, total_result.scalar() or 0)

    async def delete_by_module(
        self,
        project_id: str,
        module_number: int,
    ) -> int:
        """删除模块关联的所有源文件"""
        stmt = (
            delete(CodingSourceFile)
            .where(CodingSourceFile.project_id == project_id)
            .where(CodingSourceFile.module_number == module_number)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def delete_by_project(self, project_id: str) -> int:
        """删除项目的所有源文件"""
        stmt = (
            delete(CodingSourceFile)
            .where(CodingSourceFile.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.rowcount


class CodingFileVersionRepository(BaseRepository[CodingFileVersion]):
    """文件Prompt版本仓储"""

    model = CodingFileVersion

    async def get_by_file(self, file_id: int) -> List[CodingFileVersion]:
        """获取文件的所有版本"""
        versions = await self.list(
            filters={"file_id": file_id},
            order_by="created_at",
            order_desc=False,
        )
        return list(versions)

    async def get_latest(self, file_id: int) -> Optional[CodingFileVersion]:
        """获取文件的最新版本"""
        versions = await self.list(
            filters={"file_id": file_id},
            order_by="created_at",
            order_desc=True,
        )
        versions_list = list(versions)
        return versions_list[0] if versions_list else None

    async def count_by_file(self, file_id: int) -> int:
        """统计文件的版本数量"""
        stmt = (
            select(func.count(CodingFileVersion.id))
            .where(CodingFileVersion.file_id == file_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def delete_by_file(self, file_id: int) -> int:
        """删除文件的所有版本"""
        stmt = (
            delete(CodingFileVersion)
            .where(CodingFileVersion.file_id == file_id)
        )
        result = await self.session.execute(stmt)
        return result.rowcount


class CodingAgentStateRepository(BaseRepository[CodingAgentState]):
    """Agent状态仓储"""

    model = CodingAgentState

    async def get_by_project_and_type(
        self,
        project_id: str,
        agent_type: str,
    ) -> Optional[CodingAgentState]:
        """根据项目ID和Agent类型获取状态"""
        return await self.get(project_id=project_id, agent_type=agent_type)

    async def get_paused(
        self,
        project_id: str,
        agent_type: str,
    ) -> Optional[CodingAgentState]:
        """获取暂停的Agent状态"""
        stmt = (
            select(CodingAgentState)
            .where(CodingAgentState.project_id == project_id)
            .where(CodingAgentState.agent_type == agent_type)
            .where(CodingAgentState.status == "paused")
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def save_state(
        self,
        project_id: str,
        agent_type: str,
        current_phase: str,
        state_data: dict,
        output_log: str = "",
        progress_percent: int = 0,
        progress_message: str = "",
        status: str = "running",
    ) -> CodingAgentState:
        """保存或更新Agent状态"""
        existing = await self.get_by_project_and_type(project_id, agent_type)
        if existing:
            existing.current_phase = current_phase
            existing.state_data = state_data
            existing.output_log = output_log
            existing.progress_percent = progress_percent
            existing.progress_message = progress_message
            existing.status = status
            await self.session.flush()
            return existing
        else:
            state = CodingAgentState(
                project_id=project_id,
                agent_type=agent_type,
                current_phase=current_phase,
                state_data=state_data,
                output_log=output_log,
                progress_percent=progress_percent,
                progress_message=progress_message,
                status=status,
            )
            self.session.add(state)
            await self.session.flush()
            return state

    async def update_status(
        self,
        project_id: str,
        agent_type: str,
        status: str,
    ) -> None:
        """更新Agent状态"""
        existing = await self.get_by_project_and_type(project_id, agent_type)
        if existing:
            existing.status = status
            await self.session.flush()

    async def delete_state(
        self,
        project_id: str,
        agent_type: str,
    ) -> int:
        """删除Agent状态"""
        stmt = (
            delete(CodingAgentState)
            .where(CodingAgentState.project_id == project_id)
            .where(CodingAgentState.agent_type == agent_type)
        )
        result = await self.session.execute(stmt)
        return result.rowcount
