# backend/app/models/update_log.py - 更新日志模型

## 文件概述

定义系统更新日志的数据模型，用于记录应用的版本更新、新功能发布、bug修复等信息。支持置顶功能，可在管理后台和用户公告中使用。

**文件路径：** `backend/app/models/update_log.py`  
**代码行数：** 18 行  
**复杂度：** ⭐ 简单

## 数据模型定义

### UpdateLog 类

```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from ..db.base import Base

class UpdateLog(Base):
    """更新日志表，供公告与后台管理使用。"""
    
    __tablename__ = "update_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(64))
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

## 字段详解

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `int` | 主键、自增 | 日志唯一标识 |
| `content` | `Text` | 非空 | 更新内容（支持长文本）|
| `created_at` | `datetime` | 服务器时间 | 创建时间（带时区）|
| `created_by` | `String(64)` | 可选 | 创建者用户名 |
| `is_pinned` | `bool` | 默认 False | 是否置顶显示 |

## 数据库表结构

```sql
CREATE TABLE update_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(64),
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE
);

-- 建议创建索引
CREATE INDEX idx_update_logs_created_at ON update_logs(created_at DESC);
CREATE INDEX idx_update_logs_pinned ON update_logs(is_pinned, created_at DESC);
```

## 使用示例

### 1. 创建更新日志

```python
from backend.app.models.update_log import UpdateLog

async def create_update_log(
    session: AsyncSession,
    content: str,
    created_by: str = None,
    is_pinned: bool = False
) -> UpdateLog:
    """创建更新日志"""
    log = UpdateLog(
        content=content,
        created_by=created_by,
        is_pinned=is_pinned
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log
```

### 2. 查询最新日志

```python
from sqlalchemy import select

async def get_latest_logs(
    session: AsyncSession, 
    limit: int = 10
) -> list[UpdateLog]:
    """查询最新的更新日志"""
    result = await session.execute(
        select(UpdateLog)
        .order_by(UpdateLog.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
```

### 3. 查询置顶日志

```python
async def get_pinned_logs(session: AsyncSession) -> list[UpdateLog]:
    """查询所有置顶的更新日志"""
    result = await session.execute(
        select(UpdateLog)
        .where(UpdateLog.is_pinned == True)
        .order_by(UpdateLog.created_at.desc())
    )
    return result.scalars().all()
```

### 4. 置顶/取消置顶

```python
async def toggle_pin(session: AsyncSession, log_id: int) -> UpdateLog:
    """切换日志的置顶状态"""
    log = await session.get(UpdateLog, log_id)
    if not log:
        raise ValueError(f"UpdateLog {log_id} not found")
    
    log.is_pinned = not log.is_pinned
    await session.commit()
    await session.refresh(log)
    return log
```

### 5. 分页查询

```python
async def get_logs_paginated(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20
) -> tuple[list[UpdateLog], int]:
    """分页查询更新日志"""
    # 查询总数
    count_result = await session.execute(
        select(func.count(UpdateLog.id))
    )
    total = count_result.scalar()
    
    # 查询数据
    offset = (page - 1) * page_size
    result = await session.execute(
        select(UpdateLog)
        .order_by(
            UpdateLog.is_pinned.desc(),  # 置顶优先
            UpdateLog.created_at.desc()   # 时间倒序
        )
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()
    
    return logs, total
```

### 6. 删除旧日志

```python
from datetime import timedelta

async def delete_old_logs(
    session: AsyncSession,
    days: int = 180
) -> int:
    """删除指定天数之前的非置顶日志"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = await session.execute(
        delete(UpdateLog)
        .where(
            UpdateLog.created_at < cutoff_date,
            UpdateLog.is_pinned == False
        )
    )
    await session.commit()
    return result.rowcount
```

## 典型应用场景

### 1. 版本更新公告

```python
async def publish_version_update(session: AsyncSession, version: str, features: list[str]):
    """发布版本更新公告"""
    content = f"""
# 版本 {version} 更新

## 新功能
{chr(10).join(f"- {f}" for f in features)}

感谢您的使用！
"""
    await create_update_log(
        session,
        content=content,
        created_by="system",
        is_pinned=True  # 重要更新置顶
    )
```

### 2. Bug 修复通知

```python
async def publish_bugfix(session: AsyncSession, bug_desc: str, fix_desc: str):
    """发布 Bug 修复通知"""
    content = f"""
## Bug 修复

**问题：** {bug_desc}

**解决方案：** {fix_desc}
"""
    await create_update_log(session, content=content, created_by="admin")
```

### 3. 用户端展示

```python
async def get_user_announcements(session: AsyncSession) -> dict:
    """获取用户可见的公告（置顶 + 最新5条）"""
    pinned = await get_pinned_logs(session)
    latest = await get_latest_logs(session, limit=5)
    
    # 去重（置顶可能也在最新中）
    seen_ids = {log.id for log in pinned}
    latest_unique = [log for log in latest if log.id not in seen_ids]
    
    return {
        "pinned": pinned,
        "latest": latest_unique
    }
```

## 内容格式建议

### Markdown 格式

```markdown
# 版本 1.2.0 更新

## 新功能
- 支持章节版本管理
- 新增灵感模式

## 优化
- 提升写作速度 30%
- 改进 UI 交互体验

## Bug 修复
- 修复章节保存失败的问题
```

### 纯文本格式

```
【版本更新】v1.2.0

新功能：
- 章节版本管理
- 灵感模式

优化：
- 写作速度提升
- UI 体验改进
```

## 相关文件

- [`backend/app/repositories/update_log_repository.py`](../repositories/update_log_repository.md) - 数据访问层
- [`backend/app/services/update_log_service.py`](../services/update_log_service.md) - 业务逻辑层
- [`backend/app/api/routers/update_logs.py`](../api/routers/update_logs.md) - API 路由（如果存在）

## 注意事项

1. **时区处理**：`created_at` 使用 `DateTime(timezone=True)`，确保时区一致性
2. **内容长度**：使用 `Text` 类型，支持长文本（建议单条不超过 10KB）
3. **置顶数量**：建议限制置顶日志数量（如不超过 3 条），避免刷屏
4. **权限控制**：创建、置顶、删除操作应限制管理员权限
5. **定期清理**：建议定期清理旧日志，避免表过大

## 扩展建议

### 1. 添加分类字段

```python
category: Mapped[str] = mapped_column(
    String(20), 
    default="general"
)  # general, feature, bugfix, announcement
```

### 2. 添加版本号字段

```python
version: Mapped[str | None] = mapped_column(String(20))
```

### 3. 支持多语言

```python
lang: Mapped[str] = mapped_column(String(5), default="zh-CN")
```

---

**文档版本：** v1.0.0  
**最后更新：** 2025-11-06