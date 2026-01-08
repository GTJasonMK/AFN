"""
章节生成工作流

封装整个章节生成的业务流程，支持同步和流式两种调用方式。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .context import ChapterGenerationResult
from .prompt_builder import ChapterPromptBuilder
from ...schemas.novel import ChapterGenerationStatus
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
        # Bug 7 修复: 保存重生成前的状态，用于失败时恢复
        self._previous_selected_version_id = None
        self._previous_real_summary = None

    async def _initialize(self) -> None:
        """阶段1: 初始化和验证"""
        from ...core.state_machine import ProjectStatus
        from ...exceptions import ResourceNotFoundError, InvalidStateTransitionError, InvalidParameterError

        # 验证项目所有权
        self._project = await self.novel_service.ensure_project_owner(
            self.project_id, self.user_id
        )

        # 强制校验项目状态：只允许在大纲就绪或写作中状态下生成章节
        allowed_states = [
            ProjectStatus.CHAPTER_OUTLINES_READY.value,
            ProjectStatus.WRITING.value,
            ProjectStatus.COMPLETED.value,  # 允许在完成状态下继续编辑
        ]
        if self._project.status not in allowed_states:
            current_status = self._project.status
            # 提供友好的错误信息，引导用户完成前置步骤
            if current_status == ProjectStatus.DRAFT.value:
                hint = "请先完成灵感对话并生成蓝图"
            elif current_status == ProjectStatus.BLUEPRINT_READY.value:
                # 检查是否是空白项目（没有蓝图数据）
                blueprint = self._project.blueprint
                is_blank_project = not blueprint or not getattr(blueprint, 'total_chapters', None)
                if is_blank_project:
                    hint = "空白项目请先手动创建章节，然后再使用AI生成功能"
                else:
                    hint = "请先生成章节大纲"
            elif current_status == ProjectStatus.PART_OUTLINES_READY.value:
                hint = "请先生成章节大纲（基于分部大纲）"
            else:
                hint = "请确保已完成章节大纲生成"
            raise InvalidStateTransitionError(
                f"当前项目状态为 {current_status}，无法生成章节正文。{hint}"
            )

        # P0修复: 连贯性校验 - 只允许生成下一章或重生成已有章节
        # 获取已完成生成的最大章节号（有selected_version_id表示已选择版本）
        max_generated = 0
        existing_chapter_numbers = set()
        for ch in self._project.chapters:
            existing_chapter_numbers.add(ch.chapter_number)
            if ch.selected_version_id is not None:
                max_generated = max(max_generated, ch.chapter_number)

        # 允许的情况：
        # 1. 重生成已有章节（chapter_number在existing_chapter_numbers中）
        # 2. 生成下一章（chapter_number == max_generated + 1）
        # 3. 第一章（chapter_number == 1 且 max_generated == 0）
        is_regenerate = self.chapter_number in existing_chapter_numbers
        is_next_chapter = self.chapter_number == max_generated + 1
        is_first_chapter = self.chapter_number == 1 and max_generated == 0

        if not (is_regenerate or is_next_chapter or is_first_chapter):
            raise InvalidParameterError(
                f"章节生成必须按顺序进行。当前已生成到第{max_generated}章，"
                f"请先生成第{max_generated + 1}章，或选择重生成已有章节。",
                "chapter_number"
            )

        # 状态转换：从大纲就绪进入写作状态
        if self._project.status == ProjectStatus.CHAPTER_OUTLINES_READY.value:
            await self.novel_service.transition_project_status(
                self._project, ProjectStatus.WRITING.value
            )
            logger.info("项目 %s 状态更新为 %s", self.project_id, ProjectStatus.WRITING.value)

        # 检查版本数
        self._version_count = self._chapter_gen_service.resolve_version_count()

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

        # Bug 10 修复: 互斥保护 - 如果章节正在生成中，拒绝重复请求
        if self._chapter.status == "generating":
            raise InvalidStateTransitionError(
                f"第 {self.chapter_number} 章正在生成中，请等待当前生成完成后再试。"
            )

        # Bug 7 修复: 在清除前保存当前状态，用于失败时恢复
        self._previous_selected_version_id = self._chapter.selected_version_id
        self._previous_real_summary = self._chapter.real_summary

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
        from ..rag.scene_extractor import SceneStateExtractor
        from ...exceptions import InvalidParameterError

        # 准备蓝图
        project_schema = await self.novel_service.get_project_schema(
            self.project_id, self.user_id
        )
        # Bug 1 修复: 检查蓝图是否存在
        if not project_schema.blueprint:
            raise InvalidParameterError(
                "项目缺少蓝图数据，无法生成章节。请先完成灵感对话生成蓝图。",
                "blueprint"
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

        # 提取场景状态（新增）
        scene_extractor = SceneStateExtractor()
        scene_state = scene_extractor.extract(
            prev_chapter_analysis=gen_context.prev_chapter_analysis,
            previous_tail_excerpt=previous_tail,
        )

        # 构建用户提示词（场景聚焦结构）
        prompt_input = self._prompt_builder.build_writing_prompt(
            outline=self._outline,
            blueprint_dict=blueprint_dict,
            previous_summary_text=previous_summary,
            previous_tail_excerpt=previous_tail,
            rag_context=gen_context.rag_context,
            writing_notes=self.writing_notes,
            chapter_number=self.chapter_number,
            completed_chapters=completed_chapters,
            scene_state=scene_state,
            generation_context=gen_context.generation_context,
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
                self._chapter.status = ChapterGenerationStatus.NOT_GENERATED.value
                # Bug 7 修复: 恢复之前保存的版本选择和摘要
                if self._previous_selected_version_id is not None:
                    self._chapter.selected_version_id = self._previous_selected_version_id
                    self._chapter.status = ChapterGenerationStatus.SUCCESSFUL.value
                    logger.info(
                        "已恢复第 %s 章之前选中的版本 %s",
                        self.chapter_number, self._previous_selected_version_id
                    )
                if self._previous_real_summary is not None:
                    self._chapter.real_summary = self._previous_real_summary

                await self.session.commit()
                logger.info("已重置第 %s 章状态", self.chapter_number)
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

        except asyncio.CancelledError:
            # 用户取消操作 - 这是预期行为，不记录为错误
            logger.info(
                "项目 %s 第 %s 章生成被用户取消",
                self.project_id, self.chapter_number
            )
            # 尝试重置章节状态（使用独立的异常处理避免二次错误）
            await self._reset_chapter_status_safe()
            # 返回取消事件，不重新抛出异常（让生成器正常结束）
            yield {
                "stage": "cancelled",
                "message": "生成已取消",
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

    async def _reset_chapter_status_safe(self) -> None:
        """安全地重置章节状态（用于取消场景，不抛出异常）"""
        if self._chapter is None:
            return

        try:
            # 使用新的session来避免被取消的session的问题
            # 由于当前session可能处于不一致状态，直接尝试操作
            self._chapter.status = ChapterGenerationStatus.NOT_GENERATED.value
            # Bug 7 修复: 恢复之前保存的版本选择和摘要
            if self._previous_selected_version_id is not None:
                self._chapter.selected_version_id = self._previous_selected_version_id
                self._chapter.status = ChapterGenerationStatus.SUCCESSFUL.value
            if self._previous_real_summary is not None:
                self._chapter.real_summary = self._previous_real_summary

            await self.session.commit()
            logger.info("已重置第 %s 章状态（取消后清理）", self.chapter_number)
        except asyncio.CancelledError:
            # commit时也可能被取消，忽略
            logger.debug("重置章节状态时被取消，跳过")
        except Exception as reset_error:
            # 其他错误也只记录，不抛出
            logger.warning("取消后重置章节状态失败（可忽略）: %s", reset_error)


__all__ = [
    "ChapterGenerationWorkflow",
]
