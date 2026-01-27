"""
部分大纲服务

负责长篇小说的分层大纲生成，作为协调者委托具体职责给各子模块。
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.state_machine import ProjectStatus
from ...core.config import settings
from ...core.constants import NovelConstants, LLMConstants, GenerationStatus
from ...exceptions import (
    ResourceNotFoundError,
    InvalidParameterError,
    BlueprintNotReadyError,
)
from ...models.part_outline import PartOutline
from ...models.novel import NovelProject
from ...utils.exception_helpers import log_exception
from ...repositories.part_outline_repository import PartOutlineRepository
from ...repositories.novel_repository import NovelRepository
from ...repositories.chapter_repository import ChapterOutlineRepository
from ...schemas.novel import (
    PartOutline as PartOutlineSchema,
    PartOutlineGenerationProgress,
    ChapterOutline as ChapterOutlineSchema,
)
from ...serializers.part_outline_serializer import build_part_outline_schema
from ..llm_service import LLMService
from ..llm_wrappers import call_llm_json, LLMProfile
from ..prompt_service import PromptService
from ..novel_service import NovelService
from ..prompt_builder import PromptBuilder
from ..vector_store_service import VectorStoreService

from .parser import PartOutlineParser, get_part_outline_parser
from .model_factory import PartOutlineModelFactory, get_part_outline_factory
from .context_retriever import PartOutlineContextRetriever
from .chapter_outline_workflow import (
    ChapterOutlineWorkflow,
    GenerationCancelledException,
    get_chapter_outline_workflow,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PartOutlineService:
    """
    部分大纲服务

    负责长篇小说的分层大纲生成，作为协调者委托具体职责给各子模块：
    - parser: LLM响应解析
    - model_factory: 模型创建
    - context_retriever: 上下文检索

    依赖注入说明：
    - 所有外部服务通过构造函数注入，便于测试和解耦
    - 使用 dependencies.get_part_outline_service() 获取实例
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service: Optional[LLMService] = None,
        prompt_service: Optional[PromptService] = None,
        novel_service: Optional[NovelService] = None,
        vector_store: Optional[VectorStoreService] = None,
    ):
        """
        初始化部分大纲服务

        Args:
            session: 数据库会话
            llm_service: LLM服务（可选，未提供则内部创建）
            prompt_service: 提示词服务（可选，未提供则内部创建）
            novel_service: 小说服务（可选，未提供则内部创建）
            vector_store: 向量库服务（可选）

        Note:
            为保持向后兼容，未传入的服务会在内部创建。
            推荐通过依赖注入传入所有服务。
        """
        self.session = session
        self.repo = PartOutlineRepository(session)
        self.novel_repo = NovelRepository(session)
        self.chapter_outline_repo = ChapterOutlineRepository(session)

        # 依赖注入：优先使用传入的服务，否则内部创建
        self.llm_service = llm_service or LLMService(session)
        self.prompt_service = prompt_service or PromptService(session)
        self.novel_service = novel_service or NovelService(session)
        self.prompt_builder = PromptBuilder(part_outline_repo=self.repo)
        self._vector_store = vector_store

        # 子模块
        self._parser = get_part_outline_parser()
        self._model_factory = get_part_outline_factory()
        self._context_retriever = PartOutlineContextRetriever(
            chapter_outline_repo=self.chapter_outline_repo,
            llm_service=self.llm_service,
            vector_store=vector_store,
        )
        self._chapter_outline_workflow = get_chapter_outline_workflow(
            session=session,
            llm_service=self.llm_service,
            prompt_service=self.prompt_service,
            prompt_builder=self.prompt_builder,
            parser=self._parser,
            context_retriever=self._context_retriever,
            part_repo=self.repo,
            chapter_outline_repo=self.chapter_outline_repo,
        )

    async def _check_if_cancelled(self, part_outline: PartOutline) -> bool:
        """
        检查部分大纲是否被请求取消

        Args:
            part_outline: 部分大纲对象

        Returns:
            bool: 如果被取消返回True

        Raises:
            GenerationCancelledException: 如果检测到取消状态
        """
        await self.session.refresh(part_outline)

        if part_outline.generation_status == GenerationStatus.CANCELLING:
            logger.info("检测到第 %d 部分被请求取消生成", part_outline.part_number)
            raise GenerationCancelledException(f"第 {part_outline.part_number} 部分的生成已被取消")

        return False

    async def cancel_part_generation(
        self,
        project_id: str,
        part_number: int,
        user_id: int,
    ) -> bool:
        """
        取消指定部分的大纲生成

        Args:
            project_id: 项目ID
            part_number: 部分编号
            user_id: 用户ID

        Returns:
            bool: 是否成功设置取消标志
        """
        await self.novel_service.ensure_project_owner(project_id, user_id)

        part_outline = await self.repo.get_by_part_number(project_id, part_number)
        if not part_outline:
            raise ResourceNotFoundError("部分大纲", f"第 {part_number} 部分")

        if part_outline.generation_status != GenerationStatus.GENERATING:
            logger.warning(
                "第 %d 部分当前状态为 %s，无法取消",
                part_number,
                part_outline.generation_status,
            )
            return False

        await self.repo.update_status(part_outline, GenerationStatus.CANCELLING, part_outline.progress)
        await self.session.commit()

        logger.info("第 %d 部分已设置为取消中状态", part_number)
        return True

    async def cleanup_stale_generating_status(
        self,
        project_id: str,
        timeout_minutes: int = 15,
    ) -> int:
        """
        清理超时的generating状态，将其改为failed

        Args:
            project_id: 项目ID
            timeout_minutes: 超时时间（分钟），默认15分钟

        Returns:
            int: 清理的数量
        """
        all_parts = await self.repo.get_by_project_id(project_id)
        timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        cleaned_count = 0

        for part in all_parts:
            if part.generation_status == GenerationStatus.GENERATING:
                if part.updated_at is None or part.updated_at < timeout_threshold:
                    logger.warning(
                        "检测到第 %d 部分超时（超过%d分钟未更新），将状态改为failed",
                        part.part_number,
                        timeout_minutes,
                    )
                    await self.repo.update_status(part, GenerationStatus.FAILED, 0)
                    cleaned_count += 1

        if cleaned_count > 0:
            await self.session.commit()
            logger.info("项目 %s 清理了 %d 个超时状态", project_id, cleaned_count)

        return cleaned_count

    async def _validate_part_outline_request(
        self,
        project_id: str,
        user_id: int,
        total_chapters: int,
    ) -> NovelProject:
        """
        验证部分大纲生成请求

        Args:
            project_id: 项目ID
            user_id: 用户ID
            total_chapters: 总章节数

        Returns:
            NovelProject: 验证通过的项目对象

        Raises:
            InvalidParameterError: 如果章节数不满足要求
            BlueprintNotReadyError: 如果蓝图未生成
        """
        # P1修复: 使用统一的可配置阈值，而非硬编码常量
        threshold = settings.part_outline_threshold
        if total_chapters < threshold:
            raise InvalidParameterError(
                f"章节数为 {total_chapters}，不需要使用部分大纲功能（仅适用于{threshold}章及以上的长篇小说）",
                "total_chapters"
            )

        project = await self.novel_service.ensure_project_owner(project_id, user_id)

        if not project.blueprint:
            raise BlueprintNotReadyError(project_id)

        return project

    def _prepare_blueprint_data(self, project: NovelProject) -> tuple:
        """
        准备蓝图数据

        Args:
            project: 项目对象

        Returns:
            tuple: (world_setting, full_synopsis, characters)
        """
        world_setting = project.blueprint.world_setting or {}
        full_synopsis = project.blueprint.full_synopsis or ""

        characters = [
            {
                "name": char.name,
                "identity": char.identity or "",
                "personality": char.personality or "",
                "goals": char.goals or "",
                "abilities": char.abilities or "",
                **(char.extra or {}),
            }
            for char in sorted(project.characters, key=lambda c: c.position)
        ]

        return world_setting, full_synopsis, characters

    def _to_schema(self, part: PartOutline) -> PartOutlineSchema:
        """将数据库模型转换为Pydantic Schema"""
        return build_part_outline_schema(part)

    async def generate_part_outlines(
        self,
        project_id: str,
        user_id: int,
        total_chapters: int,
        chapters_per_part: int = NovelConstants.CHAPTERS_PER_PART,
        optimization_prompt: Optional[str] = None,
        skip_status_update: bool = False,
    ) -> PartOutlineGenerationProgress:
        """
        生成部分大纲（大纲的大纲） - 串行生成模式

        Args:
            project_id: 项目ID
            user_id: 用户ID
            total_chapters: 总章节数
            chapters_per_part: 每个部分包含的章节数（默认25章）
            optimization_prompt: 可选的优化提示词
            skip_status_update: 是否跳过状态更新（重新生成时使用）

        Returns:
            PartOutlineGenerationProgress: 生成进度和结果
        """
        logger.info("开始为项目 %s 串行生成部分大纲，总章节数=%d",
                   project_id, total_chapters)

        project = await self._validate_part_outline_request(project_id, user_id, total_chapters)
        world_setting, full_synopsis, characters = self._prepare_blueprint_data(project)

        total_parts = math.ceil(total_chapters / chapters_per_part)
        logger.info("计划串行生成 %d 个部分，每部分约 %d 章", total_parts, chapters_per_part)

        await self.repo.delete_by_project_id(project_id)

        part_outlines = []
        # 使用新的单部分生成专用提示词，回退到旧版本
        system_prompt = await self.prompt_service.get_prompt("part_outline_single")
        if not system_prompt:
            system_prompt = await self.prompt_service.get_prompt("part_outline")

        for current_part_num in range(1, total_parts + 1):
            logger.info("开始生成第 %d/%d 部分（串行模式）", current_part_num, total_parts)

            user_prompt = self.prompt_builder.build_part_outline_prompt(
                total_chapters=total_chapters,
                chapters_per_part=chapters_per_part,
                total_parts=total_parts,
                world_setting=world_setting,
                characters=characters,
                full_synopsis=full_synopsis,
                current_part_number=current_part_num,
                previous_parts=part_outlines,
                optimization_prompt=optimization_prompt,
            )

            response = await call_llm_json(
                self.llm_service,
                LLMProfile.BLUEPRINT,
                system_prompt=system_prompt,
                user_content=user_prompt,
                user_id=user_id,
                timeout_override=LLMConstants.PART_OUTLINE_GENERATION_TIMEOUT,
            )

            part_data = self._parser.parse_single_part(response, current_part_num)
            part_outline = self._model_factory.create_from_dict(
                project_id,
                part_data,
                default_part_number=current_part_num,
                total_chapters=total_chapters,
                total_parts=total_parts,
            )

            await self.repo.add(part_outline)
            await self.session.commit()

            part_outlines.append(part_outline)
            logger.info("第 %d/%d 部分生成成功：%s", current_part_num, total_parts, part_outline.title)

        logger.info("串行生成完成，共 %d 个部分大纲", len(part_outlines))

        if not skip_status_update:
            await self.novel_service.transition_project_status(project, ProjectStatus.PART_OUTLINES_READY.value)
            logger.info("项目 %s 状态已更新为 %s", project_id, ProjectStatus.PART_OUTLINES_READY.value)

        return PartOutlineGenerationProgress(
            parts=[self._to_schema(p) for p in part_outlines],
            total_parts=len(part_outlines),
            completed_parts=len(part_outlines),
            status="completed",
        )

    async def generate_part_chapters(
        self,
        project_id: str,
        user_id: int,
        part_number: int,
        regenerate: bool = False,
        chapters_per_batch: int = 5,
    ) -> List[ChapterOutlineSchema]:
        """
        为指定部分生成详细的章节大纲 - 串行生成模式

        Args:
            project_id: 项目ID
            user_id: 用户ID
            part_number: 部分编号
            regenerate: 是否重新生成（默认False）
            chapters_per_batch: 每批生成的章节数（默认5章）

        Returns:
            List[ChapterOutlineSchema]: 生成的章节大纲列表
        """
        logger.info("开始为项目 %s 的第 %d 部分串行生成章节大纲",
                   project_id, part_number)

        part_outline = await self.repo.get_by_part_number(project_id, part_number)
        if not part_outline:
            raise ResourceNotFoundError("部分大纲", f"第 {part_number} 部分")

        project = await self.novel_service.ensure_project_owner(project_id, user_id)
        if not project.blueprint:
            raise BlueprintNotReadyError(project_id)

        await self.repo.update_status(part_outline, GenerationStatus.GENERATING, 0)
        await self.session.commit()

        generation_successful = False
        result_chapters: List[ChapterOutlineSchema] = []

        try:
            result_chapters = await self._chapter_outline_workflow.execute(
                project=project,
                part_outline=part_outline,
                user_id=user_id,
                regenerate=regenerate,
                chapters_per_batch=chapters_per_batch,
                cancellation_checker=self._check_if_cancelled,
            )
            generation_successful = True
            logger.info("串行生成完成，第 %d 部分共生成 %d 个章节大纲",
                       part_number, len(result_chapters))
            return result_chapters

        except GenerationCancelledException as exc:
            logger.info("第 %d 部分生成已被用户取消: %s", part_number, exc)
            return result_chapters

        except Exception as exc:
            log_exception(
                exc,
                "生成部分章节大纲",
                project_id=project_id,
                part_number=part_number,
                user_id=user_id,
            )
            raise

        finally:
            await self._finalize_generation_status(
                part_outline, part_number, generation_successful
            )

    async def _finalize_generation_status(
        self,
        part_outline: PartOutline,
        part_number: int,
        generation_successful: bool,
    ) -> None:
        """
        完成生成后更新状态

        Args:
            part_outline: 部分大纲对象
            part_number: 部分编号
            generation_successful: 是否生成成功
        """
        try:
            await self.session.refresh(part_outline)

            if generation_successful:
                await self.repo.update_status(part_outline, GenerationStatus.COMPLETED, 100)
                status_desc = "completed"
            elif part_outline.generation_status == GenerationStatus.CANCELLING:
                await self.repo.update_status(part_outline, "cancelled", part_outline.progress)
                status_desc = "cancelled"
            else:
                await self.repo.update_status(part_outline, GenerationStatus.FAILED, 0)
                status_desc = "failed"

            await self.session.commit()
            logger.info("第 %d 部分状态已更新: %s", part_number, status_desc)

        except Exception as status_update_error:
            log_exception(
                status_update_error,
                "更新部分状态",
                level="error",
                part_number=part_number,
            )

    async def batch_generate_chapters(
        self,
        project_id: str,
        user_id: int,
        part_numbers: Optional[List[int]] = None,
        max_concurrent: int = 3,
    ) -> PartOutlineGenerationProgress:
        """
        批量生成多个部分的章节大纲

        Args:
            project_id: 项目ID
            user_id: 用户ID
            part_numbers: 要生成的部分编号列表（None表示生成所有待生成的部分）
            max_concurrent: 最大并发数（默认3）

        Returns:
            PartOutlineGenerationProgress: 生成进度
        """
        logger.info("开始批量生成章节大纲（串行模式）")

        if part_numbers:
            parts = []
            for pn in part_numbers:
                part = await self.repo.get_by_part_number(project_id, pn)
                if part:
                    parts.append(part)
        else:
            parts = await self.repo.get_pending_parts(project_id)

        if not parts:
            logger.info("没有待生成的部分大纲")
            return PartOutlineGenerationProgress(
                parts=[],
                total_parts=0,
                completed_parts=0,
                status="completed",
            )

        logger.info("共有 %d 个部分待生成", len(parts))

        results = []
        for part in parts:
            try:
                logger.info("开始生成第 %d 部分", part.part_number)
                chapters = await self.generate_part_chapters(
                    project_id=project_id,
                    user_id=user_id,
                    part_number=part.part_number,
                    regenerate=False,
                )
                results.append({"success": True, "part_number": part.part_number, "chapters": len(chapters)})
            except Exception as exc:
                log_exception(
                    exc,
                    "批量生成部分章节",
                    level="error",
                    project_id=project_id,
                    part_number=part.part_number,
                    user_id=user_id
                )
                results.append({"success": False, "part_number": part.part_number, "error": str(exc)})

        completed = sum(1 for r in results if r["success"])
        failed = len(results) - completed

        logger.info("批量生成完成，成功=%d，失败=%d", completed, failed)

        all_parts = await self.repo.get_by_project_id(project_id)

        all_completed = all(p.generation_status == GenerationStatus.COMPLETED for p in all_parts)
        if all_completed and completed > 0:
            project = await self.novel_repo.get(project_id)
            if project:
                await self.novel_service.transition_project_status(
                    project,
                    ProjectStatus.CHAPTER_OUTLINES_READY.value
                )
                logger.info("项目 %s 所有部分大纲已完成", project_id)

        return PartOutlineGenerationProgress(
            parts=[self._to_schema(p) for p in all_parts],
            total_parts=len(all_parts),
            completed_parts=sum(1 for p in all_parts if p.generation_status == GenerationStatus.COMPLETED),
            status=GenerationStatus.COMPLETED if failed == 0 else GenerationStatus.PARTIAL,
        )

    async def regenerate_single_part_outline(
        self,
        project_id: str,
        user_id: int,
        part_number: int,
        total_parts: int,
        total_chapters: int,
        chapters_per_part: int,
        previous_parts: List[PartOutline],
        optimization_prompt: Optional[str] = None,
    ) -> PartOutline:
        """
        重新生成单个部分大纲

        Args:
            project_id: 项目ID
            user_id: 用户ID
            part_number: 要重新生成的部分编号
            total_parts: 总部分数
            total_chapters: 总章节数
            chapters_per_part: 每部分章节数
            previous_parts: 前面的部分大纲列表（用于上下文）
            optimization_prompt: 优化提示词（可选）

        Returns:
            PartOutline: 新生成的部分大纲
        """
        logger.info("开始重新生成项目 %s 的第 %d 部分大纲", project_id, part_number)

        project = await self.novel_service.ensure_project_owner(project_id, user_id)
        world_setting, full_synopsis, characters = self._prepare_blueprint_data(project)

        # 使用新的单部分生成专用提示词，回退到旧版本
        system_prompt = await self.prompt_service.get_prompt("part_outline_single")
        if not system_prompt:
            system_prompt = await self.prompt_service.get_prompt("part_outline")

        user_prompt = self.prompt_builder.build_part_outline_prompt(
            total_chapters=total_chapters,
            chapters_per_part=chapters_per_part,
            total_parts=total_parts,
            world_setting=world_setting,
            characters=characters,
            full_synopsis=full_synopsis,
            current_part_number=part_number,
            previous_parts=previous_parts,
            optimization_prompt=optimization_prompt,
        )

        response = await call_llm_json(
            self.llm_service,
            LLMProfile.BLUEPRINT,
            system_prompt=system_prompt,
            user_content=user_prompt,
            user_id=user_id,
            timeout_override=LLMConstants.PART_OUTLINE_GENERATION_TIMEOUT,
        )

        part_data = self._parser.parse_single_part(response, part_number)
        new_part = self._model_factory.create_from_dict(
            project_id,
            part_data,
            default_part_number=part_number,
            total_chapters=total_chapters,
            total_parts=total_parts,
        )

        await self.repo.add(new_part)

        logger.info("项目 %s 第 %d 部分大纲重新生成成功：%s", project_id, part_number, new_part.title)

        return new_part

    async def get_regenerate_progress(
        self,
        project_id: str,
    ) -> PartOutlineGenerationProgress:
        """
        获取部分大纲的当前进度

        Args:
            project_id: 项目ID

        Returns:
            PartOutlineGenerationProgress: 进度信息
        """
        all_parts = await self.repo.get_by_project_id(project_id)
        completed_count = sum(1 for p in all_parts if p.generation_status == GenerationStatus.COMPLETED)

        return PartOutlineGenerationProgress(
            parts=[self._to_schema(p) for p in all_parts],
            total_parts=len(all_parts),
            completed_parts=completed_count,
            status=GenerationStatus.COMPLETED if completed_count == len(all_parts) else GenerationStatus.PARTIAL,
        )


__all__ = [
    "PartOutlineService",
    "GenerationCancelledException",
]
