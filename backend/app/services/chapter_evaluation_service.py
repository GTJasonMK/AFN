"""
章节评估服务

封装章节版本评估的完整业务逻辑，包括：
- 前序章节上下文构建
- RAG检索增强
- LLM调用评估
- 评估结果处理

此服务遵循单一职责原则，专注于章节评估流程。
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.constants import LLMConstants
from ..models.novel import Chapter, ChapterEvaluation, ChapterOutline, NovelProject
from ..utils.json_utils import remove_think_tags, unwrap_markdown_json
from ..utils.rag_helpers import build_query_text, get_query_embedding
from .evaluation_workflow_base import EvaluationPromptContext, EvaluationWorkflowBase
from .llm_wrappers import call_llm, LLMProfile

if TYPE_CHECKING:
    from .llm_service import LLMService
    from .vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)


@dataclass
class EvaluationContext:
    """评估上下文数据"""

    completed_chapters: List[Dict[str, Any]]
    relevant_chunks: List[Dict[str, Any]]
    relevant_summaries: List[Dict[str, Any]]


class ChapterEvaluationWorkflow(EvaluationWorkflowBase):
    """章节评估工作流"""

    def __init__(
        self,
        service: "ChapterEvaluationService",
        project: NovelProject,
        chapter: Chapter,
        evaluator_prompt: str,
        user_id: int,
        versions_to_evaluate: List[Dict[str, Any]],
        blueprint_dict: Dict[str, Any],
    ):
        self._service = service
        self._project = project
        self._chapter = chapter
        self._evaluator_prompt = evaluator_prompt
        self._user_id = user_id
        self._versions_to_evaluate = versions_to_evaluate
        self._blueprint_dict = blueprint_dict
        self._context: Optional[EvaluationContext] = None
        self._failed = False

    async def _prepare_context(self) -> EvaluationPromptContext:
        context = await self._service.retrieve_evaluation_context(
            project=self._project,
            chapter_number=self._chapter.chapter_number,
            versions_to_evaluate=self._versions_to_evaluate,
            user_id=self._user_id,
        )
        self._context = context

        logger.info(
            "项目 %s 第 %s 章评估准备: 前序章节数=%d RAG片段=%d RAG摘要=%d",
            self._project.id,
            self._chapter.chapter_number,
            len(context.completed_chapters),
            len(context.relevant_chunks),
            len(context.relevant_summaries),
        )

        evaluator_payload = self._service.build_evaluation_payload(
            blueprint_dict=self._blueprint_dict,
            chapter_number=self._chapter.chapter_number,
            versions_to_evaluate=self._versions_to_evaluate,
            context=context,
        )

        rag_context = None
        if context.relevant_chunks or context.relevant_summaries:
            rag_context = {
                "relevant_chunks": context.relevant_chunks,
                "relevant_summaries": context.relevant_summaries,
            }

        return EvaluationPromptContext(
            system_prompt=self._evaluator_prompt,
            user_prompt=json.dumps(evaluator_payload, ensure_ascii=False),
            rag_context=rag_context,
        )

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        return await call_llm(
            self._service.llm_service,
            LLMProfile.EVALUATION,
            system_prompt=system_prompt,
            user_content=user_prompt,
            user_id=self._user_id,
        )

    async def _post_process(self, raw_content: str) -> str:
        evaluation_clean = remove_think_tags(raw_content)
        return unwrap_markdown_json(evaluation_clean)

    async def _handle_llm_error(self, exc: Exception) -> str:
        self._failed = True
        logger.error(
            "项目 %s 第 %s 章评估失败: %s",
            self._project.id,
            self._chapter.chapter_number,
            exc,
        )
        return json.dumps(
            {"error": "评估失败，请稍后重试", "details": str(exc)},
            ensure_ascii=False,
        )


class ChapterEvaluationService:
    """
    章节评估服务

    负责协调章节版本评估的完整流程，包括上下文构建、RAG检索、LLM调用等。
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service: "LLMService",
        vector_store: Optional["VectorStoreService"] = None,
    ):
        """
        初始化章节评估服务

        Args:
            session: 数据库会话
            llm_service: LLM服务实例
            vector_store: 向量库服务（可选，用于RAG检索）
        """
        self.session = session
        self.llm_service = llm_service
        self.vector_store = vector_store

    def build_completed_chapters_context(
        self,
        project: NovelProject,
        current_chapter_number: int,
    ) -> List[Dict[str, Any]]:
        """
        构建前序章节上下文

        获取当前章节之前所有已确认的章节信息，用于评估时的连贯性判断。

        Args:
            project: 项目对象
            current_chapter_number: 当前章节号

        Returns:
            前序章节列表，包含章节号、标题、摘要
        """
        completed_chapters = []

        # 使用字典映射优化查询效率
        outlines_map = {o.chapter_number: o for o in project.outlines}
        chapters_map = {c.chapter_number: c for c in project.chapters}

        for ch_num in sorted(outlines_map.keys()):
            if ch_num >= current_chapter_number:
                break

            outline = outlines_map.get(ch_num)
            chapter = chapters_map.get(ch_num)

            # 只包含已完成的章节（有选中版本）
            if chapter and chapter.selected_version_id:
                summary = (
                    chapter.real_summary
                    or (outline.summary if outline else None)
                    or "(无摘要)"
                )
                completed_chapters.append({
                    "chapter_number": ch_num,
                    "title": outline.title if outline else f"第{ch_num}章",
                    "summary": summary,
                })

        return completed_chapters

    async def retrieve_evaluation_context(
        self,
        project: NovelProject,
        chapter_number: int,
        versions_to_evaluate: List[Dict[str, Any]],
        user_id: int,
    ) -> EvaluationContext:
        """
        检索评估所需的上下文

        包括前序章节和RAG检索的相关内容。

        Args:
            project: 项目对象
            chapter_number: 当前章节号
            versions_to_evaluate: 待评估版本列表
            user_id: 用户ID

        Returns:
            EvaluationContext: 评估上下文
        """
        # 1. 构建前序章节上下文
        completed_chapters = self.build_completed_chapters_context(
            project, chapter_number
        )

        # 2. RAG检索
        relevant_chunks: List[Dict[str, Any]] = []
        relevant_summaries: List[Dict[str, Any]] = []

        if self.vector_store:
            try:
                # 构建查询文本
                outlines_map = {o.chapter_number: o for o in project.outlines}
                current_outline = outlines_map.get(chapter_number)

                outline_text = ""
                if current_outline:
                    outline_text = f"{current_outline.title}: {current_outline.summary or ''}"

                # 取第一个版本的开头作为查询补充
                first_version_preview = (
                    versions_to_evaluate[0]["content"][:800]
                    if versions_to_evaluate
                    else ""
                )
                query_text = build_query_text([outline_text, first_version_preview])

                if query_text:
                    # 生成查询向量
                    query_embedding = await get_query_embedding(
                        self.llm_service,
                        query_text,
                        user_id,
                        logger=logger,
                    )

                    if query_embedding:
                        # 检索相关历史片段
                        chunks = await self.vector_store.query_chunks(
                            project_id=project.id,
                            embedding=query_embedding,
                            top_k=5,
                        )
                        # 过滤：只保留当前章节之前的片段
                        chunks = [c for c in chunks if c.chapter_number < chapter_number]

                        # 检索相关摘要
                        summaries = await self.vector_store.query_summaries(
                            project_id=project.id,
                            embedding=query_embedding,
                            top_k=3,
                        )
                        # 过滤：只保留当前章节之前的摘要
                        summaries = [s for s in summaries if s.chapter_number < chapter_number]

                        # 格式化检索结果
                        for chunk in chunks:
                            relevant_chunks.append({
                                "chapter_number": chunk.chapter_number,
                                "chapter_title": chunk.chapter_title or f"第{chunk.chapter_number}章",
                                "content": chunk.content,
                                "relevance_score": round(chunk.score, 3) if chunk.score else None,
                            })

                        for summary in summaries:
                            relevant_summaries.append({
                                "chapter_number": summary.chapter_number,
                                "title": summary.title,
                                "summary": summary.summary,
                                "relevance_score": round(summary.score, 3) if summary.score else None,
                            })

                        logger.info(
                            "项目 %s 第 %s 章评估RAG检索完成: chunks=%d summaries=%d",
                            project.id,
                            chapter_number,
                            len(relevant_chunks),
                            len(relevant_summaries),
                        )

            except Exception as rag_exc:
                logger.warning(
                    "项目 %s 第 %s 章评估RAG检索失败，将使用基础上下文: %s",
                    project.id,
                    chapter_number,
                    rag_exc,
                )

        return EvaluationContext(
            completed_chapters=completed_chapters,
            relevant_chunks=relevant_chunks,
            relevant_summaries=relevant_summaries,
        )

    def build_evaluation_payload(
        self,
        blueprint_dict: Dict[str, Any],
        chapter_number: int,
        versions_to_evaluate: List[Dict[str, Any]],
        context: EvaluationContext,
    ) -> Dict[str, Any]:
        """
        构建评估请求payload

        Args:
            blueprint_dict: 蓝图数据
            chapter_number: 章节号
            versions_to_evaluate: 待评估版本
            context: 评估上下文

        Returns:
            评估payload字典
        """
        payload = {
            "novel_blueprint": blueprint_dict,
            "completed_chapters": context.completed_chapters,
            "content_to_evaluate": {
                "chapter_number": chapter_number,
                "versions": versions_to_evaluate,
            },
        }

        # 添加RAG检索结果
        if context.relevant_chunks or context.relevant_summaries:
            payload["relevant_context"] = {
                "description": "以下是通过语义检索找到的与待评估章节最相关的历史内容，可用于判断伏笔处理、人物一致性等",
                "relevant_chunks": context.relevant_chunks,
                "relevant_summaries": context.relevant_summaries,
            }

        return payload

    async def evaluate_chapter_versions(
        self,
        project: NovelProject,
        chapter: Chapter,
        evaluator_prompt: str,
        user_id: int,
    ) -> str:
        """
        评估章节的多个版本

        完整的评估流程，包括上下文构建、RAG检索、LLM调用。

        Args:
            project: 项目对象
            chapter: 章节对象
            evaluator_prompt: 评估提示词
            user_id: 用户ID

        Returns:
            评估结果JSON字符串
        """
        from .novel_service import NovelService

        # 1. 准备待评估版本
        versions_to_evaluate = [
            {"version_id": idx + 1, "content": version.content}
            for idx, version in enumerate(
                sorted(chapter.versions, key=lambda item: item.created_at)
            )
        ]

        # 2. 获取蓝图数据
        novel_service = NovelService(self.session)
        project_schema = await novel_service.get_project_schema(project.id, user_id)
        # Bug 13 修复: 检查蓝图是否存在
        if not project_schema.blueprint:
            return json.dumps(
                {"error": "项目缺少蓝图数据，无法进行评估", "details": "请先完成灵感对话生成蓝图"},
                ensure_ascii=False,
            )
        blueprint_dict = project_schema.blueprint.model_dump()

        workflow = ChapterEvaluationWorkflow(
            service=self,
            project=project,
            chapter=chapter,
            evaluator_prompt=evaluator_prompt,
            user_id=user_id,
            versions_to_evaluate=versions_to_evaluate,
            blueprint_dict=blueprint_dict,
        )
        evaluation_json = await workflow.run()

        if not workflow._failed:
            logger.info("项目 %s 第 %s 章评估完成", project.id, chapter.chapter_number)
        return evaluation_json

    async def add_evaluation(
        self,
        chapter: Chapter,
        feedback: str,
        decision: Optional[str] = None,
    ) -> None:
        """
        添加章节评价记录

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            chapter: 章节对象
            feedback: 评价内容
            decision: 决策（可选）
        """
        from ..schemas.novel import ChapterGenerationStatus

        evaluation = ChapterEvaluation(
            chapter_id=chapter.id,
            version_id=None,
            feedback=feedback,
            decision=decision,
        )
        self.session.add(evaluation)
        chapter.status = ChapterGenerationStatus.WAITING_FOR_CONFIRM.value


__all__ = [
    "ChapterEvaluationService",
    "EvaluationContext",
]
