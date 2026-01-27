"""
文件 Prompt 子模块：RAG 上下文检索（RagMixin）

拆分自 `backend/app/services/coding_files/file_prompt_service.py`。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ....models.coding_files import CodingSourceFile
from ....utils.rag_helpers import build_query_text, get_query_embedding
from ...coding_rag.data_types import CodingDataType

logger = logging.getLogger(__name__)


class RagMixin:
    """RAG 检索能力"""

    async def _retrieve_rag_context(
        self,
        project_id: str,
        file: CodingSourceFile,
        vector_store: Any,
        llm_service: Any,
        user_id: int,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """检索与文件相关的RAG上下文"""
        if not vector_store or not llm_service:
            return {}

        context = {
            "architecture": [],
            "modules": [],
            "tech_stack": [],
            "related_files": [],
        }

        try:
            query_parts = []
            if file.filename:
                query_parts.append(file.filename)
            if file.description:
                query_parts.append(file.description)
            if file.purpose:
                query_parts.append(file.purpose)

            query_text = build_query_text(query_parts, file.file_path or "file implementation")

            query_embedding = await get_query_embedding(
                llm_service,
                query_text,
                user_id,
                logger=logger,
            )

            if not query_embedding:
                logger.warning("无法获取查询embedding")
                return context

            results = await vector_store.search(
                project_id=project_id,
                query_embedding=query_embedding,
                top_k=top_k * 2,
            )

            for result in results:
                metadata = result.get("metadata", {})
                data_type = metadata.get("data_type", "")
                content = result.get("content", "")
                score = result.get("score", 0)

                if score < 0.5:
                    continue

                if data_type == CodingDataType.ARCHITECTURE.value:
                    context["architecture"].append({"content": content[:500], "score": score})
                elif data_type == CodingDataType.MODULE.value:
                    context["modules"].append(
                        {
                            "content": content[:300],
                            "module_number": metadata.get("module_number"),
                            "score": score,
                        }
                    )
                elif data_type == CodingDataType.TECH_STACK.value:
                    context["tech_stack"].append({"content": content[:300], "score": score})
                elif data_type == CodingDataType.FILE_PROMPT.value:
                    if metadata.get("file_path") != file.file_path:
                        context["related_files"].append(
                            {
                                "file_path": metadata.get("file_path", ""),
                                "content": content[:400],
                                "score": score,
                            }
                        )

            for key in context:
                context[key] = sorted(context[key], key=lambda x: x.get("score", 0), reverse=True)[:3]

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


__all__ = ["RagMixin"]

