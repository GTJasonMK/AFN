from typing import Any, Generic, Iterable, List, Optional, TypeVar

from sqlalchemy import delete, func, select
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

    async def list_all(self) -> Iterable[ModelType]:
        """获取所有记录"""
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def add(self, instance: ModelType) -> ModelType:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        # 注意：session.delete() 不是异步方法，不需要await
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

        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def delete_by_field(self, field_name: str, value: Any) -> int:
        """
        根据字段值删除记录

        通用删除方法，支持任意字段条件删除。

        Args:
            field_name: 字段名称
            value: 字段值

        Returns:
            int: 删除的记录数

        Example:
            await repo.delete_by_field("project_id", "proj-123")
            await repo.delete_by_field("user_id", 1)
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            raise ValueError(f"模型 {self.model.__name__} 没有字段 {field_name}")

        stmt = delete(self.model).where(field == value)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def delete_by_project_id(self, project_id: str) -> int:
        """
        根据项目ID删除所有相关记录

        这是最常用的删除模式，大多数业务模型都关联到项目。

        Args:
            project_id: 项目ID

        Returns:
            int: 删除的记录数

        Raises:
            ValueError: 如果模型没有project_id字段
        """
        return await self.delete_by_field("project_id", project_id)

    async def count_by_field(self, field_name: str, value: Any) -> int:
        """
        根据字段值统计记录数

        Args:
            field_name: 字段名称
            value: 字段值

        Returns:
            int: 记录数
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            raise ValueError(f"模型 {self.model.__name__} 没有字段 {field_name}")

        stmt = select(func.count(self.model.id)).where(field == value)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
