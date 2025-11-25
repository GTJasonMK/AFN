# Base Repository - 通用仓储基类

## 文件概述

**文件路径**: `backend/app/repositories/base.py`  
**代码行数**: 44行  
**核心职责**: 通用仓储基类，封装常见的增删改查操作，使用泛型支持任意数据模型

## 核心功能

### 1. 查询单个实体

```python
async def get(self, **filters: Any) -> Optional[ModelType]
```

**使用示例**：
```python
# 按ID查询
user = await user_repo.get(id=1)

# 按用户名查询
user = await user_repo.get(username="john")

# 多条件查询
config = await llm_config_repo.get(user_id=1, is_active=True)
```

### 2. 查询列表

```python
async def list(self, *, filters: Optional[dict[str, Any]] = None) -> Iterable[ModelType]
```

**使用示例**：
```python
# 查询所有
all_users = await user_repo.list()

# 带过滤条件
active_users = await user_repo.list(filters={"is_active": True})
admin_users = await user_repo.list(filters={"is_admin": True})
```

### 3. 添加实体

```python
async def add(self, instance: ModelType) -> ModelType
```

**使用示例**：
```python
# 创建新用户
new_user = User(username="john", email="john@example.com")
await user_repo.add(new_user)
await session.commit()  # 需要在外部commit
```

### 4. 删除实体

```python
async def delete(self, instance: ModelType) -> None
```

**使用示例**：
```python
user = await user_repo.get(id=1)
if user:
    await user_repo.delete(user)
    await session.commit()
```

### 5. 更新字段

```python
async def update_fields(self, instance: ModelType, **values: Any) -> ModelType
```

**特性**：
- 跳过None值
- 使用flush而不是commit

**使用示例**：
```python
user = await user_repo.get(id=1)
await user_repo.update_fields(
    user,
    email="new@example.com",
    is_active=True
)
await session.commit()
```

## 使用模式

### 基本继承

```python
from .base import BaseRepository
from ..models import User

class UserRepository(BaseRepository[User]):
    model = User
    
    # 可以添加自定义方法
    async def get_by_username(self, username: str):
        # 自定义查询逻辑
        pass
```

### 完整示例

```python
async def user_management_example():
    # 创建
    user = User(username="john", email="john@example.com")
    await user_repo.add(user)
    await session.commit()
    
    # 查询
    found_user = await user_repo.get(username="john")
    
    # 更新
    await user_repo.update_fields(found_user, email="new@example.com")
    await session.commit()
    
    # 列表
    all_users = await user_repo.list()
    
    # 删除
    await user_repo.delete(found_user)
    await session.commit()
```

## 设计特点

### 泛型支持

```python
ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    model: type[ModelType]
```

### Flush vs Commit

- **flush**: 将更改发送到数据库，但不提交事务
- **commit**: 在Service层统一管理事务

### 过滤器使用

```python
# 使用filter_by进行简单过滤
stmt = select(self.model).filter_by(**filters)
```

## 相关文档

- **服务层**: [`backend/app/services/`](../services/)
- **数据模型**: [`backend/app/models/`](../models/)