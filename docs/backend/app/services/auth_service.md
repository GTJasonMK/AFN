
# Auth Service - 认证与授权服务

## 文件概述

**文件路径**: `backend/app/services/auth_service.py`  
**代码行数**: 389行  
**核心职责**: 用户认证授权、注册登录、邮箱验证码、OAuth集成、密码管理等完整认证体系

## 核心功能

### 1. 用户登录认证

```python
async def authenticate_user(self, username: str, password: str) -> User
```

**使用示例**：
```python
auth_service = AuthService(session)

# 验证用户凭证
try:
    user = await auth_service.authenticate_user(
        username="user1",
        password="password123"
    )
    print(f"登录成功: {user.username}")
except HTTPException as e:
    print(f"登录失败: {e.detail}")  # "用户名或密码错误"
```

### 2. 创建访问令牌

```python
async def create_access_token(
    self,
    user: User | UserInDB,
    *,
    must_change_password: Optional[bool] = None,
) -> Token
```

**特性**：
- 自动检测是否需要强制修改密码（管理员使用默认密码时）
- 在JWT中包含用户角色信息

**使用示例**：
```python
# 创建访问令牌
token = await auth_service.create_access_token(user)

# 返回结构
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "must_change_password": False
}

# 管理员首次登录（使用默认密码）
admin_token = await auth_service.create_access_token(admin_user)
{
    "access_token": "...",
    "must_change_password": True  # 强制修改密码
}
```

### 3. 用户注册

```python
async def register_user(self, payload: UserRegistration) -> User
```

**注册流程**：
1. 检查注册开关是否启用
2. 验证用户名和邮箱唯一性
3. 验证邮箱验证码
4. 创建用户并哈希密码

**使用示例**：
```python
from backend.app.schemas.user import UserRegistration

# 注册新用户
try:
    user = await auth_service.register_user(
        UserRegistration(
            username="newuser",
            email="user@example.com",
            password="SecurePass123!",
            verification_code="123456"
        )
    )
    print(f"注册成功: {user.username}")
except HTTPException as e:
    if e.status_code == 403:
        print("当前暂未开放注册")
    elif e.status_code == 400:
        print(f"注册失败: {e.detail}")
        # 可能的错误：
        # - "用户名已存在"
        # - "邮箱已被使用"
        # - "验证码错误或已过期"
```

### 4. 邮箱验证码功能

#### 发送验证码

```python
async def send_verification_code(self, email: str) -> None
```

**特性**：
- 6位数字验证码
- 5分钟有效期
- 1分钟内不可重复发送
- 精美的HTML邮件模板

**使用示例**：
```python
# 发送验证码
try:
    await auth_service.send_verification_code("user@example.com")
    print("验证码已发送")
except HTTPException as e:
    if e.status_code == 429:
        print("请稍后再试，1分钟内不可重复发送")
    elif e.status_code == 500:
        print("未配置邮件服务，请联系管理员")
```

#### 验证验证码

```python
def verify_code(self, email: str | None, code: str) -> bool
```

**使用示例**：
```python
# 验证验证码
is_valid = auth_service.verify_code("user@example.com", "123456")
if is_valid:
    print("验证码正确")
else:
    print("验证码错误或已过期")

# 验证后验证码自动失效
is_valid_again = auth_service.verify_code("user@example.com", "123456")
# is_valid_again == False
```

#### SMTP配置加载

```python
async def _load_smtp_config(self) -> Optional[Dict[str, str]]
```

**必需配置项**：
- `smtp.server` - SMTP服务器地址
- `smtp.port` - 端口（465用SSL，587用STARTTLS）
- `smtp.username` - 登录用户名
- `smtp.password` - 登录密码
- `smtp.from` - 发件人信息

**配置示例**：
```python
# 在system_configs表中配置
smtp_configs = [
    ("smtp.server", "smtp.gmail.com"),
    ("smtp.port", "587"),
    ("smtp.username", "your-email@gmail.com"),
    ("smtp.password", "your-app-password"),
    ("smtp.from", "Arboris Novel <noreply@example.com>"),
]
```

#### 邮件发送实现

```python
async def _send_email(self, to_email: str, code: str, smtp_config: Dict[str, str]) -> None
```

**特性**：
- 支持SSL（465端口）和STARTTLS（587端口）
- 智能处理发件人格式（支持中文显示名）
- HTML邮件模板，响应式设计
- 异步发送（不阻塞主线程）
- 详细的错误日志

**邮件模板**：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<body style="background-color: #f3f4f6;">
    <table style="max-width: 512px; background-color: #ffffff; border-radius: 16px;">
        <!-- 邮件头部 -->
        <tr>
            <td style="background-color: #2563eb; padding: 32px;">
                <h1 style="color: #ffffff;">操作验证码</h1>
                <p style="color: #dbeafe;">请使用下方验证码完成操作。</p>
            </td>
        </tr>
        <!-- 验证码显示 -->
        <tr>
            <td style="padding: 32px 48px;">
                <p style="font-size: 48px; color: #1d4ed8; letter-spacing: 0.1em;">
                    123456
                </p>
            </td>
        </tr>
        <!-- 有效期提示 -->
        <tr>
            <td>
                <p>此验证码将在 <strong>5分钟</strong> 内有效。</p>
            </td>
        </tr>
        <!-- 安全提示 -->
        <tr>
            <td>
                <p style="color: #ef4444;">为保障安全，请勿泄露此验证码。</p>
            </td>
        </tr>
        <!-- 页脚 -->
        <tr>
            <td style="background-color: #f9fafb;">
                <p>如非本人操作，请忽略此邮件。</p>
                <p>&copy; 2024 拯救小说家. All rights reserved.</p>
            </td>
        </tr>
    </table>
</body>
</html>
```

### 5. OAuth集成（Linux.do示例）

```python
async def handle_linuxdo_callback(self, code: str) -> Token
```

**OAuth流程**：
1. 检查OAuth登录是否启用
2. 使用授权码换取访问令牌
3. 使用访问令牌获取用户信息
4. 自动创建或关联本地用户
5. 返回JWT令牌

**使用示例**：
```python
# 处理OAuth回调
try:
    token = await auth_service.handle_linuxdo_callback(code="auth_code_from_callback")
    print(f"OAuth登录成功: {token.access_token}")
except HTTPException as e:
    if e.status_code == 403:
        print("未启用 Linux.do 登录")
    elif e.status_code == 500:
        print("未正确配置 Linux.do OAuth 参数")
```

**OAuth配置**：
```python
# 在system_configs表中配置
oauth_configs = [
    ("linuxdo.client_id", "your-client-id"),
    ("linuxdo.client_secret", "your-client-secret"),
    ("linuxdo.redirect_uri", "http://localhost:8000/api/auth/linuxdo/callback"),
    ("linuxdo.token_url", "https://connect.linux.do/oauth2/token"),
    ("linuxdo.user_info_url", "https://connect.linux.do/api/user"),
]
```

**用户绑定逻辑**：
```python
# OAuth用户标识格式
external_id = f"linuxdo:{data['id']}"  # 例如: "linuxdo:12345"

# 首次登录自动创建用户
user = await self.user_repo.get_by_external_id(external_id)
if user is None:
    placeholder_password = secrets.token_urlsafe(16)
    user = User(
        username=data["username"],
        email=data.get("email"),
        external_id=external_id,
        hashed_password=hash_password(placeholder_password),
    )
    self.session.add(user)
    await self.session.commit()
```

### 6. 密码管理

#### 修改密码

```python
async def change_password(self, username: str, old_password: str, new_password: str) -> None
```

**验证规则**：
- 旧密码必须正确
- 新密码不能与当前密码相同
- 管理员不能使用默认密码

**使用示例**：
```python
# 修改密码
try:
    await auth_service.change_password(
        username="user1",
        old_password="OldPass123",
        new_password="NewSecurePass456"
    )
    print("密码修改成功")
except HTTPException as e:
    print(f"修改失败: {e.detail}")
    # 可能的错误：
    # - "用户不存在"
    # - "当前密码错误"
    # - "新密码不能与当前密码相同"
    # - "新密码不能为默认密码"（仅管理员）
```

#### 检查是否需要重置密码

```python
def requires_password_reset(self, user: User | UserInDB) -> bool
```

**逻辑**：
- 仅对管理员检查
- 仅检查默认管理员账号
- 验证是否使用默认密码

**使用示例**：
```python
# 检查是否需要强制修改密码
if auth_service.requires_password_reset(user):
    print("请立即修改默认密码")
    # 前端跳转到密码修改页面
```

### 7. 配置管理

#### 读取配置

```python
async def get_config_value(self, key: str) -> Optional[str]
```

#### 解析布尔值

```python
@staticmethod
def _parse_bool(value: Optional[str], fallback: bool) -> bool
```

**支持的布尔值表示**：
- `True`: "1", "true", "yes", "on"
- `False`: "0", "false", "no", "off"
- 其他值或None: 使用fallback默认值

#### 检查注册是否启用

```python
async def is_registration_enabled(self) -> bool
```

**配置优先级**：
1. 数据库配置（`auth.allow_registration`）
2. 环境变量（`settings.allow_registration`）

#### 检查OAuth登录是否启用

```python
async def is_linuxdo_login_enabled(self) -> bool
```

#### 获取认证选项

```python
async def get_auth_options(self) -> AuthOptions
```

**使用示例**：
```python
# 前端拉取认证配置
auth_options = await auth_service.get_auth_options()

# 返回结构
{
    "allow_registration": True,
    "enable_linuxdo_login": False
}

# 前端根据配置显示/隐藏相关UI
if auth_options.allow_registration:
    # 显示注册按钮
    pass
if auth_options.enable_linuxdo_login:
    # 显示Linux.do登录按钮
    pass
```

## 完整使用流程

### 1. 用户注册流程

```python
async def user_registration_flow(email: str, username: str, password: str):
    """完整的用户注册流程"""
    auth_service = AuthService(session)
    
    # 1. 发送验证码
    await auth_service.send_verification_code(email)
    print("验证码已发送到邮箱")
    
    # 2. 用户输入验证码
    code = input("请输入验证码: ")
    
    # 3. 注册用户
    user = await auth_service.register_user(
        UserRegistration(
            username=username,
            email=email,
            password=password,
            verification_code=code
        )
    )
    
    # 4. 创建访问令牌
    token = await auth_service.create_access_token(user)
    
    return token
```

### 2. 用户登录流程

```python
async def user_login_flow(username: str, password: str):
    """完整的用户登录流程"""
    auth_service = AuthService(session)
    
    # 1. 验证用户凭证
    user = await auth_service.authenticate_user(username, password)
    
    # 2. 创建访问令牌
    token = await auth_service.create_access_token(user)
    
    # 3. 检查是否需要强制修改密码
    if token.must_change_password:
        print("检测到使用默认密码，请立即修改")
        # 引导用户修改密码
    
    return token
```

### 3. OAuth登录流程

```python
async def oauth_login_flow(authorization_code: str):
    """OAuth登录流程"""
    auth_service = AuthService(session)
    
    # 处理OAuth回调
    token = await auth_service.handle_linuxdo_callback(authorization_code)
    
    return token
```

## 数据结构

### 验证码缓存

```python
_VERIFICATION_CACHE: Dict[str, tuple[str, float]] = {}
# 格式: {
#     "user@example.com": ("123456", 1705738200.0)  # (验证码, 过期时间戳)
# }

_LAST_SEND_TIME: Dict[str, float] = {}
# 格式: {
#     "user@example.com": 1705738100.0  # 最后发送时间戳
# }
```

## 依赖关系

### 内部依赖
- [`UserRepository`](../repositories/user_repository.md) - 用户数据操作
- [`SystemConfigRepository`](../repositories/system_config_repository.md) 