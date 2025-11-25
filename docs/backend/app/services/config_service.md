# Config Service - 系统配置服务

## 文件概述

**文件路径**: `backend/app/services/config_service.py`  
**代码行数**: 49行  
**核心职责**: 系统配置服务，提供系统级配置的CRUD操作，负责转换Pydantic模型和数据库模型

## 核心功能

### 1. 列出所有配置

```python
async def list_configs(self) -> list[SystemConfigRead]
```

**使用示例**：
```python
config_service = ConfigService(session)

# 获取所有系统配置
configs = await config_service.list_configs()

for config in configs:
    print(f"{config.key}: {config.value}")
    print(f"描述: {config.description}")
```

### 2. 获取单个配置

```python
async def get_config(self, key: str) -> Optional[SystemConfigRead]
```

**使用示例**：
```python
# 获取LLM API Key配置
llm_config = await config_service.get_config("llm.api_key")
if llm_config:
    api_key = llm_config.value
    print(f"API Key: {api_key[:10]}...")
else:
    print("未配置LLM API Key")
```

### 3. 创建或更新配置（Upsert）

```python
async def upsert_config(self, payload: SystemConfigCreate) -> SystemConfigRead
```

**功能说明**：
- 如果配置键已存在，则更新
- 如果配置键不存在，则创建

**使用示例**：
```python
from backend.app.schemas.config import SystemConfigCreate

# 设置LLM配置
config = await config_service.upsert_config(
    SystemConfigCreate(
        key="llm.api_key",
        value="sk-xxxx",
        description="OpenAI API密钥"
    )
)

# 更新邮件配置
smtp_config = await config_service.upsert_config(
    SystemConfigCreate(
        key="smtp.server",
        value="smtp.gmail.com",
        description="SMTP服务器地址"
    )
)
```

### 4. 部分更新配置

```python
async def patch_config(
    self, 
    key: str, 
    payload: SystemConfigUpdate
) -> Optional[SystemConfigRead]
```

**使用示例**：
```python
from backend.app.schemas.config import SystemConfigUpdate

# 仅更新值
updated = await config_service.patch_config(
    key="llm.api_key",
    payload=SystemConfigUpdate(value="sk-new-key")
)

# 仅更新描述
updated = await config_service.patch_config(
    key="llm.api_key",
    payload=SystemConfigUpdate(description="新的描述")
)

# 同时更新值和描述
updated = await config_service.patch_config(
    key="llm.api_key",
    payload=SystemConfigUpdate(
        value="sk-new-key",
        description="更新后的API密钥"
    )
)
```

### 5. 删除配置

```python
async def remove_config(self, key: str) -> bool
```

**返回值**：
- `True` - 删除成功
- `False` - 配置不存在

**使用示例**：
```python
# 删除配置
success = await config_service.remove_config("test.config")
if success:
    print("配置已删除")
else:
    print("配置不存在")
```

## 常用配置项

### LLM相关配置

```python
# 默认LLM配置
await config_service.upsert_config(
    SystemConfigCreate(
        key="llm.api_key",
        value="sk-xxxx",
        description="LLM API密钥"
    )
)

await config_service.upsert_config(
    SystemConfigCreate(
        key="llm.base_url",
        value="https://api.openai.com/v1",
        description="LLM API基础URL"
    )
)

await config_service.upsert_config(
    SystemConfigCreate(
        key="llm.model",
        value="gpt-4",
        description="默认使用的LLM模型"
    )
)
```

### SMTP邮件配置

```python
# SMTP服务器配置
smtp_configs = [
    ("smtp.server", "smtp.gmail.com", "SMTP服务器地址"),
    ("smtp.port", "587", "SMTP端口"),
    ("smtp.username", "user@example.com", "SMTP用户名"),
    ("smtp.password", "password", "SMTP密码"),
    ("smtp.from", "Arboris Novel <noreply@example.com>", "发件人"),
]

for key, value, description in smtp_configs:
    await config_service.upsert_config(
        SystemConfigCreate(
            key=key,
            value=value,
            description=description
        )
    )
```

### 认证相关配置

```python
# 注册开关
await config_service.upsert_config(
    SystemConfigCreate(
        key="auth.allow_registration",
        value="true",
        description="是否允许用户注册"
    )
)

# OAuth配置
await config_service.upsert_config(
    SystemConfigCreate(
        key="auth.linuxdo_enabled",
        value="false",
        description="是否启用Linux.do OAuth登录"
    )
)
```

### 管理员配置

```python
# 每日请求限额
await config_service.upsert_config(
    SystemConfigCreate(
        key="daily_request_limit",
        value="100",
        description="每日免费请求次数限制"
    )
)
```

## 配置读取的优先级

在实际使用中，配置的读取遵循以下优先级：

1. **数据库配置**（最高优先级）
2. **环境变量**（降级方案）
3. **代码默认值**（最后兜底）

**示例**：
```python
# LLMService中的配置读取
async def _get_config_value(self, key: str) -> Optional[str]:
    # 1. 先从数据库读取
    record = await self.system_config_repo.get_by_key(key)
    if record:
        return record.value
    
    # 2. 兼容环境变量（首次迁移时无需立即写入数据库）
    env_key = key.upper().replace(".", "_")
    return os.getenv(env_key)

# 使用示例
api_key = await self._get_config_value("llm.api_key")  # 查找 llm.api_key 或 LLM_API_KEY
```

## 完整使用流程

### 初始化系统配置

```python
async def initialize_system_configs():
    """应用首次启动时初始化系统配置"""
    config_service = ConfigService(session)
    
    # 1. LLM配置
    await config_service.upsert_config(
        SystemConfigCreate(
            key="llm.api_key",
            value=os.getenv("LLM_API_KEY", ""),
            description="LLM API密钥"
        )
    )
    
    await config_service.upsert_config(
        SystemConfigCreate(
            key="llm.base_url",
            value=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            description="LLM API基础URL"
        )
    )
    
    await config_service.upsert_config(
        SystemConfigCreate(
            key="llm.model",
            value=os.getenv("LLM_MODEL", "gpt-4"),
            description="默认LLM模型"
        )
    )
    
    # 2. 认证配置
    await config_service.upsert_config(
        SystemConfigCreate(
            key="auth.allow_registration",
            value=os.getenv("ALLOW_REGISTRATION", "true"),
            description="是否允许注册"
        )
    )
    
    # 3. 管理员配置
    await config_service.upsert_config(
        SystemConfigCreate(
            key="daily_request_limit",
            value=os.getenv("DAILY_REQUEST_LIMIT", "100"),
            description="每日免费请求限制"
        )
    )
```

### 管理后台配置管理

```python
# 获取所有配置（管理后台）
@router.get("/admin/configs")
async def list_all_configs(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    config_service = ConfigService(session)
    configs = await config_service.list_configs()
    return {"configs": configs}

# 更新配置
@router.put("/admin/configs/{key}")
async def update_config(
    key: str,
    payload: SystemConfigUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    config_service = ConfigService(session)
    updated = await config_service.patch_config(key, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="配置不存在")
    return updated
```

## 依赖关系

### 内部依赖
- [`SystemConfigRepository`](backend/app/repositories/system_config_repository.py) - 数据库操作
- [`SystemConfig`](backend/app/models/system_config.py) - 数据模型

### Schema定义
- [`SystemConfigCreate`](backend/app/schemas/config.py) - 创建Schema
- [`SystemConfigUpdate`](backend/app/schemas/config.py) - 更新Schema
- [`SystemConfigRead`](backend/app/schemas/config.py) - 读取Schema

### 调用方
- [`AuthService`](backend/app/services/auth_service.py) - 读取认证配置
- [`LLMService`](backend/app/services/llm_service.py) - 读取LLM配置
- 管理后台API路由

## 数据模型

### SystemConfig表结构

```python
class SystemConfig(Base):
    __tablename__ = "system_configs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

## 最佳实践

### 1. 使用Upsert避免重复

```python
# 好的做法：使用upsert
await config_service.upsert_config(
    SystemConfigCreate(key="test.key", value="value")
)

# 不推荐：先查询再决定创建或更新
existing = await config_service.get_config("test.key")
if existing:
    await config_service.patch_config(...)
else:
    await config_service.upsert_config(...)
```

### 2. 配置键命名规范

```python
# 好的命名：使用点号分隔，层级清晰
"llm.api_key"
"llm.base_url"
"smtp.server"
"auth.allow_registration"

# 不推荐：下划线或扁平命名
"llm_api_key"
"allowregistration"
```

### 3. 敏感配置处理

```python
# 读取时不显示完整值
config = await config_service.get_config("llm.api_key")
masked_value = f"{config.value[:10]}...{config.value[-4:]}"

# 更新时验证格式
if key == "llm.api_key" and len(value) < 20:
    raise HTTPException(status_code=400, detail="API Key格式不正确")
```

### 4. 配置变更通知

```python
# 重要配置更新后清理缓存
async def update_llm_config(key: str, value: str):
    await config_service.upsert_config(
        SystemConfigCreate(key=key, value=value)
    )
    
    # 清理相关缓存
    if key.startswith("llm."):
        await clear_llm_cache()
```

## 相关文件

- **数据模型**: [`backend/app/models/system_config.py`](backend/app/models/system_config.py)
- **仓储层**: [`backend/app/repositories/system_config_repository.py`](backend/app/repositories/system_config_repository.py)
- **Schema**: [`backend/app/schemas/config.py`](backend/app/schemas/config.py)
- **默认配置**: [`backend/app/db/system_config_defaults.py`](backend/app/db/system_config_defaults.py)