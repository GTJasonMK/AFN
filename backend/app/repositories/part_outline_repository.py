from typing import List, Optional

from sqlalchemy import select

from .base import BaseRepository
from ..models.part_outline import PartOutline


class PartOutlineRepository(BaseRepository[PartOutline]):
    """部分大纲仓库，负责part_outlines表的数据访问"""

    model = PartOutline

    async def get_by_project_id(self, project_id: str) -> List[PartOutline]:
        """获取指定项目的所有部分大纲，按part_number升序排列"""
        result = await self.list_by_project(project_id, order_by="part_number")
        return list(result)

    async def get_by_part_number(self, project_id: str, part_number: int) -> Optional[PartOutline]:
        """获取指定项目的特定部分大纲"""
        return await self.get(project_id=project_id, part_number=part_number)

    # delete_by_project_id 已在 BaseRepository 中实现，无需重复定义

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
        return await self.delete_from_value("part_number", project_id, from_part)

    async def batch_create(self, part_outlines: List[PartOutline]) -> List[PartOutline]:
        """批量创建部分大纲"""
        return await self.bulk_add(part_outlines)

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
