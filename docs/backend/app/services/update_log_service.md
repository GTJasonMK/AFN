
# Update Log Service - 更新日志服务

## 文件概述

**文件路径**: `backend/app/services/update_log_service.py`  
**代码行数**: 60行  
**核心职责**: 更新日志服务，提供增删改查能力，并保证置顶唯一性

## 核心功能

### 1. 查询日志列表

```python
async def list_logs(self, limit: Optional[int] = None) -> List[UpdateLog]
```

**使用示例**：
```python
update_log_service = UpdateLogService(session)

# 获取所有日志
all_logs = await update_log_service.list_logs()

# 获取最新的10条日志
latest_logs = await update_log_service.list_logs(limit=10)

for log in latest_logs:
    print(f"[{log.created_at}] {log.content}")
    if log.is_pinned:
        print("📌 置顶")
```

### 2. 创建日志

```python
async def create_log(
    self,
    content: str,
    creator: str | None = None,
    *,
    is_pinned: bool = False
) -> UpdateLog
```

**特性**：
- 如果设置为置顶，自动取消其他日志的置顶状态
- 保证系统中只有一条置顶日志

**使用示例**：
```python
# 创建普通更新日志
log = await update_log_service.create_log(
    content="修复了章节生成的bug",
    creator="admin"
)

# 创建置顶日志（重要公告）
pinned_log = await update_log_service.create_log(
    content="🎉 系统已升级到v2.0，新增AI智能分析功能",
    creator="admin",
    is_pinned=True
)
# 注意：如果之前有置顶日志，会被自动取消置顶

# 创建版本更新日志
version_log = await update_log_service.create_log(
    content="""
    v2.1.0 更新内容：
    - 新增：DeepSeek R1模型支持
    - 优化：章节生成速度提升30%
    - 修复：向量检索偶发失败的问题
    """,
    creator="system"
)
```

### 3. 更新日志

```python
async def update_log(
    self,
    log_id: int,
    *,
    content: Optional[str] = None,
    is_pinned: Optional[bool] = None
) -> UpdateLog
```

**特性**：
- 支持部分更新
- 设置为置顶时自动取消其他置顶

**使用示例**：
```python
# 仅更新内容
updated_log = await update_log_service.update_log(
    log_id=1,
    content="修复了章节生成的bug（已验证）"
)

# 仅更新置顶状态
await update_log_service.update_log(
    log_id=2,
    is_pinned=True
)

# 同时更新内容和置顶状态
await update_log_service.update_log(
    log_id=3,
    content="【重要公告】系统维护通知",
    is_pinned=True
)

# 取消置顶
await update_log_service.update_log(
    log_id=3,
    is_pinned=False
)
```

### 4. 删除日志

```python
async def delete_log(self, log_id: int) -> None
```

**使用示例**：
```python
# 删除指定日志
try:
    await update_log_service.delete_log(log_id=5)
    print("日志已删除")
except HTTPException as e:
    print(f"删除失败: {e.detail}")  # "更新记录不存在"
```

## 完整使用示例

