"""
漫画提示词数据访问层

提供章节漫画提示词的CRUD操作。
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.novel import ChapterMangaPrompt, Chapter


class MangaPromptRepository(BaseRepository[ChapterMangaPrompt]):
    """漫画提示词Repository"""

    model = ChapterMangaPrompt

    async def get_by_chapter_id(self, chapter_id: int) -> Optional[ChapterMangaPrompt]:
        """
        根据章节ID获取漫画提示词

        Args:
            chapter_id: 章节ID

        Returns:
            漫画提示词实例，不存在返回None
        """
        stmt = select(ChapterMangaPrompt).where(
            ChapterMangaPrompt.chapter_id == chapter_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_project_and_chapter(
        self,
        project_id: str,
        chapter_number: int
    ) -> Optional[ChapterMangaPrompt]:
        """
        根据项目ID和章节号获取漫画提示词

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            漫画提示词实例，不存在返回None
        """
        # 先查找章节
        chapter_stmt = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.chapter_number == chapter_number
        ).options(
            selectinload(Chapter.manga_prompt)
        )
        result = await self.session.execute(chapter_stmt)
        chapter = result.scalars().first()

        if chapter:
            return chapter.manga_prompt
        return None

    async def delete_by_chapter_id(self, chapter_id: int) -> bool:
        """
        根据章节ID删除漫画提示词

        Args:
            chapter_id: 章节ID

        Returns:
            是否删除成功
        """
        manga_prompt = await self.get_by_chapter_id(chapter_id)
        if manga_prompt:
            await self.delete(manga_prompt)
            return True
        return False

    async def upsert(
        self,
        chapter_id: int,
        style: str,
        total_pages: int,
        total_panels: int,
        character_profiles: dict,
        scenes: list,
        panels: list,
        source_version_id: Optional[int] = None,
        generation_status: str = "completed",
    ) -> ChapterMangaPrompt:
        """
        创建或更新漫画提示词

        如果已存在则更新，不存在则创建。

        Args:
            chapter_id: 章节ID
            style: 漫画风格
            total_pages: 总页数
            total_panels: 总画格数
            character_profiles: 角色外观配置
            scenes: 场景列表
            panels: 画格提示词列表
            source_version_id: 源版本ID
            generation_status: 生成状态

        Returns:
            漫画提示词实例
        """
        existing = await self.get_by_chapter_id(chapter_id)

        if existing:
            # 更新现有记录
            existing.style = style
            existing.total_pages = total_pages
            existing.total_panels = total_panels
            existing.character_profiles = character_profiles
            existing.scenes = scenes
            existing.panels = panels
            existing.source_version_id = source_version_id
            existing.generation_status = generation_status
            # 完成时清除断点数据
            if generation_status == "completed":
                existing.checkpoint_data = None
                existing.generation_progress = None
            await self.session.flush()
            return existing
        else:
            # 创建新记录
            manga_prompt = ChapterMangaPrompt(
                chapter_id=chapter_id,
                style=style,
                total_pages=total_pages,
                total_panels=total_panels,
                character_profiles=character_profiles,
                scenes=scenes,
                panels=panels,
                source_version_id=source_version_id,
                generation_status=generation_status,
            )
            return await self.add(manga_prompt)

    async def save_checkpoint(
        self,
        chapter_id: int,
        status: str,
        progress: dict,
        checkpoint_data: dict,
        style: str = "manga",
        source_version_id: Optional[int] = None,
    ) -> ChapterMangaPrompt:
        """
        保存生成断点

        Args:
            chapter_id: 章节ID
            status: 生成状态
            progress: 进度信息 {stage, current, total, message}
            checkpoint_data: 断点数据
            style: 漫画风格
            source_version_id: 源版本ID

        Returns:
            漫画提示词实例
        """
        existing = await self.get_by_chapter_id(chapter_id)

        if existing:
            existing.generation_status = status
            existing.generation_progress = progress
            existing.checkpoint_data = checkpoint_data
            existing.source_version_id = source_version_id
            await self.session.flush()
            return existing
        else:
            manga_prompt = ChapterMangaPrompt(
                chapter_id=chapter_id,
                style=style,
                generation_status=status,
                generation_progress=progress,
                checkpoint_data=checkpoint_data,
                source_version_id=source_version_id,
            )
            return await self.add(manga_prompt)

    async def get_checkpoint(
        self,
        project_id: str,
        chapter_number: int
    ) -> Optional[dict]:
        """
        获取生成断点信息

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            断点信息字典，包含 status, progress, checkpoint_data
        """
        manga_prompt = await self.get_by_project_and_chapter(project_id, chapter_number)

        if not manga_prompt:
            return None

        # 只有未完成的任务才返回断点
        if manga_prompt.generation_status in ("completed", "pending"):
            return None

        return {
            "status": manga_prompt.generation_status,
            "progress": manga_prompt.generation_progress,
            "checkpoint_data": manga_prompt.checkpoint_data,
            "style": manga_prompt.style,
        }

    async def clear_checkpoint(
        self,
        project_id: str,
        chapter_number: int
    ) -> bool:
        """
        清除生成断点状态（只清除锁定状态，保留已有数据）

        用于处理卡住的生成任务，允许重新开始生成而不丢失已有数据。

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            是否成功清除
        """
        manga_prompt = await self.get_by_project_and_chapter(project_id, chapter_number)

        if not manga_prompt:
            return False

        # 只清除checkpoint相关状态，保留已有的panels等数据
        manga_prompt.generation_status = "pending"
        manga_prompt.generation_progress = None
        manga_prompt.checkpoint_data = None

        await self.session.flush()
        return True
