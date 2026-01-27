"""
文件 Prompt 生成工作流（拆分自 file_prompt_service.py）

目标：将“工作流骨架”与“服务实现细节”解耦到不同文件，降低单文件复杂度。
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Callable, Dict, Optional

from ....models.coding_files import CodingFileVersion, CodingSourceFile
from ...evaluation_workflow_base import EvaluationPromptContext, EvaluationWorkflowBase
from ...workflow_base import GenerationWorkflowBase

logger = logging.getLogger(__name__)


class FileReviewWorkflow(EvaluationWorkflowBase):
    """文件审查 Prompt 生成工作流"""

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
        from ....core.config import settings

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
        from ....core.config import settings

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
    """文件 Prompt 生成工作流"""

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
        complete_builder: Optional[
            Callable[[CodingSourceFile, Optional[CodingFileVersion], str], Dict[str, Any]]
        ] = None,
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


__all__ = ["FileReviewWorkflow", "FilePromptGenerationWorkflow"]

