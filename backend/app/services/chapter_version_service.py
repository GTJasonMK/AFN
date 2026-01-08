"""
章节版本管理服务

负责章节版本的创建、选择、评价等操作。
从NovelService中拆分出来，遵循单一职责原则。
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, TYPE_CHECKING

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..exceptions import InvalidParameterError
from ..models import Chapter, ChapterEvaluation, ChapterOutline, ChapterVersion, NovelProject
from ..models.novel import CharacterStateIndex, ForeshadowingIndex
from ..repositories.chapter_repository import (
    ChapterRepository,
    ChapterVersionRepository,
    ChapterEvaluationRepository,
    ChapterOutlineRepository,
)
from ..schemas.novel import ChapterGenerationStatus
from ..utils.content_normalizer import count_chinese_characters

if TYPE_CHECKING:
    from .llm_service import LLMService

logger = logging.getLogger(__name__)


class ChapterVersionService:
    """
    章节版本管理服务

    负责：
    - 章节版本的创建和替换
    - 版本选择
    - 章节评价管理
    - 章节删除和清理

    从NovelService中拆分，职责更加单一。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化ChapterVersionService

        Args:
            session: 数据库会话
        """
        self.session = session
        self.chapter_repo = ChapterRepository(session)
        self.chapter_version_repo = ChapterVersionRepository(session)
        self.chapter_evaluation_repo = ChapterEvaluationRepository(session)
        self.chapter_outline_repo = ChapterOutlineRepository(session)

    # ------------------------------------------------------------------
    # 章节基础操作
    # ------------------------------------------------------------------

    async def get_or_create_chapter(self, project_id: str, chapter_number: int) -> Chapter:
        """
        获取或创建章节

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            Chapter: 章节实例
        """
        return await self.chapter_repo.get_or_create(project_id, chapter_number)

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

    # ------------------------------------------------------------------
    # 版本管理
    # ------------------------------------------------------------------

    async def replace_chapter_versions(
        self,
        chapter: Chapter,
        contents: List[str],
        metadata: Optional[List[Dict]] = None
    ) -> List[ChapterVersion]:
        """
        替换章节的所有版本

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            chapter: 章节实例
            contents: 版本内容列表（已经由version_processor提取好的纯文本）
            metadata: 版本元数据列表（可选，仅用于记录，不再用于提取内容）

        Returns:
            List[ChapterVersion]: 创建的版本列表
        """
        # 准备版本数据
        # contents 已经是 version_processor._extract_content_from_dict 提取的纯文本
        # 不需要再通过 normalize_version_content 处理
        versions_data = []
        for index, content in enumerate(contents):
            # 确保 content 是字符串
            if not isinstance(content, str):
                logger.warning(
                    "[DEBUG] replace_chapter_versions - index=%d, content不是字符串，类型=%s",
                    index, type(content).__name__
                )
                content = str(content) if content else ""

            logger.info(
                "[DEBUG] replace_chapter_versions - index=%d, content长度=%d, 前100字符=%s",
                index, len(content), repr(content[:100]) if content else "EMPTY"
            )

            # Bug 6 修复: 使用传入的 metadata 参数，而非硬编码为 None
            version_metadata = None
            if metadata and index < len(metadata):
                version_metadata = metadata[index]

            versions_data.append({
                "content": content,
                "metadata": version_metadata,
                "version_label": f"v{index+1}",
            })

        # 使用Repository替换所有版本
        versions = await self.chapter_version_repo.replace_all(chapter.id, versions_data)

        # 更新章节状态
        chapter.status = ChapterGenerationStatus.WAITING_FOR_CONFIRM.value
        await self.session.flush()
        await self._touch_project(chapter.project_id)

        return versions

    async def select_chapter_version(
        self,
        chapter: Chapter,
        version_index: int,
        llm_service: Optional["LLMService"] = None,
    ) -> ChapterVersion:
        """
        选择章节版本

        当选择新版本时，会清理旧版本的索引数据并重新建立索引。
        这确保了角色状态和伏笔索引始终反映当前选中版本的内容。

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            chapter: 章节实例
            version_index: 版本索引
            llm_service: LLM服务（用于重新索引，可选）

        Returns:
            ChapterVersion: 被选中的版本

        Raises:
            InvalidParameterError: 版本索引无效
        """
        versions = sorted(chapter.versions, key=lambda item: item.created_at)
        if not versions or version_index < 0 or version_index >= len(versions):
            raise InvalidParameterError("版本索引无效", "version_index")

        selected = versions[version_index]

        # 检查是否切换了版本（避免重复清理索引）
        old_version_id = chapter.selected_version_id
        is_version_changed = old_version_id is not None and old_version_id != selected.id

        # 更新章节的选中版本
        chapter.selected_version_id = selected.id
        chapter.selected_version = selected
        chapter.status = ChapterGenerationStatus.SUCCESSFUL.value
        chapter.word_count = count_chinese_characters(selected.content or "")

        # 如果版本发生变化，清理旧索引并重新建立索引
        if is_version_changed:
            logger.info(
                "章节版本切换: project=%s chapter=%d old_version=%s new_version=%s",
                chapter.project_id,
                chapter.chapter_number,
                old_version_id,
                selected.id,
            )

            # 清理旧版本的索引数据（角色状态、伏笔）
            from .incremental_indexer import IncrementalIndexer
            indexer = IncrementalIndexer(self.session)
            await indexer.cleanup_chapter_indexes(chapter.project_id, chapter.chapter_number)

            # 如果提供了LLM服务，重新为新版本建立索引
            # 注意：重新索引是异步的且可能耗时较长，这里只做清理
            # 实际的重新索引应该由调用方决定是否执行
            logger.info(
                "已清理章节 %d 的旧版本索引，新版本索引将在章节分析时重建",
                chapter.chapter_number,
            )

        # 注意：主角档案同步已移至RAG入库流程（update_chapter with trigger_rag=True）
        # 版本选择只是确定大致方向，用户可能还需要细调内容后再入库

        await self._touch_project(chapter.project_id)
        return selected

    # ------------------------------------------------------------------
    # 评价管理
    # ------------------------------------------------------------------

    async def add_chapter_evaluation(
        self,
        chapter: Chapter,
        version: Optional[ChapterVersion],
        feedback: str,
        decision: Optional[str] = None
    ) -> ChapterEvaluation:
        """
        添加章节评价

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            chapter: 章节实例
            version: 版本实例（可选）
            feedback: 评价反馈
            decision: 决策（可选）

        Returns:
            ChapterEvaluation: 创建的评价实例
        """
        evaluation = ChapterEvaluation(
            chapter_id=chapter.id,
            version_id=version.id if version else None,
            feedback=feedback,
            decision=decision,
        )
        self.session.add(evaluation)

        # 更新章节状态
        chapter.status = ChapterGenerationStatus.WAITING_FOR_CONFIRM.value
        await self.session.flush()
        await self._touch_project(chapter.project_id)

        return evaluation

    # ------------------------------------------------------------------
    # 删除和清理
    # ------------------------------------------------------------------

    async def delete_chapters(self, project_id: str, chapter_numbers: Iterable[int]) -> None:
        """
        删除章节

        同时清理关联的索引数据（CharacterStateIndex、ForeshadowingIndex）。

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            project_id: 项目ID
            chapter_numbers: 要删除的章节号列表
        """
        chapter_numbers_list = list(chapter_numbers)

        # 1. 删除章节记录
        await self.session.execute(
            delete(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number.in_(chapter_numbers_list),
            )
        )

        # 2. 删除章节大纲
        await self.session.execute(
            delete(ChapterOutline).where(
                ChapterOutline.project_id == project_id,
                ChapterOutline.chapter_number.in_(chapter_numbers_list),
            )
        )

        # 3. 清理角色状态索引
        await self.session.execute(
            delete(CharacterStateIndex).where(
                CharacterStateIndex.project_id == project_id,
                CharacterStateIndex.chapter_number.in_(chapter_numbers_list),
            )
        )

        # 4. 清理伏笔索引
        # 4.1 删除在这些章节埋下的伏笔
        await self.session.execute(
            delete(ForeshadowingIndex).where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.planted_chapter.in_(chapter_numbers_list),
            )
        )

        # 4.2 重置在这些章节回收的伏笔状态（改为pending，而不是删除）
        result = await self.session.execute(
            select(ForeshadowingIndex).where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.resolved_chapter.in_(chapter_numbers_list),
            )
        )
        for fs in result.scalars().all():
            fs.status = "pending"
            fs.resolved_chapter = None
            fs.resolution = None

        await self._touch_project(project_id)

    async def delete_chapter_outlines(self, project_id: str) -> int:
        """
        删除项目的所有章节大纲

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            project_id: 项目ID

        Returns:
            int: 删除的大纲数量
        """
        count = await self.chapter_outline_repo.count_by_project(project_id)
        if count > 0:
            await self.chapter_outline_repo.delete_by_project(project_id)
        return count

    async def reset_chapter(self, project_id: str, chapter_number: int) -> Optional[Chapter]:
        """
        重置章节数据（清空内容、版本等，还原为未生成状态）

        此方法会：
        1. 删除章节的所有版本
        2. 重置章节状态为 not_generated
        3. 清空字数、摘要、分析数据
        4. 清理角色状态索引和伏笔索引中的相关数据

        注意：此方法不commit，调用方需要在适当时候commit
        注意：此方法不清理漫画数据和图片，需要调用方单独处理

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            重置后的章节对象，如果章节不存在则返回None
        """
        # 1. 获取章节
        chapter = await self.chapter_repo.get_by_project_and_number(project_id, chapter_number)
        if not chapter:
            return None

        # 2. 删除该章节的所有版本
        await self.chapter_version_repo.delete_by_chapter(chapter.id)

        # 3. 删除该章节的所有评价
        await self.session.execute(
            delete(ChapterEvaluation).where(ChapterEvaluation.chapter_id == chapter.id)
        )

        # 4. 重置章节字段
        chapter.status = ChapterGenerationStatus.NOT_GENERATED.value
        chapter.word_count = 0
        chapter.selected_version_id = None
        chapter.real_summary = None
        chapter.analysis_data = None

        # 5. 清理角色状态索引
        await self.session.execute(
            delete(CharacterStateIndex).where(
                CharacterStateIndex.project_id == project_id,
                CharacterStateIndex.chapter_number == chapter_number,
            )
        )

        # 6. 清理伏笔索引
        # 6.1 删除在此章节埋下的伏笔
        await self.session.execute(
            delete(ForeshadowingIndex).where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.planted_chapter == chapter_number,
            )
        )

        # 6.2 重置在此章节回收的伏笔状态（改为pending，而不是删除）
        result = await self.session.execute(
            select(ForeshadowingIndex).where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.resolved_chapter == chapter_number,
            )
        )
        for fs in result.scalars().all():
            fs.status = "pending"
            fs.resolved_chapter = None
            fs.resolution = None

        await self.session.flush()
        await self._touch_project(project_id)

        logger.info("章节 %s-%d 已重置为未生成状态", project_id, chapter_number)
        return chapter

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    async def _touch_project(self, project_id: str) -> None:
        """
        更新项目的updated_at时间戳

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            project_id: 项目ID
        """
        await self.session.execute(
            update(NovelProject)
            .where(NovelProject.id == project_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
