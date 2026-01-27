"""
文件 Prompt 子模块：审查 Prompt（ReviewMixin）

拆分自 `backend/app/services/coding_files/file_prompt_service.py`。
"""

import logging
from typing import Any, AsyncGenerator, Dict, Optional

from ....exceptions import InvalidParameterError, ResourceNotFoundError
from ....models.coding_files import CodingSourceFile
from .workflows import FileReviewWorkflow

logger = logging.getLogger(__name__)


class ReviewMixin:
    """审查 Prompt 生成与保存能力"""

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
        """为文件生成审查Prompt（非流式）"""
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
        """为文件生成审查Prompt（流式）"""
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
        """保存审查Prompt内容"""
        await self._project_service.ensure_project_owner(project_id, user_id)

        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise ResourceNotFoundError("源文件", str(file_id))

        file.review_prompt = content
        await self.session.flush()

        return content


__all__ = ["ReviewMixin"]

