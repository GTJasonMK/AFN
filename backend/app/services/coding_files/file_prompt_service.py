"""
文件Prompt生成服务

负责为源文件生成实现Prompt。
支持RAG增强的上下文感知生成。
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Callable, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ...exceptions import InvalidParameterError, ResourceNotFoundError
from ...models.coding_files import CodingSourceFile, CodingFileVersion
from ...repositories.coding_repository import (
    CodingModuleRepository,
)
from ...repositories.coding_files_repository import (
    CodingSourceFileRepository,
    CodingFileVersionRepository,
)
from ...schemas.coding_files import (
    SourceFileResponse,
    SourceFileDetail,
    FileVersionResponse,
)
from ...services.coding import CodingProjectService
from ...services.coding_rag.data_types import CodingDataType
from ...utils.prompt_helpers import (
    build_prompt_block,
    build_prompt_section,
    format_prompt_json,
    join_prompt_lines,
)
from ...utils.rag_helpers import build_query_text, get_query_embedding
from ..evaluation_workflow_base import EvaluationPromptContext, EvaluationWorkflowBase
from ..workflow_base import GenerationWorkflowBase

logger = logging.getLogger(__name__)


class FileReviewWorkflow(EvaluationWorkflowBase):
    """文件审查Prompt生成工作流"""

    def __init__(
        self,
        service: "FilePromptService",
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str],
        llm_service: Any,
        prompt_service: Any,
        vector_store: Any,
        user_id: int,
        *,
        commit: bool,
        progress_messages: Optional[Dict[str, str]] = None,
    ):
        self._service = service
        self._project = project
        self._file = file
        self._writing_notes = writing_notes
        self._llm_service = llm_service
        self._prompt_service = prompt_service
        self._vector_store = vector_store
        self._user_id = user_id
        self._commit = commit
        self._progress_messages = progress_messages or {}

    async def _prepare_context(self) -> EvaluationPromptContext:
        rag_context, system_prompt, user_prompt = await self._service._prepare_prompt_inputs(
            project=self._project,
            file=self._file,
            writing_notes=self._writing_notes,
            llm_service=self._llm_service,
            prompt_service=self._prompt_service,
            vector_store=self._vector_store,
            user_id=self._user_id,
            build_system_prompt=self._service._build_review_system_prompt,
            build_user_prompt=self._service._build_review_user_prompt,
        )

        return EvaluationPromptContext(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            rag_context=rag_context,
        )

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        from ...core.config import settings

        return await self._service._call_llm_content(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_service=self._llm_service,
            user_id=self._user_id,
            max_tokens=settings.llm_max_tokens_coding_prompt,
        )

    async def _iter_llm_tokens(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncGenerator[str, None]:
        from ...core.config import settings

        async for token in self._service._iter_llm_tokens(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_service=self._llm_service,
            user_id=self._user_id,
            max_tokens=settings.llm_max_tokens_coding_prompt,
        ):
            yield token

    async def _save_result(self, result: str) -> None:
        await self._service._finalize_prompt_result(
            file=self._file,
            content=result,
            is_review=True,
            commit=self._commit,
        )

    async def _ingest_result(self, result: str) -> None:
        await self._service._ingest_review_prompt(
            file=self._file,
            content=result,
            vector_store=self._vector_store,
            llm_service=self._llm_service,
            user_id=self._user_id,
        )

    def _get_progress_messages(self) -> Dict[str, str]:
        return self._progress_messages

    async def _build_complete_payload(self, result: str) -> Dict[str, Any]:
        return {
            "file_id": self._file.id,
            "content": result,
        }

    def _should_emit_indexing(self) -> bool:
        return bool(self._vector_store)


class FilePromptGenerationWorkflow(GenerationWorkflowBase):
    """文件Prompt生成工作流"""

    def __init__(
        self,
        service: "FilePromptService",
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str],
        llm_service: Any,
        prompt_service: Any,
        vector_store: Any,
        user_id: int,
        *,
        commit: bool,
        progress_messages: Optional[Dict[str, str]] = None,
        complete_builder: Optional[Callable[[CodingSourceFile, Optional[CodingFileVersion], str], Dict[str, Any]]] = None,
        include_version_count: bool = False,
    ):
        super().__init__()
        self._service = service
        self._project = project
        self._file = file
        self._writing_notes = writing_notes
        self._llm_service = llm_service
        self._prompt_service = prompt_service
        self._vector_store = vector_store
        self._user_id = user_id
        self._commit = commit
        self._progress_messages = progress_messages or {}
        self._complete_builder = complete_builder
        self._include_version_count = include_version_count

    async def _run_generation(self, streaming: bool) -> AsyncGenerator[Dict[str, Any], None]:
        """执行生成流程（同步/流式共用）"""
        await self._service._set_file_status(self._file, "generating", commit=False)

        try:
            if streaming:
                async for event in self._service._stream_prompt_generation(
                    project=self._project,
                    file=self._file,
                    writing_notes=self._writing_notes,
                    llm_service=self._llm_service,
                    prompt_service=self._prompt_service,
                    vector_store=self._vector_store,
                    user_id=self._user_id,
                    build_system_prompt=self._service._build_system_prompt,
                    build_user_prompt=self._service._build_user_prompt,
                    ingest_func=self._service._ingest_file_prompt,
                    is_review=False,
                    progress_messages=self._progress_messages,
                    complete_builder=self._complete_builder,
                    include_version_count=self._include_version_count,
                ):
                    yield event
            else:
                _, version = await self._service._generate_prompt_non_stream(
                    project=self._project,
                    file=self._file,
                    writing_notes=self._writing_notes,
                    llm_service=self._llm_service,
                    prompt_service=self._prompt_service,
                    vector_store=self._vector_store,
                    user_id=self._user_id,
                    build_system_prompt=self._service._build_system_prompt,
                    build_user_prompt=self._service._build_user_prompt,
                    ingest_func=self._service._ingest_file_prompt,
                    is_review=False,
                    commit=self._commit,
                )
                self._set_final_result(version)
        except Exception as exc:
            await self._service._set_file_status(self._file, "failed", commit=False)
            if streaming:
                logger.exception("文件Prompt生成失败: %s", str(exc))
                yield {"event": "error", "data": {"message": str(exc)}}
            else:
                raise


class FilePromptService:
    """
    文件Prompt生成服务

    负责：
    - 源文件的CRUD操作
    - 为源文件生成实现Prompt（流式和非流式）
    - 版本管理
    - 文件内容保存
    """

    def __init__(self, session: AsyncSession):
        """
        初始化FilePromptService

        Args:
            session: 数据库会话
        """
        self.session = session
        self.file_repo = CodingSourceFileRepository(session)
        self.version_repo = CodingFileVersionRepository(session)
        self.module_repo = CodingModuleRepository(session)
        self._project_service = CodingProjectService(session)

    # ------------------------------------------------------------------
    # 文件查询
    # ------------------------------------------------------------------

    async def get_file(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
    ) -> SourceFileDetail:
        """
        获取文件详情（包含内容）

        Args:
            project_id: 项目ID
            user_id: 用户ID
            file_id: 文件ID

        Returns:
            文件详情
        """
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
        """
        获取文件列表

        Args:
            project_id: 项目ID
            user_id: 用户ID
            module_number: 按模块筛选
            directory_id: 按目录筛选

        Returns:
            文件列表
        """
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
    # Prompt生成
    # ------------------------------------------------------------------

    async def _prepare_prompt_inputs(
        self,
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str],
        llm_service: Any,
        prompt_service: Any,
        vector_store: Any,
        user_id: int,
        build_system_prompt: Callable[[Any], Any],
        build_user_prompt: Callable[..., Any],
    ) -> Tuple[Dict[str, Any], str, str]:
        """准备RAG上下文与提示词"""
        rag_context = await self._retrieve_rag_context(
            project_id=project.id,
            file=file,
            vector_store=vector_store,
            llm_service=llm_service,
            user_id=user_id,
        )

        system_prompt = await build_system_prompt(prompt_service)
        user_prompt = await build_user_prompt(
            project=project,
            file=file,
            writing_notes=writing_notes,
            rag_context=rag_context,
        )

        return rag_context, system_prompt, user_prompt

    async def _run_llm_prompt(
        self,
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str],
        llm_service: Any,
        prompt_service: Any,
        vector_store: Any,
        user_id: int,
        build_system_prompt: Callable[[Any], Any],
        build_user_prompt: Callable[..., Any],
    ) -> str:
        """执行非流式Prompt生成并返回内容"""
        _, system_prompt, user_prompt = await self._prepare_prompt_inputs(
            project=project,
            file=file,
            writing_notes=writing_notes,
            llm_service=llm_service,
            prompt_service=prompt_service,
            vector_store=vector_store,
            user_id=user_id,
            build_system_prompt=build_system_prompt,
            build_user_prompt=build_user_prompt,
        )

        from ...core.config import settings
        return await self._call_llm_content(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_service=llm_service,
            user_id=user_id,
            max_tokens=settings.llm_max_tokens_coding_prompt,
        )

    async def _call_llm_content(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        llm_service: Any,
        user_id: int,
        max_tokens: int,
    ) -> str:
        """执行LLM调用并提取内容"""
        response = await llm_service.get_llm_response(
            system_prompt=system_prompt,
            conversation_history=[{"role": "user", "content": user_prompt}],
            user_id=user_id,
            max_tokens=max_tokens,
            response_format=None,
        )

        from ...utils.json_utils import extract_llm_content
        content, _ = extract_llm_content(response)
        return content

    async def _generate_prompt_non_stream(
        self,
        *,
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str],
        llm_service: Any,
        prompt_service: Any,
        vector_store: Any,
        user_id: int,
        build_system_prompt: Callable[[Any], Any],
        build_user_prompt: Callable[..., Any],
        ingest_func: Callable[..., Any],
        is_review: bool,
        commit: bool,
    ) -> Tuple[str, Optional[CodingFileVersion]]:
        """执行非流式Prompt生成并保存结果"""
        content = await self._run_llm_prompt(
            project=project,
            file=file,
            writing_notes=writing_notes,
            llm_service=llm_service,
            prompt_service=prompt_service,
            vector_store=vector_store,
            user_id=user_id,
            build_system_prompt=build_system_prompt,
            build_user_prompt=build_user_prompt,
        )

        version = await self._finalize_prompt_result(
            file=file,
            content=content,
            is_review=is_review,
            commit=commit,
        )

        await ingest_func(
            file=file,
            content=content,
            vector_store=vector_store,
            llm_service=llm_service,
            user_id=user_id,
        )

        return content, version

    async def _stream_prompt_generation(
        self,
        *,
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str],
        llm_service: Any,
        prompt_service: Any,
        vector_store: Any,
        user_id: int,
        build_system_prompt: Callable[[Any], Any],
        build_user_prompt: Callable[..., Any],
        ingest_func: Callable[..., Any],
        is_review: bool,
        progress_messages: Dict[str, str],
        complete_builder: Callable[[CodingSourceFile, Optional[CodingFileVersion], str], Dict[str, Any]],
        include_version_count: bool = False,
    ) -> AsyncGenerator[Dict, None]:
        """流式生成Prompt并输出事件"""
        yield {"event": "progress", "data": {"stage": "preparing", "message": progress_messages["preparing"]}}

        rag_context, system_prompt, user_prompt = await self._prepare_prompt_inputs(
            project=project,
            file=file,
            writing_notes=writing_notes,
            llm_service=llm_service,
            prompt_service=prompt_service,
            vector_store=vector_store,
            user_id=user_id,
            build_system_prompt=build_system_prompt,
            build_user_prompt=build_user_prompt,
        )

        if rag_context:
            yield {"event": "progress", "data": {"stage": "rag", "message": progress_messages["rag"]}}

        yield {"event": "progress", "data": {"stage": "generating", "message": progress_messages["generating"]}}

        from ...core.config import settings
        full_content = ""
        async for token in self._iter_llm_tokens(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_service=llm_service,
            user_id=user_id,
            max_tokens=settings.llm_max_tokens_coding_prompt,
        ):
            full_content += token
            yield {"event": "token", "data": {"token": token}}

        yield {"event": "progress", "data": {"stage": "saving", "message": progress_messages["saving"]}}

        version = await self._finalize_prompt_result(
            file=file,
            content=full_content,
            is_review=is_review,
            commit=True,
        )

        if vector_store:
            yield {"event": "progress", "data": {"stage": "indexing", "message": progress_messages["indexing"]}}
            await ingest_func(
                file=file,
                content=full_content,
                vector_store=vector_store,
                llm_service=llm_service,
                user_id=user_id,
            )

        complete_payload = complete_builder(file, version, full_content)
        if include_version_count:
            complete_payload["version_count"] = await self.version_repo.count_by_file(file.id)
        yield {"event": "complete", "data": complete_payload}

    async def _iter_llm_tokens(
        self,
        system_prompt: str,
        user_prompt: str,
        llm_service: Any,
        user_id: int,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """流式迭代LLM生成的token片段"""
        conversation_history = [{"role": "user", "content": user_prompt}]
        async for chunk in llm_service.stream_llm_response(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user_id=user_id,
            response_format=None,
            max_tokens=max_tokens,
        ):
            content = chunk.get("content", "")
            if content:
                yield content

    async def _set_file_status(
        self,
        file: CodingSourceFile,
        status: str,
        *,
        commit: bool,
    ) -> None:
        """统一设置文件状态并提交"""
        file.status = status
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()

    async def _finalize_prompt_result(
        self,
        file: CodingSourceFile,
        content: str,
        *,
        is_review: bool,
        commit: bool,
    ) -> Optional[CodingFileVersion]:
        """保存生成结果并处理事务提交"""
        if is_review:
            file.review_prompt = content
            if commit:
                await self.session.commit()
            else:
                await self.session.flush()
            return None

        version = await self._save_version(file, content)
        file.status = "generated"
        file.selected_version_id = version.id
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        return version

    async def generate_prompt(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
        writing_notes: Optional[str] = None,
        llm_service=None,
        prompt_service=None,
        vector_store=None,
    ) -> CodingFileVersion:
        """
        为文件生成Prompt（非流式）

        Args:
            project_id: 项目ID
            user_id: 用户ID
            file_id: 文件ID
            writing_notes: 额外的写作指导
            llm_service: LLM服务
            prompt_service: 提示词服务
            vector_store: 向量存储服务（用于RAG检索）

        Returns:
            生成的版本
        """
        project = await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_with_relations(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        if not llm_service:
            raise InvalidParameterError("LLM服务不可用", parameter="llm_service")

        workflow = FilePromptGenerationWorkflow(
            service=self,
            project=project,
            file=file,
            writing_notes=writing_notes,
            llm_service=llm_service,
            prompt_service=prompt_service,
            vector_store=vector_store,
            user_id=user_id,
            commit=False,
        )
        return await workflow.execute()

    async def generate_prompt_stream(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
        writing_notes: Optional[str] = None,
        llm_service=None,
        prompt_service=None,
        vector_store=None,
    ) -> AsyncGenerator[Dict, None]:
        """
        为文件生成Prompt（流式）

        Args:
            vector_store: 向量存储服务（用于RAG检索）

        Yields:
            SSE事件数据
        """
        project = await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_with_relations(file_id)
        if not file or file.project_id != project_id:
            yield {"event": "error", "data": {"message": f"源文件不存在: {file_id}"}}
            return

        if not llm_service:
            yield {"event": "error", "data": {"message": "LLM服务不可用"}}
            return

        workflow = FilePromptGenerationWorkflow(
            service=self,
            project=project,
            file=file,
            writing_notes=writing_notes,
            llm_service=llm_service,
            prompt_service=prompt_service,
            vector_store=vector_store,
            user_id=user_id,
            commit=True,
            progress_messages={
                "preparing": "准备提示词...",
                "rag": "已检索相关上下文...",
                "generating": "正在生成...",
                "saving": "保存结果...",
                "indexing": "更新索引...",
            },
            complete_builder=lambda f, v, content: {
                "file_id": f.id,
                "version_id": v.id if v else None,
                "content": content,
            },
            include_version_count=True,
        )
        async for event in workflow.execute_with_progress():
            yield event

    async def _save_version(
        self,
        file: CodingSourceFile,
        content: str,
    ) -> CodingFileVersion:
        """保存新版本"""
        version_count = await self.version_repo.count_by_file(file.id)

        version = CodingFileVersion(
            file_id=file.id,
            version_label=f"v{version_count + 1}",
            content=content,
        )
        self.session.add(version)
        await self.session.flush()

        return version

    # ------------------------------------------------------------------
    # 审查Prompt生成
    # ------------------------------------------------------------------

    async def generate_review_prompt(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
        writing_notes: Optional[str] = None,
        llm_service=None,
        prompt_service=None,
        vector_store=None,
    ) -> str:
        """
        为文件生成审查Prompt（非流式）

        Args:
            project_id: 项目ID
            user_id: 用户ID
            file_id: 文件ID
            writing_notes: 额外的写作指导
            llm_service: LLM服务
            prompt_service: 提示词服务
            vector_store: 向量存储服务

        Returns:
            生成的审查Prompt内容
        """
        project = await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_with_relations(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        if not llm_service:
            raise InvalidParameterError("LLM服务不可用", parameter="llm_service")

        try:
            workflow = FileReviewWorkflow(
                service=self,
                project=project,
                file=file,
                writing_notes=writing_notes,
                llm_service=llm_service,
                prompt_service=prompt_service,
                vector_store=vector_store,
                user_id=user_id,
                commit=False,
            )
            content = await workflow.run()

            return content

        except Exception as e:
            logger.exception("文件审查Prompt生成失败: %s", str(e))
            raise

    async def generate_review_prompt_stream(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
        writing_notes: Optional[str] = None,
        llm_service=None,
        prompt_service=None,
        vector_store=None,
    ) -> AsyncGenerator[Dict, None]:
        """
        为文件生成审查Prompt（流式）

        Yields:
            SSE事件数据
        """
        project = await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_with_relations(file_id)
        if not file or file.project_id != project_id:
            yield {"event": "error", "data": {"message": f"源文件不存在: {file_id}"}}
            return

        if not llm_service:
            yield {"event": "error", "data": {"message": "LLM服务不可用"}}
            return

        try:
            workflow = FileReviewWorkflow(
                service=self,
                project=project,
                file=file,
                writing_notes=writing_notes,
                llm_service=llm_service,
                prompt_service=prompt_service,
                vector_store=vector_store,
                user_id=user_id,
                commit=True,
                progress_messages={
                    "preparing": "准备提示词...",
                    "rag": "已检索相关上下文...",
                    "generating": "正在生成审查Prompt...",
                    "saving": "保存结果...",
                    "indexing": "更新索引...",
                },
            )
            async for event in workflow.run_stream():
                yield event

        except Exception as e:
            logger.exception("文件审查Prompt生成失败: %s", str(e))
            yield {"event": "error", "data": {"message": str(e)}}

    async def save_review_prompt(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
        content: str,
    ) -> str:
        """
        保存审查Prompt内容

        Args:
            project_id: 项目ID
            user_id: 用户ID
            file_id: 文件ID
            content: 审查Prompt内容

        Returns:
            保存的内容
        """
        await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        file.review_prompt = content
        await self.session.flush()

        return content

    async def _build_review_system_prompt(self, prompt_service) -> str:
        """构建审查Prompt的系统提示词

        P0修复: 遵循CLAUDE.md规范，提示词加载失败时直接报错，不使用硬编码回退
        """
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

    # 以下为原硬编码模板，已废弃，仅保留作为参考
    # 如需恢复，请在 backend/prompts/coding/ 目录创建 file_review_generation.md
    _DEPRECATED_REVIEW_TEMPLATE = """你是一位资深软件质量工程师，擅长编写清晰、完整的代码审查和测试Prompt。

输出原则：
1. 可直接使用：输出的内容是可以直接复制给AI编程助手使用的审查/测试Prompt
2. 覆盖全面：涵盖功能测试、边界测试、异常处理、性能考虑
3. 实践导向：基于文件的实际实现Prompt，给出具体的测试点
4. 格式清晰：使用Markdown格式，结构化展示

输出模板：
# {文件名} - 审查与测试指南

## 代码审查要点

### 1. 功能完整性
{检查实现是否覆盖了所有功能需求}

### 2. 代码质量
{代码风格、可读性、可维护性检查点}

### 3. 错误处理
{异常处理、边界条件检查点}

### 4. 性能考虑
{性能相关的检查点}

## 单元测试用例

### 正常流程测试
{列出需要测试的正常使用场景}

### 边界条件测试
{列出边界值和特殊情况测试}

### 异常处理测试
{列出错误处理和异常情况测试}

## 集成测试建议

{与其他模块的集成测试点}

## 测试数据建议

{推荐的测试数据和mock方案}

直接输出Markdown格式，不要任何前缀说明。"""

    async def _build_prompt_input_data(
        self,
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str],
        include_module: bool,
        include_tech_constraints: bool,
    ) -> Dict[str, Any]:
        """构建用户提示词输入数据"""
        from ...serializers.coding_serializer import CodingSerializer

        # 获取蓝图信息
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
                module = await self.module_repo.get_by_project_and_number(
                    file.project_id,
                    file.module_number
                )
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
            arch_content = join_prompt_lines([
                item["content"] for item in rag_context["architecture"]
            ])
            if arch_content:
                rag_parts.append(build_prompt_section("架构设计参考", arch_content, level=3))

        if rag_context.get("tech_stack"):
            tech_content = join_prompt_lines([
                item["content"] for item in rag_context["tech_stack"]
            ])
            if tech_content:
                rag_parts.append(build_prompt_section("技术栈参考", tech_content, level=3))

        if include_modules and rag_context.get("modules"):
            mod_content = join_prompt_lines([
                item["content"] for item in rag_context["modules"]
            ])
            if mod_content:
                rag_parts.append(build_prompt_section("相关模块", mod_content, level=3))

        if rag_context.get("features"):
            feat_content = join_prompt_lines([
                item["content"] for item in rag_context["features"]
            ])
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
                rag_parts.append(build_prompt_section(
                    "相关文件参考",
                    "\n\n".join(file_parts),
                    level=3,
                ))

        if not rag_parts:
            return ""

        return build_prompt_block(title, rag_parts)

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

        # 构建实现Prompt部分
        impl_section = ""
        if file.selected_version_id and file.selected_version:
            implementation_prompt = file.selected_version.content
            # 截取实现Prompt的关键部分
            impl_section = f"\n\n## 文件实现Prompt（参考）\n\n{implementation_prompt[:2000]}"

        # 构建RAG上下文部分
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

    async def _ingest_review_prompt(
        self,
        file: CodingSourceFile,
        content: str,
        vector_store: Any,
        llm_service: Any,
        user_id: int,
    ) -> bool:
        """
        将审查Prompt入库到向量库

        Args:
            file: 源文件对象
            content: 审查Prompt内容
            vector_store: 向量存储服务
            llm_service: LLM服务
            user_id: 用户ID

        Returns:
            是否入库成功
        """
        if not vector_store or not llm_service or not content:
            return False

        try:
            from ..coding_rag.content_splitter import ContentSplitter

            # 使用ContentSplitter分块
            splitter = ContentSplitter()
            records = splitter.split_content(
                content=content,
                data_type=CodingDataType.REVIEW_PROMPT,
                source_id=str(file.id),
                project_id=file.project_id,
                filename=file.filename,
                file_path=file.file_path,
                parent_title=f"{file.file_path} - 审查",
            )

            if not records:
                return False

            # 批量生成embedding并入库
            for record in records:
                embedding = await llm_service.get_embedding(
                    record.content,
                    user_id=user_id
                )
                if not embedding:
                    continue

                chunk_id = record.get_chunk_id()
                metadata = {
                    **record.metadata,
                    "data_type": record.data_type.value,
                    "paragraph_hash": record.get_content_hash(),
                    "length": len(record.content),
                    "source_id": record.source_id,
                    "is_file_review": True,
                }

                await vector_store.upsert_chunks(records=[{
                    "id": chunk_id,
                    "project_id": file.project_id,
                    "chapter_number": file.module_number or 0,
                    "chunk_index": record.metadata.get("section_index", 0),
                    "chapter_title": f"{file.file_path} - 审查",
                    "content": record.content,
                    "embedding": embedding,
                    "metadata": metadata,
                }])

            logger.info(
                "文件审查Prompt入库完成: file=%s chunks=%d",
                file.filename, len(records)
            )
            return True

        except Exception as e:
            logger.warning("文件审查Prompt入库失败: file=%s error=%s", file.filename, str(e))
            return False

    # ------------------------------------------------------------------
    # 内容保存
    # ------------------------------------------------------------------

    async def save_content(
        self,
        project_id: str,
        user_id: int,
        file_id: int,
        content: str,
        version_label: Optional[str] = None,
    ) -> CodingFileVersion:
        """
        保存文件内容（编辑后创建新版本）

        Args:
            project_id: 项目ID
            user_id: 用户ID
            file_id: 文件ID
            content: 内容
            version_label: 版本标签

        Returns:
            保存的版本
        """
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
        """
        选择文件版本

        Args:
            project_id: 项目ID
            user_id: 用户ID
            file_id: 文件ID
            version_id: 版本ID

        Returns:
            更新后的文件
        """
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
        """
        获取文件的所有版本

        Args:
            project_id: 项目ID
            user_id: 用户ID
            file_id: 文件ID

        Returns:
            版本列表
        """
        await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        versions = await self.version_repo.get_by_file(file_id)

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
        ]

    # ------------------------------------------------------------------
    # 文件CRUD
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
        from ...repositories.coding_files_repository import CodingDirectoryNodeRepository

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
        from ...repositories.coding_files_repository import CodingDirectoryNodeRepository

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

    # ------------------------------------------------------------------
    # 自动入库
    # ------------------------------------------------------------------

    async def _ingest_file_prompt(
        self,
        file: CodingSourceFile,
        content: str,
        vector_store: Any,
        llm_service: Any,
        user_id: int,
    ) -> bool:
        """
        将生成的文件Prompt入库到向量库

        Args:
            file: 源文件对象
            content: Prompt内容
            vector_store: 向量存储服务
            llm_service: LLM服务
            user_id: 用户ID

        Returns:
            是否入库成功
        """
        if not vector_store or not llm_service or not content:
            return False

        try:
            from ..coding_rag.content_splitter import ContentSplitter

            # 使用ContentSplitter分块
            splitter = ContentSplitter()
            records = splitter.split_file_prompt(
                content=content,
                file_id=str(file.id),
                filename=file.filename,
                file_path=file.file_path,
                project_id=file.project_id,
                module_number=file.module_number,
                system_number=file.system_number,
                file_type=file.file_type,
                language=file.language,
            )

            if not records:
                return False

            # 批量生成embedding并入库
            for record in records:
                embedding = await llm_service.get_embedding(
                    record.content,
                    user_id=user_id
                )
                if not embedding:
                    continue

                chunk_id = record.get_chunk_id()
                metadata = {
                    **record.metadata,
                    "data_type": record.data_type.value,
                    "paragraph_hash": record.get_content_hash(),
                    "length": len(record.content),
                    "source_id": record.source_id,
                }

                await vector_store.upsert_chunks(records=[{
                    "id": chunk_id,
                    "project_id": file.project_id,
                    "chapter_number": file.module_number or 0,
                    "chunk_index": record.metadata.get("section_index", 0),
                    "chapter_title": file.file_path or file.filename,
                    "content": record.content,
                    "embedding": embedding,
                    "metadata": metadata,
                }])

            logger.info(
                "文件Prompt入库完成: file=%s chunks=%d",
                file.filename, len(records)
            )
            return True

        except Exception as e:
            logger.warning("文件Prompt入库失败: file=%s error=%s", file.filename, str(e))
            return False

    # ------------------------------------------------------------------
    # RAG检索
    # ------------------------------------------------------------------

    async def _retrieve_rag_context(
        self,
        project_id: str,
        file: CodingSourceFile,
        vector_store: Any,
        llm_service: Any,
        user_id: int,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        检索与文件相关的RAG上下文

        使用文件信息构建查询，从向量库检索相关内容。

        Args:
            project_id: 项目ID
            file: 源文件对象
            vector_store: 向量存储服务
            llm_service: LLM服务（用于生成embedding）
            user_id: 用户ID
            top_k: 返回结果数量

        Returns:
            包含各类型上下文的字典
        """
        if not vector_store or not llm_service:
            return {}

        context = {
            "architecture": [],
            "modules": [],
            "tech_stack": [],
            "related_files": [],
        }

        try:
            # 构建查询文本：结合文件信息
            query_parts = []
            if file.filename:
                query_parts.append(file.filename)
            if file.description:
                query_parts.append(file.description)
            if file.purpose:
                query_parts.append(file.purpose)

            query_text = build_query_text(
                query_parts,
                file.file_path or "file implementation",
            )

            # 获取查询embedding
            query_embedding = await get_query_embedding(
                llm_service,
                query_text,
                user_id,
                logger=logger,
            )

            if not query_embedding:
                logger.warning("无法获取查询embedding")
                return context

            # 执行向量检索
            results = await vector_store.search(
                project_id=project_id,
                query_embedding=query_embedding,
                top_k=top_k * 2,  # 多检索一些，后面按类型过滤
            )

            # 按数据类型分类结果
            for result in results:
                metadata = result.get("metadata", {})
                data_type = metadata.get("data_type", "")
                content = result.get("content", "")
                score = result.get("score", 0)

                # 只保留相关度较高的结果
                if score < 0.5:
                    continue

                if data_type == CodingDataType.ARCHITECTURE.value:
                    context["architecture"].append({
                        "content": content[:500],
                        "score": score,
                    })
                elif data_type == CodingDataType.MODULE.value:
                    context["modules"].append({
                        "content": content[:300],
                        "module_number": metadata.get("module_number"),
                        "score": score,
                    })
                elif data_type == CodingDataType.TECH_STACK.value:
                    context["tech_stack"].append({
                        "content": content[:300],
                        "score": score,
                    })
                elif data_type == CodingDataType.FILE_PROMPT.value:
                    # 其他已生成的文件Prompt作为参考
                    if metadata.get("file_path") != file.file_path:
                        context["related_files"].append({
                            "file_path": metadata.get("file_path", ""),
                            "content": content[:400],
                            "score": score,
                        })

            # 按分数排序并限制数量
            for key in context:
                context[key] = sorted(
                    context[key],
                    key=lambda x: x.get("score", 0),
                    reverse=True
                )[:3]

            logger.info(
                "RAG检索完成: file=%s arch=%d mod=%d tech=%d related=%d",
                file.filename,
                len(context["architecture"]),
                len(context["modules"]),
                len(context["tech_stack"]),
                len(context["related_files"]),
            )

            return context

        except Exception as e:
            logger.warning("RAG检索失败: %s", str(e))
            return context

    # ------------------------------------------------------------------
    # 提示词构建
    # ------------------------------------------------------------------

    async def _build_system_prompt(self, prompt_service) -> str:
        """构建系统提示词

        P0修复: 遵循CLAUDE.md规范，提示词加载失败时直接报错，不使用硬编码回退
        """
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

    # 以下为原硬编码模板，已废弃，仅保留作为参考
    # 如需恢复，请在 backend/prompts/coding/ 目录创建 file_prompt_generation.md
    _DEPRECATED_PROMPT_TEMPLATE = """你是一位资深软件工程师，擅长编写清晰、完整的功能实现Prompt。

输出原则：
1. 可直接使用：输出的内容是可以直接复制给AI编程助手使用的Prompt
2. 描述清晰：说明文件的作用、解决什么问题
3. 实现明确：描述核心算法和实现思路
4. 接口规范：明确类、函数签名、参数、返回值
5. 使用Markdown格式，不要输出JSON

输出模板：
# {文件名}

## 文件描述
{这个文件做什么，解决什么问题，2-3句话}

## 主要功能
{列出该文件需要实现的主要功能点}

## 实现思路
{核心算法或实现方案，为什么选择这个方案}

## 接口定义
{完整的类和函数签名，参数说明，返回值}

## 实现步骤
{分步骤的实现指导}

## 依赖关系
{需要导入的模块，与其他文件的关系}

## 注意事项
{实现注意点，性能优化，安全考虑}

直接输出Markdown格式，不要任何前缀说明。"""

    async def _build_user_prompt(
        self,
        project,
        file: CodingSourceFile,
        writing_notes: Optional[str] = None,
        rag_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建用户提示词（支持RAG上下文）"""
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
