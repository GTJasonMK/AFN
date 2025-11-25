from __future__ import annotations

"""
章节上下文组装服务：负责调用向量库检索上下文，并对结果做基础格式化。

所有关键步骤均包含中文注释，方便团队理解 RAG 流程。
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from ..core.config import settings
from ..services.llm_service import LLMService
from .vector_store_service import RetrievedChunk, RetrievedSummary, VectorStoreService

logger = logging.getLogger(__name__)


@dataclass
class ChapterRAGContext:
    """封装检索得到的上下文结果。"""

    query: str
    chunks: List[RetrievedChunk]
    summaries: List[RetrievedSummary]

    def chunk_texts(self) -> List[str]:
        """将检索到的 chunk 转换成带序号的 Markdown 段落。"""
        lines = []
        for idx, chunk in enumerate(self.chunks, start=1):
            title = chunk.chapter_title or f"第{chunk.chapter_number}章"
            lines.append(
                f"### Chunk {idx}(来源：{title})\n{chunk.content.strip()}"
            )
        return lines

    def summary_lines(self) -> List[str]:
        """整理章节摘要，方便直接插入 Prompt。"""
        lines = []
        for summary in self.summaries:
            lines.append(
                f"- 第{summary.chapter_number}章 - {summary.title}:{summary.summary.strip()}"
            )
        return lines


class ChapterContextService:
    """章节上下文服务，整合查询、格式化与容错逻辑。"""

    def __init__(
        self,
        *,
        llm_service: LLMService,
        vector_store: Optional[VectorStoreService] = None,
    ) -> None:
        self._llm_service = llm_service
        self._vector_store = vector_store

    async def retrieve_for_generation(
        self,
        *,
        project_id: str,
        query_text: str,
        user_id: int,
        top_k_chunks: Optional[int] = None,
        top_k_summaries: Optional[int] = None,
    ) -> ChapterRAGContext:
        """
        根据章节摘要构造检索向量，并返回 RAG 上下文。

        Args:
            project_id: 项目ID
            query_text: 查询文本
            user_id: 用户ID
            top_k_chunks: 检索chunk数量（默认使用settings.vector_top_k_chunks）
            top_k_summaries: 检索摘要数量（默认使用settings.vector_top_k_summaries）

        Returns:
            ChapterRAGContext: 包含检索结果的上下文对象
        """
        query = self._normalize(query_text)
        if not settings.vector_store_enabled or not self._vector_store:
            logger.debug("向量库未启用或初始化失败，跳过检索: project=%s", project_id)
            return ChapterRAGContext(query=query, chunks=[], summaries=[])

        # 解析默认值：如果未指定则使用配置文件的值
        resolved_top_k_chunks = top_k_chunks if top_k_chunks is not None else settings.vector_top_k_chunks
        resolved_top_k_summaries = top_k_summaries if top_k_summaries is not None else settings.vector_top_k_summaries

        embedding_model = None if settings.embedding_provider == "ollama" else settings.embedding_model
        embedding = await self._llm_service.get_embedding(query, user_id=user_id, model=embedding_model)
        if not embedding:
            logger.warning("检索查询向量生成失败: project=%s chapter_query=%s", project_id, query)
            return ChapterRAGContext(query=query, chunks=[], summaries=[])

        chunks = await self._vector_store.query_chunks(
            project_id=project_id,
            embedding=embedding,
            top_k=resolved_top_k_chunks,
        )
        summaries = await self._vector_store.query_summaries(
            project_id=project_id,
            embedding=embedding,
            top_k=resolved_top_k_summaries,
        )
        logger.info(
            "章节上下文检索完成: project=%s chunks=%d summaries=%d query_preview=%s",
            project_id,
            len(chunks),
            len(summaries),
            query[:80],
        )
        return ChapterRAGContext(query=query, chunks=chunks, summaries=summaries)

    @staticmethod
    def _normalize(text: str) -> str:
        """统一压缩空白字符，避免影响检索效果。"""
        return " ".join(text.split())


__all__ = [
    "ChapterContextService",
    "ChapterRAGContext",
]
