from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.state_machine import ProjectStatus, ProjectStateMachine, InvalidStateTransitionError
from ..utils.content_normalizer import normalize_version_content
from ..serializers.novel_serializer import NovelSerializer
from ..models import (
    Chapter,
    ChapterEvaluation,
    ChapterOutline,
    ChapterVersion,
    NovelBlueprint,
    NovelProject,
)
from ..repositories.novel_repository import NovelRepository
from ..repositories.chapter_repository import (
    ChapterRepository,
    ChapterVersionRepository,
    ChapterEvaluationRepository,
    ChapterOutlineRepository,
)
from ..schemas.novel import (
    Chapter as ChapterSchema,
    ChapterGenerationStatus,
    ChapterOutline as ChapterOutlineSchema,
    NovelProject as NovelProjectSchema,
    NovelProjectSummary,
    NovelSectionResponse,
    NovelSectionType,
    PartOutline as PartOutlineSchema,
)

logger = logging.getLogger(__name__)


class NovelService:
    """小说项目服务，基于拆表后的结构提供聚合与业务操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NovelRepository(session)
        # 初始化章节相关Repository
        self.chapter_repo = ChapterRepository(session)
        self.chapter_version_repo = ChapterVersionRepository(session)
        self.chapter_evaluation_repo = ChapterEvaluationRepository(session)
        self.chapter_outline_repo = ChapterOutlineRepository(session)

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
        # 记录状态转换上下文（project_id, user_id, 当前状态, 目标状态）
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

        # 记录转换成功
        logger.info(
            "状态转换成功: project_id=%s 新状态=%s",
            project.id,
            project.status
        )

    def _is_backward_transition(self, current_status: str, new_status: str) -> bool:
        """
        判断是否为回退转换

        回退规则：状态机允许的反向转换
        - writing -> chapter_outlines_ready（回退修改大纲）
        - chapter_outlines_ready -> blueprint_ready/part_outlines_ready（回退重新规划）
        - blueprint_ready -> draft（回退重新对话）

        Args:
            current_status: 当前状态
            new_status: 目标状态

        Returns:
            bool: 是否为回退转换
        """
        # 定义回退映射：当前状态 -> 被认为是回退的目标状态列表
        backward_transitions = {
            ProjectStatus.WRITING: [ProjectStatus.CHAPTER_OUTLINES_READY],
            ProjectStatus.CHAPTER_OUTLINES_READY: [
                ProjectStatus.BLUEPRINT_READY,
                ProjectStatus.PART_OUTLINES_READY,
            ],
            ProjectStatus.BLUEPRINT_READY: [ProjectStatus.DRAFT],
        }

        return new_status in backward_transitions.get(current_status, [])

    async def _cleanup_data_for_backward_transition(
        self,
        project: NovelProject,
        new_status: str
    ) -> None:
        """
        清理回退转换时的相关数据

        注意：此方法不commit，由transition_project_status统一commit

        Args:
            project: 项目实例
            new_status: 目标状态
        """
        project_id = project.id
        current_status = project.status

        # 场景1：writing -> chapter_outlines_ready
        # 清理：删除所有已生成的章节（因为要重新调整大纲）
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
                await self.delete_chapters(project_id, chapter_numbers)
                logger.info(
                    "项目 %s 回退时删除了 %d 个章节",
                    project_id,
                    len(chapter_numbers)
                )

        # 场景2：chapter_outlines_ready -> blueprint_ready/part_outlines_ready
        # 清理：删除所有章节大纲（因为要重新规划结构）
        elif (
            current_status == ProjectStatus.CHAPTER_OUTLINES_READY
            and new_status in [ProjectStatus.BLUEPRINT_READY, ProjectStatus.PART_OUTLINES_READY]
        ):
            logger.warning(
                "项目 %s 从大纲状态回退，将删除所有章节大纲",
                project_id
            )
            outline_count = await self.chapter_outline_repo.count_by_project(project_id)
            if outline_count > 0:
                await self.chapter_outline_repo.delete_by_project(project_id)
                logger.info(
                    "项目 %s 回退时删除了 %d 个章节大纲",
                    project_id,
                    outline_count
                )

        # 场景3：blueprint_ready -> draft
        # 清理：由BlueprintService.cleanup_old_blueprint_data处理
        # 这里不需要额外处理，因为重新生成蓝图时会自动清理
        elif (
            current_status == ProjectStatus.BLUEPRINT_READY
            and new_status == ProjectStatus.DRAFT
        ):
            logger.info(
                "项目 %s 回退到草稿状态，蓝图数据将在重新生成时清理",
                project_id
            )

    # ------------------------------------------------------------------
    # 项目与摘要
    # ------------------------------------------------------------------
    async def create_project(self, user_id: int, title: str, initial_prompt: str) -> NovelProject:
        """
        创建新项目

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            user_id: 用户ID
            title: 项目标题
            initial_prompt: 初始提示词

        Returns:
            NovelProject: 创建的项目对象
        """
        project = NovelProject(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            initial_prompt=initial_prompt,
        )
        blueprint = NovelBlueprint(project=project)
        self.session.add_all([project, blueprint])
        await self.session.flush()  # 刷新到数据库以获取ID，但不提交事务
        await self.session.refresh(project)
        return project

    async def ensure_project_owner(self, project_id: str, user_id: int) -> NovelProject:
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
        if project.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该项目")
        return project

    async def get_project_schema(self, project_id: str, user_id: Optional[int] = None) -> NovelProjectSchema:
        """
        获取项目Schema

        Args:
            project_id: 项目ID
            user_id: 用户ID，如果提供则检查权限，否则为管理员模式

        Returns:
            NovelProjectSchema: 项目Schema
        """
        if user_id is not None:
            project = await self.ensure_project_owner(project_id, user_id)
        else:
            project = await self.repo.get_by_id(project_id)
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
        return await NovelSerializer.serialize_project(project)

    async def get_section_data(
        self,
        project_id: str,
        section: NovelSectionType,
        user_id: Optional[int] = None,
    ) -> NovelSectionResponse:
        """
        获取项目的某个section数据

        Args:
            project_id: 项目ID
            section: Section类型
            user_id: 用户ID，如果提供则检查权限，否则为管理员模式

        Returns:
            NovelSectionResponse: Section响应数据
        """
        if user_id is not None:
            project = await self.ensure_project_owner(project_id, user_id)
        else:
            project = await self.repo.get_by_id(project_id)
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
        return NovelSerializer.build_section_response(project, section)

    async def get_chapter_schema(
        self,
        project_id: str,
        chapter_number: int,
        user_id: Optional[int] = None,
    ) -> ChapterSchema:
        """
        获取章节Schema

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            user_id: 用户ID，如果提供则检查权限，否则为管理员模式

        Returns:
            ChapterSchema: 章节Schema
        """
        if user_id is not None:
            project = await self.ensure_project_owner(project_id, user_id)
        else:
            project = await self.repo.get_by_id(project_id)
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
        return NovelSerializer.build_chapter_schema(project, chapter_number)

    async def list_projects_for_user(self, user_id: int) -> List[NovelProjectSummary]:
        projects = await self.repo.list_by_user(user_id)
        summaries: List[NovelProjectSummary] = []
        for project in projects:
            blueprint = project.blueprint
            genre = blueprint.genre if blueprint and blueprint.genre else "未知"
            outlines = project.outlines
            chapters = project.chapters
            total = len(outlines) or len(chapters)
            completed = sum(1 for chapter in chapters if chapter.selected_version_id)
            summaries.append(
                NovelProjectSummary(
                    id=project.id,
                    title=project.title,
                    genre=genre,
                    last_edited=project.updated_at.isoformat() if project.updated_at else "未知",
                    completed_chapters=completed,
                    total_chapters=total,
                    status=project.status,  # 添加状态字段
                )
            )
        return summaries

    async def delete_projects(self, project_ids: List[str], user_id: int) -> None:
        """
        删除项目（批量）

        注意：此方法不commit，调用方需要在适当时候commit

        使用SQL级别的DELETE语句确保删除操作执行，
        依赖数据库外键CASCADE自动清理关联数据。

        Args:
            project_ids: 要删除的项目ID列表
            user_id: 用户ID（用于权限验证）
        """
        from sqlalchemy import delete

        # 先验证所有项目的所有权
        for pid in project_ids:
            await self.ensure_project_owner(pid, user_id)

        # 使用SQL DELETE直接删除（外键CASCADE会自动删除子记录）
        await self.session.execute(
            delete(NovelProject).where(NovelProject.id.in_(project_ids))
        )

    async def count_projects(self) -> int:
        """统计所有项目数量"""
        return await self.repo.count_all()

    # ------------------------------------------------------------------
    # 章节与版本
    # ------------------------------------------------------------------
    async def get_outline(self, project_id: str, chapter_number: int) -> Optional[ChapterOutline]:
        """
        获取章节大纲

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            章节大纲实例，不存在返回None
        """
        return await self.chapter_outline_repo.get_by_project_and_number(project_id, chapter_number)

    async def count_chapter_outlines(self, project_id: str) -> int:
        """
        统计项目的章节大纲数量

        Args:
            project_id: 项目ID

        Returns:
            章节大纲数量
        """
        return await self.chapter_outline_repo.count_by_project(project_id)

    async def get_or_create_chapter(self, project_id: str, chapter_number: int) -> Chapter:
        """
        获取或创建章节

        注意：此方法不commit，调用方需要在适当时候commit
        """
        chapter = await self.chapter_repo.get_or_create(project_id, chapter_number)
        return chapter

    async def replace_chapter_versions(self, chapter: Chapter, contents: List[str], metadata: Optional[List[Dict]] = None) -> List[ChapterVersion]:
        """
        替换章节的所有版本

        注意：此方法不commit，调用方需要在适当时候commit
        """
        # 准备版本数据
        versions_data = []
        for index, content in enumerate(contents):
            extra = metadata[index] if metadata and index < len(metadata) else None
            text_content = normalize_version_content(content, extra)
            versions_data.append({
                "content": text_content,
                "metadata": None,
                "version_label": f"v{index+1}",
            })

        # 使用Repository替换所有版本
        versions = await self.chapter_version_repo.replace_all(chapter.id, versions_data)

        # 更新章节状态
        chapter.status = ChapterGenerationStatus.WAITING_FOR_CONFIRM.value
        await self.session.refresh(chapter)
        await self._touch_project(chapter.project_id)
        return versions

    async def select_chapter_version(self, chapter: Chapter, version_index: int) -> ChapterVersion:
        """
        选择章节版本

        注意：此方法不commit，调用方需要在适当时候commit
        """
        versions = sorted(chapter.versions, key=lambda item: item.created_at)
        if not versions or version_index < 0 or version_index >= len(versions):
            raise HTTPException(status_code=400, detail="版本索引无效")

        selected = versions[version_index]
        chapter.selected_version_id = selected.id
        chapter.selected_version = selected
        chapter.status = ChapterGenerationStatus.SUCCESSFUL.value
        chapter.word_count = len(selected.content or "")

        # 注意：不要在这里调用 refresh()，因为还没有 commit，
        # refresh 会从数据库重新加载数据，覆盖我们刚设置的值！
        await self._touch_project(chapter.project_id)
        return selected

    async def add_chapter_evaluation(self, chapter: Chapter, version: Optional[ChapterVersion], feedback: str, decision: Optional[str] = None) -> None:
        """
        添加章节评价

        注意：此方法不commit，调用方需要在适当时候commit
        """
        evaluation = ChapterEvaluation(
            chapter_id=chapter.id,
            version_id=version.id if version else None,
            feedback=feedback,
            decision=decision,
        )
        self.session.add(evaluation)  # 这里保留直接添加，因为是临时对象
        chapter.status = ChapterGenerationStatus.WAITING_FOR_CONFIRM.value
        await self.session.refresh(chapter)
        await self._touch_project(chapter.project_id)

    async def delete_chapters(self, project_id: str, chapter_numbers: Iterable[int]) -> None:
        """
        删除章节

        注意：此方法不commit，调用方需要在适当时候commit
        """
        await self.session.execute(
            delete(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number.in_(list(chapter_numbers)),
            )
        )
        await self.session.execute(
            delete(ChapterOutline).where(
                ChapterOutline.project_id == project_id,
                ChapterOutline.chapter_number.in_(list(chapter_numbers)),
            )
        )
        await self._touch_project(project_id)

    async def _touch_project(self, project_id: str) -> None:
        """
        更新项目的updated_at时间戳

        注意：此方法不commit，调用方需要在适当时候commit
        """
        await self.session.execute(
            update(NovelProject)
            .where(NovelProject.id == project_id)
            .values(updated_at=datetime.now(timezone.utc))
        )

    # ------------------------------------------------------------------
    # 项目状态管理
    # ------------------------------------------------------------------
    async def check_and_update_completion_status(self, project_id: str, user_id: int) -> None:
        """
        检查项目是否完成，如果所有章节都已选择版本，更新状态为completed

        Args:
            project_id: 项目ID
            user_id: 用户ID（用于权限验证）
        """
        import logging
        logger = logging.getLogger(__name__)

        # 获取项目完整信息
        project_schema = await self.get_project_schema(project_id, user_id)
        project = await self.repo.get_by_id(project_id)

        # 检查蓝图是否存在并且有total_chapters
        if not project_schema.blueprint or not project_schema.blueprint.total_chapters:
            return

        total_chapters = project_schema.blueprint.total_chapters

        # 统计已完成的章节数（有选中版本的章节）
        completed_chapters = sum(1 for ch in project_schema.chapters if ch.selected_version)

        # 如果所有章节都完成了，且当前状态是writing，则更新为completed
        if completed_chapters == total_chapters and project.status == ProjectStatus.WRITING.value:
            await self.transition_project_status(project, ProjectStatus.COMPLETED.value)
            logger.info("项目 %s 所有章节完成，状态更新为 %s", project_id, ProjectStatus.COMPLETED.value)
