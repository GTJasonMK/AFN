"""章节版本数据访问层"""

from typing import Iterable, List

from sqlalchemy import delete, select

from .base import BaseRepository
from ..models.novel import ChapterVersion


class ChapterVersionRepository(BaseRepository[ChapterVersion]):
    """章节版本Repository"""

    model = ChapterVersion

    async def list_by_chapter(self, chapter_id: int) -> Iterable[ChapterVersion]:
        """
        获取章节的所有版本

        Args:
            chapter_id: 章节ID

        Returns:
            版本列表
        """
        stmt = (
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == chapter_id)
            .order_by(ChapterVersion.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_chapter(self, chapter_id: int) -> None:
        """
        删除章节的所有版本

        Args:
            chapter_id: 章节ID
        """
        await self.session.execute(
            delete(ChapterVersion).where(ChapterVersion.chapter_id == chapter_id)
        )

    async def replace_all(
        self,
        chapter_id: int,
        versions_data: List[dict]
    ) -> List[ChapterVersion]:
        """
        替换章节的所有版本（先删除再创建）

        Args:
            chapter_id: 章节ID
            versions_data: 版本数据列表，每个dict包含content, metadata, version_label

        Returns:
            创建的版本列表
        """
        # 先删除所有旧版本
        await self.delete_by_chapter(chapter_id)

        # 使用批量创建而非循环
        versions = [
            ChapterVersion(
                chapter_id=chapter_id,
                content=data.get("content", ""),
                metadata=data.get("metadata"),
                version_label=data.get("version_label", ""),
            )
            for data in versions_data
        ]

        if versions:
            self.session.add_all(versions)
        await self.session.flush()
        return versions
