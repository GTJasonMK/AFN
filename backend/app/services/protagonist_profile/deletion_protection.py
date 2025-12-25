"""删除保护服务

实现5次连续标记才能删除的保护机制。
"""
import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.protagonist import ProtagonistDeletionMark
from ...repositories.protagonist_repository import ProtagonistDeletionMarkRepository

logger = logging.getLogger(__name__)

# 删除保护阈值：需要连续标记的次数
DELETION_THRESHOLD = 5


class DeletionProtectionService:
    """删除保护服务

    实现删除保护机制：
    1. 首次请求删除时创建标记
    2. 连续章节再次请求时增加计数
    3. 达到阈值（默认5次）后才允许实际删除
    4. 如果属性被引用或使用，重置连续计数
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.mark_repo = ProtagonistDeletionMarkRepository(session)

    async def add_mark(
        self,
        profile_id: int,
        category: str,
        key: str,
        reason: str,
        evidence: str,
        chapter_number: int
    ) -> ProtagonistDeletionMark:
        """添加或更新删除标记

        Args:
            profile_id: 档案ID
            category: 属性类别
            key: 属性键名
            reason: 删除原因
            evidence: 支持删除的原文证据
            chapter_number: 章节号

        Returns:
            删除标记对象
        """
        # 检查是否已有该属性的标记
        existing_mark = await self.mark_repo.get_mark(profile_id, category, key)

        if existing_mark:
            # 已有标记，检查是否连续章节
            if existing_mark.is_executed:
                # 如果已执行，需要创建新标记
                await self.mark_repo.delete(existing_mark)
                existing_mark = None
            elif chapter_number == existing_mark.last_marked_chapter + 1:
                # 连续章节，增加计数
                existing_mark.consecutive_count += 1
                existing_mark.last_marked_chapter = chapter_number
                existing_mark.mark_reason = reason
                existing_mark.evidence = evidence
                await self.session.flush()
                logger.info(
                    f"更新删除标记: profile={profile_id}, {category}.{key}, "
                    f"count={existing_mark.consecutive_count}"
                )
                return existing_mark
            else:
                # 非连续章节，重置计数
                existing_mark.consecutive_count = 1
                existing_mark.chapter_number = chapter_number
                existing_mark.last_marked_chapter = chapter_number
                existing_mark.mark_reason = reason
                existing_mark.evidence = evidence
                await self.session.flush()
                logger.info(
                    f"重置删除标记（非连续）: profile={profile_id}, {category}.{key}"
                )
                return existing_mark

        # 创建新标记
        mark = ProtagonistDeletionMark(
            profile_id=profile_id,
            attribute_category=category,
            attribute_key=key,
            chapter_number=chapter_number,
            mark_reason=reason,
            evidence=evidence,
            consecutive_count=1,
            last_marked_chapter=chapter_number,
            is_executed=False,
        )
        await self.mark_repo.add(mark)
        logger.info(f"创建删除标记: profile={profile_id}, {category}.{key}")
        return mark

    async def get_marks(
        self,
        profile_id: int,
        category: Optional[str] = None
    ) -> List[ProtagonistDeletionMark]:
        """获取档案的删除标记"""
        return await self.mark_repo.list_by_profile(profile_id, category=category)

    async def get_pending_marks(self, profile_id: int) -> List[ProtagonistDeletionMark]:
        """获取所有未执行的删除标记"""
        return await self.mark_repo.list_pending_marks(profile_id)

    async def check_ready_for_deletion(
        self,
        profile_id: int,
        category: str,
        key: str,
        threshold: int = DELETION_THRESHOLD
    ) -> Tuple[bool, int]:
        """检查是否达到删除阈值

        Args:
            profile_id: 档案ID
            category: 属性类别
            key: 属性键名
            threshold: 阈值（默认5）

        Returns:
            (是否达到阈值, 当前连续次数)
        """
        mark = await self.mark_repo.get_mark(profile_id, category, key)
        if not mark or mark.is_executed:
            return False, 0
        return mark.consecutive_count >= threshold, mark.consecutive_count

    async def mark_as_executed(
        self,
        profile_id: int,
        category: str,
        key: str
    ) -> bool:
        """标记删除已执行

        Args:
            profile_id: 档案ID
            category: 属性类别
            key: 属性键名

        Returns:
            是否成功
        """
        mark = await self.mark_repo.get_mark(profile_id, category, key)
        if not mark:
            return False

        mark.is_executed = True
        await self.session.flush()
        logger.info(f"标记删除已执行: profile={profile_id}, {category}.{key}")
        return True

    async def reset_marks(
        self,
        profile_id: int,
        category: str,
        key: str
    ) -> bool:
        """重置删除标记

        当属性被引用或使用时调用，重置连续计数。

        Args:
            profile_id: 档案ID
            category: 属性类别
            key: 属性键名

        Returns:
            是否有标记被重置
        """
        mark = await self.mark_repo.get_mark(profile_id, category, key)
        if not mark or mark.is_executed:
            return False

        # 删除标记（下次需要重新开始计数）
        await self.mark_repo.delete(mark)
        logger.info(f"重置删除标记（属性被使用）: profile={profile_id}, {category}.{key}")
        return True

    async def get_ready_for_deletion_list(
        self,
        profile_id: int,
        threshold: int = DELETION_THRESHOLD
    ) -> List[ProtagonistDeletionMark]:
        """获取所有达到删除阈值的标记"""
        return await self.mark_repo.list_ready_for_deletion(profile_id, threshold)
