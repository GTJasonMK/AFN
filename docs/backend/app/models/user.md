
# backend/app/models/user.py - 用户模型

## 文件概述

定义用户账户的数据模型，存储用户的基本信息、认证凭据和权限状态。在桌面版中，默认使用单一的 `desktop_user`。

**文件路径：** `backend/app/models/user.py`  
**代码行数：** 31 行  
**复杂度：** ⭐⭐ 简单

## 数据模型定义

### User 类

```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

class User(Base):
    """用户主表，记录账号及权限信息。"""
    
    __tablename__ = "users"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # 基本信息
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    
    # 状态标志
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # 关系映射
    novel_projects: Mapped[list["NovelProject"]] = relationship(
        "NovelProject", 
        back_populates="owner"
    )
    llm_configs: Mapped[list["LLMConfig"]] = relationship(
        "LLMConfig", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
```

## 字段详解

### 主键

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `Integer` | 主键，索引 | 用户唯一标识符 |

### 基本信息

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `username` | `String(64)` | 唯一，非空，索引 | 用户名 |
| `email` | `String(128)` | 唯一，可选 | 电子邮箱 |
| `hashed_password` | `String(255)` | 非空 | 密码哈希 |
| `external_id` | `String(255)` | 唯一，可选 | 第三方登录 ID |

**字段说明：**

**username：**
- 用户登录名
- 全局唯一
- 桌面版默认：`desktop_user`

**email：**
- 用户邮箱
- 用于密码重置、通知等
- 桌面版可为空

**hashed_password：**
- 密码的哈希值（非明文）
- 使用 bcrypt 或 argon2 加密
- 桌面版虽然存储但不使用

**external_id：**
- 第三方登录的用户 ID
- 如 Linux.do OAuth 的用户 ID
- 桌面版不使用

### 状态标志

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| `is_admin` | `Boolean` | 非空 | `False` | 是否为管理员 |
| `is_active` | `Boolean` | 非空 | `True` | 账户是否激活 |

**状态组合：**

```python
is_admin=True, is_active=True   # 激活的管理员
is_admin=False, is_active=True  # 激活的普通用户（桌面版）
is_admin=False, is_active=False # 停用的账户
```

### 时间戳

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `created_at` | `DateTime(TZ)` | 非空 | 账户创建时间 |
| `updated_at` | `DateTime(TZ)` | 非空 | 最后更新时间 |

**自动管理：**
- `created_at`：使用 `server_default=func.now()`
- `updated_at`：使用 `onupdate=func.now()`

## 关系映射

### 1. 与 NovelProject 的关系

```python
novel_projects: Mapped[list["NovelProject"]] = relationship(
    "NovelProject", 
    back_populates="owner"
)
```

**关系类型：** 一对多（One-to-Many）

```
User (1) ←──────→ (N) NovelProject
```

**说明：**
- 一个用户可以创建多个小说项目
- 每个项目属于一个用户

### 2. 与 LLMConfig 的关系

```python
llm_configs: Mapped[list["LLMConfig"]] = relationship(
    "LLMConfig", 
    back_populates="user", 
    cascade="all, delete-orphan"
)
```

**关系类型：** 一对多（One-to-Many）

```
User (1) ←──────→ (N) LLMConfig
```

**级联删除：**
- 删除用户时，自动删除其所有 LLM 配置
- `cascade="all, delete-orphan"`

## 数据库表结构

### 表定义

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(128) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    external_id VARCHAR(255) UNIQUE,
    is_admin BOOLEAN NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_users_id ON users(id);
CREATE INDEX ix_users_username ON users(username);
CREATE UNIQUE INDEX uq_users_email ON users(email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX uq_users_external_id ON users(external_id) WHERE external_id IS NOT NULL;
```

### 索引

| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| `PRIMARY` | `id` | 主键 | 唯一标识 |
| `ix_users_id` | `id` | 普通索引 | 快速查找 |
| `ix_users_username` | `username` | 唯一索引 | 用户名查询 |
| `uq_users_email` | `email` | 唯一索引 | 邮箱查询 |
| `uq_users_external_id` | `external_id` | 唯一索引 | 第三方ID查询 |

## 使用示例

### 1. 创建用户（桌面版）

```python
from backend.app.models.user import User
from backend.app.core.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession

async def create_desktop_user(session: AsyncSession) -> User:
    """创建默认桌面用户"""
    user = User(
        username="desktop_user",
        email="desktop@example.com",
        hashed_password=hash_password("desktop"),
        is_admin=False,  # 桌面版不需要管理员
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
```

### 2. 创建用户（Web 版）

```python
async def create_user(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
) -> User:
    """创建新用户"""
    from backend.app.core.security import hash_password
    
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        is_admin=False,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
```

### 3. 查询用户

```python
from sqlalchemy import select

async def get_user_by_username(
    session: AsyncSession, 
    username: str
) -> Optional[User]:
    """根据用户名查询用户"""
    result = await session.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()

async def get_user_by_email(
    session: AsyncSession, 
    email: str
) -> Optional[User]:
    """根据邮箱查询用户"""
    result = await session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()

async def get_user_by_id(
    session: AsyncSession, 
    user_id: int
) -> Optional[User]:
    """根据 ID 查询用户"""
    return await session.get(User, user_id)
```

### 4. 验证密码

```python
from backend.app.core.security import verify_password

async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> Optional[User]:
    """验证用户名和密码"""
    user = await get_user_by_username(session, username)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if not user.is_active:
        return None
    
    return user
```

### 5. 更新用户信息

```python
async def update_user(
    session: AsyncSession,
    user_id: int,
    **updates
) -> User:
    """更新用户信息"""
    user = await session.get(User, user_id)
    
    for key, value in updates.items():
        if hasattr(user, key) and key != 'id':
            setattr(user, key, value)
    
    await session.commit()
    await session.refresh(user)
    return user
```

### 6. 删除用户

```python
async def delete_user(session: AsyncSession, user_id: int):
    """删除用户（级联删除相关数据）"""
    user = await session.get(User, user_id)
    await session.delete(user)
    await session.commit()
```

### 7. 查询用户的项目

```python
async def get_user_projects(session: AsyncSession, user_id: int):
    """查询用户的所有小说项目"""
    user = await session.get(User, user_id)
    # 使用关系映射
    return user.novel_projects
```

## 桌面版特殊处理

### 默认用户

桌面版使用固定的默认用户：

```python
# backend/app/db/init_db.py

async def init_db():
    async with AsyncSessionLocal() as session:
        # 检查是否存在默认桌面用户
        desktop_user_exists = await session.execute(
            select(User).where(User.username == "desktop_user")
        )
        
        if not desktop_user_exists.scalars().first():
            desktop_user = User(
                username="desktop_user",
                email="desktop@example.com",
                hashed_password=hash_password("desktop"),
                is_admin=False,
            )
            session.add(desktop_user)
            await session.commit()
```

### 获取默认用户

```python
# backend/app/core/dependencies.py

async def get_default_user(
    session: AsyncSession = Depends(get_session)
) -> User:
    """桌面版：返回默认用户"""
    result = await session.execute(
        select(User).where(User.username == "desktop_user")
    )
    return result.scalar_one()
```

### 在 API 中使用

```python
from backend.app.core.dependencies import get_default_user

@router.get("/novels/")
async def list_novels(
    user: User = Depends(get_default_user),
    session: AsyncSession = Depends(get_session)
):
    """桌面版自动使用 desktop_user"""
    result = await session.execute(
        select(NovelProject).where(NovelProject.user_id == user.id)
    )
    return result.scalars().all()
```

## 安全考虑

### 1. 密码哈希

⚠️ **永远不要存储明文密码**

```python
from backend.app.core.security import hash_password, verify_password

# 创建用户时
hashed = hash_password("user_password")
user = User(username="john", hashed_password=hashed)

# 验证密码时
if verify_password("user_password", user.hashed_password):
    print("密码正确")
```

### 2. 敏感信息脱敏

在日志和 API 响应中隐藏敏感信息：

```python
class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: datetime
    
    # ❌ 不要包含 hashed_password
    # hashed_password: str
```

### 3. SQL 注入防护

使用 SQLAlchemy ORM 自动防止 SQL 注入：

```python
# ✅ 安全：使用参数化查询
result = await session.execute(
    select(User).where(User.username == username)
)

# ❌ 危险：字符串拼接
# query = f"SELECT * FROM users WHERE username = '{username}'"
```

## Web 版 vs 桌面版

### Web 版特性

```python
# 用户注册
@router.post("/register")
async def register(data: UserCreate):
    user = await create_user(session, data)
    return user

# 用户登录
@router.post("/login")
async def login(credentials: LoginRequest):
    user = await authenticate_user(session, credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id)
    return {"access_token": token}

# 权限检查
@router.get("/admin/users")
async def list_all_users(current_user: User = Depends(get_current_admin)):
    # 只有管理员可以访问
    pass
```

### 桌面版特性

```python
# 无需注册和登录
# 直接使用默认用户

@router.get("/novels/")
async def list_novels(
    user: User = Depends(get_default_user)  # 自动注入 desktop_user
):
    # 所有操作都归属于 desktop_user
    pass
```

## 相关文件

### 安全模块
- [`backend/app/core/security.py`](../core/security.md) - 密码哈希和验证
- [`backend/app/core/dependencies.py`](../core/dependencies.md) - 用户依赖注入

### 数据模型
- [`backend/app/models/novel.py`](novel.md) - 小说项目模型
- [`backend/app/models/llm_config.py`](llm_config.md) - LLM 配置模型

### 数据库
- [`backend/app/db/init_db.py`](../db/init_db.md) - 创建默认用户

### Schema
- [`backend/app/schemas/user.py`](../schemas/user.md) - 用户 Schema

## 最佳实践

### 1. 密码强度

```python
def validate_password_strength(password: str) -> bool:
    """验证密码强度"""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True
```

### 2. 用户名规范

```python
import re

def validate_username(username: str) -> bool:
    """验证用户名格式"""
    # 