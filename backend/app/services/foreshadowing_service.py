"""
伏笔管理服务

提供伏笔的智能推荐、优先级计算、回收提醒等功能。
与章节生成流程集成，在生成前提供待回收伏笔建议。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.novel import ForeshadowingIndex, Chapter

logger = logging.getLogger(__name__)


@dataclass
class ForeshadowingSuggestion:
    """伏笔回收建议"""
    id: int
    description: str
    priority: str
    category: str
    planted_chapter: int
    chapters_pending: int  # 已经悬置的章节数
    urgency_score: float  # 紧迫度得分 (0-1)
    related_entities: List[str] = field(default_factory=list)
    reason: str = ""  # 推荐理由


class ForeshadowingService:
    """伏笔管理服务

    核心功能：
    1. 智能推荐待回收伏笔
    2. 计算伏笔紧迫度
    3. 检测过期伏笔预警
    4. 提供章节生成时的伏笔上下文

    使用方式：
        service = ForeshadowingService(session)
        suggestions = await service.get_suggestions_for_chapter(
            project_id=project_id,
            chapter_number=10,
            outline_summary="主角与反派对决...",
        )
    """

    # 伏笔超时阈值（章节数）
    HIGH_PRIORITY_TIMEOUT = 15  # 高优先级伏笔超过15章未回收则预警
    MEDIUM_PRIORITY_TIMEOUT = 25  # 中优先级伏笔超过25章未回收则预警
    LOW_PRIORITY_TIMEOUT = 40  # 低优先级伏笔超过40章未回收则预警

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_suggestions_for_chapter(
        self,
        project_id: str,
        chapter_number: int,
        outline_summary: Optional[str] = None,
        outline_title: Optional[str] = None,
        max_suggestions: int = 5,
    ) -> List[ForeshadowingSuggestion]:
        """获取章节的伏笔回收建议

        根据当前章节信息，智能推荐应该考虑回收的伏笔。

        Args:
            project_id: 项目ID
            chapter_number: 当前章节号
            outline_summary: 章节大纲摘要（用于相关性匹配）
            outline_title: 章节标题（用于相关性匹配）
            max_suggestions: 最大建议数量

        Returns:
            List[ForeshadowingSuggestion]: 排序后的伏笔建议列表
        """
        # 获取所有待回收伏笔
        result = await self.session.execute(
            select(ForeshadowingIndex).where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.status == "pending",
                ForeshadowingIndex.planted_chapter < chapter_number,
            )
        )
        pending_foreshadowing = result.scalars().all()

        if not pending_foreshadowing:
            return []

        # 计算每个伏笔的紧迫度和相关性
        suggestions = []
        outline_text = f"{outline_title or ''} {outline_summary or ''}".lower()

        for fs in pending_foreshadowing:
            chapters_pending = chapter_number - fs.planted_chapter
            urgency_score = self._calculate_urgency(fs.priority, chapters_pending)
            relevance_score = self._calculate_relevance(
                fs.description,
                fs.related_entities or [],
                outline_text,
            )

            # 综合得分 = 紧迫度 * 0.6 + 相关性 * 0.4
            combined_score = urgency_score * 0.6 + relevance_score * 0.4

            reason = self._generate_reason(
                fs.priority,
                chapters_pending,
                urgency_score,
                relevance_score,
            )

            suggestions.append(ForeshadowingSuggestion(
                id=fs.id,
                description=fs.description,
                priority=fs.priority,
                category=fs.category,
                planted_chapter=fs.planted_chapter,
                chapters_pending=chapters_pending,
                urgency_score=combined_score,
                related_entities=fs.related_entities or [],
                reason=reason,
            ))

        # 按综合得分排序
        suggestions.sort(key=lambda x: x.urgency_score, reverse=True)

        return suggestions[:max_suggestions]

    def _calculate_urgency(self, priority: str, chapters_pending: int) -> float:
        """计算伏笔紧迫度

        Args:
            priority: 伏笔优先级
            chapters_pending: 已悬置章节数

        Returns:
            float: 紧迫度得分 (0-1)
        """
        timeout_map = {
            "high": self.HIGH_PRIORITY_TIMEOUT,
            "medium": self.MEDIUM_PRIORITY_TIMEOUT,
            "low": self.LOW_PRIORITY_TIMEOUT,
        }
        timeout = timeout_map.get(priority, self.MEDIUM_PRIORITY_TIMEOUT)

        # 使用sigmoid-like函数计算紧迫度
        # 接近timeout时急剧上升
        if chapters_pending >= timeout:
            return 1.0
        elif chapters_pending <= 0:
            return 0.0
        else:
            # 在timeout的50%之前缓慢上升，之后加速
            ratio = chapters_pending / timeout
            if ratio < 0.5:
                return ratio * 0.4  # 0-0.2
            else:
                return 0.2 + (ratio - 0.5) * 1.6  # 0.2-1.0

    def _calculate_relevance(
        self,
        description: str,
        related_entities: List[str],
        outline_text: str,
    ) -> float:
        """计算伏笔与当前章节的相关性

        Args:
            description: 伏笔描述
            related_entities: 关联实体
            outline_text: 章节大纲文本

        Returns:
            float: 相关性得分 (0-1)
        """
        if not outline_text:
            return 0.0

        score = 0.0

        # 检查关联实体是否出现在大纲中
        for entity in related_entities:
            if entity.lower() in outline_text:
                score += 0.3

        # 检查描述中的关键词
        desc_words = [w for w in description.lower().split() if len(w) > 1]
        matching_words = sum(1 for w in desc_words if w in outline_text)
        if desc_words:
            score += (matching_words / len(desc_words)) * 0.4

        return min(score, 1.0)

    def _generate_reason(
        self,
        priority: str,
        chapters_pending: int,
        urgency_score: float,
        relevance_score: float,
    ) -> str:
        """生成推荐理由

        Args:
            priority: 优先级
            chapters_pending: 悬置章节数
            urgency_score: 紧迫度
            relevance_score: 相关性

        Returns:
            str: 推荐理由
        """
        reasons = []

        if urgency_score >= 0.8:
            reasons.append(f"已悬置{chapters_pending}章，急需回收")
        elif urgency_score >= 0.5:
            reasons.append(f"悬置{chapters_pending}章，建议近期回收")

        if priority == "high":
            reasons.append("高优先级伏笔")

        if relevance_score >= 0.3:
            reasons.append("与本章内容相关")

        return "；".join(reasons) if reasons else "常规提醒"

    async def get_overdue_warnings(
        self,
        project_id: str,
        current_chapter: int,
    ) -> List[Dict[str, Any]]:
        """获取超期伏笔预警

        Args:
            project_id: 项目ID
            current_chapter: 当前章节号

        Returns:
            List[Dict]: 超期伏笔列表
        """
        result = await self.session.execute(
            select(ForeshadowingIndex).where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.status == "pending",
            )
        )
        all_pending = result.scalars().all()

        overdue = []
        for fs in all_pending:
            chapters_pending = current_chapter - fs.planted_chapter
            timeout = {
                "high": self.HIGH_PRIORITY_TIMEOUT,
                "medium": self.MEDIUM_PRIORITY_TIMEOUT,
                "low": self.LOW_PRIORITY_TIMEOUT,
            }.get(fs.priority, self.MEDIUM_PRIORITY_TIMEOUT)

            if chapters_pending >= timeout:
                overdue.append({
                    "id": fs.id,
                    "description": fs.description,
                    "priority": fs.priority,
                    "planted_chapter": fs.planted_chapter,
                    "chapters_overdue": chapters_pending - timeout,
                    "warning_level": "critical" if chapters_pending >= timeout * 1.5 else "warning",
                })

        # 按超期程度排序
        overdue.sort(key=lambda x: x["chapters_overdue"], reverse=True)
        return overdue

    async def get_foreshadowing_stats(
        self,
        project_id: str,
    ) -> Dict[str, Any]:
        """获取项目伏笔统计

        Args:
            project_id: 项目ID

        Returns:
            Dict: 统计信息
        """
        # 统计各状态数量
        result = await self.session.execute(
            select(
                ForeshadowingIndex.status,
                func.count(ForeshadowingIndex.id).label("count"),
            )
            .where(ForeshadowingIndex.project_id == project_id)
            .group_by(ForeshadowingIndex.status)
        )
        status_counts = {row.status: row.count for row in result}

        # 统计各优先级数量（仅pending）
        result = await self.session.execute(
            select(
                ForeshadowingIndex.priority,
                func.count(ForeshadowingIndex.id).label("count"),
            )
            .where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.status == "pending",
            )
            .group_by(ForeshadowingIndex.priority)
        )
        priority_counts = {row.priority: row.count for row in result}

        return {
            "total": sum(status_counts.values()),
            "pending": status_counts.get("pending", 0),
            "resolved": status_counts.get("resolved", 0),
            "abandoned": status_counts.get("abandoned", 0),
            "by_priority": priority_counts,
        }

    async def get_pending_for_generation(
        self,
        project_id: str,
        chapter_number: int,
        outline_summary: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """获取用于章节生成的待回收伏笔列表

        这是提供给EnhancedChapterContextService使用的接口。

        Args:
            project_id: 项目ID
            chapter_number: 当前章节号
            outline_summary: 章节大纲摘要
            limit: 返回数量限制

        Returns:
            List[Dict]: 格式化的伏笔列表，适合传入RAG上下文
        """
        suggestions = await self.get_suggestions_for_chapter(
            project_id=project_id,
            chapter_number=chapter_number,
            outline_summary=outline_summary,
            max_suggestions=limit,
        )

        return [
            {
                "id": s.id,
                "description": s.description,
                "priority": s.priority,
                "category": s.category,
                "planted_chapter": s.planted_chapter,
                "related_entities": s.related_entities,
            }
            for s in suggestions
        ]

    async def mark_as_resolved(
        self,
        foreshadowing_id: int,
        resolved_chapter: int,
        resolution: Optional[str] = None,
    ) -> bool:
        """手动标记伏笔为已回收

        Args:
            foreshadowing_id: 伏笔ID
            resolved_chapter: 回收章节号
            resolution: 回收方式描述

        Returns:
            bool: 是否成功
        """
        result = await self.session.execute(
            select(ForeshadowingIndex).where(
                ForeshadowingIndex.id == foreshadowing_id,
            )
        )
        fs = result.scalar_one_or_none()

        if not fs:
            return False

        fs.status = "resolved"
        fs.resolved_chapter = resolved_chapter
        fs.resolution = resolution
        await self.session.flush()

        logger.info(
            "伏笔已标记为回收: id=%d chapter=%d",
            foreshadowing_id,
            resolved_chapter,
        )
        return True

    async def mark_as_abandoned(
        self,
        foreshadowing_id: int,
        reason: Optional[str] = None,
    ) -> bool:
        """标记伏笔为已放弃

        用于处理不再需要回收的伏笔。

        Args:
            foreshadowing_id: 伏笔ID
            reason: 放弃原因

        Returns:
            bool: 是否成功
        """
        result = await self.session.execute(
            select(ForeshadowingIndex).where(
                ForeshadowingIndex.id == foreshadowing_id,
            )
        )
        fs = result.scalar_one_or_none()

        if not fs:
            return False

        fs.status = "abandoned"
        fs.resolution = reason or "已放弃"
        await self.session.flush()

        logger.info("伏笔已标记为放弃: id=%d", foreshadowing_id)
        return True
