from __future__ import annotations

"""
基于 libsql 的向量检索服务，封装章节内容的存储与查询。

本文件中的注释均使用中文，便于团队成员快速理解 RAG 相关逻辑。
"""

import asyncio
import json
import logging
import math
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Sequence, TypeVar

from ..core.config import settings

try:  # noqa: SIM105 - 明确区分依赖缺失的情况
    import libsql_client
except ImportError:  # pragma: no cover - 在未安装依赖时提供友好提示
    libsql_client = None  # type: ignore[assignment]

# 尝试导入numpy用于加速向量计算
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None  # type: ignore[assignment]
    NUMPY_AVAILABLE = False

logger = logging.getLogger(__name__)

# P2修复: RAG检索超时和重试配置
RAG_QUERY_TIMEOUT = 10.0  # 单次查询超时时间（秒）
RAG_MAX_RETRIES = 2  # 最大重试次数
RAG_RETRY_DELAY = 0.5  # 重试间隔基础时间（秒），实际使用指数退避


@dataclass
class RetrievedChunk:
    """向量检索得到的剧情片段。"""

    content: str
    chapter_number: int
    chapter_title: Optional[str]
    score: float
    metadata: Dict[str, Any]


@dataclass
class RetrievedSummary:
    """向量检索得到的章节摘要。"""

    chapter_number: int
    title: str
    summary: str
    score: float


# 泛型类型变量，用于统一回退查询逻辑
T = TypeVar("T", RetrievedChunk, RetrievedSummary)


class VectorStoreService:
    """libsql 向量库操作工具，确保不同小说项目的数据隔离。"""

    def __init__(self) -> None:
        if not settings.vector_store_enabled:
            logger.warning("未开启向量库配置，RAG 检索将被跳过。")
            self._client = None
            self._schema_ready = True
            return

        if libsql_client is None:  # pragma: no cover - 运行环境缺少依赖
            raise RuntimeError("缺少 libsql-client 依赖，请先在环境中安装。")

        url = settings.vector_db_url
        if url and url.startswith("file:"):
            path_part = url.split("file:", 1)[1]
            path_obj = Path(path_part).expanduser()
            if not path_obj.is_absolute():
                # 相对路径：基于 storage_dir 解析，避免因工作目录不同导致路径错误
                # 例如 "storage/vectors.db" 会解析为 "{project_root}/storage/vectors.db"
                resolved = (settings.storage_dir.parent / path_part).resolve()
            else:
                resolved = path_obj.resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            url = f"file:{resolved}"
            logger.info("向量库使用本地文件: %s", resolved)

        try:
            logger.info("初始化 libsql 客户端: url=%s", url)
            self._client = libsql_client.create_client(
                url=url,
                auth_token=settings.vector_db_auth_token,
            )
        except Exception as exc:  # pragma: no cover - 连接异常仅打印日志
            logger.error("初始化 libsql 客户端失败: %s", exc)
            self._client = None
            self._schema_ready = True
            self._vector_func_available = False
        else:
            self._schema_ready = False
            self._vector_func_available: Optional[bool] = None  # 延迟检测
            logger.info("libsql 客户端初始化成功，等待建表。")

    async def ensure_schema(self) -> None:
        """初始化向量表结构，保证系统首次运行即可使用。"""
        if not self._client or self._schema_ready:
            return

        statements = [
            """
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                chapter_title TEXT,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT,
                created_at INTEGER DEFAULT (unixepoch())
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_project
            ON rag_chunks(project_id, chapter_number)
            """,
            """
            CREATE TABLE IF NOT EXISTS rag_summaries (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at INTEGER DEFAULT (unixepoch())
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_rag_summaries_project
            ON rag_summaries(project_id, chapter_number)
            """,
        ]

        try:
            for sql in statements:
                await self._client.execute(sql)  # type: ignore[union-attr]
            logger.info("已确保向量库表结构存在。")
        except Exception as exc:  # pragma: no cover - 初始化失败时记录日志
            logger.error("创建向量库表结构失败: %s", exc)
        else:
            self._schema_ready = True
            # 检测向量函数可用性
            await self._check_vector_function_availability()

    async def _check_vector_function_availability(self) -> None:
        """
        检测向量距离函数是否可用

        在首次查询前检测 vector_distance_cosine 函数是否可用。
        如果不可用，会记录警告日志并标记使用Python回退计算。
        """
        if self._vector_func_available is not None:
            return  # 已经检测过

        if not self._client:
            self._vector_func_available = False
            return

        # 尝试执行一个简单的向量函数调用来检测可用性
        test_sql = "SELECT vector_distance_cosine(X'00000000', X'00000000') AS test"
        try:
            await self._client.execute(test_sql)
            self._vector_func_available = True
            logger.info("向量库函数检测通过: vector_distance_cosine 可用")
        except Exception as exc:
            if "no such function" in str(exc).lower():
                self._vector_func_available = False
                logger.warning(
                    "===== 性能警告 =====\n"
                    "向量库缺少 vector_distance_cosine 函数！\n"
                    "系统将回退至 Python 层相似度计算，这会导致：\n"
                    "  - 全表扫描所有向量数据\n"
                    "  - 内存占用大幅增加\n"
                    "  - 检索速度显著下降\n"
                    "建议：请确保使用支持向量扩展的 libsql 版本。\n"
                    "====================="
                )
            else:
                # 其他错误，假设函数可用（让后续查询时再处理）
                self._vector_func_available = True
                logger.warning("向量函数检测时发生未知错误: %s", exc)

    async def _execute_with_retry(
        self,
        operation: Callable[[], Any],
        operation_name: str,
        timeout: float = RAG_QUERY_TIMEOUT,
        max_retries: int = RAG_MAX_RETRIES,
    ) -> Any:
        """
        P2修复: 带超时和重试的操作执行器

        Args:
            operation: 要执行的异步操作（无参数的协程函数）
            operation_name: 操作名称（用于日志）
            timeout: 单次操作超时时间（秒）
            max_retries: 最大重试次数

        Returns:
            操作结果

        Raises:
            最后一次尝试的异常（如果所有重试都失败）
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                # 使用 asyncio.wait_for 添加超时控制
                return await asyncio.wait_for(operation(), timeout=timeout)

            except asyncio.TimeoutError:
                last_exception = asyncio.TimeoutError(
                    f"{operation_name} 超时（{timeout}秒）"
                )
                logger.warning(
                    "%s 第 %d/%d 次尝试超时",
                    operation_name,
                    attempt + 1,
                    max_retries + 1,
                )

            except Exception as exc:
                last_exception = exc
                # 检查是否为可重试的错误（网络错误、连接错误等）
                error_str = str(exc).lower()
                is_retryable = any(
                    keyword in error_str
                    for keyword in ["timeout", "connection", "network", "temporary", "busy"]
                )

                if not is_retryable:
                    # 不可重试的错误，直接抛出
                    raise

                logger.warning(
                    "%s 第 %d/%d 次尝试失败: %s",
                    operation_name,
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )

            # 如果还有重试机会，等待后重试（指数退避）
            if attempt < max_retries:
                delay = RAG_RETRY_DELAY * (2 ** attempt)
                await asyncio.sleep(delay)

        # 所有重试都失败，抛出最后一个异常
        if last_exception:
            raise last_exception
        raise RuntimeError(f"{operation_name} 失败，原因未知")

    async def _query_with_vector_distance(
        self,
        *,
        operation_name: str,
        failure_title: str,
        sql: str,
        params: Dict[str, Any],
        top_k: int,
        row_mapper: Callable[[Dict[str, Any]], T],
        python_fallback: Callable[[], Awaitable[List[T]]],
    ) -> List[T]:
        """
        统一封装“向量距离函数查询 + 超时重试 + 回退”的通用模板。

        - 当 `vector_distance_cosine` 不可用时，自动切换到 Python 相似度计算（一次检测，后续直接回退）。
        - 当查询超时/失败时，返回空结果（保持原接口的容错语义）。
        """
        if not self._client or top_k <= 0:
            return []

        # 如果已知向量函数不可用，直接使用Python回退计算
        if self._vector_func_available is False:
            return await python_fallback()

        async def _do_query():
            return await self._client.execute(  # type: ignore[union-attr]
                sql,
                params,
            )

        try:
            result = await self._execute_with_retry(
                _do_query,
                operation_name,
            )
        except asyncio.TimeoutError:
            logger.warning("%s超时，返回空结果", operation_name)
            return []
        except Exception as exc:  # pragma: no cover - 查询异常时仅记录
            if "no such function: vector_distance_cosine" in str(exc).lower():
                # 更新缓存状态，后续查询直接使用Python计算
                self._vector_func_available = False
                logger.warning("向量库缺少 vector_distance_cosine 函数，回退至应用层相似度计算。")
                return await python_fallback()
            logger.warning("%s失败: %s", failure_title, exc)
            return []

        items: List[T] = []
        for row in self._iter_rows(result):
            items.append(row_mapper(row))
        return items

    async def query_chunks(
        self,
        *,
        project_id: str,
        embedding: Sequence[float],
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        """
        根据查询向量检索剧情片段，结果已按相似度排序。

        P2修复: 增加超时和重试机制，提高检索稳定性。
        """
        if not self._client or not embedding:
            return []

        await self.ensure_schema()
        top_k = top_k or settings.vector_top_k_chunks
        if top_k <= 0:
            return []

        blob = self._to_f32_blob(embedding)
        sql = """
        SELECT
            content,
            chapter_number,
            chapter_title,
            COALESCE(metadata, '{}') AS metadata,
            vector_distance_cosine(embedding, :query) AS distance
        FROM rag_chunks
        WHERE project_id = :project_id
        ORDER BY distance ASC
        LIMIT :limit
        """

        async def _fallback():
            return await self._query_chunks_with_python_similarity(
                project_id=project_id,
                embedding=embedding,
                top_k=top_k,
            )

        def _row_mapper(row: Dict[str, Any]) -> RetrievedChunk:
            return RetrievedChunk(
                content=row.get("content", ""),
                chapter_number=row.get("chapter_number", 0),
                chapter_title=row.get("chapter_title"),
                score=row.get("distance", 0.0),
                metadata=self._parse_metadata(row.get("metadata")),
            )

        return await self._query_with_vector_distance(
            operation_name="RAG检索剧情片段",
            failure_title="向量检索剧情片段",
            sql=sql,
            params={
                "project_id": project_id,
                "query": blob,
                "limit": top_k,
            },
            top_k=top_k,
            row_mapper=_row_mapper,
            python_fallback=_fallback,
        )

    async def query_summaries(
        self,
        *,
        project_id: str,
        embedding: Sequence[float],
        top_k: Optional[int] = None,
    ) -> List[RetrievedSummary]:
        """
        根据查询向量检索章节摘要列表。

        P2修复: 增加超时和重试机制，提高检索稳定性。
        """
        if not self._client or not embedding:
            return []

        await self.ensure_schema()
        top_k = top_k or settings.vector_top_k_summaries
        if top_k <= 0:
            return []

        blob = self._to_f32_blob(embedding)
        sql = """
        SELECT
            chapter_number,
            title,
            summary,
            vector_distance_cosine(embedding, :query) AS distance
        FROM rag_summaries
        WHERE project_id = :project_id
        ORDER BY distance ASC
        LIMIT :limit
        """

        async def _fallback():
            return await self._query_summaries_with_python_similarity(
                project_id=project_id,
                embedding=embedding,
                top_k=top_k,
            )

        def _row_mapper(row: Dict[str, Any]) -> RetrievedSummary:
            return RetrievedSummary(
                chapter_number=row.get("chapter_number", 0),
                title=row.get("title", ""),
                summary=row.get("summary", ""),
                score=row.get("distance", 0.0),
            )

        return await self._query_with_vector_distance(
            operation_name="RAG检索章节摘要",
            failure_title="向量检索章节摘要",
            sql=sql,
            params={
                "project_id": project_id,
                "query": blob,
                "limit": top_k,
            },
            top_k=top_k,
            row_mapper=_row_mapper,
            python_fallback=_fallback,
        )

    async def _bulk_upsert(
        self,
        *,
        sql: str,
        payload: List[Dict[str, Any]],
        success_log: str,
        error_log: str,
        item_error_logger: Callable[[Dict[str, Any], Exception], None],
    ) -> None:
        """批量写入模板：优先 batch/事务，失败回退逐条写入。"""
        if not self._client or not payload:
            return

        # 性能优化：使用批量事务写入
        # libsql支持batch()方法，将多个SQL语句合并为单个网络请求
        try:
            # 构建批量执行的语句列表
            batch_statements = [(sql, item) for item in payload]

            # 检查是否支持batch方法
            if hasattr(self._client, "batch"):
                # 使用batch一次性执行所有INSERT
                await self._client.batch(batch_statements)  # type: ignore[union-attr]
                logger.info(
                    "%s（batch模式）: 总计=%d",
                    success_log,
                    len(payload),
                )
                return

            # 回退：使用事务包装的逐条执行
            await self._client.execute("BEGIN TRANSACTION")  # type: ignore[union-attr]
            try:
                for item in payload:
                    await self._client.execute(sql, item)  # type: ignore[union-attr]
                await self._client.execute("COMMIT")  # type: ignore[union-attr]
                logger.info(
                    "%s（事务模式）: 总计=%d",
                    success_log,
                    len(payload),
                )
                return
            except Exception as txn_exc:
                await self._client.execute("ROLLBACK")  # type: ignore[union-attr]
                raise txn_exc

        except Exception as exc:
            logger.error(
                "%s: %s (尝试写入 %d 条)",
                error_log,
                exc,
                len(payload),
            )
            # 回退到逐条写入模式，确保部分数据能够保存
            success_count = 0
            failed_count = 0
            for item in payload:
                try:
                    await self._client.execute(sql, item)  # type: ignore[union-attr]
                    success_count += 1
                except Exception as item_exc:
                    failed_count += 1
                    item_error_logger(item, item_exc)

            if success_count > 0:
                logger.info(
                    "回退逐条写入完成: 成功=%d 失败=%d 总计=%d",
                    success_count,
                    failed_count,
                    len(payload),
                )

    async def upsert_chunks(
        self,
        *,
        records: Iterable[Dict[str, Any]],
    ) -> None:
        """批量写入章节片段，供后续检索使用。

        性能优化：使用批量事务写入，减少网络往返次数。
        - 将多条INSERT合并为单个事务
        - 使用executemany批量执行（如果支持）
        - 失败时记录详细日志便于排查
        """
        if not self._client:
            return

        await self.ensure_schema()
        sql = """
        INSERT INTO rag_chunks (
            id,
            project_id,
            chapter_number,
            chunk_index,
            chapter_title,
            content,
            embedding,
            metadata
        ) VALUES (
            :id,
            :project_id,
            :chapter_number,
            :chunk_index,
            :chapter_title,
            :content,
            :embedding,
            :metadata
        )
        ON CONFLICT(id) DO UPDATE SET
            project_id=excluded.project_id,
            content=excluded.content,
            embedding=excluded.embedding,
            metadata=excluded.metadata,
            chapter_title=excluded.chapter_title
        """
        payload = []
        for item in records:
            embedding = item.get("embedding", [])
            payload.append(
                {
                    **item,
                    "embedding": self._to_f32_blob(embedding),
                    "metadata": json.dumps(item.get("metadata") or {}, ensure_ascii=False),
                }
            )

        if not payload:
            return

        def _item_error_logger(item: Dict[str, Any], item_exc: Exception) -> None:
            logger.warning(
                "写入单条 rag_chunk 失败: project=%s chapter=%s chunk=%s error=%s",
                item.get("project_id"),
                item.get("chapter_number"),
                item.get("chunk_index"),
                item_exc,
            )

        await self._bulk_upsert(
            sql=sql,
            payload=payload,
            success_log="批量写入章节片段完成",
            error_log="批量写入 rag_chunks 失败",
            item_error_logger=_item_error_logger,
        )

    async def upsert_summaries(
        self,
        *,
        records: Iterable[Dict[str, Any]],
    ) -> None:
        """同步章节摘要向量，供摘要层检索使用。

        性能优化：使用批量事务写入，减少网络往返次数。
        - 将多条INSERT合并为单个事务
        - 使用executemany批量执行（如果支持）
        - 失败时记录详细日志便于排查
        """
        if not self._client:
            return

        await self.ensure_schema()
        sql = """
        INSERT INTO rag_summaries (
            id,
            project_id,
            chapter_number,
            title,
            summary,
            embedding
        ) VALUES (
            :id,
            :project_id,
            :chapter_number,
            :title,
            :summary,
            :embedding
        )
        ON CONFLICT(id) DO UPDATE SET
            summary=excluded.summary,
            embedding=excluded.embedding,
            title=excluded.title
        """

        payload = []
        for item in records:
            embedding = item.get("embedding", [])
            payload.append(
                {
                    **item,
                    "embedding": self._to_f32_blob(embedding),
                }
            )

        if not payload:
            return

        def _item_error_logger(item: Dict[str, Any], item_exc: Exception) -> None:
            logger.warning(
                "写入单条 rag_summary 失败: project=%s chapter=%s error=%s",
                item.get("project_id"),
                item.get("chapter_number"),
                item_exc,
            )

        await self._bulk_upsert(
            sql=sql,
            payload=payload,
            success_log="批量写入章节摘要完成",
            error_log="批量写入 rag_summaries 失败",
            item_error_logger=_item_error_logger,
        )

    async def delete_by_chapters(self, project_id: str, chapter_numbers: Sequence[int]) -> None:
        """根据章节编号批量删除对应的上下文数据。"""
        if not self._client or not chapter_numbers:
            return

        await self.ensure_schema()
        placeholders = ",".join(":chapter_" + str(idx) for idx in range(len(chapter_numbers)))
        params = {
            "project_id": project_id,
            **{f"chapter_{idx}": number for idx, number in enumerate(chapter_numbers)},
        }
        chunk_sql = f"""
        DELETE FROM rag_chunks
        WHERE project_id = :project_id
          AND chapter_number IN ({placeholders})
        """
        summary_sql = f"""
        DELETE FROM rag_summaries
        WHERE project_id = :project_id
          AND chapter_number IN ({placeholders})
        """
        try:
            await self._client.execute(chunk_sql, params)  # type: ignore[union-attr]
            await self._client.execute(summary_sql, params)  # type: ignore[union-attr]
            logger.info(
                "已删除章节向量: project=%s chapters=%s",
                project_id,
                list(chapter_numbers),
            )
        except Exception as exc:  # pragma: no cover - 删除失败时记录日志
            logger.error("删除章节向量失败: project=%s chapters=%s error=%s", project_id, chapter_numbers, exc)

    async def delete_by_project(self, project_id: str) -> int:
        """
        删除项目的所有RAG数据

        Args:
            project_id: 项目ID

        Returns:
            删除的记录数
        """
        if not self._client:
            logger.warning("delete_by_project: 向量库客户端未初始化")
            return 0

        await self.ensure_schema()

        try:
            # 先统计现有记录数
            count_sql = "SELECT COUNT(*) as cnt FROM rag_chunks WHERE project_id = :project_id"
            count_result = await self._client.execute(count_sql, {"project_id": project_id})
            before_count = 0
            for row in self._iter_rows(count_result):
                before_count = row.get("cnt", 0)
                break

            logger.info(
                "delete_by_project: 开始删除 project=%s 删除前chunks数量=%d",
                project_id, before_count
            )

            # 删除 chunks
            chunk_sql = "DELETE FROM rag_chunks WHERE project_id = :project_id"
            await self._client.execute(chunk_sql, {"project_id": project_id})

            # 删除 summaries
            summary_sql = "DELETE FROM rag_summaries WHERE project_id = :project_id"
            await self._client.execute(summary_sql, {"project_id": project_id})

            # 验证删除结果
            verify_result = await self._client.execute(count_sql, {"project_id": project_id})
            after_count = 0
            for row in self._iter_rows(verify_result):
                after_count = row.get("cnt", 0)
                break

            deleted_count = before_count - after_count

            logger.info(
                "delete_by_project: 删除完成 project=%s 删除前=%d 删除后=%d 实际删除=%d",
                project_id, before_count, after_count, deleted_count
            )

            if after_count > 0:
                logger.warning(
                    "delete_by_project: 删除不完整! 仍有 %d 条记录未删除",
                    after_count
                )

            return deleted_count
        except Exception as exc:
            logger.error("删除项目RAG数据失败: project=%s error=%s", project_id, exc)
            return 0

    async def delete_legacy_chunks(self, project_id: str) -> int:
        """
        删除项目中没有data_type字段的旧数据

        这些是在添加data_type字段之前入库的数据，
        可能导致来源显示错误（如显示"F1"而不是正确的类型）。

        Args:
            project_id: 项目ID

        Returns:
            删除的记录数
        """
        if not self._client:
            return 0

        await self.ensure_schema()

        try:
            # 删除没有data_type字段的chunks
            # json_extract返回NULL表示字段不存在
            sql = """
            DELETE FROM rag_chunks
            WHERE project_id = :project_id
            AND (
                json_extract(metadata, '$.data_type') IS NULL
                OR json_extract(metadata, '$.data_type') = ''
            )
            """
            result = await self._client.execute(sql, {"project_id": project_id})
            deleted_count = 0
            if hasattr(result, 'rowcount'):
                deleted_count = result.rowcount

            if deleted_count > 0:
                logger.info(
                    "已删除项目旧版RAG数据（无data_type字段）: project=%s deleted=%d",
                    project_id, deleted_count
                )
            return deleted_count
        except Exception as exc:
            logger.warning(
                "删除旧版RAG数据失败: project=%s error=%s",
                project_id, exc
            )
            return 0

    async def get_chapter_chunks_metadata(
        self,
        project_id: str,
        chapter_number: int,
    ) -> List[Dict[str, Any]]:
        """
        获取章节所有chunk的元数据（用于增量更新检测）

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            chunk元数据列表，每个元素包含id、content、metadata等字段
        """
        if not self._client:
            return []

        await self.ensure_schema()
        sql = """
        SELECT id, content, COALESCE(metadata, '{}') AS metadata
        FROM rag_chunks
        WHERE project_id = :project_id AND chapter_number = :chapter_number
        """
        try:
            result = await self._client.execute(  # type: ignore[union-attr]
                sql,
                {"project_id": project_id, "chapter_number": chapter_number},
            )
            chunks = []
            for row in self._iter_rows(result):
                chunks.append({
                    "id": row.get("id", ""),
                    "content": row.get("content", ""),
                    "metadata": self._parse_metadata(row.get("metadata")),
                })
            return chunks
        except Exception as exc:
            logger.warning(
                "获取章节chunk元数据失败: project=%s chapter=%s error=%s",
                project_id, chapter_number, exc
            )
            return []

    async def delete_chunks_by_ids(self, chunk_ids: Sequence[str]) -> None:
        """
        按ID删除指定的chunk（用于增量更新时删除过时内容）

        Args:
            chunk_ids: 要删除的chunk ID列表
        """
        if not self._client or not chunk_ids:
            return

        await self.ensure_schema()

        # 构建批量删除的SQL
        placeholders = ",".join(f":id_{idx}" for idx in range(len(chunk_ids)))
        params = {f"id_{idx}": cid for idx, cid in enumerate(chunk_ids)}
        sql = f"DELETE FROM rag_chunks WHERE id IN ({placeholders})"

        try:
            await self._client.execute(sql, params)  # type: ignore[union-attr]
            logger.info("已删除 %d 个过时的chunk", len(chunk_ids))
        except Exception as exc:
            logger.warning("按ID删除chunk失败: count=%d error=%s", len(chunk_ids), exc)

    async def get_chunks_hashes_by_type(
        self,
        project_id: str,
        data_type: str,
    ) -> Dict[str, str]:
        """
        获取指定项目和类型的所有chunk的内容哈希

        用于变动检测：对比数据库中记录的哈希和向量库中存储的哈希。

        Args:
            project_id: 项目ID
            data_type: 数据类型（如 "architecture", "module" 等）

        Returns:
            字典 {chunk_id: paragraph_hash}，用于快速查找和比对
        """
        if not self._client:
            logger.debug("get_chunks_hashes_by_type: 向量库客户端未初始化")
            return {}

        await self.ensure_schema()

        sql = """
        SELECT id, json_extract(metadata, '$.paragraph_hash') AS paragraph_hash
        FROM rag_chunks
        WHERE project_id = :project_id
        AND json_extract(metadata, '$.data_type') = :data_type
        """

        try:
            result = await self._client.execute(
                sql,
                {"project_id": project_id, "data_type": data_type}
            )
            hashes = {}
            null_hash_count = 0
            for row in self._iter_rows(result):
                chunk_id = row.get("id", "")
                paragraph_hash = row.get("paragraph_hash", "")
                if chunk_id and paragraph_hash:
                    hashes[chunk_id] = paragraph_hash
                elif chunk_id:
                    # 记录有ID但没有paragraph_hash的情况
                    null_hash_count += 1

            # 调试日志
            if null_hash_count > 0:
                logger.warning(
                    "get_chunks_hashes_by_type: 发现 %d 条记录缺少paragraph_hash "
                    "(project=%s type=%s)",
                    null_hash_count, project_id, data_type
                )

            logger.info(
                "get_chunks_hashes_by_type: project=%s type=%s 返回 %d 条哈希",
                project_id, data_type, len(hashes)
            )
            return hashes
        except Exception as exc:
            logger.warning(
                "获取chunk哈希失败: project=%s type=%s error=%s",
                project_id, data_type, exc
            )
            return {}

    @staticmethod
    def _to_f32_blob(embedding: Sequence[float]) -> bytes:
        """将向量浮点列表编码为 libsql 可识别的 float32 二进制。"""
        return array("f", embedding).tobytes()

    @staticmethod
    def _from_f32_blob(blob: Any) -> List[float]:
        """将数据库中的 BLOB 解码为浮点列表。"""
        if not blob:
            return []
        if isinstance(blob, memoryview):
            blob = blob.tobytes()
        data = array("f")
        data.frombytes(bytes(blob))
        return list(data)

    @staticmethod
    def _cosine_distance(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
        """计算余弦距离（1 - similarity），避免除零。"""
        if not vec_a or not vec_b:
            return 1.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 1.0
        similarity = dot / (norm_a * norm_b)
        return 1.0 - similarity

    @staticmethod
    def _cosine_distance_batch_numpy(
        query_vec: Sequence[float],
        stored_vecs: List[List[float]],
    ) -> List[float]:
        """
        使用numpy批量计算余弦距离（性能优化版）

        相比逐个计算，批量处理可以利用numpy的向量化运算，
        显著提高大量向量的相似度计算效率。

        Args:
            query_vec: 查询向量
            stored_vecs: 存储的向量列表

        Returns:
            余弦距离列表（1 - similarity），与stored_vecs顺序对应
        """
        if not NUMPY_AVAILABLE or not query_vec or not stored_vecs:
            # 回退到逐个计算
            return [
                VectorStoreService._cosine_distance(query_vec, vec)
                for vec in stored_vecs
            ]

        # 转换为numpy数组
        query = np.array(query_vec, dtype=np.float32)
        stored = np.array(stored_vecs, dtype=np.float32)

        # 计算L2范数
        query_norm = np.linalg.norm(query)
        stored_norms = np.linalg.norm(stored, axis=1)

        # 避免除零
        if query_norm == 0:
            return [1.0] * len(stored_vecs)

        # 将零范数替换为1以避免除零（这些向量的距离会是1.0）
        zero_mask = stored_norms == 0
        stored_norms[zero_mask] = 1.0

        # 归一化
        query_normalized = query / query_norm
        stored_normalized = stored / stored_norms[:, np.newaxis]

        # 批量点积计算相似度
        similarities = np.dot(stored_normalized, query_normalized)

        # 转换为距离并处理零范数情况
        distances = 1.0 - similarities
        distances[zero_mask] = 1.0

        return distances.tolist()

    async def _query_with_python_similarity(
        self,
        *,
        project_id: str,
        embedding: Sequence[float],
        top_k: int,
        sql: str,
        row_mapper: Callable[[Dict[str, Any], float], T],
    ) -> List[T]:
        """
        通用的Python回退相似度查询（numpy批量优化版）

        当向量数据库不支持原生向量函数时，使用Python/numpy计算余弦距离。
        优化：批量提取所有向量后使用numpy一次性计算，比逐个计算快10-100倍。

        Args:
            project_id: 项目ID
            embedding: 查询向量
            top_k: 返回数量
            sql: 查询SQL（必须包含embedding列）
            row_mapper: 行数据转换函数，接收(row_dict, distance)返回结果对象

        Returns:
            按相似度排序的结果列表
        """
        result = await self._client.execute(sql, {"project_id": project_id})  # type: ignore[union-attr]

        # 收集所有行和向量
        rows_list: List[Dict[str, Any]] = []
        embeddings_list: List[List[float]] = []

        for row in self._iter_rows(result):
            stored_embedding = self._from_f32_blob(row.get("embedding"))
            if stored_embedding:  # 只处理有效向量
                rows_list.append(row)
                embeddings_list.append(stored_embedding)

        if not rows_list:
            return []

        # 使用numpy批量计算所有距离
        distances = self._cosine_distance_batch_numpy(embedding, embeddings_list)

        # 创建结果对象
        scored: List[T] = [
            row_mapper(row, distance)
            for row, distance in zip(rows_list, distances)
        ]

        # 按距离排序并返回top_k
        scored.sort(key=lambda item: item.score)
        return scored[:top_k]

    async def _query_chunks_with_python_similarity(
        self,
        *,
        project_id: str,
        embedding: Sequence[float],
        top_k: int,
    ) -> List[RetrievedChunk]:
        """使用Python计算相似度查询章节片段（回退模式）"""
        sql = """
        SELECT
            content,
            chapter_number,
            chapter_title,
            COALESCE(metadata, '{}') AS metadata,
            embedding
        FROM rag_chunks
        WHERE project_id = :project_id
        """

        def mapper(row: Dict[str, Any], distance: float) -> RetrievedChunk:
            return RetrievedChunk(
                content=row.get("content", ""),
                chapter_number=row.get("chapter_number", 0),
                chapter_title=row.get("chapter_title"),
                score=distance,
                metadata=self._parse_metadata(row.get("metadata")),
            )

        return await self._query_with_python_similarity(
            project_id=project_id,
            embedding=embedding,
            top_k=top_k,
            sql=sql,
            row_mapper=mapper,
        )

    async def _query_summaries_with_python_similarity(
        self,
        *,
        project_id: str,
        embedding: Sequence[float],
        top_k: int,
    ) -> List[RetrievedSummary]:
        """使用Python计算相似度查询章节摘要（回退模式）"""
        sql = """
        SELECT
            chapter_number,
            title,
            summary,
            embedding
        FROM rag_summaries
        WHERE project_id = :project_id
        """

        def mapper(row: Dict[str, Any], distance: float) -> RetrievedSummary:
            return RetrievedSummary(
                chapter_number=row.get("chapter_number", 0),
                title=row.get("title", ""),
                summary=row.get("summary", ""),
                score=distance,
            )

        return await self._query_with_python_similarity(
            project_id=project_id,
            embedding=embedding,
            top_k=top_k,
            sql=sql,
            row_mapper=mapper,
        )

    @staticmethod
    def _parse_metadata(raw: Any) -> Dict[str, Any]:
        """解析存储的 JSON 文本，确保输出为 dict。"""
        if not raw:
            return {}
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _iter_rows(result: Any) -> Iterable[Dict[str, Any]]:
        """统一处理 libsql 返回的行数据，确保以 dict 形式迭代。"""
        rows = getattr(result, "rows", None)
        if rows is None:
            rows = result
        if not rows:
            return []
        normalized: List[Dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                normalized.append(row)
            elif hasattr(row, "_asdict"):
                normalized.append(row._asdict())  # type: ignore[attr-defined]
            else:
                try:
                    normalized.append(dict(row))
                except Exception:  # pragma: no cover - 无法转换时跳过
                    continue
        return normalized


__all__ = [
    "VectorStoreService",
    "RetrievedChunk",
    "RetrievedSummary",
]
