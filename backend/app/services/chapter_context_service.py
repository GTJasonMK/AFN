from __future__ import annotations

"""
章节上下文组装服务：负责调用向量库检索上下文，并对结果做基础格式化。

本模块包含两个服务：
1. ChapterContextService: 基础版本，保持向后兼容
2. EnhancedChapterContextService: 增强版本，集成时序感知检索和智能上下文构建

所有关键步骤均包含中文注释，方便团队理解 RAG 流程。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.config import settings
from ..services.llm_service import LLMService
from ..schemas.novel import ChapterAnalysisData
from .vector_store_service import RetrievedChunk, RetrievedSummary, VectorStoreService

# 导入增强RAG模块
from .rag import (
    EnhancedQueryBuilder,
    EnhancedQuery,
    TemporalAwareRetriever,
    SmartContextBuilder,
    GenerationContext,
    ContextCompressor,
)
from .rag.context_builder import BlueprintInfo, RAGContext

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

        # 不再传入model参数，完全使用数据库中激活的嵌入配置
        embedding = await self._llm_service.get_embedding(query, user_id=user_id)
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


@dataclass
class EnhancedRAGContext:
    """增强型RAG上下文结果

    包含原始检索结果和经过智能处理的生成上下文
    """
    # 原始查询信息
    enhanced_query: EnhancedQuery
    # 检索结果
    chunks: List[RetrievedChunk] = field(default_factory=list)
    summaries: List[RetrievedSummary] = field(default_factory=list)
    # 智能构建的上下文
    generation_context: Optional[GenerationContext] = None
    # 压缩后的上下文文本
    compressed_context: str = ""

    def get_context_text(self) -> str:
        """获取用于生成的上下文文本"""
        return self.compressed_context

    def get_legacy_context(self) -> ChapterRAGContext:
        """转换为旧版上下文格式，保持向后兼容"""
        return ChapterRAGContext(
            query=self.enhanced_query.main_query,
            chunks=self.chunks,
            summaries=self.summaries,
        )


class EnhancedChapterContextService:
    """增强型章节上下文服务

    集成以下增强功能：
    1. 多维查询构建：从大纲中提取角色、伏笔等多维度查询
    2. 时序感知检索：优先返回时间上接近的内容
    3. 智能上下文构建：分层组织上下文（必需/重要/参考）
    4. 上下文压缩：在token限制内智能裁剪

    使用方式：
        service = EnhancedChapterContextService(llm_service, vector_store)
        context = await service.retrieve_enhanced_context(
            project_id=project_id,
            chapter_number=chapter_number,
            outline=outline,
            blueprint_info=blueprint_info,
            ...
        )
        prompt_context = context.get_context_text()
    """

    def __init__(
        self,
        *,
        llm_service: LLMService,
        vector_store: Optional[VectorStoreService] = None,
        # 时序检索参数
        recency_weight: float = 0.3,
        similarity_weight: float = 0.7,
        nearby_bonus: float = 0.15,
        nearby_range: int = 5,
        # 上下文压缩参数
        max_context_tokens: int = 4000,
    ) -> None:
        self._llm_service = llm_service
        self._vector_store = vector_store

        # 初始化各组件
        self._query_builder = EnhancedQueryBuilder()

        if vector_store:
            self._temporal_retriever = TemporalAwareRetriever(
                vector_store=vector_store,
                recency_weight=recency_weight,
                similarity_weight=similarity_weight,
                nearby_bonus=nearby_bonus,
                nearby_range=nearby_range,
            )
        else:
            self._temporal_retriever = None

        self._context_builder = SmartContextBuilder()
        self._compressor = ContextCompressor(max_context_tokens=max_context_tokens)

        # 保留基础服务用于回退
        self._basic_service = ChapterContextService(
            llm_service=llm_service,
            vector_store=vector_store,
        )

    async def retrieve_enhanced_context(
        self,
        *,
        project_id: str,
        chapter_number: int,
        total_chapters: int,
        outline: Dict[str, Any],
        user_id: int,
        blueprint_info: Optional[BlueprintInfo] = None,
        prev_chapter_analysis: Optional[ChapterAnalysisData] = None,
        pending_foreshadowing: Optional[List[Dict[str, Any]]] = None,
        writing_notes: Optional[str] = None,
        top_k_chunks: int = 10,
        top_k_summaries: int = 5,
    ) -> EnhancedRAGContext:
        """检索增强型上下文

        Args:
            project_id: 项目ID
            chapter_number: 当前章节号
            total_chapters: 小说总章节数
            outline: 章节大纲 {"chapter_number", "title", "summary"}
            user_id: 用户ID（用于获取embedding）
            blueprint_info: 蓝图信息
            prev_chapter_analysis: 前一章分析数据
            pending_foreshadowing: 待回收的伏笔列表
            writing_notes: 用户写作指令
            top_k_chunks: 检索chunk数量
            top_k_summaries: 检索摘要数量

        Returns:
            EnhancedRAGContext: 增强型上下文结果
        """
        # 1. 构建增强查询
        blueprint_characters = []
        if blueprint_info:
            blueprint_characters = blueprint_info.characters

        enhanced_query = self._query_builder.build_queries(
            outline=outline,
            blueprint_characters=blueprint_characters,
            prev_chapter_analysis=prev_chapter_analysis,
            pending_foreshadowing=pending_foreshadowing,
            writing_notes=writing_notes,
        )

        logger.debug(
            "构建增强查询完成: project=%s chapter=%d queries=%d",
            project_id, chapter_number, len(enhanced_query.get_all_queries()),
        )

        # 2. 检索（如果向量库可用）
        chunks: List[RetrievedChunk] = []
        summaries: List[RetrievedSummary] = []

        if settings.vector_store_enabled and self._temporal_retriever:
            # 获取主查询的embedding（使用数据库中激活的嵌入配置）
            main_embedding = await self._llm_service.get_embedding(
                enhanced_query.main_query,
                user_id=user_id,
            )

            if main_embedding:
                # 使用时序感知检索
                chunks = await self._temporal_retriever.retrieve_chunks_with_temporal(
                    project_id=project_id,
                    query_embedding=main_embedding,
                    target_chapter=chapter_number,
                    total_chapters=total_chapters,
                    top_k=top_k_chunks,
                )

                summaries = await self._temporal_retriever.retrieve_summaries_with_temporal(
                    project_id=project_id,
                    query_embedding=main_embedding,
                    target_chapter=chapter_number,
                    total_chapters=total_chapters,
                    top_k=top_k_summaries,
                )

                logger.info(
                    "时序感知检索完成: project=%s chapter=%d chunks=%d summaries=%d",
                    project_id, chapter_number, len(chunks), len(summaries),
                )

                # 如果有角色查询，补充检索
                if enhanced_query.character_queries and len(chunks) < top_k_chunks:
                    await self._supplement_character_retrieval(
                        project_id=project_id,
                        character_queries=enhanced_query.character_queries,
                        chapter_number=chapter_number,
                        total_chapters=total_chapters,
                        user_id=user_id,
                        existing_chunks=chunks,
                        max_additional=min(3, top_k_chunks - len(chunks)),
                    )

        # 3. 构建智能上下文
        generation_context = None
        if blueprint_info:
            rag_context = RAGContext(chunks=chunks, summaries=summaries)
            generation_context = self._context_builder.build_generation_context(
                outline=outline,
                blueprint=blueprint_info,
                rag_context=rag_context,
                prev_chapter_analysis=prev_chapter_analysis,
                pending_foreshadowing=pending_foreshadowing,
            )

        # 4. 压缩上下文
        compressed_context = ""
        if generation_context:
            compressed_context = self._compressor.compress_context(generation_context)
            logger.debug(
                "上下文压缩完成: project=%s chapter=%d length=%d",
                project_id, chapter_number, len(compressed_context),
            )

        return EnhancedRAGContext(
            enhanced_query=enhanced_query,
            chunks=chunks,
            summaries=summaries,
            generation_context=generation_context,
            compressed_context=compressed_context,
        )

    async def _supplement_character_retrieval(
        self,
        project_id: str,
        character_queries: List[str],
        chapter_number: int,
        total_chapters: int,
        user_id: int,
        existing_chunks: List[RetrievedChunk],
        max_additional: int,
    ) -> None:
        """补充角色相关的检索结果

        当主查询结果不足时，使用角色查询补充检索
        """
        if not self._temporal_retriever or max_additional <= 0:
            return

        existing_contents = {c.content[:100] for c in existing_chunks}

        for char_query in character_queries[:2]:  # 最多处理2个角色查询
            # 使用数据库中激活的嵌入配置
            char_embedding = await self._llm_service.get_embedding(
                char_query, user_id=user_id,
            )
            if not char_embedding:
                continue

            char_chunks = await self._temporal_retriever.retrieve_chunks_with_temporal(
                project_id=project_id,
                query_embedding=char_embedding,
                target_chapter=chapter_number,
                total_chapters=total_chapters,
                top_k=3,
            )

            # 去重并添加
            for chunk in char_chunks:
                if chunk.content[:100] not in existing_contents:
                    existing_chunks.append(chunk)
                    existing_contents.add(chunk.content[:100])
                    if len(existing_chunks) >= max_additional:
                        return

    async def retrieve_basic_context(
        self,
        *,
        project_id: str,
        query_text: str,
        user_id: int,
        top_k_chunks: Optional[int] = None,
        top_k_summaries: Optional[int] = None,
    ) -> ChapterRAGContext:
        """回退到基础检索

        当不需要增强功能或缺少必要参数时使用
        """
        return await self._basic_service.retrieve_for_generation(
            project_id=project_id,
            query_text=query_text,
            user_id=user_id,
            top_k_chunks=top_k_chunks,
            top_k_summaries=top_k_summaries,
        )


__all__ = [
    "ChapterContextService",
    "ChapterRAGContext",
    "EnhancedChapterContextService",
    "EnhancedRAGContext",
]
