from typing import Any, Generic, Iterable, List, Optional, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """通用仓储基类，封装常见的增删改查操作。"""

    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, **filters: Any) -> Optional[ModelType]:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(self, *, filters: Optional[dict[str, Any]] = None) -> Iterable[ModelType]:
        stmt = select(self.model)
        if filters:
            stmt = stmt.filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add(self, instance: ModelType) -> ModelType:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        self.session.delete(instance)
        await self.session.flush()

    async def update_fields(self, instance: ModelType, **values: Any) -> ModelType:
        for key, value in values.items():
            if value is None:
                continue
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def bulk_add(self, instances: List[ModelType]) -> List[ModelType]:
        """
        批量添加实例到数据库

        Args:
            instances: 要添加的实例列表

        Returns:
            添加后的实例列表
        """
        if not instances:
            return []

        self.session.add_all(instances)
        await self.session.flush()
        return instances

    async def bulk_delete_by_ids(self, ids: List[Any]) -> int:
        """
        根据ID列表批量删除记录

        Args:
            ids: 要删除的ID列表

        Returns:
            删除的记录数
        """
        if not ids:
            return 0

        # 假设模型有id字段
        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
