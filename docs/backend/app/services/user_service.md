# User Service - 用户领域服务

## 文件概述

**文件路径**: `backend/app/services/user_service.py`  
**代码行数**: 62行  
**核心职责**: 用户领域服务，负责用户注册、查询与每日请求配额统计

## 核心功能

### 1. 创建用户

```python
async def create_user(
    self, 
    payload: UserCreate, 
    *, 
    external_id: str | None = None
) -> UserInDB
```

**使用示例**：
```python
from backend.app.schemas.user import UserCreate

user_service = UserService(session)

# 创建普通用户
try:
    user = await user_service.create_user(
        UserCreate(
            username="newuser",
            email="user@example.com",
            password="SecurePass123"
        )
    )
    print(f"用户创建成功: {user.username}")
except ValueError as e:
    print(f"创建失败: {e}")  # "用户名或邮箱已存在"

# 创建OAuth用户
oauth_user = await user_service.create_user(
    UserCreate(
        username="oauth_user",
        email="oauth@example.com",
        password="random_placeholder"
    ),
    external_id="github:12345"
)
```

### 2. 用户查询

#### 按用户名查询

```python
async def get_by_username(self, username: str) -> Optional[UserInDB]
```

**使用示例**：
```python
user = await user_service.get_by_username("john_doe")
if user:
    print(f"用户ID: {user.id}")
    print(f"邮箱: {user.email}")
    print(f"管理员: {user.is_admin}")
```

#### 按邮箱查询

```python
async def get_by_email(self, email: str) -> Optional[UserInDB]
```

**使用示例**：
```python
user = await user_service.get_by_email("user@example.com")
if user:
    print(f"用户名: {user.username}")
```

#### 按外部ID查询

```python
async def get_by_external_id(self, external_id: str) -> Optional[UserInDB]
```

**使用示例**：
```python
# 查询GitHub OAuth用户
github_user = await user_service.get_by_external_id("github:12345")

# 查询Linux.do OAuth用户
linuxdo_user = await user_service.get_by_external_id("linuxdo:67890")
```

#### 按ID查询

```python
async def get_user(self, user_id: int) -> Optional[UserInDB]
```

**使用示例**：
```python
user = await user_service.get_user(user_id=1)
if user:
    print(f"用户信息: {user.username}")
```

### 3. 用户列表

```python
async def list_users(self) -> list[UserInDB]
```

**使用示例**：
```python
# 获取所有用户（管理后台）
all_users = await user_service.list_users()

for user in all_users:
    print(f"ID: {user.id} | 用户名: {user.username} | 管理员: {user.is_admin}")
```

### 4. 每日请求配额管理

#### 递增每日请求数

```python
async def increment_daily_request(self, user_id: int) -> None
```

**使用示例**：
```python
# 用户发起API请求时
await user_service.increment_daily_request(user_id=1)
```

#### 获取每日请求数

```python
async def get_daily_request(self, user_id: int) -> int
```

**使用示例**：
```python
# 检查用户今日请求次数
count = await user_service.get_daily_request(user_id=1)
print(f"今日已使用: {count} 次")

# 配合配额限制
daily_limit = 100  # 每日限额
if count >= daily_limit:
    raise HTTPException(status_code=429, detail="今日请求次数已达上限")
```

## 完整使用流程

### 用户注册流程

```python
async def register_new_user(username: str, email: str, password: str):
    """完整的用户注册流程"""
    user_service = UserService(session)
    
    # 1. 检查用户名是否已存在
    existing_user = await user_service.get_by_username(username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 2. 检查邮箱是否已使用
    existing_email = await user_service.get_by_email(email)
    if existing_email:
        raise HTTPException(status_code=400, detail="邮箱已被使用")
    
    # 3. 创建用户
    user = await user_service.create_user(
        UserCreate(
            username=username,
            email=email,
            password=password
        )
    )
    
    return user
```

### OAuth用户处理

```python
async def handle_oauth_user(external_id: str, username: str, email: str):
    """处理OAuth登录用户"""
    user_service = UserService(session)
    
    # 1. 检查是否已有该OAuth用户
    user = await user_service.get_by_external_id(external_id)
    
    if user:
        # 已存在，直接返回
        return user
    
    # 2. 首次OAuth登录，创建新用户
    import secrets
    placeholder_password = secrets.token_urlsafe(16)
    
    user = await user_service.create_user(
        UserCreate(
            username=username,
            email=email,
            password=placeholder_password
        ),
        external_id=external_id
    )
    
    return user
```

### 请求配额检查中间件

```python
async def check_daily_quota(user_id: int, daily_limit: int = 100):
    """检查用户每日请求配额"""
    user_service = UserService(session)
    
    # 1. 获取今日已使用次数
    used_count = await user_service.get_daily_request(user_id)
    
    # 2. 检查是否超限
    if used_count >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"今日请求次数已达上限（{daily_limit}次），请明天再试"
        )
    
    # 3. 递增计数
    await user_service.increment_daily_request(user_id)
    
    # 4. 返回剩余次数
    remaining = daily_limit - used_count - 1
    return {
        "used": used_count + 1,
        "limit": daily_limit,
        "remaining": remaining
    }
```

### 管理后台用户管理

```python
async def admin_user_management():
    """管理后台的用户管理功能"""
    user_service = UserService(session)
    
    # 1. 获取所有用户
    all_users = await user_service.list_users()
    
    # 2. 统计信息
    total_users = len(all_users)
    admin_count = sum(1 for u in all_users if u.is_admin)
    oauth_count = sum(1 for u in all_users if u.external_id)
    
    # 3. 获取每个用户今日使用情况
    user_stats = []
    for user in all_users:
        daily_count = await user_service.get_daily_request(user.id)
        user_stats.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "daily_requests": daily_count,
            "oauth_provider": user.external_id.split(":")[0] if user.external_id else None
        })
    
    return {
        "total": total_users,
        "admins": admin_count,
        "oauth_users": oauth_count,
        "users": user_stats
    }
```

## 错误处理

### IntegrityError处理

```python
# create_user方法内部已处理
try:
    await self.session.commit()
except IntegrityError as exc:
    await self.session.rollback()
    raise ValueError("用户名或邮箱已存在") from exc
```

**使用时捕获**：
```python
try:
    user = await user_service.create_user(payload)
except ValueError as e:
    # 处理重复用户名或邮箱
    return {"error": str(e)}
```

## 数据模型

### UserInDB Schema

```python
class UserInDB(BaseModel):
    id: int
    username: str
    email: Optional[str]
    is_admin: bool
    external_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # 注意：不包含 hashed_password
```

### UserCreate Schema

```python
class UserCreate(BaseModel):
    username: str
    email: Optional[str]
    password: str
```

## 依赖关系

### 内部依赖
- [`UserRepository`](../repositories/user_repository.md) - 数据库操作
- [`User`](../models/user.md) - 数据模型
- [`hash_password`](../core/security.md) - 密码哈希

### Schema定义
- [`UserCreate`](../schemas/user.md) - 创建Schema
- [`UserInDB`](../schemas/user.md) - 读取Schema

### 调用方
- [`AuthService`](auth_service.md) - 认证服务
- API路由层 - 用户管理接口

## 最佳实践

### 1. 密码处理

```python
# 好的做法：使用UserCreate Schema，自动哈希密码
user = await user_service.create_user(
    UserCreate(username="user", email="...", password="plain_password")
)

# 不要：直接传递明文密码到数据库
```

### 2. OAuth用户标识

```python
# 好的命名：提供商:用户ID
external_id = f"github:{user_id}"
external_id = f"linuxdo:{user_id}"

# 不推荐：不明确的格式
external_id = f"{user_id}"
```

### 3. 请求配额检查

```python
# 好的做法：在业务逻辑前检查配额
count = await user_service.get_daily_request(user_id)
if count >= limit:
    raise HTTPException(status_code=429, detail="配额已用尽")

await user_service.increment_daily_request(user_id)
# 执行业务逻辑...

# 不推荐：在业务逻辑后递增（可能浪费资源）
```

## 相关文件

- **数据模型**: `backend/app/models/user.py`
- **仓储层**: `backend/app/repositories/user_repository.py`
- **Schema**: `backend/app/schemas/user.py`
- **安全工具**: `backend/app/core/security.py`