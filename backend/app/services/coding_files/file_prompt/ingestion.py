"""
文件 Prompt 子模块：向量入库（IngestionMixin）

拆分自 `backend/app/services/coding_files/file_prompt_service.py`，并收敛入库循环模板以降低重复。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

from ....models.coding_files import CodingSourceFile
from ...coding_rag.data_types import CodingDataType

logger = logging.getLogger(__name__)


class IngestionMixin:
    """向量入库能力（file_prompt / review_prompt）"""

    async def _upsert_records_with_embeddings(
        self,
        *,
        file: CodingSourceFile,
        records: Iterable[Any],
        vector_store: Any,
        llm_service: Any,
        user_id: int,
        chapter_title: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """将 records 逐条生成 embedding 并 upsert 到向量库（共享模板）"""
        for record in records:
            embedding = await llm_service.get_embedding(record.content, user_id=user_id)
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
            if extra_metadata:
                metadata.update(extra_metadata)

            await vector_store.upsert_chunks(
                records=[
                    {
                        "id": chunk_id,
                        "project_id": file.project_id,
                        "chapter_number": file.module_number or 0,
                        "chunk_index": record.metadata.get("section_index", 0),
                        "chapter_title": chapter_title,
                        "content": record.content,
                        "embedding": embedding,
                        "metadata": metadata,
                    }
                ]
            )

    async def _ingest_review_prompt(
        self,
        file: CodingSourceFile,
        content: str,
        vector_store: Any,
        llm_service: Any,
        user_id: int,
    ) -> bool:
        """将审查Prompt入库到向量库"""
        if not vector_store or not llm_service or not content:
            return False

        try:
            from ...coding_rag.content_splitter import ContentSplitter

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

            await self._upsert_records_with_embeddings(
                file=file,
                records=records,
                vector_store=vector_store,
                llm_service=llm_service,
                user_id=user_id,
                chapter_title=f"{file.file_path} - 审查",
                extra_metadata={"is_file_review": True},
            )

            logger.info("文件审查Prompt入库完成: file=%s chunks=%d", file.filename, len(records))
            return True

        except Exception as e:
            logger.warning("文件审查Prompt入库失败: file=%s error=%s", file.filename, str(e))
            return False

    async def _ingest_file_prompt(
        self,
        file: CodingSourceFile,
        content: str,
        vector_store: Any,
        llm_service: Any,
        user_id: int,
    ) -> bool:
        """将生成的文件Prompt入库到向量库"""
        if not vector_store or not llm_service or not content:
            return False

        try:
            from ...coding_rag.content_splitter import ContentSplitter

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

            await self._upsert_records_with_embeddings(
                file=file,
                records=records,
                vector_store=vector_store,
                llm_service=llm_service,
                user_id=user_id,
                chapter_title=file.file_path or file.filename,
            )

            logger.info("文件Prompt入库完成: file=%s chunks=%d", file.filename, len(records))
            return True

        except Exception as e:
            logger.warning("文件Prompt入库失败: file=%s error=%s", file.filename, str(e))
            return False


__all__ = ["IngestionMixin"]

