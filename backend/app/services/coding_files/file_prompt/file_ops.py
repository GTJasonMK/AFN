"""
文件 Prompt 子模块：文件/版本/序列化相关能力（FileOpsMixin）

拆分自 `backend/app/services/coding_files/file_prompt_service.py`，用于降低单文件复杂度并提升可读性。
"""

from __future__ import annotations

from typing import List, Optional

from ....exceptions import InvalidParameterError, ResourceNotFoundError
from ....models.coding_files import CodingFileVersion, CodingSourceFile
from ....schemas.coding_files import FileVersionResponse, SourceFileDetail, SourceFileResponse
from ....serializers.coding_files_serializer import build_source_file_response


class FileOpsMixin:
    """文件查询/序列化/CRUD/版本管理能力"""

    # ------------------------------------------------------------------
    # 文件查询
    # ------------------------------------------------------------------

    async def get_file(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
    ) -> SourceFileDetail:
        """获取文件详情（包含内容）"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_with_relations(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        return await self._serialize_file_detail(file)

    async def list_files(
        self,
        project_id: str,
        user_id: int,
        module_number: Optional[int] = None,
        directory_id: Optional[int] = None,
    ) -> List[SourceFileResponse]:
        """获取文件列表（可按模块/目录筛选）"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        if directory_id is not None:
            files = await self.file_repo.get_by_directory(directory_id)
        elif module_number is not None:
            files = await self.file_repo.get_by_module(project_id, module_number)
        else:
            files = await self.file_repo.get_by_project(project_id)

        return [await self._serialize_file(f) for f in files]

    async def _serialize_file(self, file: CodingSourceFile) -> SourceFileResponse:
        """序列化文件（不含内容）"""
        version_count = await self.version_repo.count_by_file(file.id)
        return build_source_file_response(file, version_count=version_count)

    async def _serialize_file_detail(self, file: CodingSourceFile) -> SourceFileDetail:
        """序列化文件详情（含内容）"""
        base = await self._serialize_file(file)

        content = None
        if file.selected_version_id and file.selected_version:
            content = file.selected_version.content

        return SourceFileDetail(
            **base.model_dump(),
            content=content,
            review_prompt=file.review_prompt,
        )

    # ------------------------------------------------------------------
    # 内容保存 / 版本管理
    # ------------------------------------------------------------------

    async def save_content(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
        content: str,
        version_label: Optional[str] = None,
    ) -> CodingFileVersion:
        """保存文件内容（编辑后创建新版本）"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        version_count = await self.version_repo.count_by_file(file.id)

        version = CodingFileVersion(
            file_id=file.id,
            version_label=version_label or f"v{version_count + 1}",
            content=content,
        )
        self.session.add(version)
        await self.session.flush()

        # 选中新版本
        file.selected_version_id = version.id
        file.status = "generated"
        await self.session.flush()

        return version

    async def select_version(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
        version_id: int,
    ) -> CodingSourceFile:
        """选择文件版本"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        version = await self.version_repo.get(id=version_id)
        if not version or version.file_id != file_id:
            raise ResourceNotFoundError("文件版本", str(version_id))

        file.selected_version_id = version_id
        await self.session.flush()

        return file

    async def get_versions(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
    ) -> List[FileVersionResponse]:
        """获取文件的所有版本"""
        versions, _ = await self.get_versions_with_selected_version_id(
            project_id=project_id,
            user_id=user_id,
            file_id=file_id,
        )
        return versions

    async def get_versions_with_selected_version_id(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
    ) -> tuple[List[FileVersionResponse], Optional[int]]:
        """获取文件版本列表，并同时返回当前选中版本ID（避免额外查询）。"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        versions = await self.version_repo.get_by_file(file_id)
        selected_version_id = file.selected_version_id

        return [
            FileVersionResponse(
                id=v.id,
                file_id=v.file_id,
                version_label=v.version_label,
                provider=v.provider,
                content=v.content,
                metadata=v.metadata_json,
                created_at=v.created_at,
            )
            for v in versions
        ], selected_version_id

    # ------------------------------------------------------------------
    # 文件 CRUD
    # ------------------------------------------------------------------

    async def create_file(
        self,
        project_id: str,
        user_id: int,
        directory_id: int,
        filename: str,
        file_type: str = "source",
        language: Optional[str] = None,
        description: Optional[str] = None,
        purpose: Optional[str] = None,
        priority: str = "medium",
    ) -> CodingSourceFile:
        """手动创建文件"""
        from ....repositories.coding_files_repository import CodingDirectoryNodeRepository

        await self._project_service.ensure_project_owner(project_id, user_id)

        # 验证目录存在
        dir_repo = CodingDirectoryNodeRepository(self.session)
        directory = await dir_repo.get_by_id(directory_id)
        if not directory or directory.project_id != project_id:
            raise ResourceNotFoundError("目录", str(directory_id))

        # 计算完整路径
        file_path = f"{directory.path}/{filename}"

        # 检查路径唯一性
        existing = await self.file_repo.get_by_path(project_id, file_path)
        if existing:
            raise InvalidParameterError(f"文件路径已存在: {file_path}", parameter="filename")

        source_file = CodingSourceFile(
            project_id=project_id,
            directory_id=directory_id,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            language=language,
            description=description,
            purpose=purpose,
            priority=priority,
            module_number=directory.module_number,
            status="not_generated",
            is_manual=True,
        )
        self.session.add(source_file)
        await self.session.flush()

        return source_file

    async def update_file(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
        filename: Optional[str] = None,
        description: Optional[str] = None,
        purpose: Optional[str] = None,
        priority: Optional[str] = None,
        sort_order: Optional[int] = None,
    ) -> CodingSourceFile:
        """更新文件信息"""
        from ....repositories.coding_files_repository import CodingDirectoryNodeRepository

        await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        if filename is not None and filename != file.filename:
            # 更新文件名时需要更新路径
            dir_repo = CodingDirectoryNodeRepository(self.session)
            directory = await dir_repo.get_by_id(file.directory_id)
            new_path = f"{directory.path}/{filename}"

            # 检查新路径唯一性
            existing = await self.file_repo.get_by_path(project_id, new_path)
            if existing and existing.id != file_id:
                raise InvalidParameterError(f"文件路径已存在: {new_path}", parameter="filename")

            file.filename = filename
            file.file_path = new_path

        if description is not None:
            file.description = description

        if purpose is not None:
            file.purpose = purpose

        if priority is not None:
            file.priority = priority

        if sort_order is not None:
            file.sort_order = sort_order

        await self.session.flush()
        return file

    async def delete_file(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
    ) -> None:
        """删除文件"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        await self.file_repo.delete(file)
        await self.session.flush()


__all__ = ["FileOpsMixin"]
