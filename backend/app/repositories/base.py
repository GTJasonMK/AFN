from typing import Any, Generic, Iterable, List, Optional, TypeVar, Union

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

    async def list(
        self,
        *,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ) -> Iterable[ModelType]:
        """
        条件查询

        Args:
            filters: 过滤条件字典
            order_by: 排序字段名（可选）
            order_desc: 是否降序（默认升序）

        Returns:
            查询结果列表
        """
        stmt = select(self.model)
        if filters:
            stmt = stmt.filter_by(**filters)
        if order_by:
            field = getattr(self.model, order_by, None)
            if field is not None:
                stmt = stmt.order_by(field.desc() if order_desc else field)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_all(self) -> Iterable[ModelType]:
        """获取所有记录"""
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def list_by_project(
        self,
        project_id: str,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ) -> Iterable[ModelType]:
        """
        按项目ID查询（通用便捷方法）

        大多数业务模型都关联到项目，此方法提供统一的按项目查询入口。

        Args:
            project_id: 项目ID
            order_by: 排序字段名（可选）
            order_desc: 是否降序

        Returns:
            查询结果列表

        Raises:
            ValueError: 如果模型没有project_id字段
        """
        if not hasattr(self.model, "project_id"):
            raise ValueError(f"模型 {self.model.__name__} 没有 project_id 字段")
        return await self.list(
            filters={"project_id": project_id},
            order_by=order_by,
            order_desc=order_desc,
        )

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

    async def delete_from_value(
        self,
        number_field: str,
        project_id: str,
        from_value: int,
    ) -> int:
        """
        删除指定数值字段大于等于某值的所有记录（用于串行生成的级联删除）

        此方法用于实现串行生成原则下的级联删除：
        当重新生成某个编号时，需要删除该编号及之后的所有记录。

        Args:
            number_field: 数值字段名（如 chapter_number, part_number）
            project_id: 项目ID
            from_value: 起始值（包含，>=from_value的记录将被删除）

        Returns:
            int: 删除的记录数

        Example:
            # 删除第5章及之后的所有章节大纲
            await repo.delete_from_value("chapter_number", "proj-123", 5)

            # 删除第3部及之后的所有分部大纲
            await repo.delete_from_value("part_number", "proj-123", 3)
        """
        field = getattr(self.model, number_field, None)
        project_field = getattr(self.model, "project_id", None)

        if field is None:
            raise ValueError(f"模型 {self.model.__name__} 没有字段 {number_field}")
        if project_field is None:
            raise ValueError(f"模型 {self.model.__name__} 没有 project_id 字段")

        # 先统计要删除的数量
        count_stmt = (
            select(func.count(self.model.id))
            .where(project_field == project_id)
            .where(field >= from_value)
        )
        result = await self.session.execute(count_stmt)
        delete_count = result.scalar() or 0

        # 执行删除
        delete_stmt = (
            delete(self.model)
            .where(project_field == project_id)
            .where(field >= from_value)
        )
        await self.session.execute(delete_stmt)
        await self.session.flush()

        return delete_count
