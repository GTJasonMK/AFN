"""
文件 Prompt 生成服务（对外入口）

说明：
- 该服务对外提供 Coding 源文件的 CRUD、版本管理、Prompt 生成与审查等能力。
- 为提升可读性，具体实现已拆分到 `backend/app/services/coding_files/file_prompt/` 目录下，
  由多个 mixin 组合提供能力；本文件仅负责聚合与依赖初始化。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.coding_repository import CodingModuleRepository
from ...repositories.coding_files_repository import CodingFileVersionRepository, CodingSourceFileRepository
from ...services.coding import CodingProjectService
from .file_prompt.file_ops import FileOpsMixin
from .file_prompt.generation import GenerationMixin
from .file_prompt.ingestion import IngestionMixin
from .file_prompt.prompts import PromptsMixin
from .file_prompt.rag import RagMixin
from .file_prompt.review import ReviewMixin


class FilePromptService(
    FileOpsMixin,
    GenerationMixin,
    ReviewMixin,
    IngestionMixin,
    RagMixin,
    PromptsMixin,
):
    """文件 Prompt 服务聚合入口（组合各子模块能力）。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.file_repo = CodingSourceFileRepository(session)
        self.version_repo = CodingFileVersionRepository(session)
        self.module_repo = CodingModuleRepository(session)
        self._project_service = CodingProjectService(session)


__all__ = ["FilePromptService"]

