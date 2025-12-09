"""
时序感知检索器

在向量相似度的基础上引入时序权重，优先返回与当前章节时间上接近的内容，
确保生成的章节与近期情节保持连贯。
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from ..vector_store_service import RetrievedChunk, RetrievedSummary, VectorStoreService


@dataclass
class TemporalScoredChunk:
    """带时序得分的检索片段"""
    chunk: RetrievedChunk
    temporal_score: float
    final_score: float


@dataclass
class TemporalScoredSummary:
    """带时序得分的检索摘要"""
    summary: RetrievedSummary
    temporal_score: float
    final_score: float


class TemporalAwareRetriever:
    """时序感知检索器

    在向量相似度检索的基础上，引入时序权重机制：
    1. 综合得分 = 相似度得分 * 相似度权重 + 时序得分 * 时序权重
    2. 时序得分使用指数衰减，距离当前章节越近得分越高
    3. 支持临近章节额外加分

    核心思想：
    - 对于第N章的生成，第N-1章的内容应该比第1章的内容更重要
    - 但如果第1章的内容与当前章节高度相关（语义相似），也不应该完全忽略
    """

    def __init__(
        self,
        vector_store: VectorStoreService,
        recency_weight: float = 0.3,
        similarity_weight: float = 0.7,
        nearby_bonus: float = 0.15,
        nearby_range: int = 5,
        decay_factor: float = 3.0,
    ):
        """
        Args:
            vector_store: 向量存储服务
            recency_weight: 时序权重（0-1），默认0.3
            similarity_weight: 相似度权重（0-1），默认0.7
            nearby_bonus: 临近章节额外加分，默认0.15
            nearby_range: 临近章节范围，默认5章
            decay_factor: 时序衰减因子，越大衰减越快，默认3.0
        """
        self.vector_store = vector_store
        self.recency_weight = recency_weight
        self.similarity_weight = similarity_weight
        self.nearby_bonus = nearby_bonus
        self.nearby_range = nearby_range
        self.decay_factor = decay_factor

        # 确保权重和为1
        total_weight = self.recency_weight + self.similarity_weight
        if abs(total_weight - 1.0) > 0.01:
            # 归一化权重
            self.recency_weight = self.recency_weight / total_weight
            self.similarity_weight = self.similarity_weight / total_weight

    def compute_temporal_score(
        self,
        source_chapter: int,
        target_chapter: int,
        total_chapters: int,
    ) -> float:
        """计算时序得分

        使用指数衰减函数：score = exp(-decay_factor * normalized_distance)
        - 相邻章节得分接近1
        - 距离越远得分越低

        Args:
            source_chapter: 检索到的内容所在章节
            target_chapter: 当前要生成的章节
            total_chapters: 小说总章节数（用于归一化）

        Returns:
            时序得分（0-1）
        """
        if total_chapters <= 1:
            return 1.0

        # 只考虑之前的章节（不应检索到未来章节）
        if source_chapter >= target_chapter:
            return 0.0

        # 计算章节距离并归一化
        distance = target_chapter - source_chapter
        max_distance = max(target_chapter - 1, 1)
        normalized_distance = distance / max_distance

        # 指数衰减
        temporal_score = math.exp(-self.decay_factor * normalized_distance)

        return temporal_score

    def compute_final_score(
        self,
        similarity_score: float,
        source_chapter: int,
        target_chapter: int,
        total_chapters: int,
    ) -> Tuple[float, float]:
        """计算综合得分

        综合得分 = 相似度得分 * 相似度权重 + 时序得分 * 时序权重

        注意：向量检索返回的score是距离（越小越好），需要转换为相似度

        Args:
            similarity_score: 向量检索返回的距离分数（越小越相似）
            source_chapter: 检索到的内容所在章节
            target_chapter: 当前要生成的章节
            total_chapters: 小说总章节数

        Returns:
            (temporal_score, final_score) 元组
        """
        # 将距离转换为相似度（距离范围通常是0-2，转换为0-1的相似度）
        # cosine distance = 1 - cosine_similarity，范围[0, 2]
        similarity = max(0.0, 1.0 - similarity_score)

        # 计算时序得分
        temporal_score = self.compute_temporal_score(
            source_chapter, target_chapter, total_chapters
        )

        # 综合得分
        final_score = (
            similarity * self.similarity_weight +
            temporal_score * self.recency_weight
        )

        return temporal_score, final_score

    def apply_nearby_bonus(
        self,
        chunks: List[TemporalScoredChunk],
        target_chapter: int,
    ) -> List[TemporalScoredChunk]:
        """为临近章节的检索结果加分

        Args:
            chunks: 已计算综合得分的检索结果
            target_chapter: 当前要生成的章节

        Returns:
            应用加分后的结果列表
        """
        for item in chunks:
            distance = abs(item.chunk.chapter_number - target_chapter)
            if 0 < distance <= self.nearby_range:
                # 线性递减的加分：距离越近加分越多
                bonus = self.nearby_bonus * (1 - (distance - 1) / self.nearby_range)
                item.final_score = min(item.final_score + bonus, 1.0)

        return chunks

    async def retrieve_chunks_with_temporal(
        self,
        project_id: str,
        query_embedding: Sequence[float],
        target_chapter: int,
        total_chapters: int,
        top_k: int = 10,
        candidate_multiplier: float = 2.0,
    ) -> List[RetrievedChunk]:
        """带时序感知的chunk检索

        流程：
        1. 先检索更多候选（top_k * candidate_multiplier）
        2. 计算每个候选的综合得分（相似度 + 时序）
        3. 应用临近章节加分
        4. 按综合得分重新排序，返回top_k

        Args:
            project_id: 项目ID
            query_embedding: 查询向量
            target_chapter: 当前要生成的章节
            total_chapters: 小说总章节数
            top_k: 返回数量
            candidate_multiplier: 候选倍数

        Returns:
            重排序后的检索结果
        """
        # 获取更多候选
        candidate_k = int(top_k * candidate_multiplier)
        candidates = await self.vector_store.query_chunks(
            project_id=project_id,
            embedding=query_embedding,
            top_k=candidate_k,
        )

        if not candidates:
            return []

        # 过滤掉当前章节及之后的内容（不应检索到未来章节）
        candidates = [c for c in candidates if c.chapter_number < target_chapter]

        if not candidates:
            return []

        # 计算综合得分
        scored_chunks: List[TemporalScoredChunk] = []
        for chunk in candidates:
            temporal_score, final_score = self.compute_final_score(
                similarity_score=chunk.score,
                source_chapter=chunk.chapter_number,
                target_chapter=target_chapter,
                total_chapters=total_chapters,
            )
            scored_chunks.append(TemporalScoredChunk(
                chunk=chunk,
                temporal_score=temporal_score,
                final_score=final_score,
            ))

        # 应用临近章节加分
        scored_chunks = self.apply_nearby_bonus(scored_chunks, target_chapter)

        # 按综合得分排序（降序，得分越高越好）
        scored_chunks.sort(key=lambda x: x.final_score, reverse=True)

        # 返回top_k，更新原始chunk的score为综合得分
        results = []
        for item in scored_chunks[:top_k]:
            # 创建新的chunk对象，避免修改原始数据
            updated_chunk = RetrievedChunk(
                content=item.chunk.content,
                chapter_number=item.chunk.chapter_number,
                chapter_title=item.chunk.chapter_title,
                score=item.final_score,  # 使用综合得分
                metadata={
                    **item.chunk.metadata,
                    "_original_similarity": item.chunk.score,
                    "_temporal_score": item.temporal_score,
                },
            )
            results.append(updated_chunk)

        return results

    async def retrieve_summaries_with_temporal(
        self,
        project_id: str,
        query_embedding: Sequence[float],
        target_chapter: int,
        total_chapters: int,
        top_k: int = 5,
        candidate_multiplier: float = 2.0,
    ) -> List[RetrievedSummary]:
        """带时序感知的摘要检索

        Args:
            project_id: 项目ID
            query_embedding: 查询向量
            target_chapter: 当前要生成的章节
            total_chapters: 小说总章节数
            top_k: 返回数量
            candidate_multiplier: 候选倍数

        Returns:
            重排序后的摘要检索结果
        """
        # 获取更多候选
        candidate_k = int(top_k * candidate_multiplier)
        candidates = await self.vector_store.query_summaries(
            project_id=project_id,
            embedding=query_embedding,
            top_k=candidate_k,
        )

        if not candidates:
            return []

        # 过滤掉当前章节及之后的内容
        candidates = [s for s in candidates if s.chapter_number < target_chapter]

        if not candidates:
            return []

        # 计算综合得分
        scored_summaries: List[TemporalScoredSummary] = []
        for summary in candidates:
            temporal_score, final_score = self.compute_final_score(
                similarity_score=summary.score,
                source_chapter=summary.chapter_number,
                target_chapter=target_chapter,
                total_chapters=total_chapters,
            )
            scored_summaries.append(TemporalScoredSummary(
                summary=summary,
                temporal_score=temporal_score,
                final_score=final_score,
            ))

        # 按综合得分排序
        scored_summaries.sort(key=lambda x: x.final_score, reverse=True)

        # 返回top_k，更新score为综合得分
        results = []
        for item in scored_summaries[:top_k]:
            updated_summary = RetrievedSummary(
                chapter_number=item.summary.chapter_number,
                title=item.summary.title,
                summary=item.summary.summary,
                score=item.final_score,
            )
            results.append(updated_summary)

        return results


class NearbyChapterPrioritizer:
    """临近章节优先器

    独立的优先器类，可以在任何检索结果上应用临近章节优先策略。
    适用于需要单独调整临近章节权重的场景。

    注意：当前版本中此类未被使用，TemporalAwareRetriever已内置临近章节优先逻辑。
    保留此类的原因：
    1. 提供独立的优先器接口，便于在不同检索场景中复用
    2. 支持自定义的nearby_bonus和nearby_range参数
    3. 作为扩展点，未来可用于更精细的检索策略调优
    """

    def __init__(
        self,
        nearby_bonus: float = 0.2,
        nearby_range: int = 5,
    ):
        """
        Args:
            nearby_bonus: 临近章节的额外加分
            nearby_range: 定义"临近"的章节范围
        """
        self.nearby_bonus = nearby_bonus
        self.nearby_range = nearby_range

    def prioritize_chunks(
        self,
        chunks: List[RetrievedChunk],
        target_chapter: int,
    ) -> List[RetrievedChunk]:
        """为临近章节的检索结果加分并重排序

        Args:
            chunks: 检索结果列表
            target_chapter: 目标章节号

        Returns:
            重排序后的结果列表
        """
        boosted = []
        for chunk in chunks:
            distance = abs(chunk.chapter_number - target_chapter)
            new_score = chunk.score

            if 0 < distance <= self.nearby_range:
                # 计算加分：距离越近加分越多
                bonus = self.nearby_bonus * (1 - (distance - 1) / self.nearby_range)
                # 注意：这里假设score越高越好
                # 如果原始score是距离（越小越好），需要调整逻辑
                new_score = chunk.score + bonus

            boosted.append(RetrievedChunk(
                content=chunk.content,
                chapter_number=chunk.chapter_number,
                chapter_title=chunk.chapter_title,
                score=new_score,
                metadata=chunk.metadata,
            ))

        # 按分数降序排序
        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted

    def prioritize_summaries(
        self,
        summaries: List[RetrievedSummary],
        target_chapter: int,
    ) -> List[RetrievedSummary]:
        """为临近章节的摘要加分并重排序"""
        boosted = []
        for summary in summaries:
            distance = abs(summary.chapter_number - target_chapter)
            new_score = summary.score

            if 0 < distance <= self.nearby_range:
                bonus = self.nearby_bonus * (1 - (distance - 1) / self.nearby_range)
                new_score = summary.score + bonus

            boosted.append(RetrievedSummary(
                chapter_number=summary.chapter_number,
                title=summary.title,
                summary=summary.summary,
                score=new_score,
            ))

        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted
