"""管理员视图通用辅助函数（聚合统计/时间标准化）。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def normalize_datetime(value: datetime | None) -> datetime | None:
    """统一时区，避免 naive/aware 比较报错。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def collect_count_map(session: AsyncSession, model: type) -> dict[int, int]:
    """按 user_id 聚合计数。"""
    user_col = getattr(model, "user_id", None)
    id_col = getattr(model, "id", None)
    if user_col is None or id_col is None:
        return {}

    result = await session.execute(select(user_col, func.count(id_col)).group_by(user_col))

    data: dict[int, int] = {}
    for user_id, count_value in result.all():
        if user_id is None:
            continue
        data[int(user_id)] = int(count_value or 0)
    return data


async def collect_latest_map(session: AsyncSession, model: type, ts_field: str = "updated_at") -> dict[int, datetime]:
    """按 user_id 聚合最后更新时间。"""
    user_col = getattr(model, "user_id", None)
    ts_col = getattr(model, ts_field, None)
    if user_col is None or ts_col is None:
        return {}

    result = await session.execute(select(user_col, func.max(ts_col)).group_by(user_col))

    data: dict[int, datetime] = {}
    for user_id, ts_value in result.all():
        if user_id is None:
            continue
        normalized = normalize_datetime(ts_value)
        if normalized is not None:
            data[int(user_id)] = normalized
    return data

