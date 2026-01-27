"""
小说项目RAG入库服务

处理12种数据类型的向量化入库、完整性检查和增量更新。
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set, Union

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .data_types import NovelDataType, BLUEPRINT_INGESTION_TYPES
from .content_splitter import NovelContentSplitter, NovelIngestionRecord
from .chunk_strategy import NovelChunkMethod, get_novel_strategy_manager
from ..rag_common.ingestion_base import (
    BaseProjectIngestionService,
    IngestionResult,
    CompletenessReport,
)

# 导入ORM模型
from ...models.novel import (
    NovelProject,
    NovelBlueprint,
    NovelConversation,
    Chapter,
    ChapterVersion,
    ChapterOutline,
    BlueprintCharacter,
    BlueprintRelationship,
)
from ...models.part_outline import PartOutline
from ...models.protagonist import ProtagonistProfile, ProtagonistAttributeChange

logger = logging.getLogger(__name__)


_RECORD_GENERATOR_METHODS: Dict[NovelDataType, str] = {
    NovelDataType.INSPIRATION: "_generate_inspiration_records",
    NovelDataType.SYNOPSIS: "_generate_synopsis_records",
    NovelDataType.WORLD_SETTING: "_generate_world_setting_records",
    NovelDataType.BLUEPRINT_METADATA: "_generate_blueprint_metadata_records",
    NovelDataType.CHARACTER: "_generate_character_records",
    NovelDataType.RELATIONSHIP: "_generate_relationship_records",
    NovelDataType.CHARACTER_STATE: "_generate_character_state_records",
    NovelDataType.PROTAGONIST: "_generate_protagonist_records",
    NovelDataType.PROTAGONIST_CHANGE: "_generate_protagonist_change_records",
    NovelDataType.PART_OUTLINE: "_generate_part_outline_records",
    NovelDataType.CHAPTER_OUTLINE: "_generate_chapter_outline_records",
    NovelDataType.CHAPTER_CONTENT: "_generate_chapter_content_records",
    NovelDataType.CHAPTER_SUMMARY: "_generate_chapter_summary_records",
    NovelDataType.KEY_EVENT: "_generate_key_event_records",
    NovelDataType.CHAPTER_METADATA: "_generate_chapter_metadata_records",
    NovelDataType.FORESHADOWING: "_generate_foreshadowing_records",
}


def _convert_to_native_types(obj: Any) -> Any:
    """
    递归将 numpy 类型转换为 Python 原生类型，确保 JSON 可序列化

    Args:
        obj: 需要转换的对象（可以是字典、列表、numpy类型或其他）

    Returns:
        转换后的对象
    """
    if isinstance(obj, dict):
        return {k: _convert_to_native_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_native_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj


class NovelProjectIngestionService(BaseProjectIngestionService):
    """
    小说项目向量入库服务

    支持12种数据类型的入库：
    - inspiration: 灵感对话
    - synopsis: 故事概述
    - world_setting: 世界观设定
    - character: 角色设定
    - relationship: 角色关系
    - character_state: 角色状态快照
    - protagonist: 主角档案
    - part_outline: 分部大纲
    - chapter_outline: 章节大纲
    - chapter_content: 章节正文
    - chapter_summary: 章节摘要
    - foreshadowing: 伏笔记录
    """

    DATA_TYPE_ENUM = NovelDataType
    SPLITTER_FACTORY = NovelContentSplitter
    LOG_TITLE = "开始小说项目入库"
    LOGGER_OBJ = logger
    RECORD_GENERATOR_METHODS = _RECORD_GENERATOR_METHODS

    def _prepare_metadata_for_vector_store(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Novel 侧 metadata 可能包含 numpy 类型，需转为原生类型以保证可序列化/可存储"""
        return _convert_to_native_types(metadata)

    def _prepare_embedding_for_vector_store(self, embedding: Any) -> Any:
        """兼容 numpy.ndarray embedding"""
        return embedding.tolist() if isinstance(embedding, np.ndarray) else embedding

    def _get_ingest_method_map(self) -> Dict[NovelDataType, Any]:
        """获取数据类型到入库方法的映射"""
        return {
            NovelDataType.INSPIRATION: self._ingest_inspiration,
            NovelDataType.SYNOPSIS: self._ingest_synopsis,
            NovelDataType.WORLD_SETTING: self._ingest_world_setting,
            NovelDataType.BLUEPRINT_METADATA: self._ingest_blueprint_metadata,
            NovelDataType.CHARACTER: self._ingest_characters,
            NovelDataType.RELATIONSHIP: self._ingest_relationships,
            NovelDataType.CHARACTER_STATE: self._ingest_character_states,
            NovelDataType.PROTAGONIST: self._ingest_protagonist,
            NovelDataType.PROTAGONIST_CHANGE: self._ingest_protagonist_changes,
            NovelDataType.PART_OUTLINE: self._ingest_part_outlines,
            NovelDataType.CHAPTER_OUTLINE: self._ingest_chapter_outlines,
            NovelDataType.CHAPTER_CONTENT: self._ingest_chapter_content,
            NovelDataType.CHAPTER_SUMMARY: self._ingest_chapter_summaries,
            NovelDataType.KEY_EVENT: self._ingest_key_events,
            NovelDataType.CHAPTER_METADATA: self._ingest_chapter_metadata,
            NovelDataType.FORESHADOWING: self._ingest_foreshadowing,
        }

    # ==================== 记录生成方法 ====================

    async def _generate_inspiration_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成灵感对话记录"""
        stmt = select(NovelConversation).where(
            NovelConversation.project_id == project_id
        ).order_by(NovelConversation.seq)
        conversations = (await self.session.execute(stmt)).scalars().all()

        if not conversations:
            return []

        conv_dicts = [
            {"role": conv.role, "content": conv.content, "seq": conv.seq}
            for conv in conversations
        ]
        return self.splitter.merge_qa_rounds(conv_dicts, project_id)

    async def _generate_synopsis_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成故事概述记录"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.full_synopsis:
            return []

        return self.splitter.split_synopsis(
            content=blueprint.full_synopsis,
            source_id=project_id
        )

    async def _generate_blueprint_metadata_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成蓝图元数据记录（标题、体裁、风格、基调、目标读者、一句话简介）"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint:
            return []

        records: List[NovelIngestionRecord] = []

        # 构建元数据内容
        metadata_parts = []

        if blueprint.title:
            metadata_parts.append(f"小说标题: {blueprint.title}")

        if blueprint.genre:
            metadata_parts.append(f"体裁类型: {blueprint.genre}")

        if blueprint.style:
            metadata_parts.append(f"写作风格: {blueprint.style}")

        if blueprint.tone:
            metadata_parts.append(f"情感基调: {blueprint.tone}")

        if blueprint.target_audience:
            metadata_parts.append(f"目标读者: {blueprint.target_audience}")

        if blueprint.one_sentence_summary:
            metadata_parts.append(f"一句话简介: {blueprint.one_sentence_summary}")

        if not metadata_parts:
            return []

        # 合并为一条记录
        content = "\n".join(metadata_parts)
        record = self.splitter.create_simple_record(
            content=content,
            data_type=NovelDataType.BLUEPRINT_METADATA,
            source_id=project_id,
            title=blueprint.title or "",
            genre=blueprint.genre or "",
            style=blueprint.style or "",
            tone=blueprint.tone or "",
            target_audience=blueprint.target_audience or "",
            one_sentence_summary=blueprint.one_sentence_summary or "",
        )
        if record:
            records.append(record)

        return records

    async def _generate_world_setting_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成世界观设定记录 - 使用细粒度分割"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.world_setting:
            return []

        world_setting = blueprint.world_setting
        if isinstance(world_setting, str):
            try:
                world_setting = json.loads(world_setting)
            except json.JSONDecodeError:
                # 如果是纯文本，整体入库
                record = self.splitter.create_simple_record(
                    content=world_setting,
                    data_type=NovelDataType.WORLD_SETTING,
                    source_id=project_id,
                    setting_key="world_setting"
                )
                return [record] if record else []

        # 使用新的细粒度分割方法
        return self.splitter.split_world_setting(world_setting, project_id)

    async def _generate_character_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成角色设定记录 - 按属性维度分割"""
        stmt = select(BlueprintCharacter).where(
            BlueprintCharacter.project_id == project_id
        ).order_by(BlueprintCharacter.position)
        characters = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for idx, char in enumerate(characters):
            # 将ORM对象转换为字典
            char_dict = {
                'name': char.name,
                'identity': char.identity,
                'personality': char.personality,
                'appearance': char.appearance,
                'goals': char.goals,
                'abilities': char.abilities,
                'relationship_to_protagonist': char.relationship_to_protagonist,
            }
            # 使用新的细粒度分割方法
            char_records = self.splitter.split_character(
                char_dict,
                source_id=str(char.id),
                char_index=idx
            )
            records.extend(char_records)
        return records

    async def _generate_relationship_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成角色关系记录"""
        stmt = select(BlueprintRelationship).where(
            BlueprintRelationship.project_id == project_id
        )
        relationships = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for rel in relationships:
            content = f"{rel.character_from} -> {rel.character_to}: {rel.description or '关系未描述'}"
            record = self.splitter.create_simple_record(
                content=content,
                data_type=NovelDataType.RELATIONSHIP,
                source_id=str(rel.id),
                character_from=rel.character_from,
                character_to=rel.character_to
            )
            if record:
                records.append(record)
        return records

    async def _generate_character_state_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成角色状态记录"""
        # 尝试从 character_state_index 表获取
        try:
            from ...models.novel import CharacterStateIndex
            stmt = select(CharacterStateIndex).where(
                CharacterStateIndex.project_id == project_id
            ).order_by(CharacterStateIndex.chapter_number)
            states = (await self.session.execute(stmt)).scalars().all()

            records: List[NovelIngestionRecord] = []
            for state in states:
                content = self._format_character_state(state)
                if content:
                    record = self.splitter.create_simple_record(
                        content=content,
                        data_type=NovelDataType.CHARACTER_STATE,
                        source_id=str(state.id),
                        chapter_number=state.chapter_number,
                        character_name=state.character_name
                    )
                    if record:
                        record.chapter_number = state.chapter_number
                        records.append(record)
            return records
        except Exception as e:
            logger.warning("获取角色状态失败: %s", str(e))
            return []

    async def _generate_protagonist_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成主角档案记录 - 按维度分割"""
        stmt = select(ProtagonistProfile).where(
            ProtagonistProfile.project_id == project_id
        )
        profiles = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for profile in profiles:
            # 将ORM对象转换为字典
            profile_dict = {
                'name': profile.character_name,
            }

            # 解析显性属性
            if profile.explicit_attributes:
                attrs = profile.explicit_attributes
                if isinstance(attrs, str):
                    try:
                        attrs = json.loads(attrs)
                    except json.JSONDecodeError:
                        attrs = {}
                profile_dict.update(attrs)

            # 解析隐性属性
            if profile.implicit_attributes:
                attrs = profile.implicit_attributes
                if isinstance(attrs, str):
                    try:
                        attrs = json.loads(attrs)
                    except json.JSONDecodeError:
                        attrs = {}
                # 将隐性属性添加到对应字段
                for k, v in attrs.items():
                    if k not in profile_dict:
                        profile_dict[k] = v

            # 解析社会属性
            if profile.social_attributes:
                attrs = profile.social_attributes
                if isinstance(attrs, str):
                    try:
                        attrs = json.loads(attrs)
                    except json.JSONDecodeError:
                        attrs = {}
                for k, v in attrs.items():
                    if k not in profile_dict:
                        profile_dict[k] = v

            # 使用新的细粒度分割方法
            profile_records = self.splitter.split_protagonist(
                profile_dict,
                source_id=str(profile.id)
            )
            records.extend(profile_records)
        return records

    async def _generate_part_outline_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成分部大纲记录 - 按字段分割"""
        stmt = select(PartOutline).where(
            PartOutline.project_id == project_id
        ).order_by(PartOutline.part_number)
        parts = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for part in parts:
            # 将ORM对象转换为字典
            part_dict = {
                'title': part.title,
                'theme': part.theme,
                'summary': part.summary,
                'key_events': part.key_events,
                'ending_hook': part.ending_hook,
                'start_chapter': part.start_chapter,
                'end_chapter': part.end_chapter,
            }
            # 使用新的细粒度分割方法
            part_records = self.splitter.split_part_outline(
                part_dict,
                source_id=str(part.id),
                part_number=part.part_number
            )
            records.extend(part_records)
        return records

    async def _generate_chapter_outline_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成章节大纲记录"""
        stmt = select(ChapterOutline).where(
            ChapterOutline.project_id == project_id
        ).order_by(ChapterOutline.chapter_number)
        outlines = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for outline in outlines:
            content = f"第{outline.chapter_number}章: {outline.title or ''}\n{outline.summary or ''}"
            record = self.splitter.create_simple_record(
                content=content,
                data_type=NovelDataType.CHAPTER_OUTLINE,
                source_id=str(outline.id),
                chapter_number=outline.chapter_number
            )
            if record:
                record.chapter_number = outline.chapter_number
                records.append(record)
        return records

    async def _generate_chapter_content_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成章节正文记录

        根据策略配置，使用不同的分块方法：
        - SEMANTIC_DP: 使用语义动态规划分块（基于句子嵌入）
        - 其他: 使用传统分块方法
        """
        # 检查策略配置
        config = get_novel_strategy_manager().get_config(NovelDataType.CHAPTER_CONTENT)
        use_semantic = config.method == NovelChunkMethod.SEMANTIC_DP

        # 先获取章节大纲，建立章节号到标题的映射
        outline_stmt = select(ChapterOutline).where(
            ChapterOutline.project_id == project_id
        )
        outlines = (await self.session.execute(outline_stmt)).scalars().all()
        title_map = {outline.chapter_number: outline.title for outline in outlines}

        stmt = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.selected_version_id.isnot(None)
        ).options(
            selectinload(Chapter.selected_version)
        ).order_by(Chapter.chapter_number)
        chapters = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for chapter in chapters:
            if not chapter.selected_version or not chapter.selected_version.content:
                continue

            content = chapter.selected_version.content
            if not content.strip():
                continue

            # 从大纲映射获取章节标题
            chapter_title = title_map.get(chapter.chapter_number, f"第{chapter.chapter_number}章")

            if use_semantic:
                # 使用语义分块 - 需要提供嵌入函数
                try:
                    chapter_records = await self.splitter.split_content_semantic_async(
                        content=content,
                        data_type=NovelDataType.CHAPTER_CONTENT,
                        source_id=str(chapter.id),
                        embedding_func=self._get_sentence_embeddings,
                        config=config,
                        chapter_number=chapter.chapter_number,
                        chapter_title=chapter_title
                    )
                    records.extend(chapter_records)
                except Exception as e:
                    logger.warning(
                        "语义分块失败，降级为传统分块: chapter=%d error=%s",
                        chapter.chapter_number, str(e)
                    )
                    # 降级为传统分块
                    chapter_records = self.splitter.split_content(
                        content=content,
                        data_type=NovelDataType.CHAPTER_CONTENT,
                        source_id=str(chapter.id),
                        config=config,
                        chapter_number=chapter.chapter_number,
                        chapter_title=chapter_title,
                    )
                    records.extend(chapter_records)
            else:
                # 使用传统分块
                chapter_records = self.splitter.split_content(
                    content=content,
                    data_type=NovelDataType.CHAPTER_CONTENT,
                    source_id=str(chapter.id),
                    config=config,
                    chapter_number=chapter.chapter_number,
                    chapter_title=chapter_title,
                )
                records.extend(chapter_records)

        return records

    async def _generate_chapter_summary_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成章节摘要记录"""
        stmt = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.real_summary.isnot(None)
        ).order_by(Chapter.chapter_number)
        chapters = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for chapter in chapters:
            if not chapter.real_summary or not chapter.real_summary.strip():
                continue

            record = self.splitter.create_simple_record(
                content=chapter.real_summary,
                data_type=NovelDataType.CHAPTER_SUMMARY,
                source_id=str(chapter.id),
                chapter_number=chapter.chapter_number
            )
            if record:
                record.chapter_number = chapter.chapter_number
                records.append(record)

        return records

    async def _generate_foreshadowing_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成伏笔记录"""
        try:
            from ...models.novel import ForeshadowingIndex
            stmt = select(ForeshadowingIndex).where(
                ForeshadowingIndex.project_id == project_id
            ).order_by(ForeshadowingIndex.planted_chapter)
            foreshadowings = (await self.session.execute(stmt)).scalars().all()

            records: List[NovelIngestionRecord] = []
            for fs in foreshadowings:
                content = self._format_foreshadowing(fs)
                if content:
                    record = self.splitter.create_simple_record(
                        content=content,
                        data_type=NovelDataType.FORESHADOWING,
                        source_id=str(fs.id),
                        chapter_number=fs.planted_chapter,
                        category=fs.category,
                        priority=fs.priority,
                        status=fs.status
                    )
                    if record:
                        record.chapter_number = fs.planted_chapter
                        records.append(record)
            return records
        except Exception as e:
            logger.warning("获取伏笔记录失败: %s", str(e))
            return []

    async def _generate_key_event_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成关键事件记录

        从章节的analysis_data.key_events中提取关键事件，
        每个事件单独入库，便于精确检索。
        """
        stmt = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.analysis_data.isnot(None)
        ).order_by(Chapter.chapter_number)
        chapters = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for chapter in chapters:
            if not chapter.analysis_data:
                continue

            # 解析analysis_data
            analysis = chapter.analysis_data
            if isinstance(analysis, str):
                try:
                    analysis = json.loads(analysis)
                except json.JSONDecodeError:
                    continue

            key_events = analysis.get("key_events", [])
            if not key_events:
                continue

            for idx, event in enumerate(key_events):
                if isinstance(event, dict):
                    content = self._format_key_event(event, chapter.chapter_number)
                    if content:
                        record = self.splitter.create_simple_record(
                            content=content,
                            data_type=NovelDataType.KEY_EVENT,
                            source_id=f"{chapter.id}_event_{idx}",
                            chapter_number=chapter.chapter_number,
                            event_type=event.get("type", "unknown"),
                            importance=event.get("importance", "medium"),
                            involved_characters=event.get("involved_characters", [])
                        )
                        if record:
                            record.chapter_number = chapter.chapter_number
                            records.append(record)

        return records

    async def _generate_chapter_metadata_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成章节元数据记录

        从章节的analysis_data.metadata中提取地点、物品、标签等元数据，
        整合为一条记录入库，便于检索场景相关信息。
        """
        stmt = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.analysis_data.isnot(None)
        ).order_by(Chapter.chapter_number)
        chapters = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for chapter in chapters:
            if not chapter.analysis_data:
                continue

            # 解析analysis_data
            analysis = chapter.analysis_data
            if isinstance(analysis, str):
                try:
                    analysis = json.loads(analysis)
                except json.JSONDecodeError:
                    continue

            metadata = analysis.get("metadata", {})
            if not metadata:
                continue

            # 构建元数据内容
            content = self._format_chapter_metadata(metadata, chapter.chapter_number)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=NovelDataType.CHAPTER_METADATA,
                    source_id=f"{chapter.id}_metadata",
                    chapter_number=chapter.chapter_number,
                    locations=metadata.get("locations", []),
                    items=metadata.get("items", []),
                    tags=metadata.get("tags", []),
                    tone=metadata.get("tone"),
                    timeline_marker=metadata.get("timeline_marker")
                )
                if record:
                    record.chapter_number = chapter.chapter_number
                    records.append(record)

        return records

    async def _generate_protagonist_change_records(self, project_id: str) -> List[NovelIngestionRecord]:
        """生成主角属性变更记录

        从protagonist_attribute_changes表中提取主角的属性变更历史，
        用于追踪角色成长轨迹。
        """
        # 先获取项目的所有主角档案ID
        profile_stmt = select(ProtagonistProfile.id, ProtagonistProfile.character_name).where(
            ProtagonistProfile.project_id == project_id
        )
        profiles = (await self.session.execute(profile_stmt)).all()

        if not profiles:
            return []

        profile_ids = [p[0] for p in profiles]
        profile_name_map = {p[0]: p[1] for p in profiles}

        # 获取属性变更记录
        stmt = select(ProtagonistAttributeChange).where(
            ProtagonistAttributeChange.profile_id.in_(profile_ids)
        ).order_by(
            ProtagonistAttributeChange.chapter_number,
            ProtagonistAttributeChange.created_at
        )
        changes = (await self.session.execute(stmt)).scalars().all()

        records: List[NovelIngestionRecord] = []
        for change in changes:
            character_name = profile_name_map.get(change.profile_id, "未知角色")
            content = self._format_protagonist_change(change, character_name)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=NovelDataType.PROTAGONIST_CHANGE,
                    source_id=str(change.id),
                    chapter_number=change.chapter_number,
                    character_name=character_name,
                    attribute_category=change.attribute_category,
                    attribute_key=change.attribute_key,
                    operation=change.operation
                )
                if record:
                    record.chapter_number = change.chapter_number
                    records.append(record)

        return records

    # ==================== 入库方法 ====================

    async def _ingest_inspiration(self, project_id: str) -> IngestionResult:
        """入库灵感对话"""
        result = IngestionResult(success=True, data_type=NovelDataType.INSPIRATION)
        records = await self._generate_inspiration_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_synopsis(self, project_id: str) -> IngestionResult:
        """入库故事概述"""
        result = IngestionResult(success=True, data_type=NovelDataType.SYNOPSIS)
        records = await self._generate_synopsis_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_world_setting(self, project_id: str) -> IngestionResult:
        """入库世界观设定"""
        result = IngestionResult(success=True, data_type=NovelDataType.WORLD_SETTING)
        records = await self._generate_world_setting_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_blueprint_metadata(self, project_id: str) -> IngestionResult:
        """入库蓝图元数据"""
        result = IngestionResult(success=True, data_type=NovelDataType.BLUEPRINT_METADATA)
        records = await self._generate_blueprint_metadata_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_characters(self, project_id: str) -> IngestionResult:
        """入库角色设定"""
        result = IngestionResult(success=True, data_type=NovelDataType.CHARACTER)
        records = await self._generate_character_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_relationships(self, project_id: str) -> IngestionResult:
        """入库角色关系"""
        result = IngestionResult(success=True, data_type=NovelDataType.RELATIONSHIP)
        records = await self._generate_relationship_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_character_states(self, project_id: str) -> IngestionResult:
        """入库角色状态"""
        result = IngestionResult(success=True, data_type=NovelDataType.CHARACTER_STATE)
        records = await self._generate_character_state_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_protagonist(self, project_id: str) -> IngestionResult:
        """入库主角档案"""
        result = IngestionResult(success=True, data_type=NovelDataType.PROTAGONIST)
        records = await self._generate_protagonist_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_part_outlines(self, project_id: str) -> IngestionResult:
        """入库分部大纲"""
        result = IngestionResult(success=True, data_type=NovelDataType.PART_OUTLINE)
        records = await self._generate_part_outline_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_chapter_outlines(self, project_id: str) -> IngestionResult:
        """入库章节大纲"""
        result = IngestionResult(success=True, data_type=NovelDataType.CHAPTER_OUTLINE)
        records = await self._generate_chapter_outline_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_chapter_content(self, project_id: str) -> IngestionResult:
        """入库章节正文"""
        result = IngestionResult(success=True, data_type=NovelDataType.CHAPTER_CONTENT)
        records = await self._generate_chapter_content_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_chapter_summaries(self, project_id: str) -> IngestionResult:
        """入库章节摘要"""
        result = IngestionResult(success=True, data_type=NovelDataType.CHAPTER_SUMMARY)
        records = await self._generate_chapter_summary_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_foreshadowing(self, project_id: str) -> IngestionResult:
        """入库伏笔记录"""
        result = IngestionResult(success=True, data_type=NovelDataType.FORESHADOWING)
        records = await self._generate_foreshadowing_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_key_events(self, project_id: str) -> IngestionResult:
        """入库关键事件"""
        result = IngestionResult(success=True, data_type=NovelDataType.KEY_EVENT)
        records = await self._generate_key_event_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_chapter_metadata(self, project_id: str) -> IngestionResult:
        """入库章节元数据"""
        result = IngestionResult(success=True, data_type=NovelDataType.CHAPTER_METADATA)
        records = await self._generate_chapter_metadata_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_protagonist_changes(self, project_id: str) -> IngestionResult:
        """入库主角属性变更历史"""
        result = IngestionResult(success=True, data_type=NovelDataType.PROTAGONIST_CHANGE)
        records = await self._generate_protagonist_change_records(project_id)
        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    # ==================== 辅助方法 ====================

    async def _get_blueprint(self, project_id: str) -> Optional[NovelBlueprint]:
        """获取项目蓝图"""
        stmt = select(NovelBlueprint).where(NovelBlueprint.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _get_source_info(self, record: NovelIngestionRecord) -> tuple:
        """
        根据数据类型获取来源信息

        Returns:
            (chapter_number, chapter_title) 元组
        """
        data_type = record.data_type
        metadata = record.metadata
        record_chapter_number = getattr(record, "chapter_number", None)

        if data_type == NovelDataType.CHAPTER_CONTENT:
            num = metadata.get("chapter_number")
            if num is None:
                num = record_chapter_number or 0
            title = metadata.get("chapter_title", f"第{num}章")
            return (num, title)

        elif data_type == NovelDataType.CHAPTER_SUMMARY:
            num = metadata.get("chapter_number")
            if num is None:
                num = record_chapter_number or 0
            return (num, f"第{num}章摘要")

        elif data_type == NovelDataType.CHAPTER_OUTLINE:
            num = metadata.get("chapter_number")
            if num is None:
                num = record_chapter_number or 0
            return (num, f"第{num}章大纲")

        elif data_type == NovelDataType.PART_OUTLINE:
            num = metadata.get("part_number", 0)
            return (num, f"第{num}部大纲")

        elif data_type == NovelDataType.CHARACTER:
            name = metadata.get("character_name", "角色")
            return (0, f"角色: {name}")

        elif data_type == NovelDataType.RELATIONSHIP:
            from_char = metadata.get("character_from", "")
            to_char = metadata.get("character_to", "")
            return (0, f"关系: {from_char} -> {to_char}")

        elif data_type == NovelDataType.CHARACTER_STATE:
            num = metadata.get("chapter_number")
            if num is None:
                num = record_chapter_number or 0
            name = metadata.get("character_name", "")
            return (num, f"第{num}章 {name}状态")

        elif data_type == NovelDataType.PROTAGONIST:
            # 兼容两种元数据键名：protagonist_name（新）和 character_name（旧）
            name = metadata.get("protagonist_name", "") or metadata.get("character_name", "主角")
            return (0, f"主角: {name}")

        elif data_type == NovelDataType.FORESHADOWING:
            num = metadata.get("chapter_number")
            if num is None:
                num = record_chapter_number or 0
            return (num, f"第{num}章伏笔")

        elif data_type == NovelDataType.KEY_EVENT:
            num = metadata.get("chapter_number")
            if num is None:
                num = record_chapter_number or 0
            event_type = metadata.get("event_type", "")
            return (num, f"第{num}章关键事件: {event_type}" if event_type else f"第{num}章关键事件")

        elif data_type == NovelDataType.CHAPTER_METADATA:
            num = metadata.get("chapter_number")
            if num is None:
                num = record_chapter_number or 0
            return (num, f"第{num}章元数据")

        elif data_type == NovelDataType.PROTAGONIST_CHANGE:
            num = metadata.get("chapter_number")
            if num is None:
                num = record_chapter_number or 0
            name = metadata.get("character_name", "主角")
            return (num, f"第{num}章 {name}属性变更")

        elif data_type == NovelDataType.INSPIRATION:
            round_num = metadata.get("round_number", 0) + 1
            return (round_num, f"对话轮次{round_num}")

        elif data_type == NovelDataType.SYNOPSIS:
            section = metadata.get("section_title", "")
            idx = metadata.get("section_index", 0) + 1
            return (idx, section or f"故事概述{idx}")

        elif data_type == NovelDataType.WORLD_SETTING:
            # 优先使用 field_name（中文名），其次 field（英文键名）
            field_name = metadata.get("field_name", "") or metadata.get("field", "")
            return (0, f"世界观: {field_name}" if field_name else "世界观设定")

        elif data_type == NovelDataType.BLUEPRINT_METADATA:
            title = metadata.get("title", "")
            return (0, f"蓝图元数据: {title}" if title else "蓝图元数据")

        return (0, NovelDataType.get_display_name(data_type.value))

    # ==================== 格式化方法 ====================

    def _format_character(self, char: BlueprintCharacter) -> str:
        """格式化角色设定"""
        parts = [f"角色: {char.name or ''}"]
        if char.identity:
            parts.append(f"身份: {char.identity}")
        if char.personality:
            parts.append(f"性格: {char.personality}")
        if char.appearance:
            parts.append(f"外貌: {char.appearance}")
        if char.goals:
            parts.append(f"目标: {char.goals}")
        if char.abilities:
            parts.append(f"能力: {char.abilities}")
        if char.relationship_to_protagonist:
            parts.append(f"与主角关系: {char.relationship_to_protagonist}")
        return "\n".join(parts)

    def _format_character_state(self, state) -> str:
        """格式化角色状态"""
        parts = [f"第{state.chapter_number}章 - {state.character_name}的状态"]
        if hasattr(state, 'location') and state.location:
            parts.append(f"位置: {state.location}")
        if hasattr(state, 'status') and state.status:
            parts.append(f"状态: {state.status}")
        if hasattr(state, 'emotional_state') and state.emotional_state:
            parts.append(f"情绪: {state.emotional_state}")
        if hasattr(state, 'changes') and state.changes:
            changes = state.changes if isinstance(state.changes, list) else [state.changes]
            parts.append(f"本章变化: {', '.join(str(c) for c in changes)}")
        return "\n".join(parts)

    def _format_protagonist(self, profile: ProtagonistProfile) -> str:
        """格式化主角档案"""
        parts = [f"主角: {profile.character_name or ''}"]

        if profile.explicit_attributes:
            attrs = profile.explicit_attributes
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs)
                except json.JSONDecodeError:
                    attrs = {}
            if attrs:
                parts.append("\n【显性属性】")
                for k, v in attrs.items():
                    parts.append(f"  {k}: {v}")

        if profile.implicit_attributes:
            attrs = profile.implicit_attributes
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs)
                except json.JSONDecodeError:
                    attrs = {}
            if attrs:
                parts.append("\n【隐性属性】")
                for k, v in attrs.items():
                    parts.append(f"  {k}: {v}")

        if profile.social_attributes:
            attrs = profile.social_attributes
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs)
                except json.JSONDecodeError:
                    attrs = {}
            if attrs:
                parts.append("\n【社会属性】")
                for k, v in attrs.items():
                    parts.append(f"  {k}: {v}")

        return "\n".join(parts)

    def _format_part_outline(self, part: PartOutline) -> str:
        """格式化分部大纲"""
        parts = [f"第{part.part_number}部: {part.title or ''}"]
        if part.start_chapter and part.end_chapter:
            parts.append(f"章节范围: 第{part.start_chapter}-{part.end_chapter}章")
        if part.theme:
            parts.append(f"主题: {part.theme}")
        if part.summary:
            parts.append(f"摘要: {part.summary}")
        if part.key_events:
            events = part.key_events if isinstance(part.key_events, list) else [part.key_events]
            parts.append(f"关键事件: {', '.join(str(e) for e in events)}")
        if part.ending_hook:
            parts.append(f"衔接点: {part.ending_hook}")
        return "\n".join(parts)

    def _format_foreshadowing(self, fs) -> str:
        """格式化伏笔记录"""
        parts = []
        if hasattr(fs, 'description') and fs.description:
            parts.append(f"伏笔: {fs.description}")
        if hasattr(fs, 'original_text') and fs.original_text:
            parts.append(f"原文: {fs.original_text}")
        if hasattr(fs, 'category') and fs.category:
            parts.append(f"类型: {fs.category}")
        if hasattr(fs, 'priority') and fs.priority:
            parts.append(f"优先级: {fs.priority}")
        if hasattr(fs, 'planted_chapter') and fs.planted_chapter:
            parts.append(f"埋设章节: 第{fs.planted_chapter}章")
        if hasattr(fs, 'status') and fs.status:
            parts.append(f"状态: {fs.status}")
        if hasattr(fs, 'related_entities') and fs.related_entities:
            entities = fs.related_entities if isinstance(fs.related_entities, list) else [fs.related_entities]
            parts.append(f"相关角色/物品: {', '.join(str(e) for e in entities)}")

        # 已回收的伏笔
        if hasattr(fs, 'status') and fs.status == "resolved":
            if hasattr(fs, 'resolved_chapter') and fs.resolved_chapter:
                parts.append(f"回收章节: 第{fs.resolved_chapter}章")
            if hasattr(fs, 'resolution') and fs.resolution:
                parts.append(f"回收方式: {fs.resolution}")

        return "\n".join(parts) if parts else "伏笔记录"

    def _format_key_event(self, event: dict, chapter_number: int) -> str:
        """格式化关键事件

        Args:
            event: 事件字典，包含type, description, importance, involved_characters
            chapter_number: 章节号

        Returns:
            格式化的事件文本
        """
        parts = [f"第{chapter_number}章关键事件"]

        event_type = event.get("type", "")
        if event_type:
            type_names = {
                "battle": "战斗",
                "revelation": "揭示",
                "relationship": "关系变化",
                "discovery": "发现",
                "decision": "重要决定",
            }
            parts.append(f"类型: {type_names.get(event_type, event_type)}")

        description = event.get("description", "")
        if description:
            parts.append(f"描述: {description}")

        importance = event.get("importance", "medium")
        importance_names = {"high": "高", "medium": "中", "low": "低"}
        parts.append(f"重要性: {importance_names.get(importance, importance)}")

        involved = event.get("involved_characters", [])
        if involved:
            parts.append(f"涉及角色: {', '.join(involved)}")

        return "\n".join(parts)

    def _format_chapter_metadata(self, metadata: dict, chapter_number: int) -> str:
        """格式化章节元数据

        Args:
            metadata: 元数据字典，包含locations, items, tags, tone, timeline_marker
            chapter_number: 章节号

        Returns:
            格式化的元数据文本
        """
        parts = [f"第{chapter_number}章元数据"]

        locations = metadata.get("locations", [])
        if locations:
            parts.append(f"地点: {', '.join(locations)}")

        items = metadata.get("items", [])
        if items:
            parts.append(f"重要物品: {', '.join(items)}")

        tags = metadata.get("tags", [])
        if tags:
            parts.append(f"章节标签: {', '.join(tags)}")

        tone = metadata.get("tone")
        if tone:
            parts.append(f"情感基调: {tone}")

        timeline = metadata.get("timeline_marker")
        if timeline:
            parts.append(f"时间线标记: {timeline}")

        characters = metadata.get("characters", [])
        if characters:
            parts.append(f"出场角色: {', '.join(characters)}")

        return "\n".join(parts)

    def _format_protagonist_change(self, change: ProtagonistAttributeChange, character_name: str) -> str:
        """格式化主角属性变更

        Args:
            change: 属性变更记录
            character_name: 角色名称

        Returns:
            格式化的变更文本
        """
        parts = [f"第{change.chapter_number}章 - {character_name}的属性变更"]

        # 操作类型
        operation_names = {"add": "新增", "modify": "修改", "delete": "删除"}
        parts.append(f"操作: {operation_names.get(change.operation, change.operation)}")

        # 属性类别
        category_names = {"explicit": "显性属性", "implicit": "隐性属性", "social": "社会属性"}
        parts.append(f"类别: {category_names.get(change.attribute_category, change.attribute_category)}")

        # 属性键
        parts.append(f"属性: {change.attribute_key}")

        # 值变化
        if change.old_value:
            parts.append(f"原值: {change.old_value}")
        if change.new_value:
            parts.append(f"新值: {change.new_value}")

        # 变更描述
        if change.change_description:
            parts.append(f"变更说明: {change.change_description}")

        # 触发事件
        if change.event_cause:
            parts.append(f"触发事件: {change.event_cause}")

        # 证据
        if change.evidence:
            parts.append(f"原文证据: {change.evidence}")

        return "\n".join(parts)


__all__ = [
    "NovelProjectIngestionService",
    "IngestionResult",
    "CompletenessReport",
]
