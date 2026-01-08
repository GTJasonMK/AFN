"""
小说项目服务

负责项目级别的CRUD、状态机管理和数据查询。
章节版本管理委托给ChapterVersionService，遵循单一职责原则。
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.state_machine import ProjectStatus, ProjectStateMachine
from ..exceptions import ResourceNotFoundError, PermissionDeniedError, InvalidParameterError
from ..serializers.novel_serializer import NovelSerializer
from ..models import Chapter, ChapterOutline, ChapterVersion, NovelBlueprint, NovelProject
from ..repositories.novel_repository import NovelRepository
from ..repositories.chapter_repository import ChapterOutlineRepository
from ..schemas.novel import (
    Chapter as ChapterSchema,
    NovelProject as NovelProjectSchema,
    NovelProjectSummary,
    NovelSectionResponse,
    NovelSectionType,
)
from ..services.chapter_version_service import ChapterVersionService

logger = logging.getLogger(__name__)


class NovelService:
    """
    小说项目服务

    负责：
    - 项目CRUD（创建、查询、删除）
    - 状态机管理（状态转换、回退清理）
    - 权限验证（确保项目归属）
    - 数据查询（项目、区段、章节Schema）

    章节版本管理委托给ChapterVersionService。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化NovelService

        Args:
            session: 数据库会话
        """
        self.session = session
        self.repo = NovelRepository(session)
        self.chapter_outline_repo = ChapterOutlineRepository(session)
        # 组合ChapterVersionService，委托章节版本管理
        self._chapter_version_service = ChapterVersionService(session)

    # ------------------------------------------------------------------
    # 状态机管理
    # ------------------------------------------------------------------

    async def transition_project_status(
        self,
        project: NovelProject,
        new_status: str,
        force: bool = False
    ) -> None:
        """
        安全地转换项目状态

        Args:
            project: 项目实例
            new_status: 目标状态
            force: 是否强制转换（跳过验证）

        Raises:
            InvalidStateTransitionError: 非法状态转换
        """
        logger.info(
            "开始状态转换: project_id=%s user_id=%s title='%s' %s -> %s%s",
            project.id,
            project.user_id,
            project.title or "未命名",
            project.status,
            new_status,
            " (force=True)" if force else ""
        )

        # 检测回退转换，执行数据清理
        if self._is_backward_transition(project.status, new_status):
            logger.warning(
                "检测到状态回退: %s -> %s，开始清理相关数据",
                project.status,
                new_status
            )
            await self._cleanup_data_for_backward_transition(project, new_status)

        state_machine = ProjectStateMachine(project.status)
        project.status = state_machine.transition_to(new_status, force=force)
        await self.session.commit()

        logger.info(
            "状态转换成功: project_id=%s 新状态=%s",
            project.id,
            project.status
        )

    def _is_backward_transition(self, current_status: str, new_status: str) -> bool:
        """判断是否为回退转换（使用状态机统一定义）"""
        return ProjectStateMachine.check_backward_transition(current_status, new_status)

    async def _cleanup_data_for_backward_transition(
        self,
        project: NovelProject,
        new_status: str
    ) -> None:
        """清理回退转换时的相关数据"""
        project_id = project.id
        current_status = project.status

        # writing -> chapter_outlines_ready：删除所有已生成的章节
        if (
            current_status == ProjectStatus.WRITING
            and new_status == ProjectStatus.CHAPTER_OUTLINES_READY
        ):
            logger.warning(
                "项目 %s 从写作状态回退到大纲状态，将删除所有已生成章节",
                project_id
            )
            if project.chapters:
                chapter_numbers = [ch.chapter_number for ch in project.chapters]
                await self._chapter_version_service.delete_chapters(project_id, chapter_numbers)
                logger.info("项目 %s 回退时删除了 %d 个章节", project_id, len(chapter_numbers))

                # 同步清理向量库数据，防止RAG检索返回已删除章节内容
                await self._cleanup_vector_store(project_id, chapter_numbers)

        # chapter_outlines_ready -> blueprint_ready/part_outlines_ready：删除所有章节大纲
        elif (
            current_status == ProjectStatus.CHAPTER_OUTLINES_READY
            and new_status in [ProjectStatus.BLUEPRINT_READY, ProjectStatus.PART_OUTLINES_READY]
        ):
            logger.warning("项目 %s 从大纲状态回退，将删除所有章节大纲", project_id)
            count = await self._chapter_version_service.delete_chapter_outlines(project_id)
            if count > 0:
                logger.info("项目 %s 回退时删除了 %d 个章节大纲", project_id, count)

        # blueprint_ready -> draft：由BlueprintService处理
        elif (
            current_status == ProjectStatus.BLUEPRINT_READY
            and new_status == ProjectStatus.DRAFT
        ):
            logger.info("项目 %s 回退到草稿状态，蓝图数据将在重新生成时清理", project_id)

    # ------------------------------------------------------------------
    # 项目CRUD
    # ------------------------------------------------------------------

    async def create_project(
        self,
        user_id: int,
        title: str,
        initial_prompt: str = "",
        skip_inspiration: bool = False,
    ) -> NovelProject:
        """
        创建新项目

        Args:
            user_id: 用户ID
            title: 项目标题
            initial_prompt: 灵感对话的初始提示词
            skip_inspiration: 是否跳过灵感对话（自由创作模式）

        注意：此方法不commit，调用方需要在适当时候commit
        """
        # 自由创作模式：跳过灵感对话，直接进入蓝图就绪状态
        initial_status = (
            ProjectStatus.BLUEPRINT_READY.value
            if skip_inspiration
            else ProjectStatus.DRAFT.value
        )

        project = NovelProject(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            initial_prompt=initial_prompt,
            status=initial_status,
        )
        blueprint = NovelBlueprint(project=project)
        self.session.add_all([project, blueprint])
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def delete_projects(
        self,
        project_ids: List[str],
        user_id: int,
        vector_store: Optional["VectorStoreService"] = None,
    ) -> None:
        """
        删除项目（批量）

        Args:
            project_ids: 要删除的项目ID列表
            user_id: 用户ID（用于权限验证）
            vector_store: 向量库服务（可选，用于清理RAG数据）

        注意：此方法不commit，调用方需要在适当时候commit
        """
        from sqlalchemy import delete
        from ..models.image_config import GeneratedImage

        for pid in project_ids:
            await self.ensure_project_owner(pid, user_id)

        # 清理向量库数据（在数据库删除之前执行）
        if vector_store:
            for pid in project_ids:
                try:
                    deleted_count = await vector_store.delete_by_project(pid)
                    logger.info("项目 %s 向量库清理完成，删除 %d 条记录", pid, deleted_count)
                except Exception as exc:
                    # 向量库清理失败不阻止项目删除，仅记录警告
                    logger.warning("项目 %s 向量库清理失败: %s", pid, exc)

        # 清理生成的图片记录（project_id不是外键，需要手动清理）
        # 注意：图片文件保留在磁盘上，不自动删除（用户可能需要备份）
        await self.session.execute(
            delete(GeneratedImage).where(GeneratedImage.project_id.in_(project_ids))
        )

        await self.session.execute(
            delete(NovelProject).where(NovelProject.id.in_(project_ids))
        )

    async def count_projects(self) -> int:
        """统计所有项目数量"""
        return await self.repo.count_all()

    # ------------------------------------------------------------------
    # 权限验证
    # ------------------------------------------------------------------

    async def ensure_project_owner(self, project_id: str, user_id: int) -> NovelProject:
        """确保项目归属于指定用户"""
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise ResourceNotFoundError("项目", project_id)
        if project.user_id != user_id:
            raise PermissionDeniedError("无权访问该项目")
        return project

    async def ensure_blueprint_ready(
        self,
        project_id: str,
        user_id: int,
        require_total_chapters: bool = False,
    ) -> Tuple[NovelProject, NovelProjectSchema]:
        """确保项目蓝图已就绪"""
        from ..exceptions import BlueprintNotReadyError

        project = await self.ensure_project_owner(project_id, user_id)
        project_schema = await NovelSerializer.serialize_project(project)

        if not project_schema.blueprint:
            raise BlueprintNotReadyError(project_id)

        if require_total_chapters:
            total_chapters = project_schema.blueprint.total_chapters or 0
            if total_chapters == 0:
                raise InvalidParameterError("蓝图未设置总章节数", "total_chapters")

        return project, project_schema

    async def ensure_part_outline_eligible(
        self,
        project_id: str,
        user_id: int,
    ) -> Tuple[NovelProject, NovelProjectSchema]:
        """确保项目符合部分大纲操作条件"""
        project, project_schema = await self.ensure_blueprint_ready(project_id, user_id)

        if not project_schema.blueprint.needs_part_outlines:
            raise InvalidParameterError(
                "该项目不需要部分大纲（章节数未超过阈值）",
                "needs_part_outlines"
            )

        return project, project_schema

    # ------------------------------------------------------------------
    # 数据查询
    # ------------------------------------------------------------------

    async def get_project_schema(
        self,
        project_id: str,
        user_id: Optional[int] = None
    ) -> NovelProjectSchema:
        """获取项目Schema"""
        if user_id is not None:
            project = await self.ensure_project_owner(project_id, user_id)
        else:
            project = await self.repo.get_by_id(project_id)
            if not project:
                raise ResourceNotFoundError("项目", project_id)
        return await NovelSerializer.serialize_project(project)

    async def get_section_data(
        self,
        project_id: str,
        section: NovelSectionType,
        user_id: Optional[int] = None,
    ) -> NovelSectionResponse:
        """获取项目的某个section数据"""
        if user_id is not None:
            project = await self.ensure_project_owner(project_id, user_id)
        else:
            project = await self.repo.get_by_id(project_id)
            if not project:
                raise ResourceNotFoundError("项目", project_id)
        return NovelSerializer.build_section_response(project, section)

    async def get_chapter_schema(
        self,
        project_id: str,
        chapter_number: int,
        user_id: Optional[int] = None,
    ) -> ChapterSchema:
        """获取章节Schema"""
        if user_id is not None:
            project = await self.ensure_project_owner(project_id, user_id)
        else:
            project = await self.repo.get_by_id(project_id)
            if not project:
                raise ResourceNotFoundError("项目", project_id)
        return NovelSerializer.build_chapter_schema(project, chapter_number)

    async def list_projects_for_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[NovelProjectSummary], int]:
        """分页获取用户的项目摘要列表

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
        """
        projects, total = await self.repo.list_by_user(
            user_id, page, page_size
        )
        summaries: List[NovelProjectSummary] = []

        for project in projects:
            blueprint = project.blueprint
            genre = blueprint.genre if blueprint and blueprint.genre else "未知"
            outlines = project.outlines
            chapters = project.chapters
            total_chapters = len(outlines) or len(chapters)
            completed = sum(1 for chapter in chapters if chapter.selected_version_id)
            summaries.append(
                NovelProjectSummary(
                    id=project.id,
                    title=project.title,
                    genre=genre,
                    last_edited=project.updated_at.isoformat() if project.updated_at else "未知",
                    completed_chapters=completed,
                    total_chapters=total_chapters,
                    status=project.status,
                    is_imported=project.is_imported,
                    import_analysis_status=project.import_analysis_status,
                )
            )

        return summaries, total

    # ------------------------------------------------------------------
    # 章节版本管理（委托给ChapterVersionService）
    # ------------------------------------------------------------------

    async def get_outline(self, project_id: str, chapter_number: int) -> Optional[ChapterOutline]:
        """获取章节大纲"""
        return await self._chapter_version_service.get_outline(project_id, chapter_number)

    async def get_outline_or_raise(self, project_id: str, chapter_number: int) -> "ChapterOutline":
        """
        获取章节大纲，不存在则抛出异常

        统一的大纲获取和验证方法，消除路由层重复的验证代码。

        Args:
            project_id: 项目ID
            chapter_number: 章节编号

        Returns:
            ChapterOutline: 章节大纲实例

        Raises:
            ResourceNotFoundError: 大纲不存在

        Example:
            # 之前：
            outline = await novel_service.get_outline(project_id, chapter_number)
            if not outline:
                raise ResourceNotFoundError("章节大纲", f"项目 {project_id} 第 {chapter_number} 章")

            # 之后：
            outline = await novel_service.get_outline_or_raise(project_id, chapter_number)
        """
        from ..exceptions import ResourceNotFoundError

        outline = await self.get_outline(project_id, chapter_number)
        if not outline:
            raise ResourceNotFoundError("章节大纲", f"项目 {project_id} 第 {chapter_number} 章")
        return outline

    async def count_chapter_outlines(self, project_id: str) -> int:
        """统计项目的章节大纲数量"""
        return await self._chapter_version_service.count_chapter_outlines(project_id)

    async def get_or_create_chapter(self, project_id: str, chapter_number: int) -> Chapter:
        """获取或创建章节"""
        return await self._chapter_version_service.get_or_create_chapter(project_id, chapter_number)

    async def replace_chapter_versions(
        self,
        chapter: Chapter,
        contents: List[str],
        metadata: Optional[List[Dict]] = None
    ) -> List[ChapterVersion]:
        """替换章节的所有版本"""
        return await self._chapter_version_service.replace_chapter_versions(chapter, contents, metadata)

    async def select_chapter_version(self, chapter: Chapter, version_index: int) -> ChapterVersion:
        """选择章节版本"""
        return await self._chapter_version_service.select_chapter_version(chapter, version_index)

    async def add_chapter_evaluation(
        self,
        chapter: Chapter,
        version: Optional[ChapterVersion],
        feedback: str,
        decision: Optional[str] = None
    ) -> None:
        """添加章节评价"""
        await self._chapter_version_service.add_chapter_evaluation(chapter, version, feedback, decision)

    async def delete_chapters(self, project_id: str, chapter_numbers: Iterable[int]) -> None:
        """删除章节"""
        await self._chapter_version_service.delete_chapters(project_id, chapter_numbers)

    # ------------------------------------------------------------------
    # 项目状态检查
    # ------------------------------------------------------------------

    async def check_and_update_completion_status(self, project_id: str, user_id: int) -> None:
        """检查并更新项目完成状态，支持升级和降级

        升级: 当所有章节都已选择版本时，从 WRITING 升级到 COMPLETED
        降级: 当已完成章节数少于总章节数时，从 COMPLETED 降级到 WRITING
              (Bug 19 修复: 删除章节后项目状态能够正确回退)

        注意：空白项目（跳过灵感对话创建的项目）没有预设的章节总数，
        因此不会自动转换状态。用户需要手动管理空白项目的状态。
        """
        project_schema = await self.get_project_schema(project_id, user_id)
        project = await self.repo.get_by_id(project_id)

        # 空白项目没有蓝图或章节总数，跳过自动状态检查
        if not project_schema.blueprint or not project_schema.blueprint.total_chapters:
            return

        total_chapters = project_schema.blueprint.total_chapters
        completed_chapters = sum(1 for ch in project_schema.chapters if ch.selected_version)

        # 升级: WRITING -> COMPLETED
        if completed_chapters == total_chapters and project.status == ProjectStatus.WRITING.value:
            await self.transition_project_status(project, ProjectStatus.COMPLETED.value)
            logger.info("项目 %s 所有章节完成，状态更新为 %s", project_id, ProjectStatus.COMPLETED.value)

        # Bug 19 修复: 降级: COMPLETED -> WRITING (当章节被删除后)
        elif completed_chapters < total_chapters and project.status == ProjectStatus.COMPLETED.value:
            await self.transition_project_status(project, ProjectStatus.WRITING.value)
            logger.info(
                "项目 %s 完成章节数(%d)少于总章节数(%d)，状态降级为 %s",
                project_id, completed_chapters, total_chapters, ProjectStatus.WRITING.value
            )

    # ------------------------------------------------------------------
    # 向量库清理
    # ------------------------------------------------------------------

    async def _cleanup_vector_store(self, project_id: str, chapter_numbers: List[int]) -> None:
        """
        清理向量库中的章节数据

        在状态回退时调用，确保RAG检索不会返回已删除章节的内容。

        Args:
            project_id: 项目ID
            chapter_numbers: 要清理的章节号列表
        """
        from ..core.config import settings

        if not settings.vector_store_enabled or not chapter_numbers:
            return

        try:
            from .vector_store_service import VectorStoreService
            from .chapter_ingest_service import ChapterIngestionService

            vector_store = VectorStoreService()
            ingest_service = ChapterIngestionService(
                llm_service=None,
                vector_store=vector_store
            )
            await ingest_service.delete_chapters(project_id, list(chapter_numbers))
            logger.info(
                "向量库清理完成: project_id=%s chapters=%s",
                project_id,
                chapter_numbers
            )
        except Exception as exc:
            # 向量库清理失败不应阻断主流程，仅记录警告
            logger.warning(
                "状态回退时向量库清理失败 (project_id=%s): %s",
                project_id,
                exc
            )
