
# backend/app/core/security.py - 安全认证模块

## 文件概述

提供密码哈希、JWT令牌生成与验证等安全相关功能。使用 bcrypt 算法进行密码加密，使用 JWT 进行无状态身份认证，确保用户数据和API访问的安全性。

**文件路径：** `backend/app/core/security.py`  
**代码行数：** 58 行  
**复杂度：** ⭐⭐ 中等

## 核心功能

### 1. 密码哈希处理
### 2. JWT 令牌管理
### 3. 令牌验证与解析

## 依赖库

```python
from passlib.context import CryptContext  # 密码哈希
from jose import JWTError, jwt             # JWT处理
```

## 密码哈希上下文

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**配置说明：**
- `schemes=["bcrypt"]`：使用 bcrypt 算法（业界标准）
- `deprecated="auto"`：自动处理算法升级和迁移

## 函数详解

### 1. hash_password() - 密码哈希

```python
def hash_password(password: str) -> str:
    """对用户密码进行哈希处理，任何时候都不要存储明文密码。"""
    return pwd_context.hash(password)
```

**用途：** 用户注册时对密码进行不可逆加密

**示例：**
```python
# 用户注册
plain_password = "MySecurePass123"
hashed = hash_password(plain_password)
# 结果类似: "$2b$12$KIXl.../..."

# 存储到数据库
user.hashed_password = hashed
```

**安全特性：**
- **单向加密**：不可逆，即使数据库泄露也无法还原明文
- **自动加盐**：每次哈希结果不同，防止彩虹表攻击
- **计算开销**：bcrypt 故意设计为慢速算法，防止暴力破解

### 2. verify_password() - 密码验证

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配哈希值。"""
    return pwd_context.verify(plain_password, hashed_password)
```

**用途：** 用户登录时验证密码

**示例：**
```python
# 用户登录
input_password = request.form.get("password")
user = await get_user_by_username(username)

if verify_password(input_password, user.hashed_password):
    # 密码正确，生成令牌
    token = create_access_token(str(user.id))
    return {"access_token": token}
else:
    # 密码错误
    raise HTTPException(status_code=401, detail="用户名或密码错误")
```

### 3. create_access_token() - 生成访问令牌

```python
def create_access_token(
    subject: str,
    *,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """生成 JWT 访问令牌，默认过期时间读取自配置。"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    now = datetime.utcnow()
    expire = now + expires_delta

    to_encode: Dict[str, Any] = {
        "sub": subject,      # Subject: 用户ID
        "iat": now,          # Issued At: 签发时间
        "exp": expire        # Expiration: 过期时间
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
```

**参数说明：**
- `subject`：通常是用户ID（字符串格式）
- `expires_delta`：自定义过期时长（可选）
- `extra_claims`：额外的JWT载荷数据（可选）

**示例：**
```python
# 基本用法：生成30分钟有效期的令牌
token = create_access_token(str(user.id))

# 自定义过期时间：7天有效期
token = create_access_token(
    str(user.id),
    expires_delta=timedelta(days=7)
)

# 添加额外信息
token = create_access_token(
    str(user.id),
    extra_claims={
        "username": user.username,
        "role": "admin",
        "permissions": ["read", "write"]
    }
)
```

**JWT 结构示例：**
```json
{
  "sub": "123",                      // 用户ID
  "iat": 1699200000,                 // 签发时间
  "exp": 1699201800,                 // 过期时间（30分钟后）
  "username": "john_doe",            // 额外载荷
  "role": "admin"
}
```

### 4. decode_access_token() - 解析令牌

```python
def decode_access_token(token: str) -> Dict[str, Any]:
    """解析并校验 JWT，失败时抛出 401 异常。"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise credentials_exception from exc

    if "sub" not in payload:
        raise credentials_exception
    return payload
```

**示例：**
```python
# API 路由中的令牌验证
from fastapi import Header, HTTPException

async def get_current_user(authorization: str = Header(...)) -> User:
    """从 Authorization 头中提取并验证令牌"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="无效的令牌")
    
    # 从数据库加载用户
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return user

# 在路由中使用
@app.get("/api/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username}
```

## 完整的认证流程

### 1. 用户注册

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str

@router.post("/register")
async def register(request: RegisterRequest, session: AsyncSession):
    # 检查用户名是否已存在
    existing = await get_user_by_username(session, request.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建新用户
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password)
    )
    session.add(user)
    await session.commit()
    
    return {"message": "注册成功"}
```

### 2. 用户登录

```python
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, session: AsyncSession):
    # 查询用户
    user = await get_user_by_username(session, request.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 验证密码
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 生成令牌
    token = create_access_token(str(user.id))
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }
```

### 3. 受保护的API

```python
@router.get("/api/protected-resource")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {
        "message": "这是受保护的资源",
        "user": current_user.username
    }
```

### 4. 令牌刷新（可选）

```python
@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """刷新令牌，延长会话"""
    new_token = create_access_token(
        str(current_user.id),
        expires_delta=timedelta(days=7)  # 刷新后有效期7天
    )
    return {"access_token": new_token, "token_type": "bearer"}
```

## 前端集成示例

### JavaScript/TypeScript

```typescript
// 登录
async function login(username: string, password: string) {
    const response = await fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    });
    
    const data = await response.json();
    
    // 保存令牌到 localStorage
    localStorage.setItem('access_token', data.access_token);
    
    return data;
}

// 访问受保护的API
async function fetchProtectedData() {
    const token = localStorage.getItem('access_token');
    
    const response = await fetch('/api/protected-resource', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    
    if (response.status === 401) {
        // 令牌过期，跳转到登录页
        window.location.href = '/login';
        return;
    }
    
    return await response.json();
}
```

## 配置参数

在 [`backend/app/core/config.py`](config.md) 中配置：

```python
class Settings(BaseSettings):
    # JWT配置
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
```

**生产环境配置建议：**
```bash
# .env
SECRET_KEY=随机生成的强密钥（至少32字符）
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 安全最佳实践

### 1. Secret Key 生成

```python
import secrets

# 生成安全的密钥
secret_key = secrets.token_urlsafe(32)
print(secret_key)  # 使用此密钥替换配置中的默认值
```

### 2. 密码强度验证

```python
import re

def validate_password(password: str) -> bool:
    """验证密码强度"""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):  # 至少一个大写字母
        return False
    if not re.search(r'[a-z]', password):  # 至少一个小写字母
        return False
    if not re.search(r'\d', password):     # 至少一个数字
        return False
    return True
```

### 3. 防止暴力破解

```python
from datetime import datetime, timedelta

# 登录失败计数器（可使用Redis）
login_attempts = {}

async def check_rate_limit(username: str):
    """检查登录尝试次数"""
    now = datetime.utcnow()
    
    if username in login_attempts:
        attempts, last_attempt = login_attempts[username]
        
        # 5分钟内超过5次失败，锁定账户
        if attempts >= 5 and now - last_attempt < timedelta(minutes=5):
            raise HTTPException(
                status_code=429,
                detail="登录尝试次数过多，请5分钟后再试"
            )
    
    return True
```

### 4. HTTPS 强制

```python
# 生产环境必须使用 HTTPS
if settings.environment == "production":
    app.add_middleware(
        HTTPSRedirectMiddleware
    )
```

## 相关文件

- [`backend/app/core/config.py`](config.md) - 配置管理
- [`backend/app/core/dependencies.py`](dependencies.md) - 依赖注入（包含 get_current_user）
- [`backend/app/models/user.py`](../models/user.md) - 用户数据模型
- [`backend/app/services/auth_service.py`](../services/auth_service.md) - 认证服务层

## 常见问题

### Q1: JWT vs Session，如何选择？

**JWT 优势：**
- 无状态，服务器不需要存储会话
- 适合微服务架构
- 跨域友好

**Session 优势：**
- 可以随时撤销
- 更小的令牌体积
- 适合传统Web应用

**本项目选择 JWT** 是因为：
- 桌面应用场景，无需频繁撤销令牌
- 简化服务器端实现
- 支持未来的移动端扩展

### Q2: 如何实现"记住我"功能？

```python
@router.post("/login")
async def login(request: LoginRequest, remember_me: bool = False):
    # ... 验证逻辑 ...
    
    # 根据"记住我"设置不同的过期时间
    expires = timedelta(days=30) if remember_me else timedelta(minutes=30)
    token = create_access_token(str(user.id), expires_delta=expires)
    
    return {"access_token": token}
```

### Q3: 如何实现令牌黑名单？

```python
# 使用Redis存储已撤销的令牌
async def revoke_token(token: str):
    payload = decode_access_token(token)
    exp = payload["exp"]
    ttl = exp - int(datetime.utcnow().timestamp())
    
    await redis.setex(f"revoked:{token}", ttl, "1")

async def is_token_revoked(token: str) -> bool:
    return await 