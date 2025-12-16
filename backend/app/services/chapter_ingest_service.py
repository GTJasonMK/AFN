from __future__ import annotations

"""
章节向量入库服务：在章节确认后负责切分文本、生成嵌入并写入向量库。

设计原则：
1. 段落级索引 - 每个段落独立一个向量，增量更新100%精确
2. 并行embedding - 分批并行处理，提速5-10倍
3. 简单可靠 - 通过段落哈希精确追踪增删改

全部注释使用中文，方便团队成员阅读理解。
"""

import asyncio
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core.config import settings
from ..services.llm_service import LLMService
from ..services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)


class ParagraphSplitter:
    """
    段落分割器：按双换行分割成自然段落

    设计原则：
    - 每个段落独立存储，不做合并
    - 段落是小说的自然语义单位，适合作为检索单元
    - 增量更新时，修改只影响对应段落，不会级联
    """

    # 最小段落长度，过短的段落与下一段合并（如单独的省略号行）
    MIN_PARAGRAPH_LENGTH = 20

    def split(self, text: str) -> List[Tuple[str, str]]:
        """
        将文本分割为段落列表

        Args:
            text: 输入文本

        Returns:
            列表，每个元素是 (paragraph_content, paragraph_hash)
        """
        text = text.strip()
        if not text:
            return []

        # 统一换行符并按双换行分割
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        raw_paragraphs = re.split(r'\n{2,}', text)

        # 过滤空段落
        paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
        if not paragraphs:
            return []

        # 处理过短段落：与下一段合并
        merged_paragraphs: List[str] = []
        buffer = ""

        for para in paragraphs:
            if buffer:
                # 有待合并的内容，拼接
                buffer = buffer + "\n\n" + para
                if len(buffer) >= self.MIN_PARAGRAPH_LENGTH:
                    merged_paragraphs.append(buffer)
                    buffer = ""
            elif len(para) < self.MIN_PARAGRAPH_LENGTH:
                # 当前段落太短，暂存
                buffer = para
            else:
                merged_paragraphs.append(para)

        # 处理剩余buffer
        if buffer:
            if merged_paragraphs:
                # 合并到最后一段
                merged_paragraphs[-1] = merged_paragraphs[-1] + "\n\n" + buffer
            else:
                merged_paragraphs.append(buffer)

        # 计算每个段落的哈希
        result: List[Tuple[str, str]] = []
        for para in merged_paragraphs:
            para_hash = hashlib.md5(para.encode('utf-8')).hexdigest()
            result.append((para, para_hash))

        return result


class ChapterIngestionService:
    """
    章节向量入库服务

    核心设计：段落级索引
    - 每个段落独立存储一个向量
    - 增量更新时精确比较段落哈希
    - 只处理真正变化的段落（新增/修改/删除）
    """

    # 并行处理配置
    EMBEDDING_BATCH_SIZE = 5  # 每批并行处理的段落数量
    EMBEDDING_BATCH_DELAY = 0.1  # 批次间延迟（秒），避免API限流

    def __init__(
        self,
        *,
        llm_service: LLMService,
        vector_store: Optional[VectorStoreService] = None,
    ) -> None:
        self._llm_service = llm_service
        self._splitter = ParagraphSplitter()

        # 防御性处理：如果未传入vector_store且初始化失败，设置为None
        if vector_store is None:
            try:
                self._vector_store = VectorStoreService()
            except RuntimeError as exc:
                logger.warning("向量库初始化失败，RAG功能将被禁用: %s", exc)
                self._vector_store = None
        else:
            self._vector_store = vector_store

    async def ingest_chapter(
        self,
        *,
        project_id: str,
        chapter_number: int,
        title: str,
        content: str,
        summary: Optional[str],
        user_id: int,
    ) -> Dict[str, Any]:
        """
        将章节正文与摘要写入向量库，供后续RAG检索使用。

        增量更新策略：
        1. 分割内容为段落，计算每个段落的哈希
        2. 与向量库中现有段落哈希比较
        3. 只处理：新增的段落、修改的段落（哈希变化）
        4. 删除：不再存在的段落

        Returns:
            包含入库统计信息的字典
        """
        result = {
            "success": False,
            "total_paragraphs": 0,
            "added": 0,
            "deleted": 0,
            "unchanged": 0,
            "failed": 0,
            "summary_success": False,
            "message": "",
        }

        if not settings.vector_store_enabled or self._vector_store is None:
            result["message"] = "向量库未启用或初始化失败，跳过章节向量写入"
            logger.debug("%s: project=%s chapter=%s", result["message"], project_id, chapter_number)
            return result

        if not content.strip():
            result["message"] = "章节正文为空，跳过向量写入"
            logger.debug("%s: project=%s chapter=%s", result["message"], project_id, chapter_number)
            return result

        # 分割为段落
        paragraphs = self._splitter.split(content)
        if not paragraphs:
            result["message"] = "章节正文分割后为空，跳过向量写入"
            return result

        result["total_paragraphs"] = len(paragraphs)

        # 构建新段落的哈希映射: hash -> (index, content)
        new_para_map: Dict[str, Tuple[int, str]] = {}
        for idx, (para_content, para_hash) in enumerate(paragraphs):
            new_para_map[para_hash] = (idx, para_content)

        # 获取现有段落哈希
        existing_hashes = await self._get_existing_paragraph_hashes(project_id, chapter_number)

        # 计算差异
        new_hashes = set(new_para_map.keys())
        hashes_to_add = new_hashes - existing_hashes      # 新增或修改的段落
        hashes_to_delete = existing_hashes - new_hashes  # 需要删除的段落
        hashes_unchanged = new_hashes & existing_hashes  # 未变化的段落

        result["unchanged"] = len(hashes_unchanged)

        logger.info(
            "章节向量增量分析: project=%s chapter=%s "
            "总段落=%d 新增=%d 删除=%d 未变化=%d",
            project_id, chapter_number,
            len(paragraphs),
            len(hashes_to_add), len(hashes_to_delete), len(hashes_unchanged),
        )

        # 如果没有变化，跳过处理
        if not hashes_to_add and not hashes_to_delete:
            result["success"] = True
            result["message"] = f"内容无变化，跳过向量更新（{len(paragraphs)} 个段落）"
            logger.info("%s: project=%s chapter=%s", result["message"], project_id, chapter_number)
            # 仍然处理摘要
            await self._process_summary(project_id, chapter_number, title, summary, user_id, result)
            return result

        # 删除不再存在的段落
        if hashes_to_delete:
            chunk_ids = [
                f"{project_id}:{chapter_number}:p:{h[:12]}"
                for h in hashes_to_delete
            ]
            await self._vector_store.delete_chunks_by_ids(chunk_ids)
            result["deleted"] = len(hashes_to_delete)
            logger.info(
                "已删除过时段落: project=%s chapter=%s count=%d",
                project_id, chapter_number, len(hashes_to_delete)
            )

        # 并行处理需要新增的段落
        if hashes_to_add:
            paragraphs_to_process = [
                (new_para_map[h][0], new_para_map[h][1], h)
                for h in hashes_to_add
            ]

            records, failed_count = await self._process_paragraphs_parallel(
                paragraphs_to_process=paragraphs_to_process,
                project_id=project_id,
                chapter_number=chapter_number,
                title=title,
                user_id=user_id,
            )

            result["added"] = len(records)
            result["failed"] = failed_count

            if records:
                await self._vector_store.upsert_chunks(records=records)
                logger.info(
                    "章节正文向量写入完成: project=%s chapter=%s 新增=%d 失败=%d 跳过=%d",
                    project_id, chapter_number,
                    len(records), failed_count, len(hashes_unchanged),
                )

        # 处理摘要
        await self._process_summary(project_id, chapter_number, title, summary, user_id, result)

        # 生成结果消息
        result["success"] = (result["added"] > 0 or result["unchanged"] > 0)
        parts = []
        if result["added"] > 0:
            parts.append(f"新增 {result['added']} 个")
        if result["deleted"] > 0:
            parts.append(f"删除 {result['deleted']} 个")
        if result["unchanged"] > 0:
            parts.append(f"跳过 {result['unchanged']} 个未变化")
        if result["failed"] > 0:
            parts.append(f"失败 {result['failed']} 个")
        result["message"] = f"向量入库完成：{', '.join(parts)}" if parts else "向量入库完成"

        return result

    async def _get_existing_paragraph_hashes(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Set[str]:
        """获取现有段落的哈希集合"""
        if not self._vector_store:
            return set()

        try:
            existing_chunks = await self._vector_store.get_chapter_chunks_metadata(
                project_id, chapter_number
            )
            hashes = set()
            for chunk in existing_chunks:
                metadata = chunk.get("metadata", {})
                # 新格式：paragraph_hash字段
                para_hash = metadata.get("paragraph_hash")
                if para_hash:
                    hashes.add(para_hash)
                else:
                    # 兼容旧格式：从content_hash提取
                    content_hash = metadata.get("content_hash")
                    if content_hash:
                        hashes.add(content_hash)
            return hashes
        except Exception as e:
            logger.warning(
                "获取现有段落哈希失败，将执行全量更新: project=%s chapter=%s error=%s",
                project_id, chapter_number, e
            )
            return set()

    async def _process_paragraphs_parallel(
        self,
        paragraphs_to_process: List[Tuple[int, str, str]],  # (index, content, hash)
        project_id: str,
        chapter_number: int,
        title: str,
        user_id: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        并行处理段落的embedding生成

        Returns:
            (成功的记录列表, 失败数量)
        """
        records = []
        failed_count = 0
        total = len(paragraphs_to_process)

        # 分批并行处理
        for batch_start in range(0, total, self.EMBEDDING_BATCH_SIZE):
            batch = paragraphs_to_process[batch_start:batch_start + self.EMBEDDING_BATCH_SIZE]

            # 并行调用embedding
            tasks = [
                self._llm_service.get_embedding(content, user_id=user_id)
                for _, content, _ in batch
            ]
            embeddings = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for i, embedding in enumerate(embeddings):
                idx, content, para_hash = batch[i]

                if isinstance(embedding, Exception):
                    logger.warning(
                        "生成embedding异常: project=%s chapter=%s para=%d error=%s",
                        project_id, chapter_number, idx, embedding
                    )
                    failed_count += 1
                    continue

                if not embedding:
                    failed_count += 1
                    continue

                # 使用段落哈希作为ID的一部分，保证唯一性
                record_id = f"{project_id}:{chapter_number}:p:{para_hash[:12]}"
                records.append({
                    "id": record_id,
                    "project_id": project_id,
                    "chapter_number": chapter_number,
                    "chunk_index": idx,
                    "chapter_title": title,
                    "content": content,
                    "embedding": embedding,
                    "metadata": {
                        "chunk_id": record_id,
                        "paragraph_hash": para_hash,
                        "length": len(content),
                    },
                })

            # 批次间延迟，避免API限流
            if batch_start + self.EMBEDDING_BATCH_SIZE < total:
                await asyncio.sleep(self.EMBEDDING_BATCH_DELAY)

        return records, failed_count

    async def _process_summary(
        self,
        project_id: str,
        chapter_number: int,
        title: str,
        summary: Optional[str],
        user_id: int,
        result: Dict[str, Any],
    ) -> None:
        """处理章节摘要的向量入库"""
        if not summary:
            return

        cleaned_summary = summary.strip()
        if not cleaned_summary:
            return

        try:
            summary_embedding = await self._llm_service.get_embedding(
                cleaned_summary,
                user_id=user_id,
            )
            if summary_embedding:
                summary_id = f"{project_id}:{chapter_number}:summary"
                await self._vector_store.upsert_summaries(
                    records=[{
                        "id": summary_id,
                        "project_id": project_id,
                        "chapter_number": chapter_number,
                        "title": title,
                        "summary": cleaned_summary,
                        "embedding": summary_embedding,
                    }]
                )
                result["summary_success"] = True
                logger.info(
                    "章节摘要向量写入完成: project=%s chapter=%s",
                    project_id, chapter_number,
                )
        except Exception as e:
            logger.warning("摘要向量生成失败: %s", e)

    async def delete_chapters(self, project_id: str, chapter_numbers: List[int]) -> None:
        """从向量库中删除指定章节的所有段落与摘要。"""
        if not settings.vector_store_enabled or self._vector_store is None or not chapter_numbers:
            return
        logger.info(
            "准备删除章节向量: project=%s chapters=%s",
            project_id,
            list(chapter_numbers),
        )
        await self._vector_store.delete_by_chapters(project_id, list(chapter_numbers))


__all__ = ["ChapterIngestionService", "ParagraphSplitter"]
