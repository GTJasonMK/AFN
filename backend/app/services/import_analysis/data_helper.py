"""
数据库操作辅助

提供导入分析相关的数据库操作方法。
"""

import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.novel import (
    NovelProject, NovelBlueprint, Chapter, ChapterVersion,
    ChapterOutline, BlueprintCharacter, BlueprintRelationship,
)
from ...models.part_outline import PartOutline
from ...utils.content_normalizer import count_chinese_characters

from .models import ChapterSummary

logger = logging.getLogger(__name__)


class DataHelper:
    """
    数据库操作辅助类

    封装导入分析相关的所有数据库操作
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_project(self, project_id: str) -> Optional[NovelProject]:
        """获取项目"""
        result = await self.session.execute(
            select(NovelProject).where(NovelProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_project_with_chapters(self, project_id: str) -> Optional[NovelProject]:
        """获取项目及其章节"""
        result = await self.session.execute(
            select(NovelProject)
            .where(NovelProject.id == project_id)
            .options(
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
                selectinload(NovelProject.outlines),
            )
        )
        return result.scalar_one_or_none()

    async def get_chapter_title(self, chapter: Chapter) -> str:
        """获取章节标题"""
        result = await self.session.execute(
            select(ChapterOutline)
            .where(ChapterOutline.project_id == chapter.project_id)
            .where(ChapterOutline.chapter_number == chapter.chapter_number)
        )
        outline = result.scalar_one_or_none()
        return outline.title if outline else f"第{chapter.chapter_number}章"

    async def upsert_chapter_outline(
        self,
        project_id: str,
        chapter_number: int,
        title: str,
        summary: str,
    ) -> ChapterOutline:
        """创建或更新章节大纲"""
        result = await self.session.execute(
            select(ChapterOutline)
            .where(ChapterOutline.project_id == project_id)
            .where(ChapterOutline.chapter_number == chapter_number)
        )
        outline = result.scalar_one_or_none()

        if outline:
            outline.title = title
            outline.summary = summary
        else:
            outline = ChapterOutline(
                project_id=project_id,
                chapter_number=chapter_number,
                title=title,
                summary=summary,
            )
            self.session.add(outline)

        await self.session.flush()
        return outline

    async def upsert_chapter(
        self,
        project_id: str,
        chapter_number: int,
        content: str,
    ) -> Chapter:
        """创建或更新章节"""
        result = await self.session.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .where(Chapter.chapter_number == chapter_number)
            .options(selectinload(Chapter.versions))
        )
        chapter = result.scalar_one_or_none()

        if not chapter:
            chapter = Chapter(
                project_id=project_id,
                chapter_number=chapter_number,
            )
            self.session.add(chapter)
            await self.session.flush()

        # 创建新版本
        version = ChapterVersion(
            chapter_id=chapter.id,
            version_label="imported",
            provider="imported",
            content=content,
        )
        self.session.add(version)
        await self.session.flush()

        # 设置选中版本和状态
        chapter.selected_version_id = version.id
        chapter.word_count = count_chinese_characters(content)
        chapter.status = "successful" if content.strip() else "waiting_for_confirm"

        return chapter

    async def get_chapter_outlines(self, project_id: str) -> List[ChapterOutline]:
        """获取所有章节大纲"""
        result = await self.session.execute(
            select(ChapterOutline)
            .where(ChapterOutline.project_id == project_id)
            .order_by(ChapterOutline.chapter_number)
        )
        return list(result.scalars().all())

    async def load_existing_summaries(self, project_id: str) -> List[ChapterSummary]:
        """从现有大纲加载摘要（用于断点续传跳过阶段时）"""
        outlines = await self.get_chapter_outlines(project_id)
        summaries = []
        for outline in outlines:
            summaries.append(ChapterSummary(
                chapter_number=outline.chapter_number,
                title=outline.title,
                summary=outline.summary or "",
                key_characters=[],
                key_events=[],
            ))
        return summaries

    async def load_existing_part_outlines(self, project_id: str) -> List[PartOutline]:
        """加载现有分部大纲（用于断点续传跳过阶段时）"""
        result = await self.session.execute(
            select(PartOutline)
            .where(PartOutline.project_id == project_id)
            .order_by(PartOutline.part_number)
        )
        return list(result.scalars().all())

    async def save_blueprint(
        self,
        project_id: str,
        data: Dict[str, Any],
        total_chapters: int,
        needs_part_outlines: bool,
    ) -> None:
        """保存蓝图数据

        确保与正常创作流程生成的蓝图结构一致，包括：
        - 所有基础字段（title, genre, style, tone等）
        - 角色信息（包含 relationship_to_protagonist）
        - 关系信息
        - 世界观设定
        """
        # 检查是否已有蓝图
        result = await self.session.execute(
            select(NovelBlueprint).where(NovelBlueprint.project_id == project_id)
        )
        blueprint = result.scalar_one_or_none()

        if not blueprint:
            blueprint = NovelBlueprint(project_id=project_id)
            self.session.add(blueprint)

        # 更新蓝图字段
        blueprint.title = data.get("title", "")
        blueprint.genre = data.get("genre", "")
        blueprint.style = data.get("style", "")
        blueprint.tone = data.get("tone", "")
        blueprint.target_audience = data.get("target_audience", "")
        blueprint.one_sentence_summary = data.get("one_sentence_summary", "")
        blueprint.full_synopsis = data.get("full_synopsis", "")
        blueprint.world_setting = data.get("world_setting", {})
        blueprint.total_chapters = total_chapters
        blueprint.needs_part_outlines = needs_part_outlines

        # 先删除旧角色
        await self.session.execute(
            delete(BlueprintCharacter).where(BlueprintCharacter.project_id == project_id)
        )

        # 保存新角色
        characters = data.get("characters", [])
        for i, char_data in enumerate(characters):
            char = BlueprintCharacter(
                project_id=project_id,
                name=char_data.get("name", ""),
                identity=char_data.get("identity", ""),
                personality=char_data.get("personality", ""),
                appearance=char_data.get("appearance", ""),  # 外貌特征
                goals=char_data.get("goals", ""),
                abilities=char_data.get("abilities", ""),
                relationship_to_protagonist=char_data.get("relationship_to_protagonist", ""),
                position=i,
            )
            self.session.add(char)

        # 先删除旧关系
        await self.session.execute(
            delete(BlueprintRelationship).where(BlueprintRelationship.project_id == project_id)
        )

        # 保存新关系
        relationships = data.get("relationships", [])
        for i, rel_data in enumerate(relationships):
            rel = BlueprintRelationship(
                project_id=project_id,
                character_from=rel_data.get("character_from", ""),
                character_to=rel_data.get("character_to", ""),
                description=rel_data.get("description", ""),
                position=i,
            )
            self.session.add(rel)

        await self.session.flush()


__all__ = [
    "DataHelper",
]
