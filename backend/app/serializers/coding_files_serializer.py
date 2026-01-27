"""
Coding 文件/目录序列化工具

集中维护 Coding 目录树相关的响应构建，避免 router/service 并行维护字段映射。
"""

from typing import Any, List, Optional

from ..schemas.coding_files import DirectoryNodeResponse, SourceFileResponse


def build_source_file_response(file: Any, *, version_count: int) -> SourceFileResponse:
    """构建源文件响应（不含内容）。"""
    return SourceFileResponse(
        id=file.id,
        project_id=file.project_id,
        directory_id=file.directory_id,
        filename=file.filename,
        file_path=file.file_path,
        file_type=file.file_type,
        language=file.language,
        description=file.description,
        purpose=file.purpose,
        imports=file.imports or [],
        exports=file.exports or [],
        dependencies=file.dependencies or [],
        module_number=file.module_number,
        system_number=file.system_number,
        priority=file.priority,
        sort_order=file.sort_order,
        status=file.status,
        is_manual=file.is_manual,
        has_content=file.selected_version_id is not None,
        selected_version_id=file.selected_version_id,
        version_count=version_count,
    )


def build_directory_node_response(
    node: Any,
    *,
    file_count: int = 0,
    files: Optional[List[SourceFileResponse]] = None,
    children: Optional[List[DirectoryNodeResponse]] = None,
) -> DirectoryNodeResponse:
    """构建目录节点响应（基础字段 + 可选 files/children）。"""
    return DirectoryNodeResponse(
        id=node.id,
        project_id=node.project_id,
        parent_id=node.parent_id,
        name=node.name,
        path=node.path,
        node_type=node.node_type,
        description=node.description,
        sort_order=node.sort_order,
        module_number=node.module_number,
        generation_status=node.generation_status,
        is_manual=node.is_manual,
        file_count=file_count,
        files=files or [],
        children=children or [],
    )
