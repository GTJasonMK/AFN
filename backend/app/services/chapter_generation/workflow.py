"""
章节生成工作流

封装整个章节生成的业务流程，支持同步和流式两种调用方式。
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .context import ChapterGenerationResult
from .prompt_builder import ChapterPromptBuilder
from ...utils.exception_helpers import get_safe_error_message

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from ..llm_service import LLMService

logger = logging.getLogger(__name__)


class ChapterGenerationWorkflow:
    """
    章节生成工作流

    封装整个章节生成的业务流程，支持同步和流式两种调用方式。
    消除generate_chapter和generate_chapter_stream之间的代码重复。

    使用方式：
    ```python
    workflow = ChapterGenerationWorkflow(...)
    # 同步执行
    result = await workflow.execute()

    # 流式执行（带进度回调）
    async for progress in workflow.execute_with_progress():
        yield sse_event("progress", progress)
    ```
    """

    def __init__(
        self,
        session: "AsyncSession",
        llm_service: "LLMService",
        novel_service: Any,
        prompt_service: Any,
        project_id: str,
        chapter_number: int,
        user_id: int,
        writing_notes: Optional[str] = None,
        vector_store: Optional[Any] = None,
    ):
        self.session = session
        self.llm_service = llm_service
        self.novel_service = novel_service
        self.prompt_service = prompt_service
        self.project_id = project_id
        self.chapter_number = chapter_number
        self.user_id = user_id
        self.writing_notes = writing_notes
        self.vector_store = vector_store

        # 内部状态
        from .service import ChapterGenerationService
        self._chapter_gen_service = ChapterGenerationService(session, llm_service)
        self._prompt_builder = ChapterPromptBuilder()
        self._project = None
        self._chapter = None
        self._outline = None
        self._version_count = 0

    async def _initialize(self) -> None:
        """阶段1: 初始化和验证"""
        from ...core.state_machine import ProjectStatus
        from ...exceptions import ResourceNotFoundError

        # 验证项目所有权
        self._project = await self.novel_service.ensure_project_owner(
            self.project_id, self.user_id
        )

        # 状态转换
        if self._project.status == ProjectStatus.CHAPTER_OUTLINES_READY.value:
            await self.novel_service.transition_project_status(
                self._project, ProjectStatus.WRITING.value
            )
            logger.info("项目 %s 状态更新为 %s", self.project_id, ProjectStatus.WRITING.value)

        # 检查版本数和每日限额
        self._version_count = self._chapter_gen_service.resolve_version_count()
        from ...core.config import settings
        if settings.writer_parallel_generation and self._version_count > 1:
            await self.llm_service.enforce_daily_limit(self.user_id)

        # 获取大纲
        self._outline = await self.novel_service.get_outline(
            self.project_id, self.chapter_number
        )
        if not self._outline:
            raise ResourceNotFoundError(
                "章节大纲", f"项目 {self.project_id} 第 {self.chapter_number} 章"
            )

        # 获取或创建章节
        self._chapter = await self.novel_service.get_or_create_chapter(
            self.project_id, self.chapter_number
        )
        self._chapter.real_summary = None
        self._chapter.selected_version_id = None
        self._chapter.status = "generating"
        await self.session.commit()

    async def _collect_context(self) -> tuple:
        """阶段2: 收集历史章节上下文"""
        return await self._chapter_gen_service.collect_chapter_summaries(
            project=self._project,
            current_chapter_number=self.chapter_number,
            user_id=self.user_id,
            project_id=self.project_id,
        )

    async def _prepare_prompt(
        self, completed_chapters: List[Dict], previous_summary: str, previous_tail: str
    ) -> tuple:
        """阶段3: 准备提示词"""
        from ...utils.prompt_helpers import ensure_prompt

        # 准备蓝图
        project_schema = await self.novel_service.get_project_schema(
            self.project_id, self.user_id
        )
        blueprint_dict = project_schema.blueprint.model_dump()
        blueprint_dict = self._chapter_gen_service.prepare_blueprint_for_generation(blueprint_dict)

        # 获取系统提示词
        writer_prompt = ensure_prompt(
            await self.prompt_service.get_prompt("writing"), "writing"
        )

        # 准备生成上下文
        gen_context = await self._chapter_gen_service.prepare_generation_context(
            project=self._project,
            outline=self._outline,
            blueprint_dict=blueprint_dict,
            chapter_number=self.chapter_number,
            user_id=self.user_id,
            writing_notes=self.writing_notes,
            vector_store=self.vector_store,
        )

        # 获取RAG上下文
        rag_context = (
            gen_context.enhanced_rag_context.get_legacy_context()
            if gen_context.enhanced_rag_context else None
        )

        # 构建用户提示词
        prompt_input = self._prompt_builder.build_writing_prompt(
            outline=self._outline,
            blueprint_dict=blueprint_dict,
            previous_summary_text=previous_summary,
            previous_tail_excerpt=previous_tail,
            rag_context=rag_context,
            writing_notes=self.writing_notes,
            chapter_number=self.chapter_number,
            completed_chapters=completed_chapters,
        )

        return writer_prompt, prompt_input

    async def _generate_versions(
        self, writer_prompt: str, prompt_input: str
    ) -> List[Dict]:
        """阶段4: 生成版本"""
        from ...core.config import settings

        skip_usage_tracking = settings.writer_parallel_generation
        llm_config = None
        if skip_usage_tracking:
            llm_config = await self.llm_service.resolve_llm_config_cached(
                self.user_id, skip_daily_limit_check=True
            )

        return await self._chapter_gen_service.generate_chapter_versions(
            version_count=self._version_count,
            writer_prompt=writer_prompt,
            prompt_input=prompt_input,
            llm_config=llm_config,
            skip_usage_tracking=skip_usage_tracking,
            user_id=self.user_id,
            project_id=self.project_id,
            chapter_number=self.chapter_number,
        )

    async def _save_results(self, raw_versions: List[Dict]) -> ChapterGenerationResult:
        """阶段5: 保存结果"""
        contents, metadata = self._chapter_gen_service.process_generated_versions(raw_versions)
        await self.novel_service.replace_chapter_versions(self._chapter, contents, metadata)
        await self.session.commit()

        logger.info(
            "项目 %s 第 %s 章生成完成，已写入 %s 个版本",
            self.project_id, self.chapter_number, len(contents)
        )

        return ChapterGenerationResult(
            contents=contents,
            metadata=metadata,
            chapter_number=self.chapter_number,
            version_count=len(contents),
        )

    async def _reset_chapter_status(self) -> None:
        """重置章节状态（失败时调用）"""
        if self._chapter is not None:
            try:
                self._chapter.status = "draft"
                await self.session.commit()
                logger.info("已重置第 %s 章状态为 draft", self.chapter_number)
            except Exception as reset_error:
                logger.error("重置章节状态失败: %s", reset_error)

    async def execute(self) -> ChapterGenerationResult:
        """
        同步执行完整的章节生成流程

        Returns:
            ChapterGenerationResult: 生成结果
        """
        try:
            # 1. 初始化
            await self._initialize()

            # 2. 收集上下文
            completed_chapters, previous_summary, previous_tail = await self._collect_context()

            # 3. 准备提示词
            writer_prompt, prompt_input = await self._prepare_prompt(
                completed_chapters, previous_summary, previous_tail
            )

            # 4. 生成版本
            raw_versions = await self._generate_versions(writer_prompt, prompt_input)

            # 5. 保存结果
            return await self._save_results(raw_versions)

        except Exception as exc:
            logger.exception("章节生成失败: %s", exc)
            await self._reset_chapter_status()
            raise

    async def execute_with_progress(self):
        """
        流式执行章节生成，通过yield返回进度

        Yields:
            Dict: 进度信息 {"stage", "message", "current", "total"}
        """
        try:
            # 阶段1: 初始化
            yield {
                "stage": "initializing",
                "message": "正在初始化...",
                "current": 0,
                "total": 0,
            }
            await self._initialize()

            # 阶段2: 收集上下文
            yield {
                "stage": "collecting_context",
                "message": "正在收集历史章节上下文...",
                "current": 0,
                "total": self._version_count,
            }
            completed_chapters, previous_summary, previous_tail = await self._collect_context()

            # 阶段3: 准备提示词
            yield {
                "stage": "preparing_prompt",
                "message": "正在准备提示词和RAG检索...",
                "current": 0,
                "total": self._version_count,
            }
            writer_prompt, prompt_input = await self._prepare_prompt(
                completed_chapters, previous_summary, previous_tail
            )

            # 阶段4: 生成版本
            yield {
                "stage": "generating",
                "message": f"正在生成第{self.chapter_number}章（共{self._version_count}个版本）...",
                "current": 0,
                "total": self._version_count,
            }
            raw_versions = await self._generate_versions(writer_prompt, prompt_input)

            # 阶段5: 保存结果
            yield {
                "stage": "saving",
                "message": "正在保存生成结果...",
                "current": self._version_count,
                "total": self._version_count,
            }
            result = await self._save_results(raw_versions)

            # 完成
            yield {
                "stage": "complete",
                "message": f"第{self.chapter_number}章生成完成",
                "chapter_number": self.chapter_number,
                "version_count": result.version_count,
            }

        except Exception as exc:
            logger.exception("章节生成失败: %s", exc)
            await self._reset_chapter_status()
            # 使用安全的错误消息过滤，避免泄露敏感信息
            safe_message = get_safe_error_message(exc, "章节生成失败，请稍后重试")
            yield {
                "stage": "error",
                "message": safe_message,
            }


__all__ = [
    "ChapterGenerationWorkflow",
]
