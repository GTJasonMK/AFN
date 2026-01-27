"""
大纲RAG检索器

统一处理章节大纲和部分大纲生成时的RAG检索逻辑，
从已完成章节中检索相关内容，确保新生成的大纲与已有内容保持一致。
"""

import logging
from typing import Any, Dict, List, Optional

from ..chapter_context_service import ChapterContextService
from ..vector_store_service import VectorStoreService
from ..llm_service import LLMService

logger = logging.getLogger(__name__)


class OutlineRAGRetriever:
    """
    大纲RAG检索器

    为大纲生成（章节大纲、部分大纲）提供统一的RAG检索接口。
    检索已完成章节的摘要，确保新大纲与已有内容保持一致。
    """

    def __init__(
        self,
        vector_store: VectorStoreService,
        llm_service: LLMService,
        top_k: int = 5,
    ):
        """
        Args:
            vector_store: 向量库服务
            llm_service: LLM服务（用于生成查询向量）
            top_k: 检索返回的最大结果数
        """
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.top_k = top_k
        self._chapter_context_service = ChapterContextService(
            llm_service=llm_service,
            vector_store=vector_store,
        )

    async def retrieve_for_chapter_outline(
        self,
        project_id: str,
        user_id: int,
        start_chapter: int,
        end_chapter: int,
        context_text: str,
    ) -> List[Dict[str, Any]]:
        """
        为章节大纲生成检索相关的已完成章节内容

        Args:
            project_id: 项目ID
            user_id: 用户ID
            start_chapter: 起始章节号
            end_chapter: 结束章节号
            context_text: 上下文文本（如蓝图摘要、部分大纲摘要等）

        Returns:
            相关摘要列表，每项包含:
            - chapter_number: 章节号
            - title: 章节标题
            - summary: 章节摘要
            - relevance_score: 相关性分数
        """
        return await self._retrieve_relevant_summaries(
            project_id=project_id,
            user_id=user_id,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            context_text=context_text,
            filter_before_chapter=start_chapter,
        )

    async def retrieve_for_part_outline(
        self,
        project_id: str,
        user_id: int,
        start_chapter: int,
        end_chapter: int,
        part_summary: str,
    ) -> List[Dict[str, Any]]:
        """
        为部分大纲的章节生成检索相关的已完成章节内容

        Args:
            project_id: 项目ID
            user_id: 用户ID
            start_chapter: 部分起始章节号
            end_chapter: 部分结束章节号
            part_summary: 部分大纲的摘要

        Returns:
            相关摘要列表
        """
        return await self._retrieve_relevant_summaries(
            project_id=project_id,
            user_id=user_id,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            context_text=part_summary,
            filter_before_chapter=start_chapter,
        )

    @staticmethod
    def _build_query_text(*, start_chapter: int, end_chapter: int, context_text: str) -> str:
        """统一构建检索 query_text，确保范围描述只拼接一次。"""
        return f"第{start_chapter}到第{end_chapter}章的故事发展。{(context_text or '')[:500]}"

    async def _retrieve_relevant_summaries(
        self,
        project_id: str,
        user_id: int,
        start_chapter: int,
        end_chapter: int,
        context_text: str,
        filter_before_chapter: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        内部方法：检索相关的章节摘要

        Args:
            project_id: 项目ID
            user_id: 用户ID
            start_chapter: 起始章节号
            end_chapter: 结束章节号
            context_text: 用于构建查询的上下文文本
            filter_before_chapter: 只保留此章节号之前的结果

        Returns:
            相关摘要列表
        """
        try:
            query_text = self._build_query_text(
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                context_text=context_text,
            )

            rag_context = await self._chapter_context_service.retrieve_for_generation(
                project_id=project_id,
                query_text=query_text,
                user_id=user_id,
                top_k_chunks=0,
                top_k_summaries=self.top_k,
            )

            summaries = rag_context.summaries

            # 过滤：只保留指定章节之前的已完成章节
            if filter_before_chapter is not None:
                summaries = [s for s in summaries if s.chapter_number < filter_before_chapter]

            # 格式化结果
            result = []
            for summary in summaries:
                result.append({
                    "chapter_number": summary.chapter_number,
                    "title": summary.title,
                    "summary": summary.summary,
                    "relevance_score": round(summary.score, 3) if summary.score else None,
                })

            logger.info(
                "项目 %s 大纲生成RAG检索完成: 检索到 %d 个相关摘要（第 %d-%d 章）",
                project_id,
                len(result),
                start_chapter,
                end_chapter,
            )
            return result

        except Exception as exc:
            logger.warning(
                "项目 %s 大纲生成RAG检索失败: %s",
                project_id,
                exc,
            )
            return []


async def get_outline_rag_retriever(
    vector_store: Optional[VectorStoreService],
    llm_service: LLMService,
) -> Optional[OutlineRAGRetriever]:
    """
    获取大纲RAG检索器实例

    如果向量库服务不可用，返回None。

    Args:
        vector_store: 向量库服务（可选）
        llm_service: LLM服务

    Returns:
        OutlineRAGRetriever实例，或None
    """
    if vector_store is None:
        return None

    return OutlineRAGRetriever(
        vector_store=vector_store,
        llm_service=llm_service,
    )
