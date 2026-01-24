"""
部分大纲上下文检索器

负责为部分章节大纲生成检索相关的上下文信息。
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..chapter_context_service import ChapterContextService

if TYPE_CHECKING:
    from ..llm_service import LLMService
    from ..vector_store_service import VectorStoreService
    from ...repositories.chapter_repository import ChapterOutlineRepository

logger = logging.getLogger(__name__)


class PartOutlineContextRetriever:
    """
    部分大纲上下文检索器

    负责为部分章节大纲生成检索相关的已完成章节内容和历史章节大纲。
    """

    def __init__(
        self,
        chapter_outline_repo: "ChapterOutlineRepository",
        llm_service: "LLMService",
        vector_store: Optional["VectorStoreService"] = None,
    ):
        """
        初始化上下文检索器

        Args:
            chapter_outline_repo: 章节大纲仓库
            llm_service: LLM服务（用于生成嵌入向量）
            vector_store: 向量存储服务（可选）
        """
        self.chapter_outline_repo = chapter_outline_repo
        self.llm_service = llm_service
        self.vector_store = vector_store
        self._chapter_context_service = ChapterContextService(
            llm_service=llm_service,
            vector_store=vector_store,
        )

    async def get_previous_chapters(
        self,
        project_id: str,
        current_chapter: int,
    ) -> List[Dict]:
        """
        获取前面已生成的章节大纲（用于上下文）

        Args:
            project_id: 项目ID
            current_chapter: 当前章节号

        Returns:
            List[Dict]: 前面章节的大纲数据列表
        """
        # 查询所有在当前章节之前的章节大纲
        all_outlines = await self.chapter_outline_repo.list_by_project(project_id)

        # 筛选出当前章节之前的章节
        previous_chapters = [
            {
                "chapter_number": outline.chapter_number,
                "title": outline.title,
                "summary": outline.summary,
            }
            for outline in all_outlines
            if outline.chapter_number < current_chapter
        ]

        # 按章节号排序
        previous_chapters.sort(key=lambda x: x["chapter_number"])

        return previous_chapters

    async def retrieve_relevant_summaries(
        self,
        project_id: str,
        user_id: int,
        start_chapter: int,
        end_chapter: int,
        part_summary: str,
    ) -> List[Dict[str, Any]]:
        """
        为部分章节大纲生成检索相关的已完成章节内容

        Args:
            project_id: 项目ID
            user_id: 用户ID
            start_chapter: 部分起始章节号
            end_chapter: 部分结束章节号
            part_summary: 部分大纲的摘要（用于构建查询）

        Returns:
            相关摘要列表
        """
        if not self.vector_store:
            return []

        try:
            # 构建查询文本：使用部分大纲的摘要 + 章节范围描述
            query_text = f"第{start_chapter}到第{end_chapter}章的故事发展。{part_summary[:500]}"

            rag_context = await self._chapter_context_service.retrieve_for_generation(
                project_id=project_id,
                query_text=query_text,
                user_id=user_id,
                top_k_chunks=0,
                top_k_summaries=5,
            )

            summaries = rag_context.summaries

            # 过滤：只保留起始章节之前的已完成章节
            summaries = [s for s in summaries if s.chapter_number < start_chapter]

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
                "项目 %s 部分章节大纲生成RAG检索完成: 检索到 %d 个相关摘要（第 %d-%d 章）",
                project_id,
                len(result),
                start_chapter,
                end_chapter,
            )
            return result

        except Exception as exc:
            # RAG检索失败不应阻断主流程，记录详细错误后返回空列表
            logger.warning(
                "项目 %s 部分章节大纲生成RAG检索失败（将使用空上下文继续）: error_type=%s error=%s",
                project_id,
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            return []


__all__ = [
    "PartOutlineContextRetriever",
]
