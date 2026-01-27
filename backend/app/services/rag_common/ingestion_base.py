"""
RAG入库通用基础实现

提供通用的入库结果数据结构与基础入库流程，供编码/小说项目复用。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Type

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """入库结果"""
    success: bool
    data_type: Any
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


class BaseProjectIngestionService:
    """
    RAG入库基础服务

    提供通用的入库流程、完整性检查与向量库清理逻辑。
    子类负责提供数据类型枚举、分割器与具体入库方法映射。
    """

    DATA_TYPE_ENUM: Optional[Type[Any]] = None
    SPLITTER_FACTORY: Optional[Callable[[], Any]] = None
    LOG_TITLE: str = "开始入库"
    LOGGER_OBJ: Optional[logging.Logger] = None
    RECORD_GENERATOR_METHODS: Dict[Any, str] = {}

    def __init__(
        self,
        session: Any,
        vector_store: Any,
        llm_service: Any,
        user_id: int,
        data_type_enum: Optional[Type[Any]] = None,
        splitter: Optional[Any] = None,
        log_title: Optional[str] = None,
        logger_obj: Optional[logging.Logger] = None,
    ):
        self.session = session
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.user_id = self._to_int(user_id, default=1)

        resolved_data_type_enum = data_type_enum or self.DATA_TYPE_ENUM
        if not resolved_data_type_enum:
            raise RuntimeError("子类必须提供 DATA_TYPE_ENUM 或在初始化时传入 data_type_enum")
        self.data_type_enum = resolved_data_type_enum

        resolved_splitter = splitter
        if resolved_splitter is None:
            if not self.SPLITTER_FACTORY:
                raise RuntimeError("子类必须提供 SPLITTER_FACTORY 或在初始化时传入 splitter")
            resolved_splitter = self.SPLITTER_FACTORY()
        self.splitter = resolved_splitter

        self._log_title = log_title or self.LOG_TITLE
        self._logger = logger_obj or self.LOGGER_OBJ or logger

    # ==================== 子类需要实现的方法 ====================

    def _get_ingest_method_map(self) -> Dict[Any, Callable[..., Any]]:
        """获取数据类型到入库方法的映射"""
        raise NotImplementedError("子类必须实现 _get_ingest_method_map")

    async def _generate_records_for_type(self, project_id: str, data_type: Any) -> List[Any]:
        """
        生成指定类型的入库记录（默认实现）

        默认通过 `RECORD_GENERATOR_METHODS` 做表驱动分发，将 data_type 映射到
        子类的 `_generate_*_records(project_id)` 方法名。
        """
        method_name = self.RECORD_GENERATOR_METHODS.get(data_type)
        if not method_name:
            return []
        method = getattr(self, method_name, None)
        if not method:
            return []
        return await method(project_id)

    def _get_display_name(self, data_type: Any) -> str:
        """获取数据类型显示名称"""
        return self.data_type_enum.get_display_name(data_type.value)

    # ==================== 子类可覆盖的 hook（默认不处理） ====================

    def _prepare_metadata_for_vector_store(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """将 metadata 转换为可写入向量库的结构（默认直接返回）"""
        return metadata

    def _prepare_embedding_for_vector_store(self, embedding: Any) -> Any:
        """将 embedding 转换为可写入向量库的结构（默认直接返回）"""
        return embedding

    def _log_ingest_sample(self, result: IngestionResult, chunk_records: List[Dict[str, Any]]) -> None:
        """入库前的样本日志（默认 no-op，子类可按需覆盖）"""
        return None

    def _get_source_info(self, record: Any) -> tuple:
        """子类需提供：根据记录生成 (chapter_number, chapter_title) 用于来源展示"""
        raise NotImplementedError("子类必须实现 _get_source_info")

    @staticmethod
    def _to_int(value: Any, *, default: int) -> int:
        """尽量把 value 规范化为 int（兼容 numpy/int/str 等），失败时返回 default"""
        if value is None:
            return default
        try:
            return int(value)
        except Exception:
            return default

    async def _batch_get_embeddings(
        self,
        texts: List[str],
        batch_size: int = 10,
    ) -> List[Optional[List[float]]]:
        """批量获取 embedding（失败时以 None 占位，保持索引对齐）"""
        embeddings: List[Optional[List[float]]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                try:
                    embedding = await self.llm_service.get_embedding(
                        text,
                        user_id=self.user_id,
                    )
                    embeddings.append(embedding)
                except Exception as exc:
                    self._logger.warning("生成embedding失败: %s", str(exc))
                    embeddings.append(None)

        return embeddings

    async def _get_sentence_embeddings(self, sentences: List[str]) -> Any:
        """为语义分块器提供句子嵌入矩阵（失败句子用零向量占位）。"""
        import numpy as np

        if not sentences:
            return np.array([])

        raw_embeddings: List[Optional[List[float]]] = []
        for sentence in sentences:
            try:
                embedding = await self.llm_service.get_embedding(
                    sentence,
                    user_id=self.user_id,
                )
                raw_embeddings.append(embedding or None)
            except Exception as exc:
                self._logger.warning("获取句子嵌入失败: %s", str(exc))
                raw_embeddings.append(None)

        dim = next((len(e) for e in raw_embeddings if e), 1536)
        embeddings = [
            e if (e and len(e) == dim) else ([0.0] * dim)
            for e in raw_embeddings
        ]
        return np.array(embeddings)

    async def _ingest_records(
        self,
        records: List[Any],
        result: IngestionResult,
        project_id: str,
    ) -> IngestionResult:
        """将记录入库到向量库（通用骨架实现）"""
        if not records:
            return result

        if not self.vector_store:
            result.success = False
            result.error_message = "向量库未启用"
            return result

        embeddings = await self._batch_get_embeddings([r.content for r in records])
        if len(embeddings) != len(records):
            result.success = False
            result.error_message = "生成embedding数量不匹配"
            return result

        chunk_records: List[Dict[str, Any]] = []
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
                "source_id": record.source_id,
            }
            metadata = self._prepare_metadata_for_vector_store(metadata)

            chapter_number, chapter_title = self._get_source_info(record)
            chapter_number_int = self._to_int(chapter_number, default=0)

            chunk_index = record.metadata.get("section_index", idx)
            chunk_index_int = self._to_int(chunk_index, default=idx)

            chunk_records.append(
                {
                    "id": chunk_id,
                    "project_id": project_id,
                    "chapter_number": chapter_number_int,
                    "chunk_index": chunk_index_int,
                    "chapter_title": chapter_title,
                    "content": record.content,
                    "embedding": self._prepare_embedding_for_vector_store(embedding),
                    "metadata": metadata,
                }
            )

        try:
            if chunk_records:
                self._log_ingest_sample(result, chunk_records)

            await self.vector_store.upsert_chunks(records=chunk_records)
            result.added_count = len(chunk_records)
            self._logger.info(
                "入库完成: type=%s count=%d",
                result.data_type.value,
                result.added_count,
            )
        except Exception as exc:
            result.success = False
            result.error_message = str(exc)
            self._logger.error(
                "入库失败: type=%s error=%s",
                result.data_type.value,
                str(exc),
            )

        return result

    # ==================== 通用流程实现 ====================

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
        self._logger.info(
            "=== %s === project=%s force=%s vector_store=%s",
            self._log_title, project_id, force,
            "已启用" if self.vector_store else "未启用"
        )

        results: Dict[str, IngestionResult] = {}

        # 强制模式下，先删除所有旧数据
        if force and self.vector_store:
            self._logger.info("强制重建模式: 准备删除所有旧数据 project=%s", project_id)
            try:
                deleted = await self.vector_store.delete_by_project(project_id)
                self._logger.info(
                    "强制重建: 已删除项目 %s 的 %d 条旧RAG数据",
                    project_id, deleted
                )
            except Exception as e:
                self._logger.error(
                    "强制重建: 删除旧数据失败 project=%s error=%s",
                    project_id, str(e)
                )
        else:
            # 智能模式下，清理没有data_type字段的旧数据
            if self.vector_store:
                try:
                    legacy_deleted = await self.vector_store.delete_legacy_chunks(project_id)
                    if legacy_deleted > 0:
                        self._logger.info(
                            "智能同步: 已清理项目 %s 的 %d 条旧版数据",
                            project_id, legacy_deleted
                        )
                except Exception as e:
                    self._logger.warning(
                        "智能同步: 清理旧版数据失败 project=%s error=%s",
                        project_id, str(e)
                    )

        # 如果不是强制模式，先检查完整性，只入库不完整的类型
        incomplete_types: Set[Any] = set()
        if not force:
            report = await self.check_completeness(project_id)
            for type_name, detail in report.type_details.items():
                if not detail.get("complete", True):
                    try:
                        incomplete_types.add(self.data_type_enum(type_name))
                    except ValueError:
                        pass

            # 如果全部完整，直接返回空结果（表示无需入库）
            if not incomplete_types:
                self._logger.info("项目 %s 所有数据类型已完整，跳过入库", project_id)
                return results

            self._logger.info(
                "项目 %s 需要入库的类型: %s",
                project_id,
                [t.value for t in incomplete_types]
            )

        # 遍历需要入库的类型
        types_to_process = incomplete_types if incomplete_types else set(self.data_type_enum.all_types())

        for data_type in self.data_type_enum.all_types():
            if data_type not in types_to_process:
                # 跳过已完整的类型
                results[data_type.value] = IngestionResult(
                    success=True,
                    data_type=data_type,
                    skipped_count=1,
                )
                continue

            try:
                result = await self.ingest_by_type(project_id, data_type)
                results[data_type.value] = result
            except Exception as e:
                self._logger.error(
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
        data_type: Any
    ) -> IngestionResult:
        """
        按类型入库

        流程：
        1. 先清理向量库中该类型的过时数据
        2. 再执行新数据的入库（upsert）
        """
        # 先清理该类型的过时数据
        await self._cleanup_stale_chunks(project_id, data_type)

        method_map = self._get_ingest_method_map()
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
        data_type: Any
    ) -> int:
        """
        清理向量库中该类型的过时数据

        对比当前数据库中应有的chunk_id与向量库中存储的chunk_id，
        删除向量库中多余的（过时的）记录。
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
            self._logger.info(
                "清理过时向量数据: project=%s type=%s count=%d",
                project_id, data_type.value, len(stale_ids)
            )
            await self.vector_store.delete_chunks_by_ids(list(stale_ids))

            return len(stale_ids)

        except Exception as e:
            self._logger.warning(
                "清理过时向量数据失败: project=%s type=%s error=%s",
                project_id, data_type.value, str(e)
            )
            return 0

    async def check_completeness(self, project_id: str) -> CompletenessReport:
        """
        检查入库完整性（基于内容哈希的精确检测）

        对比数据库中每条记录的内容哈希与向量库中存储的哈希，
        精确检测新增、修改、删除的记录。
        """
        report = CompletenessReport(
            project_id=project_id,
            complete=True
        )

        for data_type in self.data_type_enum.all_types():
            try:
                detail = await self._check_type_completeness(project_id, data_type)

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
                self._logger.warning(
                    "检查类型完整性失败: project=%s type=%s error=%s",
                    project_id, data_type.value, str(e)
                )
                report.type_details[data_type.value] = {
                    "db_count": 0,
                    "vector_count": 0,
                    "complete": False,
                    "new_count": 0,
                    "modified_count": 0,
                    "deleted_count": 0,
                    "has_changes": False,
                    "display_name": self._get_display_name(data_type),
                    "missing": 0,
                    "error": str(e),
                }
                report.complete = False

        return report

    async def _check_type_completeness(
        self,
        project_id: str,
        data_type: Any
    ) -> TypeChangeDetail:
        """
        检查单个数据类型的完整性（基于哈希比对）
        """
        detail = TypeChangeDetail(
            display_name=self._get_display_name(data_type)
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
                self._logger.warning(
                    "获取向量库哈希失败: project=%s type=%s error=%s",
                    project_id, data_type.value, str(e)
                )

        detail.vector_count = len(stored_hashes)

        # 3. 比对哈希，检测变动
        expected_ids = set(expected_hashes.keys())
        stored_ids = set(stored_hashes.keys())

        new_ids = expected_ids - stored_ids
        detail.new_count = len(new_ids)

        deleted_ids = stored_ids - expected_ids
        detail.deleted_count = len(deleted_ids)

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

        detail.complete = (
            detail.new_count == 0 and
            detail.modified_count == 0 and
            detail.deleted_count == 0
        )

        if detail.has_changes:
            self._logger.info(
                "检测到变动: project=%s type=%s db_count=%d vector_count=%d "
                "new=%d modified=%d deleted=%d",
                project_id, data_type.value,
                detail.db_count, detail.vector_count,
                detail.new_count, detail.modified_count, detail.deleted_count
            )
            if new_ids:
                sample_new = list(new_ids)[:3]
                self._logger.info(
                    "  新增ID样本: %s", [item[:50] for item in sample_new]
                )
            if deleted_ids:
                sample_deleted = list(deleted_ids)[:3]
                self._logger.info(
                    "  删除ID样本: %s", [item[:50] for item in sample_deleted]
                )
            if modified_details:
                self._logger.info(
                    "  修改详情样本: %s", modified_details[:3]
                )
        else:
            self._logger.info(
                "类型完整: project=%s type=%s count=%d",
                project_id, data_type.value, detail.db_count
            )

        return detail


__all__ = [
    "IngestionResult",
    "TypeChangeDetail",
    "CompletenessReport",
    "BaseProjectIngestionService",
]
