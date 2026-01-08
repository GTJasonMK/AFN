"""
编程项目RAG入库服务

处理10种数据类型的向量化入库、完整性检查和增量更新。
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .data_types import CodingDataType, BLUEPRINT_INGESTION_TYPES
from .content_splitter import ContentSplitter, IngestionRecord

# 导入ORM模型
from ...models.novel import (
    NovelProject,
    NovelBlueprint,
    NovelConversation,
    Chapter,
    ChapterOutline,
    BlueprintCharacter,
    BlueprintRelationship,
)
from ...models.part_outline import PartOutline

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """入库结果"""
    success: bool
    data_type: CodingDataType
    total_records: int = 0           # 总记录数
    added_count: int = 0             # 新增数
    updated_count: int = 0           # 更新数
    skipped_count: int = 0           # 跳过数（内容未变）
    failed_count: int = 0            # 失败数
    error_message: str = ""


@dataclass
class TypeChangeDetail:
    """单个数据类型的变动详情"""
    db_count: int = 0                # 数据库记录数
    vector_count: int = 0            # 向量库记录数
    complete: bool = True            # 是否完整
    new_count: int = 0               # 新增记录数
    modified_count: int = 0          # 已修改记录数
    deleted_count: int = 0           # 已删除记录数
    display_name: str = ""           # 显示名称

    @property
    def has_changes(self) -> bool:
        """是否有任何变动"""
        return self.new_count > 0 or self.modified_count > 0 or self.deleted_count > 0


@dataclass
class CompletenessReport:
    """完整性检查报告"""
    project_id: str
    complete: bool
    total_db_count: int = 0          # 数据库总记录数
    total_vector_count: int = 0      # 向量库总记录数
    total_new: int = 0               # 总新增数
    total_modified: int = 0          # 总修改数
    total_deleted: int = 0           # 总删除数
    type_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """是否有任何变动需要同步"""
        return self.total_new > 0 or self.total_modified > 0 or self.total_deleted > 0


class CodingProjectIngestionService:
    """
    编程项目向量入库服务

    支持10种数据类型的入库：
    - inspiration: 灵感对话
    - architecture: 架构设计
    - tech_stack: 技术栈
    - requirement: 核心需求
    - challenge: 技术挑战
    - system: 系统划分
    - module: 模块定义
    - feature_outline: 功能大纲
    - dependency: 依赖关系
    - feature_prompt: 功能Prompt
    """

    def __init__(
        self,
        session: AsyncSession,
        vector_store: Any,  # VectorStoreService
        llm_service: Any,   # LLMService
        user_id: str
    ):
        self.session = session
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.user_id = user_id
        self.splitter = ContentSplitter()

    async def ingest_full_project(
        self,
        project_id: str,
        force: bool = False
    ) -> Dict[str, IngestionResult]:
        """
        完整入库 - 遍历所有数据类型

        Args:
            project_id: 项目ID
            force: 是否强制全量入库（默认False，只入库不完整的类型）

        Returns:
            各类型的入库结果字典
        """
        logger.info(
            "=== 开始入库 === project=%s force=%s vector_store=%s",
            project_id, force, "已启用" if self.vector_store else "未启用"
        )

        results: Dict[str, IngestionResult] = {}

        # 强制模式下，先删除所有旧数据，确保没有残留的"未知来源"记录
        if force and self.vector_store:
            logger.info("强制重建模式: 准备删除所有旧数据 project=%s", project_id)
            try:
                deleted = await self.vector_store.delete_by_project(project_id)
                logger.info(
                    "强制重建: 已删除项目 %s 的 %d 条旧RAG数据",
                    project_id, deleted
                )
            except Exception as e:
                logger.error(
                    "强制重建: 删除旧数据失败 project=%s error=%s",
                    project_id, str(e)
                )
        else:
            # 智能模式下，也要先清理没有data_type字段的旧数据
            # 这些旧数据会导致来源显示错误（如显示"F1"而不是正确的类型）
            if self.vector_store:
                try:
                    legacy_deleted = await self.vector_store.delete_legacy_chunks(project_id)
                    if legacy_deleted > 0:
                        logger.info(
                            "智能同步: 已清理项目 %s 的 %d 条旧版数据",
                            project_id, legacy_deleted
                        )
                except Exception as e:
                    logger.warning(
                        "智能同步: 清理旧版数据失败 project=%s error=%s",
                        project_id, str(e)
                    )

        # 如果不是强制模式，先检查完整性，只入库不完整的类型
        incomplete_types: Set[CodingDataType] = set()
        if not force:
            report = await self.check_completeness(project_id)
            for type_name, detail in report.type_details.items():
                if not detail.get("complete", True):
                    try:
                        incomplete_types.add(CodingDataType(type_name))
                    except ValueError:
                        pass

            # 如果全部完整，直接返回空结果（表示无需入库）
            if not incomplete_types:
                logger.info("项目 %s 所有数据类型已完整，跳过入库", project_id)
                return results

            logger.info(
                "项目 %s 需要入库的类型: %s",
                project_id,
                [t.value for t in incomplete_types]
            )

        # 遍历需要入库的类型
        types_to_process = incomplete_types if incomplete_types else set(CodingDataType.all_types())

        for data_type in CodingDataType.all_types():
            if data_type not in types_to_process:
                # 跳过已完整的类型
                results[data_type.value] = IngestionResult(
                    success=True,
                    data_type=data_type,
                    skipped_count=1,  # 标记为跳过
                )
                continue

            try:
                result = await self.ingest_by_type(project_id, data_type)
                results[data_type.value] = result
            except Exception as e:
                logger.error(
                    "入库类型 %s 失败: project=%s error=%s",
                    data_type.value, project_id, str(e)
                )
                results[data_type.value] = IngestionResult(
                    success=False,
                    data_type=data_type,
                    error_message=str(e)
                )

        return results

    async def ingest_by_type(
        self,
        project_id: str,
        data_type: CodingDataType
    ) -> IngestionResult:
        """
        按类型入库

        流程：
        1. 先清理向量库中该类型的过时数据
        2. 再执行新数据的入库（upsert）

        Args:
            project_id: 项目ID
            data_type: 数据类型

        Returns:
            入库结果
        """
        # 先清理该类型的过时数据
        await self._cleanup_stale_chunks(project_id, data_type)

        # 根据类型调用对应的入库方法
        method_map = {
            CodingDataType.INSPIRATION: self._ingest_inspiration,
            CodingDataType.ARCHITECTURE: self._ingest_architecture,
            CodingDataType.TECH_STACK: self._ingest_tech_stack,
            CodingDataType.REQUIREMENT: self._ingest_requirements,
            CodingDataType.CHALLENGE: self._ingest_challenges,
            CodingDataType.SYSTEM: self._ingest_systems,
            CodingDataType.MODULE: self._ingest_modules,
            CodingDataType.FEATURE_OUTLINE: self._ingest_feature_outlines,
            CodingDataType.DEPENDENCY: self._ingest_dependencies,
            CodingDataType.FEATURE_PROMPT: self._ingest_feature_prompts,
        }

        method = method_map.get(data_type)
        if not method:
            return IngestionResult(
                success=False,
                data_type=data_type,
                error_message=f"未知的数据类型: {data_type}"
            )

        return await method(project_id)

    async def _cleanup_stale_chunks(
        self,
        project_id: str,
        data_type: CodingDataType
    ) -> int:
        """
        清理向量库中该类型的过时数据

        对比当前数据库中应有的chunk_id与向量库中存储的chunk_id，
        删除向量库中多余的（过时的）记录。

        Args:
            project_id: 项目ID
            data_type: 数据类型

        Returns:
            删除的记录数
        """
        if not self.vector_store or not self.vector_store._client:
            return 0

        try:
            # 1. 获取当前数据库中该类型的所有预期chunk_id
            db_records = await self._generate_records_for_type(project_id, data_type)
            expected_ids = {record.get_chunk_id() for record in db_records}

            # 2. 获取向量库中该类型的所有chunk_id
            stored_hashes = await self.vector_store.get_chunks_hashes_by_type(
                project_id, data_type.value
            )
            stored_ids = set(stored_hashes.keys())

            # 3. 计算需要删除的ID（向量库中有但预期中没有的）
            stale_ids = stored_ids - expected_ids

            if not stale_ids:
                return 0

            # 4. 删除过时的记录
            logger.info(
                "清理过时向量数据: project=%s type=%s count=%d",
                project_id, data_type.value, len(stale_ids)
            )
            await self.vector_store.delete_chunks_by_ids(list(stale_ids))

            return len(stale_ids)

        except Exception as e:
            logger.warning(
                "清理过时向量数据失败: project=%s type=%s error=%s",
                project_id, data_type.value, str(e)
            )
            return 0

    async def check_completeness(self, project_id: str) -> CompletenessReport:
        """
        检查入库完整性（基于内容哈希的精确检测）

        对比数据库中每条记录的内容哈希与向量库中存储的哈希，
        精确检测新增、修改、删除的记录。

        Args:
            project_id: 项目ID

        Returns:
            完整性检查报告，包含各类型的变动详情
        """
        report = CompletenessReport(
            project_id=project_id,
            complete=True
        )

        for data_type in CodingDataType.all_types():
            try:
                detail = await self._check_type_completeness(project_id, data_type)

                # 转换为字典格式以保持向后兼容
                report.type_details[data_type.value] = {
                    "db_count": detail.db_count,
                    "vector_count": detail.vector_count,
                    "complete": detail.complete,
                    "new_count": detail.new_count,
                    "modified_count": detail.modified_count,
                    "deleted_count": detail.deleted_count,
                    "has_changes": detail.has_changes,
                    "display_name": detail.display_name,
                    # 保留旧字段以兼容
                    "missing": detail.new_count + detail.modified_count,
                }

                report.total_db_count += detail.db_count
                report.total_vector_count += detail.vector_count
                report.total_new += detail.new_count
                report.total_modified += detail.modified_count
                report.total_deleted += detail.deleted_count

                if not detail.complete or detail.has_changes:
                    report.complete = False

            except Exception as e:
                logger.warning(
                    "检查类型完整性失败: project=%s type=%s error=%s",
                    project_id, data_type.value, str(e)
                )
                # 检查失败时标记为不完整
                report.type_details[data_type.value] = {
                    "db_count": 0,
                    "vector_count": 0,
                    "complete": False,
                    "new_count": 0,
                    "modified_count": 0,
                    "deleted_count": 0,
                    "has_changes": False,
                    "display_name": CodingDataType.get_display_name(data_type.value),
                    "missing": 0,
                    "error": str(e),
                }
                report.complete = False

        return report

    async def _check_type_completeness(
        self,
        project_id: str,
        data_type: CodingDataType
    ) -> TypeChangeDetail:
        """
        检查单个数据类型的完整性（基于哈希比对）

        Args:
            project_id: 项目ID
            data_type: 数据类型

        Returns:
            变动详情
        """
        detail = TypeChangeDetail(
            display_name=CodingDataType.get_display_name(data_type.value)
        )

        # 1. 生成当前数据库中的记录及其哈希
        db_records = await self._generate_records_for_type(project_id, data_type)
        detail.db_count = len(db_records)

        # 构建期望的哈希映射: {chunk_id: paragraph_hash}
        expected_hashes: Dict[str, str] = {}
        for record in db_records:
            chunk_id = record.get_chunk_id()
            content_hash = record.get_content_hash()
            expected_hashes[chunk_id] = content_hash

        # 2. 获取向量库中存储的哈希
        stored_hashes: Dict[str, str] = {}
        if self.vector_store and self.vector_store._client:
            try:
                stored_hashes = await self.vector_store.get_chunks_hashes_by_type(
                    project_id, data_type.value
                )
            except Exception as e:
                logger.warning(
                    "获取向量库哈希失败: project=%s type=%s error=%s",
                    project_id, data_type.value, str(e)
                )

        detail.vector_count = len(stored_hashes)

        # 3. 比对哈希，检测变动
        expected_ids = set(expected_hashes.keys())
        stored_ids = set(stored_hashes.keys())

        # 新增：在DB中存在但向量库中不存在
        new_ids = expected_ids - stored_ids
        detail.new_count = len(new_ids)

        # 删除：在向量库中存在但DB中不存在
        deleted_ids = stored_ids - expected_ids
        detail.deleted_count = len(deleted_ids)

        # 修改：ID相同但哈希不同
        common_ids = expected_ids & stored_ids
        modified_count = 0
        modified_details = []
        for chunk_id in common_ids:
            if expected_hashes[chunk_id] != stored_hashes[chunk_id]:
                modified_count += 1
                modified_details.append({
                    "id": chunk_id[:50],
                    "expected": expected_hashes[chunk_id],
                    "stored": stored_hashes[chunk_id]
                })
        detail.modified_count = modified_count

        # 判断是否完整
        detail.complete = (
            detail.new_count == 0 and
            detail.modified_count == 0 and
            detail.deleted_count == 0
        )

        # 详细调试日志
        if detail.has_changes:
            logger.info(
                "检测到变动: project=%s type=%s db_count=%d vector_count=%d "
                "new=%d modified=%d deleted=%d",
                project_id, data_type.value,
                detail.db_count, detail.vector_count,
                detail.new_count, detail.modified_count, detail.deleted_count
            )
            # 记录新增的ID（前3个）
            if new_ids:
                sample_new = list(new_ids)[:3]
                logger.info(
                    "  新增ID样本: %s", [id[:50] for id in sample_new]
                )
            # 记录删除的ID（前3个）
            if deleted_ids:
                sample_deleted = list(deleted_ids)[:3]
                logger.info(
                    "  删除ID样本: %s", [id[:50] for id in sample_deleted]
                )
            # 记录修改详情（前3个）
            if modified_details:
                logger.info(
                    "  修改详情样本: %s", modified_details[:3]
                )
        else:
            logger.info(
                "类型完整: project=%s type=%s count=%d",
                project_id, data_type.value, detail.db_count
            )

        return detail

    async def _generate_records_for_type(
        self,
        project_id: str,
        data_type: CodingDataType
    ) -> List[IngestionRecord]:
        """
        为指定数据类型生成入库记录（不实际入库，只用于哈希计算）

        复用各类型的入库逻辑，但不执行embedding和写入操作。

        Args:
            project_id: 项目ID
            data_type: 数据类型

        Returns:
            入库记录列表
        """
        # 根据类型调用对应的记录生成方法
        if data_type == CodingDataType.INSPIRATION:
            return await self._generate_inspiration_records(project_id)
        elif data_type == CodingDataType.ARCHITECTURE:
            return await self._generate_architecture_records(project_id)
        elif data_type == CodingDataType.TECH_STACK:
            return await self._generate_tech_stack_records(project_id)
        elif data_type == CodingDataType.REQUIREMENT:
            return await self._generate_requirement_records(project_id)
        elif data_type == CodingDataType.CHALLENGE:
            return await self._generate_challenge_records(project_id)
        elif data_type == CodingDataType.SYSTEM:
            return await self._generate_system_records(project_id)
        elif data_type == CodingDataType.MODULE:
            return await self._generate_module_records(project_id)
        elif data_type == CodingDataType.FEATURE_OUTLINE:
            return await self._generate_feature_outline_records(project_id)
        elif data_type == CodingDataType.DEPENDENCY:
            return await self._generate_dependency_records(project_id)
        elif data_type == CodingDataType.FEATURE_PROMPT:
            return await self._generate_feature_prompt_records(project_id)
        return []

    async def _generate_inspiration_records(self, project_id: str) -> List[IngestionRecord]:
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

    async def _generate_architecture_records(self, project_id: str) -> List[IngestionRecord]:
        """生成架构设计记录"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.full_synopsis:
            return []

        return self.splitter.split_architecture(
            content=blueprint.full_synopsis,
            source_id=project_id,
            data_type=CodingDataType.ARCHITECTURE
        )

    async def _generate_tech_stack_records(self, project_id: str) -> List[IngestionRecord]:
        """生成技术栈记录"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.world_setting:
            return []

        world_setting = blueprint.world_setting
        if isinstance(world_setting, str):
            try:
                world_setting = json.loads(world_setting)
            except json.JSONDecodeError:
                return []

        tech_stack = world_setting.get("tech_stack", world_setting)
        records: List[IngestionRecord] = []

        for idx, comp in enumerate(tech_stack.get("components", [])):
            content = self._format_tech_component(comp)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.TECH_STACK,
                    source_id=project_id,
                    component_index=idx,
                    component_name=comp.get("name", "")
                )
                if record:
                    records.append(record)

        for idx, domain in enumerate(tech_stack.get("domains", [])):
            content = self._format_tech_domain(domain)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.TECH_STACK,
                    source_id=project_id,
                    domain_index=idx,
                    domain_name=domain.get("name", "")
                )
                if record:
                    records.append(record)

        return records

    async def _generate_requirement_records(self, project_id: str) -> List[IngestionRecord]:
        """生成核心需求记录"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.world_setting:
            return []

        world_setting = blueprint.world_setting
        if isinstance(world_setting, str):
            try:
                world_setting = json.loads(world_setting)
            except json.JSONDecodeError:
                return []

        records: List[IngestionRecord] = []
        for idx, req in enumerate(world_setting.get("core_requirements", [])):
            content = self._format_requirement(req)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.REQUIREMENT,
                    source_id=project_id,
                    requirement_index=idx
                )
                if record:
                    records.append(record)
        return records

    async def _generate_challenge_records(self, project_id: str) -> List[IngestionRecord]:
        """生成技术挑战记录"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.world_setting:
            return []

        world_setting = blueprint.world_setting
        if isinstance(world_setting, str):
            try:
                world_setting = json.loads(world_setting)
            except json.JSONDecodeError:
                return []

        records: List[IngestionRecord] = []
        for idx, challenge in enumerate(world_setting.get("technical_challenges", [])):
            content = self._format_challenge(challenge)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.CHALLENGE,
                    source_id=project_id,
                    challenge_index=idx
                )
                if record:
                    records.append(record)
        return records

    async def _generate_system_records(self, project_id: str) -> List[IngestionRecord]:
        """生成系统划分记录"""
        stmt = select(PartOutline).where(
            PartOutline.project_id == project_id
        ).order_by(PartOutline.part_number)
        systems = (await self.session.execute(stmt)).scalars().all()

        records: List[IngestionRecord] = []
        for system in systems:
            content = self._format_system(system)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.SYSTEM,
                    source_id=str(system.id),
                    system_number=system.part_number
                )
                if record:
                    records.append(record)
        return records

    async def _generate_module_records(self, project_id: str) -> List[IngestionRecord]:
        """生成模块定义记录"""
        stmt = select(BlueprintCharacter).where(
            BlueprintCharacter.project_id == project_id
        ).order_by(BlueprintCharacter.position)
        modules = (await self.session.execute(stmt)).scalars().all()

        records: List[IngestionRecord] = []
        for module in modules:
            content = self._format_module(module)
            if content:
                extra = module.extra or {}
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.MODULE,
                    source_id=str(module.id),
                    module_number=extra.get("module_number", module.position),
                    system_number=extra.get("system_number")
                )
                if record:
                    records.append(record)
        return records

    async def _generate_feature_outline_records(self, project_id: str) -> List[IngestionRecord]:
        """生成功能大纲记录"""
        stmt = select(ChapterOutline).where(
            ChapterOutline.project_id == project_id
        ).order_by(ChapterOutline.chapter_number)
        outlines = (await self.session.execute(stmt)).scalars().all()

        records: List[IngestionRecord] = []
        for outline in outlines:
            content = self._format_feature_outline(outline)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.FEATURE_OUTLINE,
                    source_id=str(outline.id),
                    feature_number=outline.chapter_number
                )
                if record:
                    records.append(record)
        return records

    async def _generate_dependency_records(self, project_id: str) -> List[IngestionRecord]:
        """生成依赖关系记录"""
        stmt = select(BlueprintRelationship).where(
            BlueprintRelationship.project_id == project_id
        )
        dependencies = (await self.session.execute(stmt)).scalars().all()

        records: List[IngestionRecord] = []
        for dep in dependencies:
            content = self._format_dependency(dep)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.DEPENDENCY,
                    source_id=str(dep.id),
                    from_module=dep.character_from,
                    to_module=dep.character_to
                )
                if record:
                    records.append(record)
        return records

    async def _generate_feature_prompt_records(self, project_id: str) -> List[IngestionRecord]:
        """生成功能Prompt记录"""
        from sqlalchemy.orm import selectinload
        stmt = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.selected_version_id.isnot(None)
        ).options(
            selectinload(Chapter.selected_version)
        ).order_by(Chapter.chapter_number)
        chapters = (await self.session.execute(stmt)).scalars().all()

        records: List[IngestionRecord] = []
        for chapter in chapters:
            if not chapter.selected_version or not chapter.selected_version.content:
                continue
            content = chapter.selected_version.content
            if not content.strip():
                continue

            chapter_records = self.splitter.split_feature_prompt(
                content=content,
                feature_number=chapter.chapter_number,
                feature_title=f"功能 {chapter.chapter_number}",
                source_id=str(chapter.id)
            )
            records.extend(chapter_records)
        return records

    # ==================== 私有方法：各类型入库 ====================

    async def _ingest_inspiration(self, project_id: str) -> IngestionResult:
        """入库灵感对话"""
        result = IngestionResult(success=True, data_type=CodingDataType.INSPIRATION)

        # 获取对话记录
        stmt = select(NovelConversation).where(
            NovelConversation.project_id == project_id
        ).order_by(NovelConversation.seq)
        conversations = (await self.session.execute(stmt)).scalars().all()

        if not conversations:
            return result

        # 转换为字典列表
        conv_dicts = [
            {
                "role": conv.role,
                "content": conv.content,
                "seq": conv.seq
            }
            for conv in conversations
        ]

        # 合并Q&A轮次
        records = self.splitter.merge_qa_rounds(conv_dicts, project_id)
        result.total_records = len(records)

        # 入库
        return await self._ingest_records(records, result, project_id)

    async def _ingest_architecture(self, project_id: str) -> IngestionResult:
        """入库架构设计"""
        result = IngestionResult(success=True, data_type=CodingDataType.ARCHITECTURE)

        blueprint = await self._get_blueprint(project_id)
        # 编程项目架构描述存储在 full_synopsis 字段
        if not blueprint or not blueprint.full_synopsis:
            return result

        records = self.splitter.split_architecture(
            content=blueprint.full_synopsis,
            source_id=project_id,
            data_type=CodingDataType.ARCHITECTURE
        )
        result.total_records = len(records)

        return await self._ingest_records(records, result, project_id)

    async def _ingest_tech_stack(self, project_id: str) -> IngestionResult:
        """入库技术栈"""
        result = IngestionResult(success=True, data_type=CodingDataType.TECH_STACK)

        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.world_setting:
            return result

        # 编程项目技术栈存储在 world_setting 字段
        world_setting = blueprint.world_setting
        if isinstance(world_setting, str):
            try:
                world_setting = json.loads(world_setting)
            except json.JSONDecodeError:
                return result

        # tech_stack 可能在子对象中，也可能直接在顶层
        tech_stack = world_setting.get("tech_stack", {})
        if not tech_stack:
            # 旧格式：直接在 world_setting 顶层
            tech_stack = world_setting

        records: List[IngestionRecord] = []

        # 处理components
        components = tech_stack.get("components", [])
        for idx, comp in enumerate(components):
            content = self._format_tech_component(comp)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.TECH_STACK,
                    source_id=project_id,
                    component_index=idx,
                    component_name=comp.get("name", "")
                )
                if record:
                    records.append(record)

        # 处理domains
        domains = tech_stack.get("domains", [])
        for idx, domain in enumerate(domains):
            content = self._format_tech_domain(domain)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.TECH_STACK,
                    source_id=project_id,
                    domain_index=idx,
                    domain_name=domain.get("name", "")
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_requirements(self, project_id: str) -> IngestionResult:
        """入库核心需求"""
        result = IngestionResult(success=True, data_type=CodingDataType.REQUIREMENT)

        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.world_setting:
            logger.info("入库核心需求: 无蓝图或world_setting为空")
            return result

        # 编程项目核心需求存储在 world_setting["core_requirements"]
        world_setting = blueprint.world_setting
        if isinstance(world_setting, str):
            try:
                world_setting = json.loads(world_setting)
            except json.JSONDecodeError:
                logger.warning("入库核心需求: world_setting JSON解析失败")
                return result

        requirements = world_setting.get("core_requirements", [])
        logger.info("入库核心需求: 找到 %d 条需求", len(requirements))

        records: List[IngestionRecord] = []
        for idx, req in enumerate(requirements):
            content = self._format_requirement(req)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.REQUIREMENT,
                    source_id=project_id,
                    requirement_index=idx
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_challenges(self, project_id: str) -> IngestionResult:
        """入库技术挑战"""
        result = IngestionResult(success=True, data_type=CodingDataType.CHALLENGE)

        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.world_setting:
            logger.info("入库技术挑战: 无蓝图或world_setting为空")
            return result

        # 编程项目技术挑战存储在 world_setting["technical_challenges"]
        world_setting = blueprint.world_setting
        if isinstance(world_setting, str):
            try:
                world_setting = json.loads(world_setting)
            except json.JSONDecodeError:
                logger.warning("入库技术挑战: world_setting JSON解析失败")
                return result

        challenges = world_setting.get("technical_challenges", [])
        logger.info("入库技术挑战: 找到 %d 条挑战", len(challenges))

        records: List[IngestionRecord] = []
        for idx, challenge in enumerate(challenges):
            content = self._format_challenge(challenge)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.CHALLENGE,
                    source_id=project_id,
                    challenge_index=idx
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_systems(self, project_id: str) -> IngestionResult:
        """入库系统划分"""
        result = IngestionResult(success=True, data_type=CodingDataType.SYSTEM)

        # 系统存储在part_outlines表
        stmt = select(PartOutline).where(
            PartOutline.project_id == project_id
        ).order_by(PartOutline.part_number)
        systems = (await self.session.execute(stmt)).scalars().all()

        if not systems:
            return result

        records: List[IngestionRecord] = []
        for system in systems:
            content = self._format_system(system)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.SYSTEM,
                    source_id=str(system.id),
                    system_number=system.part_number
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_modules(self, project_id: str) -> IngestionResult:
        """入库模块定义"""
        result = IngestionResult(success=True, data_type=CodingDataType.MODULE)

        # 模块存储在blueprint_characters表
        stmt = select(BlueprintCharacter).where(
            BlueprintCharacter.project_id == project_id
        ).order_by(BlueprintCharacter.position)
        modules = (await self.session.execute(stmt)).scalars().all()

        if not modules:
            return result

        records: List[IngestionRecord] = []
        for module in modules:
            content = self._format_module(module)
            if content:
                # module_number 和 system_number 存储在 extra 字段中
                extra = module.extra or {}
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.MODULE,
                    source_id=str(module.id),
                    module_number=extra.get("module_number", module.position),
                    system_number=extra.get("system_number")
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_feature_outlines(self, project_id: str) -> IngestionResult:
        """入库功能大纲"""
        result = IngestionResult(success=True, data_type=CodingDataType.FEATURE_OUTLINE)

        # 功能大纲存储在chapter_outlines表
        stmt = select(ChapterOutline).where(
            ChapterOutline.project_id == project_id
        ).order_by(ChapterOutline.chapter_number)
        outlines = (await self.session.execute(stmt)).scalars().all()

        if not outlines:
            return result

        records: List[IngestionRecord] = []
        for outline in outlines:
            content = self._format_feature_outline(outline)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.FEATURE_OUTLINE,
                    source_id=str(outline.id),
                    feature_number=outline.chapter_number
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_dependencies(self, project_id: str) -> IngestionResult:
        """入库依赖关系"""
        result = IngestionResult(success=True, data_type=CodingDataType.DEPENDENCY)

        # 依赖关系存储在blueprint_relationships表
        stmt = select(BlueprintRelationship).where(
            BlueprintRelationship.project_id == project_id
        )
        dependencies = (await self.session.execute(stmt)).scalars().all()

        if not dependencies:
            return result

        records: List[IngestionRecord] = []
        for dep in dependencies:
            content = self._format_dependency(dep)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.DEPENDENCY,
                    source_id=str(dep.id),
                    from_module=dep.character_from,
                    to_module=dep.character_to
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_feature_prompts(self, project_id: str) -> IngestionResult:
        """入库功能Prompt"""
        result = IngestionResult(success=True, data_type=CodingDataType.FEATURE_PROMPT)

        # 功能Prompt存储在chapters表，内容在选中版本中
        from sqlalchemy.orm import selectinload
        stmt = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.selected_version_id.isnot(None)
        ).options(
            selectinload(Chapter.selected_version)
        ).order_by(Chapter.chapter_number)
        chapters = (await self.session.execute(stmt)).scalars().all()

        if not chapters:
            return result

        records: List[IngestionRecord] = []
        for chapter in chapters:
            # 获取选中版本的内容
            if not chapter.selected_version or not chapter.selected_version.content:
                continue

            content = chapter.selected_version.content
            if not content.strip():
                continue

            # 功能Prompt需要分割
            chapter_records = self.splitter.split_feature_prompt(
                content=content,
                feature_number=chapter.chapter_number,
                feature_title=f"功能 {chapter.chapter_number}",
                source_id=str(chapter.id)
            )
            records.extend(chapter_records)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    # ==================== 私有方法：辅助函数 ====================

    async def _get_blueprint(self, project_id: str) -> Optional[NovelBlueprint]:
        """获取项目蓝图"""
        stmt = select(NovelBlueprint).where(NovelBlueprint.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_db_count(self, project_id: str, data_type: CodingDataType) -> int:
        """获取数据库中某类型的记录数"""
        table = CodingDataType.get_source_table(data_type.value)

        # 根据表名查询
        if table == "novel_conversations":
            stmt = select(func.count()).select_from(NovelConversation).where(
                NovelConversation.project_id == project_id
            )
            # 对话按轮次计算，大约是记录数/2
            result = await self.session.execute(stmt)
            count = result.scalar() or 0
            return (count + 1) // 2  # 估算轮次数

        elif table == "novel_blueprints":
            # 蓝图字段，需要检查非空
            blueprint = await self._get_blueprint(project_id)
            if not blueprint:
                return 0

            # 编程项目数据存储在 world_setting 字段中
            world_setting = blueprint.world_setting or {}
            if isinstance(world_setting, str):
                try:
                    world_setting = json.loads(world_setting)
                except json.JSONDecodeError:
                    world_setting = {}

            if data_type == CodingDataType.ARCHITECTURE:
                # 架构描述存储在 full_synopsis
                return 1 if blueprint.full_synopsis else 0
            elif data_type == CodingDataType.TECH_STACK:
                # 技术栈存储在 world_setting["tech_stack"] 或直接在 world_setting
                tech_stack = world_setting.get("tech_stack", world_setting)
                return len(tech_stack.get("components", [])) + len(tech_stack.get("domains", []))
            elif data_type == CodingDataType.REQUIREMENT:
                reqs = world_setting.get("core_requirements", [])
                return len(reqs) if isinstance(reqs, list) else 0
            elif data_type == CodingDataType.CHALLENGE:
                challenges = world_setting.get("technical_challenges", [])
                return len(challenges) if isinstance(challenges, list) else 0

        elif table == "part_outlines":
            stmt = select(func.count()).select_from(PartOutline).where(
                PartOutline.project_id == project_id
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        elif table == "blueprint_characters":
            stmt = select(func.count()).select_from(BlueprintCharacter).where(
                BlueprintCharacter.project_id == project_id
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        elif table == "chapter_outlines":
            stmt = select(func.count()).select_from(ChapterOutline).where(
                ChapterOutline.project_id == project_id
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        elif table == "blueprint_relationships":
            stmt = select(func.count()).select_from(BlueprintRelationship).where(
                BlueprintRelationship.project_id == project_id
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        elif table == "chapters":
            # 章节内容在选中版本中，需要检查有选中版本的章节数
            stmt = select(func.count()).select_from(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.selected_version_id.isnot(None)
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        return 0

    async def _get_vector_count(self, project_id: str, data_type: CodingDataType) -> int:
        """获取向量库中某类型的记录数"""
        if not self.vector_store or not self.vector_store._client:
            return 0

        try:
            await self.vector_store.ensure_schema()
            sql = """
            SELECT COUNT(*) as cnt FROM rag_chunks
            WHERE project_id = :project_id
            AND json_extract(metadata, '$.data_type') = :data_type
            """
            result = await self.vector_store._client.execute(
                sql,
                {"project_id": project_id, "data_type": data_type.value}
            )
            rows = list(self.vector_store._iter_rows(result))
            if rows:
                return rows[0].get("cnt", 0)
        except Exception as e:
            logger.warning(
                "获取向量库记录数失败: project=%s type=%s error=%s",
                project_id, data_type.value, str(e)
            )
        return 0

    async def _ingest_records(
        self,
        records: List[IngestionRecord],
        result: IngestionResult,
        project_id: str
    ) -> IngestionResult:
        """
        将记录入库到向量库

        Args:
            records: 入库记录列表
            result: 结果对象（会被修改）
            project_id: 项目ID（用于向量库的project_id字段）

        Returns:
            更新后的结果对象
        """
        if not records:
            return result

        if not self.vector_store:
            result.success = False
            result.error_message = "向量库未启用"
            return result

        # 批量生成embedding
        embeddings = await self._batch_get_embeddings([r.content for r in records])

        if len(embeddings) != len(records):
            result.success = False
            result.error_message = "生成embedding数量不匹配"
            return result

        # 构建入库数据
        chunk_records = []
        for idx, (record, embedding) in enumerate(zip(records, embeddings)):
            if not embedding:
                result.failed_count += 1
                continue

            chunk_id = record.get_chunk_id()
            metadata = {
                **record.metadata,
                "data_type": record.data_type.value,
                "paragraph_hash": record.get_content_hash(),
                "length": len(record.content),
                "source_id": record.source_id,  # 保存原始source_id到metadata
            }

            # 根据数据类型生成有意义的来源信息
            chapter_number, chapter_title = self._get_source_info(record)

            chunk_records.append({
                "id": chunk_id,
                "project_id": project_id,  # 始终使用传入的project_id
                "chapter_number": chapter_number,
                "chunk_index": record.metadata.get("section_index", idx),
                "chapter_title": chapter_title,
                "content": record.content,
                "embedding": embedding,
                "metadata": metadata,
            })

        # 写入向量库
        try:
            # 记录入库数据的详细信息
            if chunk_records:
                sample = chunk_records[0]
                logger.info(
                    "入库数据样本: type=%s id=%s chapter_title=%s metadata_keys=%s data_type_in_meta=%s",
                    result.data_type.value,
                    sample.get("id", "")[:30],
                    sample.get("chapter_title", ""),
                    list(sample.get("metadata", {}).keys()),
                    sample.get("metadata", {}).get("data_type", "MISSING!")
                )

            await self.vector_store.upsert_chunks(records=chunk_records)
            result.added_count = len(chunk_records)
            logger.info(
                "入库完成: type=%s count=%d",
                result.data_type.value, result.added_count
            )
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(
                "入库失败: type=%s error=%s",
                result.data_type.value, str(e)
            )

        return result

    def _get_source_info(self, record: IngestionRecord) -> tuple:
        """
        根据数据类型获取来源信息

        返回 (chapter_number, chapter_title) 元组，用于在前端显示来源。

        Args:
            record: 入库记录

        Returns:
            (chapter_number, chapter_title) 元组
        """
        data_type = record.data_type
        metadata = record.metadata

        # 调试日志：记录每条记录的数据类型
        logger.debug(
            "获取来源信息: data_type=%s metadata_keys=%s",
            data_type, list(metadata.keys()) if metadata else []
        )

        # 数据类型到来源信息的映射
        if data_type == CodingDataType.FEATURE_PROMPT:
            # 功能Prompt: F{feature_number} - {parent_title}
            num = metadata.get("feature_number", 0)
            title = metadata.get("parent_title", "")
            section = metadata.get("section_title", "")
            if section:
                title = f"{title} > {section}" if title else section
            return (num, title or f"功能{num}")

        elif data_type == CodingDataType.FEATURE_OUTLINE:
            # 功能大纲: F{feature_number}
            num = metadata.get("feature_number", 0)
            return (num, f"功能大纲{num}")

        elif data_type == CodingDataType.SYSTEM:
            # 系统: S{system_number}
            num = metadata.get("system_number", 0)
            return (num, f"系统{num}")

        elif data_type == CodingDataType.MODULE:
            # 模块: M{module_number}
            num = metadata.get("module_number", 0)
            sys_num = metadata.get("system_number", 0)
            return (num, f"系统{sys_num}-模块{num}")

        elif data_type == CodingDataType.INSPIRATION:
            # 灵感对话: 轮次{round_number}
            round_num = metadata.get("round_number", 0) + 1  # 从1开始显示
            return (round_num, f"对话轮次{round_num}")

        elif data_type == CodingDataType.ARCHITECTURE:
            # 架构设计: 按section显示
            section = metadata.get("section_title", "")
            section_idx = metadata.get("section_index", 0) + 1
            return (section_idx, section or f"架构设计{section_idx}")

        elif data_type == CodingDataType.TECH_STACK:
            # 技术栈: 组件/领域名称
            comp_name = metadata.get("component_name", "")
            domain_name = metadata.get("domain_name", "")
            name = comp_name or domain_name
            idx = metadata.get("component_index", metadata.get("domain_index", 0)) + 1
            return (idx, name or f"技术栈{idx}")

        elif data_type == CodingDataType.REQUIREMENT:
            # 核心需求
            idx = metadata.get("requirement_index", 0) + 1
            return (idx, f"核心需求{idx}")

        elif data_type == CodingDataType.CHALLENGE:
            # 技术挑战
            idx = metadata.get("challenge_index", 0) + 1
            return (idx, f"技术挑战{idx}")

        elif data_type == CodingDataType.DEPENDENCY:
            # 依赖关系
            from_mod = metadata.get("from_module", "")
            to_mod = metadata.get("to_module", "")
            return (0, f"{from_mod} -> {to_mod}" if from_mod and to_mod else "模块依赖")

        # 默认
        return (0, CodingDataType.get_display_name(data_type.value))

    async def _batch_get_embeddings(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[Optional[List[float]]]:
        """
        批量获取embedding

        Args:
            texts: 文本列表
            batch_size: 批次大小

        Returns:
            embedding列表（与texts顺序对应）
        """
        embeddings: List[Optional[List[float]]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                try:
                    embedding = await self.llm_service.get_embedding(
                        text,
                        user_id=self.user_id
                    )
                    embeddings.append(embedding)
                except Exception as e:
                    logger.warning("生成embedding失败: %s", str(e))
                    embeddings.append(None)

        return embeddings

    # ==================== 私有方法：格式化函数 ====================

    def _format_tech_component(self, comp: Dict[str, Any]) -> str:
        """格式化技术组件"""
        parts = []
        name = comp.get("name", "")
        if name:
            parts.append(f"技术组件: {name}")
        category = comp.get("category", "")
        if category:
            parts.append(f"分类: {category}")
        version = comp.get("version", "")
        if version:
            parts.append(f"版本: {version}")
        purpose = comp.get("purpose", "")
        if purpose:
            parts.append(f"用途: {purpose}")
        return "\n".join(parts)

    def _format_tech_domain(self, domain: Dict[str, Any]) -> str:
        """格式化技术领域"""
        parts = []
        name = domain.get("name", "")
        if name:
            parts.append(f"技术领域: {name}")
        description = domain.get("description", "")
        if description:
            parts.append(f"描述: {description}")
        techs = domain.get("technologies", [])
        if techs:
            parts.append(f"技术栈: {', '.join(techs)}")
        return "\n".join(parts)

    def _format_requirement(self, req: Any) -> str:
        """格式化核心需求"""
        if isinstance(req, str):
            return f"核心需求: {req}"
        if isinstance(req, dict):
            parts = []
            # 支持两种格式：
            # 新格式: category, requirement, priority
            # 旧格式: title/name, description, priority
            category = req.get("category", "")
            requirement = req.get("requirement", "")
            title = req.get("title", req.get("name", ""))
            desc = req.get("description", "")
            priority = req.get("priority", "")

            if category:
                parts.append(f"分类: {category}")
            if requirement:
                parts.append(f"需求: {requirement}")
            elif title:
                parts.append(f"需求: {title}")
            if desc:
                parts.append(f"描述: {desc}")
            if priority:
                parts.append(f"优先级: {priority}")

            return "\n".join(parts) if parts else ""
        return str(req) if req else ""

    def _format_challenge(self, challenge: Any) -> str:
        """格式化技术挑战"""
        if isinstance(challenge, str):
            return f"技术挑战: {challenge}"
        if isinstance(challenge, dict):
            parts = []
            # 支持两种格式：
            # 新格式: challenge, impact, solution_direction
            # 旧格式: title/name, description, solution
            challenge_text = challenge.get("challenge", "")
            title = challenge.get("title", challenge.get("name", ""))
            impact = challenge.get("impact", "")
            desc = challenge.get("description", "")
            solution_direction = challenge.get("solution_direction", "")
            solution = challenge.get("solution", "")

            if challenge_text:
                parts.append(f"挑战: {challenge_text}")
            elif title:
                parts.append(f"挑战: {title}")
            if impact:
                parts.append(f"影响: {impact}")
            if desc:
                parts.append(f"描述: {desc}")
            if solution_direction:
                parts.append(f"解决方向: {solution_direction}")
            elif solution:
                parts.append(f"解决方案: {solution}")

            return "\n".join(parts) if parts else ""
        return str(challenge) if challenge else ""

    def _format_system(self, system: PartOutline) -> str:
        """格式化系统划分"""
        parts = [f"系统 {system.part_number}: {system.title or ''}"]
        if system.summary:
            parts.append(f"描述: {system.summary}")
        # 职责存储在 theme 字段
        if system.theme:
            try:
                responsibilities = json.loads(system.theme) if system.theme.startswith('[') else [system.theme]
                if responsibilities:
                    parts.append(f"职责: {', '.join(str(r) for r in responsibilities)}")
            except (json.JSONDecodeError, TypeError):
                parts.append(f"职责: {system.theme}")
        # 技术要求存储在 key_events 字段
        if system.key_events:
            if isinstance(system.key_events, list):
                tech_req = "\n".join(str(e) for e in system.key_events)
            else:
                tech_req = str(system.key_events)
            if tech_req:
                parts.append(f"技术要求: {tech_req}")
        return "\n".join(parts)

    def _format_module(self, module: BlueprintCharacter) -> str:
        """格式化模块定义"""
        parts = [f"模块: {module.name or ''}"]
        if module.identity:
            parts.append(f"类型: {module.identity}")
        if module.personality:
            parts.append(f"描述: {module.personality}")
        if module.goals:
            parts.append(f"接口: {module.goals}")
        # 依赖存储在 abilities 字段
        if module.abilities:
            try:
                deps = json.loads(module.abilities) if module.abilities.startswith('[') else [d.strip() for d in module.abilities.split(',') if d.strip()]
                if deps:
                    parts.append(f"依赖: {', '.join(str(d) for d in deps)}")
            except (json.JSONDecodeError, TypeError):
                parts.append(f"依赖: {module.abilities}")
        return "\n".join(parts)

    def _format_feature_outline(self, outline: ChapterOutline) -> str:
        """格式化功能大纲"""
        parts = [f"功能 {outline.chapter_number}: {outline.title or ''}"]
        if outline.summary:
            parts.append(f"描述: {outline.summary}")
        return "\n".join(parts)

    def _format_dependency(self, dep: BlueprintRelationship) -> str:
        """格式化依赖关系"""
        parts = []
        # 依赖关系：从 character_from 到 character_to
        if dep.character_from and dep.character_to:
            parts.append(f"依赖关系: {dep.character_from} -> {dep.character_to}")
        if dep.description:
            parts.append(f"描述: {dep.description}")
        return "\n".join(parts) if parts else "模块依赖关系"


__all__ = [
    "CodingProjectIngestionService",
    "IngestionResult",
    "CompletenessReport",
]
