"""
小说项目序列化器

负责将ORM模型转换为Pydantic Schema，分离序列化逻辑和业务逻辑。
"""

import json
import logging
from typing import Dict, List, Optional

from ..models.novel import (
    Chapter,
    ChapterOutline,
    NovelProject,
)

logger = logging.getLogger(__name__)

from ..schemas.novel import (
    Blueprint,
    Chapter as ChapterSchema,
    ChapterAnalysisData,
    ChapterGenerationStatus,
    ChapterOutline as ChapterOutlineSchema,
    NovelProject as NovelProjectSchema,
    NovelSectionResponse,
    NovelSectionType,
    PartOutline as PartOutlineSchema,
)


class NovelSerializer:
    """
    小说项目序列化器

    提供统一的序列化接口，将ORM模型转换为API响应的Pydantic Schema。

    职责：
    - 序列化完整项目（包括蓝图、章节、对话历史）
    - 序列化单个区段（概览、世界设定、角色、章节等）
    - 序列化单个章节
    - 构建蓝图Schema

    Example:
        ```python
        serializer = NovelSerializer()

        # 序列化完整项目
        project_schema = await serializer.serialize_project(project)

        # 序列化单个区段
        section_response = serializer.build_section_response(project, NovelSectionType.OVERVIEW)

        # 序列化单个章节
        chapter_schema = serializer.build_chapter_schema(project, chapter_number=1)
        ```
    """

    @staticmethod
    async def serialize_project(project: NovelProject) -> NovelProjectSchema:
        """
        序列化完整项目

        将项目的所有关联数据（蓝图、章节、对话历史）转换为Pydantic Schema。

        Args:
            project: 项目ORM模型（需预加载所有关联数据）

        Returns:
            NovelProjectSchema: 完整的项目Schema
        """
        # 序列化对话历史
        conversations = [
            {"role": convo.role, "content": convo.content}
            for convo in sorted(project.conversations, key=lambda c: c.seq)
        ]

        # 构建蓝图Schema
        blueprint_schema = NovelSerializer.build_blueprint_schema(project)

        # 构建章节Schema列表
        # 注意：只包含已生成的章节（chapters表），不包含仅有大纲的章节
        # 章节大纲数据已包含在 blueprint.chapter_outline 中
        # 性能优化：不包含完整内容，前端通过 GET /api/novels/{id}/chapters/{num} 获取
        outlines_map = {outline.chapter_number: outline for outline in project.outlines}
        chapters_map = {chapter.chapter_number: chapter for chapter in project.chapters}
        chapter_numbers = sorted(chapters_map.keys())

        chapters_schema: List[ChapterSchema] = [
            NovelSerializer.build_chapter_schema(
                project,
                number,
                outlines_map=outlines_map,
                chapters_map=chapters_map,
                include_content=False,  # 不返回完整内容，减少数据量
            )
            for number in chapter_numbers
        ]

        return NovelProjectSchema(
            id=project.id,
            user_id=project.user_id,
            title=project.title,
            initial_prompt=project.initial_prompt or "",
            status=project.status,
            conversation_history=conversations,
            blueprint=blueprint_schema,
            chapters=chapters_schema,
        )

    @staticmethod
    def build_blueprint_schema(project: NovelProject) -> Blueprint:
        """
        构建蓝图Schema

        将项目的蓝图数据、角色、关系、章节纲要等转换为Blueprint Schema。

        Args:
            project: 项目ORM模型

        Returns:
            Blueprint: 蓝图Schema
        """
        blueprint_obj = project.blueprint

        if blueprint_obj:
            return Blueprint(
                title=blueprint_obj.title or "",
                target_audience=blueprint_obj.target_audience or "",
                genre=blueprint_obj.genre or "",
                style=blueprint_obj.style or "",
                tone=blueprint_obj.tone or "",
                one_sentence_summary=blueprint_obj.one_sentence_summary or "",
                full_synopsis=blueprint_obj.full_synopsis or "",
                world_setting=blueprint_obj.world_setting or {},
                characters=[
                    {
                        "name": character.name,
                        "identity": character.identity,
                        "personality": character.personality,
                        "goals": character.goals,
                        "abilities": character.abilities,
                        "relationship_to_protagonist": character.relationship_to_protagonist,
                        **(character.extra or {}),
                    }
                    for character in sorted(project.characters, key=lambda c: c.position)
                ],
                relationships=[
                    {
                        "character_from": relation.character_from,
                        "character_to": relation.character_to,
                        "description": relation.description or "",
                        "relationship_type": getattr(relation, "relationship_type", None),
                    }
                    for relation in sorted(project.relationships_, key=lambda r: r.position)
                ],
                chapter_outline=[
                    ChapterOutlineSchema(
                        chapter_number=outline.chapter_number,
                        title=outline.title,
                        summary=outline.summary or "",
                    )
                    for outline in sorted(project.outlines, key=lambda o: o.chapter_number)
                ],
                needs_part_outlines=blueprint_obj.needs_part_outlines,
                total_chapters=blueprint_obj.total_chapters,
                chapters_per_part=blueprint_obj.chapters_per_part,
                part_outlines=[
                    PartOutlineSchema(
                        part_number=part.part_number,
                        title=part.title or "",
                        start_chapter=part.start_chapter,
                        end_chapter=part.end_chapter,
                        summary=part.summary or "",
                        theme=part.theme or "",
                        key_events=part.key_events or [],
                        character_arcs=part.character_arcs or {},
                        conflicts=part.conflicts or [],
                        ending_hook=part.ending_hook,
                        generation_status=part.generation_status,
                        progress=part.progress,
                    )
                    for part in sorted(project.part_outlines, key=lambda p: p.part_number)
                ],
                avatar_svg=blueprint_obj.avatar_svg,
                avatar_animal=blueprint_obj.avatar_animal,
            )

        # 返回空蓝图
        return Blueprint(
            title="",
            target_audience="",
            genre="",
            style="",
            tone="",
            one_sentence_summary="",
            full_synopsis="",
            world_setting={},
            characters=[],
            relationships=[],
            chapter_outline=[],
            needs_part_outlines=False,
            total_chapters=None,
            chapters_per_part=25,
            part_outlines=[],
        )

    @staticmethod
    def build_section_response(
        project: NovelProject,
        section: NovelSectionType,
    ) -> NovelSectionResponse:
        """
        构建区段响应

        根据请求的区段类型，返回相应的数据片段。

        Args:
            project: 项目ORM模型
            section: 区段类型（概览、世界设定、角色等）

        Returns:
            NovelSectionResponse: 区段响应Schema

        Raises:
            ValueError: 未知的区段类型
        """
        blueprint = NovelSerializer.build_blueprint_schema(project)

        if section == NovelSectionType.OVERVIEW:
            data = {
                "title": project.title,
                "initial_prompt": project.initial_prompt or "",
                "status": project.status,
                "one_sentence_summary": blueprint.one_sentence_summary,
                "target_audience": blueprint.target_audience,
                "genre": blueprint.genre,
                "style": blueprint.style,
                "tone": blueprint.tone,
                "full_synopsis": blueprint.full_synopsis,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "needs_part_outlines": blueprint.needs_part_outlines,
                "total_chapters": blueprint.total_chapters,
            }
        elif section == NovelSectionType.WORLD_SETTING:
            data = {
                "world_setting": blueprint.world_setting or {},
            }
        elif section == NovelSectionType.CHARACTERS:
            data = {
                "characters": blueprint.characters,
            }
        elif section == NovelSectionType.RELATIONSHIPS:
            data = {
                "relationships": blueprint.relationships,
            }
        elif section == NovelSectionType.CHAPTER_OUTLINE:
            data = {
                "chapter_outline": [outline.model_dump() for outline in blueprint.chapter_outline],
                "needs_part_outlines": blueprint.needs_part_outlines,
                "total_chapters": blueprint.total_chapters,
                "chapters_per_part": blueprint.chapters_per_part,
                "part_outlines": [part.model_dump() for part in blueprint.part_outlines],
            }
        elif section == NovelSectionType.CHAPTERS:
            # 只返回已生成的章节，不包含仅有大纲的章节
            outlines_map = {outline.chapter_number: outline for outline in project.outlines}
            chapters_map = {chapter.chapter_number: chapter for chapter in project.chapters}
            chapter_numbers = sorted(chapters_map.keys())

            # 章节列表只返回元数据，不包含完整内容
            chapters = [
                NovelSerializer.build_chapter_schema(
                    project,
                    number,
                    outlines_map=outlines_map,
                    chapters_map=chapters_map,
                    include_content=False,
                ).model_dump()
                for number in chapter_numbers
            ]
            data = {
                "chapters": chapters,
                "total": len(chapters),
            }
        else:
            raise ValueError(f"未知的区段类型: {section}")

        return NovelSectionResponse(section=section, data=data)

    @staticmethod
    def build_chapter_schema(
        project: NovelProject,
        chapter_number: int,
        *,
        outlines_map: Optional[Dict[int, ChapterOutline]] = None,
        chapters_map: Optional[Dict[int, Chapter]] = None,
        include_content: bool = True,
    ) -> ChapterSchema:
        """
        构建章节Schema

        将单个章节的数据转换为ChapterSchema。

        Args:
            project: 项目ORM模型
            chapter_number: 章节号
            outlines_map: 章节大纲映射（可选，用于性能优化）
            chapters_map: 章节映射（可选，用于性能优化）
            include_content: 是否包含完整内容（默认True）

        Returns:
            ChapterSchema: 章节Schema

        Raises:
            ValueError: 章节不存在
        """
        outlines = outlines_map or {outline.chapter_number: outline for outline in project.outlines}
        chapters = chapters_map or {chapter.chapter_number: chapter for chapter in project.chapters}

        outline = outlines.get(chapter_number)
        chapter = chapters.get(chapter_number)

        if not outline and not chapter:
            raise ValueError(f"章节 {chapter_number} 不存在")

        # 提取基础信息
        title = outline.title if outline else f"第{chapter_number}章"
        summary = outline.summary if outline else ""
        real_summary = chapter.real_summary if chapter else None
        analysis_data = None
        content = None
        versions: Optional[List[str]] = None
        evaluation_text: Optional[str] = None
        status_value = ChapterGenerationStatus.NOT_GENERATED.value
        word_count = 0
        selected_version_idx: Optional[int] = None

        if chapter:
            status_value = chapter.status or ChapterGenerationStatus.NOT_GENERATED.value
            word_count = chapter.word_count or 0

            # 解析章节分析数据
            if chapter.analysis_data:
                try:
                    analysis_data = ChapterAnalysisData.model_validate(chapter.analysis_data)
                except Exception:
                    analysis_data = None

            # selected_version_idx 总是需要计算（用于状态判断），不依赖 include_content
            if chapter.versions and chapter.selected_version_id:
                sorted_versions = sorted(chapter.versions, key=lambda item: item.created_at)
                selected_version_idx = next(
                    (i for i, v in enumerate(sorted_versions) if v.id == chapter.selected_version_id),
                    None
                )

            # 只有在 include_content=True 时才包含完整内容
            if include_content:
                if chapter.selected_version:
                    content = NovelSerializer._extract_version_content(chapter.selected_version.content)
                if chapter.versions:
                    sorted_versions = sorted(chapter.versions, key=lambda item: item.created_at)
                    versions = [NovelSerializer._extract_version_content(v.content) for v in sorted_versions]
                if chapter.evaluations:
                    latest = sorted(chapter.evaluations, key=lambda item: item.created_at)[-1]
                    evaluation_text = latest.feedback or latest.decision

        # 安全地转换状态值为枚举，处理未知状态
        try:
            generation_status = ChapterGenerationStatus(status_value)
        except ValueError:
            # 未知状态，使用默认值
            logger.warning("未知的章节状态 '%s'，使用默认值 NOT_GENERATED", status_value)
            generation_status = ChapterGenerationStatus.NOT_GENERATED

        return ChapterSchema(
            chapter_number=chapter_number,
            title=title,
            summary=summary,
            real_summary=real_summary,
            content=content,
            versions=versions,
            evaluation=evaluation_text,
            generation_status=generation_status,
            word_count=word_count,
            selected_version=selected_version_idx,
            analysis_data=analysis_data,
        )

    @staticmethod
    def _extract_version_content(raw_content: str) -> str:
        """
        从版本内容中提取实际文本

        处理两种情况：
        1. 纯文本内容 - 直接返回
        2. JSON格式内容 - 提取 full_content/content 等字段

        Args:
            raw_content: 原始版本内容

        Returns:
            提取的纯文本内容
        """
        if not raw_content:
            return raw_content

        # 快速检查是否可能是JSON
        stripped = raw_content.strip()
        if not stripped.startswith('{'):
            return raw_content

        # 尝试解析JSON
        try:
            data = json.loads(stripped)
            if not isinstance(data, dict):
                return raw_content

            # 按优先级检查内容字段
            content_fields = [
                "full_content",
                "chapter_content",
                "content",
                "chapter_text",
                "text",
                "body",
                "chapter",
            ]
            for field in content_fields:
                if field in data and isinstance(data[field], str) and data[field].strip():
                    return data[field]

            # 如果没有找到内容字段，返回原始内容
            return raw_content
        except (json.JSONDecodeError, ValueError):
            # 不是有效的JSON，返回原始内容
            return raw_content
