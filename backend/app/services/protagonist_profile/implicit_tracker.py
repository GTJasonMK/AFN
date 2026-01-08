"""隐性属性追踪服务

负责记录主角行为、分类行为与隐性属性的符合度、检测更新阈值。
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.protagonist import ProtagonistBehaviorRecord
from ...repositories.protagonist_repository import ProtagonistBehaviorRecordRepository

logger = logging.getLogger(__name__)

# 隐性属性更新阈值：窗口内累计不符合次数
IMPLICIT_UPDATE_THRESHOLD = 5


class ImplicitAttributeTracker:
    """隐性属性追踪器

    功能：
    1. 记录主角行为和对话
    2. 对行为进行二元分类（符合/不符合）
    3. 统计分类结果，检测是否需要更新隐性属性
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.behavior_repo = ProtagonistBehaviorRecordRepository(session)

    async def record_behavior(
        self,
        profile_id: int,
        chapter_number: int,
        behavior_description: str,
        original_text: str,
        behavior_tags: List[str],
        classification_results: Dict[str, str]
    ) -> ProtagonistBehaviorRecord:
        """记录一条行为

        Args:
            profile_id: 档案ID
            chapter_number: 章节号
            behavior_description: 行为描述
            original_text: 原文摘录
            behavior_tags: 行为标签列表
            classification_results: 分类结果 {属性名: conform/non-conform}

        Returns:
            行为记录对象
        """
        record = ProtagonistBehaviorRecord(
            profile_id=profile_id,
            chapter_number=chapter_number,
            behavior_description=behavior_description,
            original_text=original_text,
            behavior_tags=behavior_tags,
            classification_results=classification_results,
        )

        await self.behavior_repo.add(record)
        logger.info(
            f"记录行为: profile={profile_id}, chapter={chapter_number}, "
            f"tags={behavior_tags}"
        )
        return record

    async def get_recent_behaviors(
        self,
        profile_id: int,
        limit: int = 20
    ) -> List[ProtagonistBehaviorRecord]:
        """获取最近的行为记录"""
        return await self.behavior_repo.list_recent_by_profile(profile_id, limit)

    async def get_behaviors_by_chapter(
        self,
        profile_id: int,
        chapter_number: int
    ) -> List[ProtagonistBehaviorRecord]:
        """获取指定章节的行为记录"""
        return await self.behavior_repo.list_by_profile(
            profile_id,
            chapter=chapter_number,
            order_desc=False
        )

    async def get_non_conform_stats(
        self,
        profile_id: int,
        attribute_key: str,
        window_chapters: int = 10
    ) -> Dict[str, Any]:
        """获取隐性属性的不符合统计

        Args:
            profile_id: 档案ID
            attribute_key: 属性键名
            window_chapters: 统计窗口（章节数）

        Returns:
            统计结果：{total, conform_count, non_conform_count, conform_rate, records}
        """
        stats = await self.behavior_repo.get_classification_stats(
            profile_id,
            attribute_key,
            window_chapters
        )

        total = stats["total"]
        conform_count = stats["conform_count"]
        non_conform_count = stats["non_conform_count"]

        # 计算符合率
        conform_rate = conform_count / total if total > 0 else 1.0

        return {
            "total": total,
            "conform_count": conform_count,
            "non_conform_count": non_conform_count,
            "conform_rate": conform_rate,
            "records": stats["records"],
        }

    async def check_update_threshold(
        self,
        profile_id: int,
        attribute_key: str,
        threshold: int = IMPLICIT_UPDATE_THRESHOLD,
        window_chapters: int = 10
    ) -> bool:
        """检查是否达到更新阈值

        当某属性在窗口内累计多次"不符合"时，返回True表示需要考虑更新。

        Args:
            profile_id: 档案ID
            attribute_key: 属性键名
            threshold: 不符合阈值（默认5）
            window_chapters: 检查窗口（章节数）

        Returns:
            是否达到更新阈值
        """
        stats = await self.get_non_conform_stats(profile_id, attribute_key, window_chapters)
        return stats["non_conform_count"] >= threshold

    async def get_attributes_needing_review(
        self,
        profile_id: int,
        implicit_attributes: Dict[str, Any],
        threshold: int = IMPLICIT_UPDATE_THRESHOLD,
        window_chapters: int = 10
    ) -> List[Dict[str, Any]]:
        """获取所有需要审查的隐性属性

        检查所有隐性属性，返回达到更新阈值的属性列表。

        Args:
            profile_id: 档案ID
            implicit_attributes: 当前隐性属性字典
            threshold: 不符合阈值
            window_chapters: 检查窗口

        Returns:
            需要审查的属性列表，每项包含 {key, current_value, stats}
        """
        results = []

        for key, value in implicit_attributes.items():
            stats = await self.get_non_conform_stats(profile_id, key, window_chapters)
            if stats["non_conform_count"] >= threshold:
                results.append({
                    "key": key,
                    "current_value": value,
                    "stats": stats,
                })

        return results

    async def get_behavior_evidence(
        self,
        profile_id: int,
        attribute_key: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取属性相关的行为证据

        用于为隐性属性更新决策提供证据支持。

        Args:
            profile_id: 档案ID
            attribute_key: 属性键名
            limit: 返回数量限制

        Returns:
            行为证据列表，每项包含 {chapter, behavior, original_text, classification}
        """
        records = await self.behavior_repo.list_recent_by_profile(profile_id, limit=50)

        evidence = []
        for record in records:
            classifications = record.classification_results or {}
            if attribute_key in classifications:
                evidence.append({
                    "chapter": record.chapter_number,
                    "behavior": record.behavior_description,
                    "original_text": record.original_text,
                    "classification": classifications[attribute_key],
                    "tags": record.behavior_tags,
                })
                if len(evidence) >= limit:
                    break

        return evidence
