
# backend/app/db/session.py - 数据库会话管理

## 文件概述

负责创建和配置 SQLAlchemy 异步引擎和会话工厂，针对不同数据库后端（SQLite/MySQL）提供优化的连接池配置。该文件是所有数据库操作的基础设施层。

**文件路径：** `backend/app/db/session.py`  
**代码行数：** 30 行  
**复杂度：** ⭐⭐ 中等

## 核心组件

### 1. 异步引擎（engine）

```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

engine_kwargs = {"echo": settings.debug}

if settings.is_sqlite_backend:
    # SQLite 配置
    engine_kwargs.update(
        pool_pre_ping=False,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
else:
    # MySQL 配置
    engine_kwargs.update(
        pool_pre_ping=True, 
        pool_recycle=3600
    )

engine = create_async_engine(settings.sqlalchemy_database_uri, **engine_kwargs)
```

**功能：**
- 创建异步数据库引擎
- 根据数据库类型自动配置连接池
- 支持调试模式下的 SQL 日志

### 2. 会话工厂（AsyncSessionLocal）

```python
from sqlalchemy.ext.asyncio import async_sessionmaker

AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False
)
```

**功能：**
- 创建异步会话工厂
- 禁用提交后对象过期（`expire_on_commit=False`）
- 绑定到异步引擎

### 3. 会话依赖（get_session）

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖项：提供一个作用域内共享的数据库会话。"""
    async with AsyncSessionLocal() as session:
        yield session
```

**功能：**
- FastAPI 依赖注入函数
- 自动管理会话生命周期
- 确保会话正确关闭

## 配置详解

### SQLite 配置

```python
if settings.is_sqlite_backend:
    engine_kwargs.update(
        pool_pre_ping=False,              # 禁用连接预检
        connect_args={"check_same_thread": False},  # 允许多线程访问
        poolclass=NullPool,               # 禁用连接池
    )
```

**配置原因：**

| 配置项 | 值 | 原因 |
|--------|-----|------|
| `pool_pre_ping` | `False` | SQLite 不需要检查连接有效性 |
| `check_same_thread` | `False` | 允许异步环境多协程访问 |
| `poolclass` | `NullPool` | 避免连接池冲突，每次创建新连接 |

**SQLite 特点：**
- 文件数据库，无网络连接
- 不支持真正的并发写入
- 适合开发和桌面应用

### MySQL 配置

```python
else:
    engine_kwargs.update(
        pool_pre_ping=True,    # 启用连接预检
        pool_recycle=3600      # 1小时回收连接
    )
```

**配置原因：**

| 配置项 | 值 | 原因 |
|--------|-----|------|
| `pool_pre_ping` | `True` | 检查连接是否仍然有效 |
| `pool_recycle` | `3600` | 防止连接超时（MySQL 默认 8 小时） |

**MySQL 特点：**
- 网络数据库服务器
- 支持真正的并发
- 连接可能超时或断开

## 使用示例

### 1. 在 FastAPI 路由中使用

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session
from backend.app.models import Novel

router = APIRouter()

@router.get("/novels/{novel_id}")
async def get_novel(
    novel_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取小说详情"""
    result = await session.execute(
        select(Novel).where(Novel.id == novel_id)
    )
    novel = result.scalar_one_or_none()
    return novel
```

### 2. 在服务层中使用

```python
from sqlalchemy.ext.asyncio import AsyncSession

class NovelService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_novel(self, title: str) -> Novel:
        """创建新小说"""
        novel = Novel(title=title)
        self.session.add(novel)
        await self.session.commit()
        await self.session.refresh(novel)
        return novel
```

### 3. 直接创建会话

```python
from backend.app.db.session import AsyncSessionLocal

async def some_background_task():
    """后台任务示例"""
    async with AsyncSessionLocal() as session:
        # 执行数据库操作
        result = await session.execute(select(Novel))
        novels = result.scalars().all()
        
        # 会话会自动关闭
```

### 4. 在应用启动时使用

```python
from backend.app.db.session import AsyncSessionLocal
from backend.app.services.prompt_service import PromptService

async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时预加载数据
    async with AsyncSessionLocal() as session:
        prompt_service = PromptService(session)
        await prompt_service.preload()
    yield
```

## 异步会话特性

### 1. expire_on_commit=False

```python
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False  # 关键配置
)
```

**作用：**
- 默认情况下，`commit()` 后对象会过期
- 设为 `False` 后，对象在提交后仍可访问
- 适合需要返回已提交对象的场景

**示例：**

```python
# expire_on_commit=True (默认)
async with AsyncSessionLocal() as session:
    novel = Novel(title="Test")
    session.add(novel)
    await session.commit()
    # ❌ 这里访问 novel.title 会触发新查询
    print(novel.title)

# expire_on_commit=False (当前配置)
async with AsyncSessionLocal() as session:
    novel = Novel(title="Test")
    session.add(novel)
    await session.commit()
    # ✅ 可以直接访问，不会触发查询
    print(novel.title)
```

### 2. 自动会话管理

使用上下文管理器自动关闭会话：

```python
async with AsyncSessionLocal() as session:
    # 执行操作
    pass
# 会话自动关闭，即使发生异常
```

等价于：

```python
session = AsyncSessionLocal()
try:
    # 执行操作
    pass
finally:
    await session.close()
```

## 连接池配置

### SQLite - NullPool

```python
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    database_uri,
    poolclass=NullPool  # 每次创建新连接
)
```

**特点：**
- 不维护连接池
- 每次请求创建新连接
- 使用后立即关闭连接
- 避免 SQLite 的并发问题

**适用场景：**
- 桌面应用
- 单用户环境
- 开发环境

### MySQL - 默认连接池

```python
engine = create_async_engine(
    database_uri,
    pool_pre_ping=True,     # 使用前检查连接
    pool_recycle=3600       # 1小时回收
)
```

**默认连接池参数：**
- `pool_size=5`：默认连接数
- `max_overflow=10`：最大溢出连接数
- `pool_timeout=30`：获取连接超时时间

**工作原理：**
```
连接池 (pool_size=5)
┌─────┬─────┬─────┬─────┬─────┐
│ C1  │ C2  │ C3  │ C4  │ C5  │
└─────┴─────┴─────┴─────┴─────┘
        ↓
    可复用连接
        
溢出连接 (max_overflow=10)
需要时临时创建，用完销毁
```

## 调试配置

### echo 参数

```python
engine_kwargs = {"echo": settings.debug}
```

**作用：**
- `echo=True`：打印所有 SQL 语句
- `echo=False`：不打印 SQL

**调试输出示例：**
```
2025-11-06 17:00:00 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2025-11-06 17:00:00 INFO sqlalchemy.engine.Engine SELECT novel.id, novel.title FROM novel WHERE novel.id = ?
2025-11-06 17:00:00 INFO sqlalchemy.engine.Engine [generated in 0.00010s] (1,)
2025-11-06 17:00:00 INFO sqlalchemy.engine.Engine COMMIT
```

### 启用 SQL 日志

在配置文件中设置：

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    debug: bool = True  # 启用 SQL 日志
```

## 事务管理

### 1. 自动提交

```python
async with AsyncSessionLocal() as session:
    novel = Novel(title="Test")
    session.add(novel)
    await session.commit()  # 显式提交
```

### 2. 自动回滚

```python
async with AsyncSessionLocal() as session:
    try:
        novel = Novel(title="Test")
        session.add(novel)
        await session.commit()
    except Exception:
        await session.rollback()  # 回滚事务
        raise
```

### 3. 嵌套事务

```python
async with AsyncSessionLocal() as session:
    async with session.begin():
        # 嵌套事务
        novel = Novel(title="Test")
        session.add(novel)
    # 自动提交或回滚
```

## 性能优化

### 1. 批量操作

```python
async with AsyncSessionLocal() as session:
    novels = [Novel(title=f"Novel {i}") for i in range(100)]
    session.add_all(novels)  # 批量添加
    await session.commit()   # 一次性提交
```

### 2. 查询优化

```python
from sqlalchemy.orm import selectinload

async with AsyncSessionLocal() as session:
    result = await session.execute(
        select(Novel)
        .options(selectinload(Novel.outlines))  # 预加载关联
        .where(Novel.status == "draft")
    )
    novels = result.scalars().all()
```

### 3. 连接池监控

```python
from backend.app.db.session import engine

# 查看连接池状态
pool = engine.pool
print(f"Size: {pool.size()}")
print(f"Checked out: {pool.checkedout()}")
print(f"Overflow: {pool.overflow()}")
```

## 与项目集成

### 1. 在依赖注入中使用

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session

async def get_current_user(
    session: AsyncSession = Depends(get_session)
):
    # 使用会话查询用户
    pass
```

### 2. 在仓储层使用

```python
from backend.app.db.session import AsyncSessionLocal

class NovelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def find_by_id(self, novel_id: int) -> Optional[Novel]:
        result = await self.session.execute(
            select(Novel).where(Novel.id == novel_id)
        )
        return result.scalar_one_or_none()
```

### 3. 在初始化中使用

```python
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.base import Base

async def init_db():
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 插入初始数据
    async with AsyncSessionLocal() as session:
        # 初始化操作
        pass
```

## 相关文件

### 数据库相关
- [`backend/app/db/base.py`](base.md) - ORM 基类
- [`backend/app/db/init_db.py`](init_db.md) - 数据库初始化
- [`backend/app/core/config.py`](../core/config.md) - 数据库配置

### 使用该会话的文件
- [`backend/app/api/routers/novels.py`](../api/routers/novels.md) - 小说 API
- [`backend/app/services/novel_service.py`](../services/novel_service.md) - 小说服务
- [`backend/app/repositories/novel_repository.py`](../repositories/novel_repository.md) - 小说仓储

## 注意事项

### 1. SQLite 并发限制

⚠️ **SQLite 不支持真正的并发写入**

```python
# ❌ 可能导致数据库锁定
async def write_concurrent():
    tasks = [write_to_db() for _ in range(10)]
    await asyncio.gather(*tasks)  # 并发写入可能失败
```

**解决方案：**
- 使用队列串行化写入
- 或切换到 MySQL

### 2. 会话生命周期

⚠️ **不要跨请求共享会话**

```python
# ❌ 错误：全局会话
global_session = AsyncSessionLocal()

@router.get("/novels")
async def get_novels():
    # 不要使用全局会话
    return await global_session.execute(select(Novel))
```

```python
# ✅ 正确：每个请求一个会话
@router.get("/novels")
async def get_novels(session: AsyncSession = Depends(get_session)):
    return await session.execute(select(Novel))
```

### 3. 异步上下文

⚠️ **必须使用 async with**

```python
# ❌ 错误：忘记 await
session = AsyncSessionLocal()
result = session.execute(select(Novel))  # 返回协程对象

# ✅ 正确：使用 async with 和 await
async with AsyncSessionLocal