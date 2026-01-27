"""
文件 Prompt 子模块：生成流程（GenerationMixin）

拆分自 `backend/app/services/coding_files/file_prompt_service.py`。
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Tuple

from ....exceptions import InvalidParameterError, ResourceNotFoundError
from ....models.coding_files import CodingFileVersion, CodingSourceFile
from .workflows import FilePromptGenerationWorkflow

logger = logging.getLogger(__name__)


class GenerationMixin:
    """文件 Prompt 生成（同步/流式）能力"""

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

        from ....core.config import settings

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

        from ....utils.json_utils import extract_llm_content

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

        from ....core.config import settings

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
        """为文件生成Prompt（非流式）"""
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
        """为文件生成Prompt（流式）"""
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


__all__ = ["GenerationMixin"]

