# backend/app/models/usage_metric.py - 使用统计模型

## 文件概述

定义通用计数器的数据模型，用于记录各种统计数据，如 API 请求次数、功能使用次数等。采用简单的键值对结构，值为整数类型，支持增量操作。

**文件路径：** `backend/app/models/usage_metric.py`  
**代码行数：** 13 行  
**复杂度：** ⭐ 简单

## 数据模型定义

### UsageMetric 类

```python
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from ..db.base import Base

class UsageMetric(Base):
    """通用计数器表，目前用于记录 API 请求次数等统计数据。"""
    
    __tablename__ = "usage_metrics"
    
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

## 字段详解

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `key` | `String(64)` | 主键 | 统计项名称 |
| `value` | `int` | 非空、默认0 | 统计计数值 |

## 数据库表结构

```sql
CREATE TABLE usage_metrics (
    key VARCHAR(64) PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);
```

## 统计项类型

### 1. API 请求统计

| Key | 说明 |
|-----|------|
| `api.requests.total` | 总请求次数 |
| `api.requests.today` | 今日请求次数 |
| `api.requests.novels` | 小说相关请求 |
| `api.requests.writer` | 写作相关请求 |
| `api.requests.llm` | LLM 调用次数 |

### 2. 功能使用统计

| Key | 说明 |
|-----|------|
| `feature.outline.generated` | 生成大纲次数 |
| `feature.chapter.written` | 写作章节次数 |
| `feature.concept.extracted` | 提取概念次数 |
| `feature.evaluation.done` | 评估次数 |

### 3. 用户行为统计

| Key | 说明 |
|-----|------|
| `user.registrations` | 注册用户数 |
| `user.active.daily` | 日活跃用户 |
| `user.active.monthly` | 月活跃用户 |

### 4. 错误统计

| Key | 说明 |
|-----|------|
| `error.llm.timeout` | LLM 超时次数 |
| `error.llm.rate_limit` | 速率限制次数 |
| `error.db.connection` | 数据库连接错误 |

## 使用示例

### 1. 增加计数

```python
from backend.app.models.usage_metric import UsageMetric
from sqlalchemy import select

async def increment_metric(session: AsyncSession, key: str, amount: int = 1) -> int:
    """增加指定统计项的计数"""
    metric = await session.get(UsageMetric, key)
    
    if metric:
        metric.value += amount
    else:
        metric = UsageMetric(key=key, value=amount)
        session.add(metric)
    
    await session.commit()
    await session.refresh(metric)
    return metric.value
```

### 2. 查询计数

```python
async def get_metric(session: AsyncSession, key: str) -> int:
    """查询指定统计项的计数"""
    metric = await session.get(UsageMetric, key)
    return metric.value if metric else 0
```

### 3. 重置计数

```python
async def reset_metric(session: AsyncSession, key: str):
    """重置指定统计项为 0"""
    metric = await session.get(UsageMetric, key)
    if metric:
        metric.value = 0
        await session.commit()
```

### 4. 批量查询

```python
async def get_metrics_by_prefix(session: AsyncSession, prefix: str) -> dict[str, int]:
    """按前缀批量查询统计项"""
    result = await session.execute(
        select(UsageMetric).where(UsageMetric.key.like(f"{prefix}%"))
    )
    metrics = result.scalars().all()
    return {m.key: m.value for m in metrics}
```

### 5. 原子递增（使用数据库级别操作）

```python
from sqlalchemy import update

async def atomic_increment(session: AsyncSession, key: str, amount: int = 1) -> int:
    """原子递增，避免并发问题"""
    # 先尝试更新
    result = await session.execute(
        update(UsageMetric)
        .where(UsageMetric.key == key)
        .values(value=UsageMetric.value + amount)
        .returning(UsageMetric.value)
    )
    updated_value = result.scalar_one_or_none()
    
    if updated_value is None:
        # 记录不存在，创建新记录
        metric = UsageMetric(key=key, value=amount)
        session.add(metric)
        await session.flush()
        return amount
    
    await session.commit()
    return updated_value
```

## 典型应用场景

### 1. API 请求中间件

```python
from fastapi import Request

async def track_request(request: Request, session: AsyncSession):
    """追踪 API 请求"""
    # 总请求数
    await atomic_increment(session, "api.requests.total")
    
    # 按路径统计
    path_key = f"api.requests.{request.url.path.replace('/', '.')}"
    await atomic_increment(session, path_key)
    
    # 按用户统计
    if hasattr(request.state, "user"):
        user_key = f"user.{request.state.user.id}.requests"
        await atomic_increment(session, user_key)
```

### 2. 功能使用追踪

```python
async def track_feature_usage(session: AsyncSession, feature: str):
    """追踪功能使用"""
    await atomic_increment(session, f"feature.{feature}.used")
```

### 3. 统计仪表板

```python
async def get_dashboard_stats(session: AsyncSession) -> dict:
    """获取仪表板统计数据"""
    api_stats = await get_metrics_by_prefix(session, "api.requests.")
    feature_stats = await get_metrics_by_prefix(session, "feature.")
    user_stats = await get_metrics_by_prefix(session, "user.")
    
    return {
        "api": api_stats,
        "features": feature_stats,
        "users": user_stats,
        "total_requests": await get_metric(session, "api.requests.total"),
    }
```

### 4. 定时任务：每日重置

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def reset_daily_metrics(session: AsyncSession):
    """每日重置统计"""
    daily_keys = [
        "api.requests.today",
        "user.active.daily",
    ]
    for key in daily_keys:
        await reset_metric(session, key)

# 配置定时任务（每天 00:00 执行）
scheduler = AsyncIOScheduler()
scheduler.add_job(reset_daily_metrics, 'cron', hour=0, minute=0)
```

### 5. LLM 调用统计

```python
async def track_llm_call(session: AsyncSession, model: str, tokens: int):
    """追踪 LLM 调用"""
    await atomic_increment(session, "api.requests.llm")
    await atomic_increment(session, f"llm.{model}.calls")
    await atomic_increment(session, f"llm.{model}.tokens", tokens)
```

## 性能优化

### 1. 批量递增

```python
async def batch_increment(session: AsyncSession, increments: dict[str, int]):
    """批量递增多个统计项"""
    for key, amount in increments.items():
        await atomic_increment(session, key, amount)
    await session.commit()
```

### 2. 缓存热点数据

```python
from functools import lru_cache
from datetime import datetime, timedelta

class MetricCache:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
    
    async def get_cached(self, session: AsyncSession, key: str, ttl: int = 60) -> int:
        """带缓存的查询"""
        now = datetime.utcnow()
        
        if key in self.cache:
            if now - self.cache_time[key] < timedelta(seconds=ttl):
                return self.cache[key]
        
        value = await get_metric(session, key)
        self.cache[key] = value
        self.cache_time[key] = now
        return value
```

### 3. 异步写入队列

```python
import asyncio
from collections import defaultdict

class MetricQueue:
    def __init__(self, session: AsyncSession, flush_interval: int = 10):
        self.session = session
        self.queue = defaultdict(int)
        self.flush_interval = flush_interval
        self.task = None
    
    def increment(self, key: str, amount: int = 1):
        """加入队列"""
        self.queue[key] += amount
    
    async def flush(self):
        """批量写入数据库"""
        if not self.queue:
            return
        
        increments = dict(self.queue)
        self.queue.clear()
        
        await batch_increment(self.session, increments)
    
    async def start(self):
        """启动定时刷新"""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()
```

## 相关文件

- [`backend/app/repositories/usage_metric_repository.py`](../repositories/usage_metric_repository.md) - 数据访问层
- [`backend/app/services/usage_service.py`](../services/usage_service.md) - 业务逻辑层
- [`backend/app/models/user_daily_request.py`](user_daily_request.md) - 用户日请求统计（更细粒度）

## 与 UserDailyRequest 的区别

| 特性 | UsageMetric | UserDailyRequest |
|------|-------------|------------------|
| **粒度** | 全局统计 | 按用户+日期统计 |
| **用途** | 系统级监控 | 用户限流控制 |
| **数据类型** | 计数器 | 用户维度+日期维度 |
| **示例** | 总请求数 | 某用户今日请求数 |

## 注意事项

1. **并发安全**：使用 `atomic_increment` 避免并发写入冲突
2. **Key 命名**：使用有意义的前缀，如 `api.`, `feature.`, `user.`
3. **定期清理**：考虑定期归档或清理历史数据
4. **性能考虑**：高频统计项建议使用缓存或队列
5. **监控告警**：对关键指标设置阈值告警

---

**文档版本：** v1.0.0  
**最后更新：** 2025-11-06