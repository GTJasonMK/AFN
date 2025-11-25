
# backend/app/models/user_daily_request.py - 用户日请求统计模型

## 文件概述

定义用户每日请求次数的数据模型，用于实现用户级别的限流控制。通过记录每位用户每天的请求次数，实现日级别的使用配额管理，防止滥用和保护系统资源。

**文件路径：** `backend/app/models/user_daily_request.py`  
**代码行数：** 18 行  
**复杂度：** ⭐⭐ 简单-中等

## 数据模型定义

### UserDailyRequest 类

```python
from datetime import date
from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db.base import Base

class UserDailyRequest(Base):
    """记录每位用户每日使用次数的限流表。"""
    
    __tablename__ = "user_daily_requests"
    __table_args__ = (
        UniqueConstraint("user_id", "request_date", name="uq_user_daily"),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    request_date: Mapped[date] = mapped_column(Date, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
```

## 字段详解

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `int` | 主键、自增 | 记录唯一标识 |
| `user_id` | `int` | 外键、索引 | 关联用户ID |
| `request_date` | `date` | 非空 | 请求日期 |
| `request_count` | `int` | 默认0 | 当日请求次数 |

## 约束说明

### 唯一约束

```python
UniqueConstraint("user_id", "request_date", name="uq_user_daily")
```

确保每个用户每天只有一条记录，防止数据重复。

### 外键约束

```python
ForeignKey("users.id", ondelete="CASCADE")
```

当用户被删除时，自动删除该用户的所有请求记录。

## 数据库表结构

```sql
CREATE TABLE user_daily_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    request_date DATE NOT NULL,
    request_count INTEGER DEFAULT 0,
    CONSTRAINT fk_user FOREIGN KEY (user_id) 
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_daily UNIQUE (user_id, request_date)
);

CREATE INDEX idx_user_daily_requests_user_id ON user_daily_requests(user_id);
CREATE INDEX idx_user_daily_requests_date ON user_daily_requests(request_date);
```

## 使用示例

### 1. 增加用户请求计数

```python
from datetime import date
from sqlalchemy import select
from backend.app.models.user_daily_request import UserDailyRequest

async def increment_user_request(
    session: AsyncSession,
    user_id: int,
    increment: int = 1
) -> int:
    """增加用户今日请求计数，返回新的计数"""
    today = date.today()
    
    # 查询今日记录
    result = await session.execute(
        select(UserDailyRequest).where(
            UserDailyRequest.user_id == user_id,
            UserDailyRequest.request_date == today
        )
    )
    record = result.scalar_one_or_none()
    
    if record:
        record.request_count += increment
    else:
        record = UserDailyRequest(
            user_id=user_id,
            request_date=today,
            request_count=increment
        )
        session.add(record)
    
    await session.commit()
    await session.refresh(record)
    return record.request_count
```

### 2. 查询用户今日请求次数

```python
async def get_user_daily_count(
    session: AsyncSession,
    user_id: int,
    target_date: date = None
) -> int:
    """查询用户指定日期的请求次数"""
    if target_date is None:
        target_date = date.today()
    
    result = await session.execute(
        select(UserDailyRequest).where(
            UserDailyRequest.user_id == user_id,
            UserDailyRequest.request_date == target_date
        )
    )
    record = result.scalar_one_or_none()
    return record.request_count if record else 0
```

### 3. 检查用户是否超过限额

```python
async def check_rate_limit(
    session: AsyncSession,
    user_id: int,
    daily_limit: int
) -> tuple[bool, int]:
    """检查用户是否超过日限额
    
    Returns:
        (是否允许请求, 剩余配额)
    """
    current_count = await get_user_daily_count(session, user_id)
    remaining = max(0, daily_limit - current_count)
    allowed = current_count < daily_limit
    
    return allowed, remaining
```

### 4. 限流装饰器

```python
from functools import wraps
from fastapi import HTTPException, status

def rate_limit(daily_limit: int = 100):
    """API 限流装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, session: AsyncSession, user_id: int, **kwargs):
            # 检查限额
            allowed, remaining = await check_rate_limit(session, user_id, daily_limit)
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Daily limit ({daily_limit}) exceeded. Try again tomorrow."
                )
            
            # 增加计数
            await increment_user_request(session, user_id)
            
            # 执行原函数
            return await func(*args, session=session, user_id=user_id, **kwargs)
        
        return wrapper
    return decorator

# 使用示例
@rate_limit(daily_limit=50)
async def generate_outline(session: AsyncSession, user_id: int, novel_id: int):
    # 业务逻辑
    pass
```

### 5. 批量查询用户统计

```python
async def get_users_daily_stats(
    session: AsyncSession,
    target_date: date = None
) -> list[dict]:
    """查询所有用户某日的请求统计"""
    if target_date is None:
        target_date = date.today()
    
    result = await session.execute(
        select(UserDailyRequest)
        .where(UserDailyRequest.request_date == target_date)
        .order_by(UserDailyRequest.request_count.desc())
    )
    records = result.scalars().all()
    
    return [
        {
            "user_id": r.user_id,
            "date": r.request_date,
            "count": r.request_count
        }
        for r in records
    ]
```

### 6. 清理过期数据

```python
from datetime import timedelta
from sqlalchemy import delete

async def cleanup_old_requests(
    session: AsyncSession,
    keep_days: int = 30
) -> int:
    """清理指定天数之前的请求记录"""
    cutoff_date = date.today() - timedelta(days=keep_days)
    
    result = await session.execute(
        delete(UserDailyRequest).where(
            UserDailyRequest.request_date < cutoff_date
        )
    )
    await session.commit()
    return result.rowcount
```

## 典型应用场景

### 1. FastAPI 依赖注入

```python
from fastapi import Depends, HTTPException
from backend.app.core.dependencies import get_current_user, get_db

async def check_and_increment_rate_limit(
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    daily_limit: int = 100
):
    """检查并递增限流计数"""
    allowed, remaining = await check_rate_limit(session, user_id, daily_limit)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Daily request limit exceeded",
                "limit": daily_limit,
                "reset_at": str(date.today() + timedelta(days=1))
            }
        )
    
    await increment_user_request(session, user_id)
    return {"remaining": remaining - 1}

# 在路由中使用
@app.post("/api/novels/{novel_id}/generate-outline")
async def generate_outline(
    novel_id: int,
    rate_limit_info: dict = Depends(check_and_increment_rate_limit),
    session: AsyncSession = Depends(get_db)
):
    # 业务逻辑
    pass
```

### 2. 中间件方式

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 仅对特定路径限流
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # 获取用户信息
        user = getattr(request.state, "user", None)
        if not user:
            return await call_next(request)
        
        # 检查限流
        session = request.state.db
        allowed, remaining = await check_rate_limit(
            session, 
            user.id, 
            user.daily_limit
        )
        
        if not allowed:
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json"
            )
        
        # 增加计数
        await increment_user_request(session, user.id)
        
        # 添加响应头
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(user.daily_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        response.headers["X-RateLimit-Reset"] = str(
            int((date.today() + timedelta(days=1)).strftime("%s"))
        )
        
        return response
```

### 3. 用户统计报告

```python
async def get_user_usage_report(
    session: AsyncSession,
    user_id: int,
    days: int = 7
) -> dict:
    """获取用户最近N天的使用报告"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    
    result = await session.execute(
        select(UserDailyRequest)
        .where(
            UserDailyRequest.user_id == user_id,
            UserDailyRequest.request_date >= start_date,
            UserDailyRequest.request_date <= end_date
        )
        .order_by(UserDailyRequest.request_date)
    )
    records = result.scalars().all()
    
    # 构建完整的日期序列
    usage_by_date = {r.request_date: r.request_count for r in records}
    complete_data = []
    
    for i in range(days):
        target_date = start_date + timedelta(days=i)
        complete_data.append({
            "date": str(target_date),
            "count": usage_by_date.get(target_date, 0)
        })
    
    total = sum(r.request_count for r in records)
    avg = total / days if days > 0 else 0
    
    return {
        "user_id": user_id,
        "period": {"start": str(start_date), "end": str(end_date)},
        "daily_data": complete_data,
        "statistics": {
            "total": total,
            "average": round(avg, 2),
            "peak": max((r.request_count for r in records), default=0)
        }
    }
```

### 4. 定时任务：每日重置提醒

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def send_daily_reset_notifications(session: AsyncSession):
    """每日重置时发送通知（可选）"""
    # 查询昨日高频用户
    yesterday = date.today() - timedelta(days=1)
    
    result = await session.execute(
        select(UserDailyRequest)
        .where(
            UserDailyRequest.request_date == yesterday,
            UserDailyRequest.request_count > 80  # 接近限额
        )
    )
    high_usage_records = result.scalars().all()
    
    for record in high_usage_records:
        # 发送通知（邮件、站内信等）
        print(f"User {record.user_id} used {record.request_count} requests yesterday")

scheduler = AsyncIOScheduler()
scheduler.add_job(send_daily_reset_notifications, 'cron', hour=0, minute=1)
```

## 与 UsageMetric 的区别

| 特性 | UserDailyRequest | UsageMetric |
|------|------------------|-------------|
| **维度** | 用户+日期 | 全局键值 |
| **粒度** | 每用户每天 | 全局计数器 |
| **用途** | 限流控制 | 系统监控 |
| **数据保留** | 短期（如30天）| 长期累计 |
| **查询频率** | 非常高 | 中等 |
| **示例** | 用户A今日请求50次 | 总请求100万次 |

## 性能优化建议

### 1. 使用数据库原子操作

```python
from sqlalchemy import update

async def atomic_increment_request(
    session: AsyncSession,
    user_id: int
) -> int:
    """原子递增，避免并发问题"""
    today = date.today()
    
    # 尝试更新
    result = await session.execute(
        update(UserDailyRequest)
        .where(
            UserDailyRequest.user_id == user_id,
            UserDailyRequest.request_date == today
        )
        .values(request_count=UserDailyRequest.request_count + 1)
        .returning(UserDailyRequest.request_count)
    )
    
    count = result.scalar_one_or_none()
    
    if count is None:
        # 记录不存在，插入新记录
        record = UserDailyRequest(
            user_id=user_id,
            request_date=today,
            request_count=1
        )
        session.add(record)
        await session.flush()
        count = 1
    
    await session.commit()
    return count
```

### 2. Redis 缓存

```python
import redis.asyncio as redis

class RateLimiterWithCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_and_increment(
        self,
        user_id: int,
        daily_limit: int
    ) -> tuple[bool, int]:
        """使用 Redis 实现高性能限流"""
        today_key = f"rate_limit:{user_id}:{date.today()}"
        
        # 原子递增
        count = await self.redis.incr(today_key)
        
        # 首次创建时设置过期时间（到第二天凌晨）
        if count == 1:
            tomorrow = date.today() + timedelta(days=1)
            expire_seconds = int(tomorrow.strftime("%s")) - int(date.today().strftime("%s"))
            await self.redis.expire(today_key, expire_seconds)
        
        allowed = count <= daily_limit
        remaining = max(0, daily_limit - count)
        
        return allowed, remaining
```

## 相关文件

- [`backend/app/models/user.py`](user.md) - 用户模型
- [`backend/app/models/usage_metric.py`](usage_metric.md) - 全局统计模型
- [`backend/app/services/usage_service.py`](../services/usage_service.md) - 使用统计服务
- [`backend/app/core/dependencies.py`](../core/dependencies.md) - 依赖注入

## 注意事项

1. **时区处理**：确保 `date.today()` 使用正确的时区
2. **并发安全**：高并发场景建议使用 Redis 或数据库原子操作
3. **定期清理**：建议保留 30-90 天数据，定期清理历史记录
4. **索引优化**：为 `(user_id, request_date)` 创建组合索引
5. **限额配置**：不同用户可能有不同的限额，建议关联到用户表
6. **异常处理**：达到限额时提供友好的错误信息和重试时间

---

**文档版本：** 