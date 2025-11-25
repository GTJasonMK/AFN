from typing import List, Optional

from sqlalchemy import delete, select

from .base import BaseRepository
from ..models.part_outline import PartOutline


class PartOutlineRepository(BaseRepository[PartOutline]):
    """部分大纲仓库，负责part_outlines表的数据访问"""

    model = PartOutline

    async def get_by_project_id(self, project_id: str) -> List[PartOutline]:
        """获取指定项目的所有部分大纲，按part_number升序排列"""
        stmt = (
            select(PartOutline)
            .where(PartOutline.project_id == project_id)
            .order_by(PartOutline.part_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_part_number(self, project_id: str, part_number: int) -> Optional[PartOutline]:
        """获取指定项目的特定部分大纲"""
        stmt = select(PartOutline).where(
            PartOutline.project_id == project_id,
            PartOutline.part_number == part_number,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def delete_by_project_id(self, project_id: str) -> None:
        """删除指定项目的所有部分大纲"""
        stmt = delete(PartOutline).where(PartOutline.project_id == project_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_from_part(self, project_id: str, from_part: int) -> int:
        """
        删除指定部分号及之后的所有部分大纲

        用于串行生成原则下的级联删除：重新生成某个部分时，删除该部分及之后的所有部分大纲。

        Args:
            project_id: 项目ID
            from_part: 起始部分编号（包含）

        Returns:
            int: 删除的部分数量
        """
        # 先统计要删除的数量
        from sqlalchemy import func
        count_stmt = (
            select(func.count(PartOutline.id))
            .where(PartOutline.project_id == project_id)
            .where(PartOutline.part_number >= from_part)
        )
        result = await self.session.execute(count_stmt)
        delete_count = result.scalar() or 0

        # 执行删除
        stmt = delete(PartOutline).where(
            PartOutline.project_id == project_id,
            PartOutline.part_number >= from_part
        )
        await self.session.execute(stmt)
        await self.session.flush()

        return delete_count

    async def batch_create(self, part_outlines: List[PartOutline]) -> List[PartOutline]:
        """批量创建部分大纲"""
        self.session.add_all(part_outlines)
        await self.session.flush()
        return part_outlines

    async def update_status(
        self, part_outline: PartOutline, status: str, progress: int
    ) -> PartOutline:
        """更新部分大纲的生成状态和进度"""
        return await self.update_fields(part_outline, generation_status=status, progress=progress)

    async def get_pending_parts(self, project_id: str) -> List[PartOutline]:
        """获取指定项目中所有待生成的部分大纲"""
        stmt = (
            select(PartOutline)
            .where(
                PartOutline.project_id == project_id,
                PartOutline.generation_status == "pending",
            )
            .order_by(PartOutline.part_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
