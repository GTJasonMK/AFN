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
        dialogue_language: str = "chinese",  # Bug 30 修复: 添加对话语言参数
        analysis_data: Optional[dict] = None,  # 分析数据
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
            dialogue_language: 对话语言
            analysis_data: 分析数据（章节信息提取和页面规划结果）

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
            existing.dialogue_language = dialogue_language  # Bug 30 修复
            existing.analysis_data = analysis_data  # 保存分析数据
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
                dialogue_language=dialogue_language,  # Bug 30 修复
                analysis_data=analysis_data,  # 保存分析数据
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

    async def save_result(
        self,
        chapter_id: int,
        result_data: dict,
        analysis_data: Optional[dict] = None,
    ) -> ChapterMangaPrompt:
        """
        保存漫画提示词生成结果

        将 MangaPromptResult.to_dict() 的数据保存到数据库。

        Args:
            chapter_id: 章节ID
            result_data: MangaPromptResult.to_dict() 返回的字典
            analysis_data: 分析数据（章节信息提取和页面规划结果）

        Returns:
            漫画提示词实例
        """
        # 从 result_data 中提取字段
        style = result_data.get("style", "manga")
        total_pages = result_data.get("total_pages", 0)
        total_panels = result_data.get("total_panels", 0)
        character_profiles = result_data.get("character_profiles", {})
        # Bug 30 修复: 提取对话语言
        dialogue_language = result_data.get("dialogue_language", "chinese")

        # 将 pages 转换为 scenes 和 panels 格式
        pages = result_data.get("pages", [])
        scenes = []  # 页面信息作为场景存储
        panels = []  # 扁平化的画格列表

        for page_data in pages:
            page_number = page_data.get("page_number", 0)

            # 构建场景（页面）信息
            scene_info = {
                "page_number": page_number,
                "layout_description": page_data.get("layout_description", ""),
                "reading_flow": page_data.get("reading_flow", "right_to_left"),
                "panel_count": len(page_data.get("panels", [])),
            }
            scenes.append(scene_info)

            # 收集画格信息
            for panel_data in page_data.get("panels", []):
                panel_data["page_number"] = page_number  # 确保页码正确
                panels.append(panel_data)

        # 使用 upsert 保存
        return await self.upsert(
            chapter_id=chapter_id,
            style=style,
            total_pages=total_pages,
            total_panels=total_panels,
            character_profiles=character_profiles,
            scenes=scenes,
            panels=panels,
            generation_status="completed",
            dialogue_language=dialogue_language,  # Bug 30 修复: 传递对话语言
            analysis_data=analysis_data,  # 保存分析数据
        )

    async def get_result(self, chapter_id: int) -> Optional[dict]:
        """
        获取漫画提示词生成结果

        返回可以用于 MangaPromptResult.from_dict() 的字典格式。

        Args:
            chapter_id: 章节ID

        Returns:
            结果字典，不存在或未完成返回None
        """
        manga_prompt = await self.get_by_chapter_id(chapter_id)

        if not manga_prompt:
            return None

        # 只返回已完成的结果
        if manga_prompt.generation_status != "completed":
            return None

        # 将 scenes 和 panels 转换回 pages 格式
        panels_by_page = {}
        for panel in manga_prompt.panels or []:
            page_num = panel.get("page_number", 1)
            if page_num not in panels_by_page:
                panels_by_page[page_num] = []
            panels_by_page[page_num].append(panel)

        # 构建 pages 列表
        pages = []
        for scene in manga_prompt.scenes or []:
            page_number = scene.get("page_number", 0)
            page_data = {
                "page_number": page_number,
                "panels": panels_by_page.get(page_number, []),
                "layout_description": scene.get("layout_description", ""),
                "reading_flow": scene.get("reading_flow", "right_to_left"),
            }
            pages.append(page_data)

        # 按页码排序
        pages.sort(key=lambda p: p.get("page_number", 0))

        return {
            "style": manga_prompt.style,
            "pages": pages,
            "total_pages": manga_prompt.total_pages,
            "total_panels": manga_prompt.total_panels,
            "character_profiles": manga_prompt.character_profiles or {},
            # Bug 30 修复: 返回对话语言
            "dialogue_language": manga_prompt.dialogue_language or "chinese",
            # 分析数据
            "analysis_data": manga_prompt.analysis_data,
        }
