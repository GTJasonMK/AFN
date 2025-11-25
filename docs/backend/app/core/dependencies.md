# backend/app/core/dependencies.py - 依赖注入模块（PyQt桌面版）

## 文件概述

PyQt 桌面版的依赖注入模块，提供无需认证的默认用户获取功能。桌面版使用固定的默认用户，无需登录认证流程。

## 核心函数

### `get_default_user()`（第15-42行）

**函数签名：**
```python
async def get_default_user(
    session: AsyncSession = Depends(get_session),
) -> UserInDB
```

**功能：** 获取桌面版默认用户

**返回：** `UserInDB` - 用户信息对象

**异常：** 
- `HTTPException(500)` - 默认用户未初始化

## 实现逻辑

### 1. 尝试获取默认用户

```python
repo = UserRepository(session)
user = await repo.get_by_username("desktop_user")
```

首先尝试获取用户名为 `desktop_user` 的用户。

### 2. 降级策略

如果 `desktop_user` 不存在，尝试获取任意用户：

```python
if not user:
    from sqlalchemy import select
    from ..models import User
    result = await session.execute(select(User))
    user = result.scalars().first()
```

### 3. 错误处理

如果数据库中完全没有用户，抛出异常：

```python
if not user:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="默认用户未初始化，请重启应用"
    )
```

### 4. 返回用户对象

```python
return UserInDB.model_validate(user)
```

使用 Pydantic 验证并转换为 `UserInDB` Schema。

## 使用场景

### 1. API 路由中注入用户

```python
from backend.app.core.dependencies import get_default_user

@router.get("/novels")
async def list_novels(
    desktop_user: UserInDB = Depends(get_default_user),
):
    # desktop_user 自动注入，无需登录
    novels = await novel_service.list_projects_for_user(desktop_user.id)
    return novels
```

### 2. 替代认证中间件

桌面版不需要：
- JWT 令牌验证
- 登录接口
- 权限检查

直接使用 `get_default_user()` 注入固定用户。

### 3. 多个依赖组合

```python
@router.post("/chapters/generate")
async def generate_chapter(
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    # 同时注入数据库会话和用户
    pass
```

## 桌面版特性

### 1. 无需认证

- 不验证 JWT 令牌
- 不检查密码
- 不管理会话

### 2. 默认用户

桌面版默认用户特征：
- 用户名：`desktop_user`
- 邮箱：`desktop@example.com`
- 密码：无关紧要（不会用到）
- 管理员权限：`is_admin=False`

### 3. 自动创建

默认用户在数据库初始化时自动创建（`init_db.py`）：

```python
desktop_user = User(
    username="desktop_user",
    email="desktop@example.com",
    hashed_password=hash_password("desktop"),
    is_admin=False,
)
session.add(desktop_user)
```

## 与 Web 版差异

### Web 版依赖注入

```python
# Web 版需要 JWT 认证
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> UserInDB:
    # 1. 解析 JWT 令牌
    payload = decode_access_token(token)
    # 2. 从数据库查询用户
    user = await user_repo.get_by_id(payload["sub"])
    # 3. 验证用户状态
    if not user or not user.is_active:
        raise HTTPException(401)
    return user
```

### 桌面版依赖注入

```python
# 桌面版直接返回默认用户
async def get_default_user(
    session: AsyncSession = Depends(get_session),
) -> UserInDB:
    user = await repo.get_by_username("desktop_user")
    return UserInDB.model_validate(user)
```

**简化点：**
- 无 `token` 参数
- 无令牌解析
- 无权限验证
- 无状态检查

## 错误场景

### 场景1：默认用户不存在

**原因：**
- 数据库未正确初始化
- 数据被手动删除

**解决：**
```bash
# 重启应用，触发数据库初始化
python -m backend.app.main
```

### 场景2：数据库连接失败

**原因：**
- 数据库服务未启动
- 连接配置错误

**解决：**
检查 `.env` 配置：
```env
DATABASE_URL=sqlite+aiosqlite:///storage/arboris.db
```

## 依赖图

```
FastAPI Request
    ↓
get_default_user()
    ↓
get_session() → AsyncSession
    ↓
UserRepository
    ↓
Database Query
    ↓
UserInDB (返回)
```

## 相关文件

- `backend/app/db/init_db.py` - 创建默认用户
- `backend/app/repositories/user_repository.py` - 用户数据访问
- `backend/app/schemas/user.py` - UserInDB Schema
- `backend/app/db/session.py` - get_session() 依赖
- `backend/app/api/routers/` - 使用此依赖的路由

## 注意事项

1. **单用户模式：** 桌面版仅支持单用户，所有操作归属于默认用户
2. **数据隔离：** 如需多用户支持，应升级到 Web 版
3. **安全性：** 桌面版无身份验证，仅适用于本地环境
4. **初始化依赖：** 确保应用启动时正确执行 `init_db()`