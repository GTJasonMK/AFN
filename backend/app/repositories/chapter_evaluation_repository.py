"""章节评价数据访问层"""

from typing import Iterable

from sqlalchemy import select

from .base import BaseRepository
from ..models.novel import ChapterEvaluation


class ChapterEvaluationRepository(BaseRepository[ChapterEvaluation]):
    """章节评价Repository"""

    model = ChapterEvaluation

    async def list_by_chapter(self, chapter_id: int) -> Iterable[ChapterEvaluation]:
        """
        获取章节的所有评价

        Args:
            chapter_id: 章节ID

        Returns:
            评价列表
        """
        stmt = (
            select(ChapterEvaluation)
            .where(ChapterEvaluation.chapter_id == chapter_id)
            .order_by(ChapterEvaluation.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
