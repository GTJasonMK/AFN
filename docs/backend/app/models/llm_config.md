
# backend/app/models/llm_config.py - LLM 配置模型

## 文件概述

定义 LLM（大语言模型）配置的数据模型，用于存储用户的多个 LLM API 配置，支持配置管理、激活切换、连接测试等功能。

**文件路径：** `backend/app/models/llm_config.py`  
**代码行数：** 39 行  
**复杂度：** ⭐⭐ 中等

## 数据模型定义

### LLMConfig 类

```python
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

class LLMConfig(Base):
    """用户自定义的 LLM 接入配置。支持多配置管理、测试和切换。"""
    
    __tablename__ = "llm_configs"
    
    # 主键和外键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # 配置基本信息
    config_name: Mapped[str] = mapped_column(String(100), nullable=False, default="默认配置")
    llm_provider_url: Mapped[str | None] = mapped_column(Text())
    llm_provider_api_key: Mapped[str | None] = mapped_column(Text())
    llm_provider_model: Mapped[str | None] = mapped_column(Text())
    
    # 配置状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 测试相关
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_status: Mapped[str | None] = mapped_column(String(50))  # success, failed, pending
    test_message: Mapped[str | None] = mapped_column(Text())
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # 关系映射
    user: Mapped["User"] = relationship("User", back_populates="llm_configs")
```

## 字段详解

### 主键和外键

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `Integer` | 主键，自增 | 配置唯一标识符 |
| `user_id` | `Integer` | 外键，索引 | 所属用户 ID |

**外键关系：**
- 关联到 `users.id`
- `ondelete="CASCADE"`：删除用户时级联删除配置

### 配置基本信息

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| `config_name` | `String(100)` | NOT NULL | "默认配置" | 配置名称 |
| `llm_provider_url` | `Text` | 可选 | None | API 基础 URL |
| `llm_provider_api_key` | `Text` | 可选 | None | API Key |
| `llm_provider_model` | `Text` | 可选 | None | 模型名称 |

**说明：**
- `config_name`：用户自定义的配置名称，如"我的 GPT-4"
- `llm_provider_url`：API 端点，如 `https://api.openai.com/v1`
- `llm_provider_api_key`：认证密钥，存储时应加密
- `llm_provider_model`：模型名称，如 `gpt-4`、`claude-3-opus`

### 配置状态

| 字段 | 类型 | 约束 | 默认值 | 说明 |
|------|------|------|--------|------|
| `is_active` | `Boolean` | NOT NULL, 索引 | False | 是否为激活配置 |
| `is_verified` | `Boolean` | NOT NULL | False | 是否已验证可用 |

**状态说明：**

```python
# 配置状态组合
is_active=True, is_verified=True   # 激活且已验证（正常使用）
is_active=True, is_verified=False  # 激活但未验证（可能有问题）
is_active=False, is_verified=True  # 未激活但已验证（备用配置）
is_active=False, is_verified=False # 未激活未验证（新建配置）
```

**激活规则：**
- 每个用户同时只能有一个激活的配置（`is_active=True`）
- 激活新配置时，自动停用其他配置

### 测试相关

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `last_test_at` | `DateTime` | 可选 | 最后一次测试时间 |
| `test_status` | `String(50)` | 可选 | 测试状态 |
| `test_message` | `Text` | 可选 | 测试消息 |

**测试状态值：**
- `success`：测试成功
- `failed`：测试失败
- `pending`：测试中

### 时间戳

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `created_at` | `DateTime(TZ)` | NOT NULL | 创建时间 |
| `updated_at` | `DateTime(TZ)` | NOT NULL | 更新时间 |

**自动更新：**
- `created_at`：创建时自动设置
- `updated_at`：每次更新时自动更新

## 关系映射

### 与 User 的关系

```python
user: Mapped["User"] = relationship("User", back_populates="llm_configs")
```

**关系类型：** 多对一（Many-to-One）

```
User (1) ←──────→ (N) LLMConfig
```

**说明：**
- 一个用户可以有多个 LLM 配置
- 每个配置属于一个用户
- 删除用户时级联删除其所有配置

## 数据库表结构

### 表名

```sql
CREATE TABLE llm_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    config_name VARCHAR(100) NOT NULL DEFAULT '默认配置',
    llm_provider_url TEXT,
    llm_provider_api_key TEXT,
    llm_provider_model TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 0,
    is_verified BOOLEAN NOT NULL DEFAULT 0,
    last_test_at TIMESTAMP WITH TIME ZONE,
    test_status VARCHAR(50),
    test_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX ix_llm_configs_user_id ON llm_configs(user_id);
CREATE INDEX ix_llm_configs_is_active ON llm_configs(is_active);
```

### 索引

| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| `PRIMARY` | `id` | 主键 | 唯一标识 |
| `ix_llm_configs_user_id` | `user_id` | 普通索引 | 加速用户查询 |
| `ix_llm_configs_is_active` | `is_active` | 普通索引 | 快速查找激活配置 |

## 使用示例

### 1. 创建配置

```python
from backend.app.models.llm_config import LLMConfig
from sqlalchemy.ext.asyncio import AsyncSession

async def create_config(session: AsyncSession, user_id: int):
    config = LLMConfig(
        user_id=user_id,
        config_name="我的 GPT-4 配置",
        llm_provider_url="https://api.openai.com/v1",
        llm_provider_api_key="sk-xxx",
        llm_provider_model="gpt-4",
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config
```

### 2. 查询用户的所有配置

```python
from sqlalchemy import select

async def list_configs(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(LLMConfig)
        .where(LLMConfig.user_id == user_id)
        .order_by(LLMConfig.created_at.desc())
    )
    return result.scalars().all()
```

### 3. 获取激活的配置

```python
async def get_active_config(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(LLMConfig)
        .where(
            LLMConfig.user_id == user_id,
            LLMConfig.is_active == True
        )
    )
    return result.scalar_one_or_none()
```

### 4. 激活配置

```python
async def activate_config(
    session: AsyncSession, 
    config_id: int, 
    user_id: int
):
    # 1. 停用所有配置
    await session.execute(
        update(LLMConfig)
        .where(LLMConfig.user_id == user_id)
        .values(is_active=False)
    )
    
    # 2. 激活指定配置
    await session.execute(
        update(LLMConfig)
        .where(
            LLMConfig.id == config_id,
            LLMConfig.user_id == user_id
        )
        .values(is_active=True)
    )
    
    await session.commit()
```

### 5. 测试配置

```python
from datetime import datetime

async def test_config(session: AsyncSession, config_id: int):
    config = await session.get(LLMConfig, config_id)
    
    try:
        # 测试 API 连接
        success = await test_llm_connection(
            config.llm_provider_url,
            config.llm_provider_api_key,
            config.llm_provider_model
        )
        
        config.test_status = "success" if success else "failed"
        config.test_message = "连接成功" if success else "连接失败"
        config.is_verified = success
        
    except Exception as e:
        config.test_status = "failed"
        config.test_message = str(e)
        config.is_verified = False
    
    config.last_test_at = datetime.utcnow()
    await session.commit()
    return config
```

### 6. 更新配置

```python
async def update_config(
    session: AsyncSession,
    config_id: int,
    **updates
):
    config = await session.get(LLMConfig, config_id)
    
    for key, value in updates.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    await session.commit()
    await session.refresh(config)
    return config
```

### 7. 删除配置

```python
async def delete_config(session: AsyncSession, config_id: int):
    config = await session.get(LLMConfig, config_id)
    await session.delete(config)
    await session.commit()
```

## 业务逻辑

### 配置激活规则

```python
# 规则：每个用户只能有一个激活配置

async def ensure_single_active(session: AsyncSession, user_id: int, new_active_id: int):
    """确保只有一个配置被激活"""
    
    # 停用所有配置
    await session.execute(
        update(LLMConfig)
        .where(LLMConfig.user_id == user_id)
        .values(is_active=False)
    )
    
    # 激活新配置
    config = await session.get(LLMConfig, new_active_id)
    config.is_active = True
    
    await session.commit()
```

### 配置验证流程

```python
async def verify_config(session: AsyncSession, config: LLMConfig) -> bool:
    """验证配置是否可用"""
    
    # 1. 检查必填字段
    if not config.llm_provider_api_key:
        return False
    
    # 2. 测试 API 连接
    try:
        client = AsyncOpenAI(
            base_url=config.llm_provider_url,
            api_key=config.llm_provider_api_key
        )
        
        # 发送测试请求
        response = await client.chat.completions.create(
            model=config.llm_provider_model or "gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        
        # 更新验证状态
        config.is_verified = True
        config.test_status = "success"
        config.test_message = "验证成功"
        config.last_test_at = datetime.utcnow()
        
        await session.commit()
        return True
        
    except Exception as e:
        config.is_verified = False
        config.test_status = "failed"
        config.test_message = str(e)
        config.last_test_at = datetime.utcnow()
        
        await session.commit()
        return False
```

## 安全考虑

### 1. API Key 加密

⚠️ **重要：API Key 应该加密存储**

```python
from cryptography.fernet import Fernet

class LLMConfigService:
    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """加密 API Key"""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """解密 API Key"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
```

### 2. 敏感信息脱敏

在日志和 API 响应中隐藏敏感信息：

```python
def mask_api_key(api_key: str) -> str:
    """脱敏 API Key"""
    if not api_key or len(api_key) < 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"

# 示例
print(mask_api_key("sk-1234567890abcdef"))
# 输出: sk-1...cdef
```

### 3. 权限检查

确保用户只能访问自己的配置：

```python
async def get_config_with_permission(
    session: AsyncSession,
    config_id: int,
    user_id: int
):
    result = await session.execute(
        select(LLMConfig)
        .where(
            LLMConfig.id == config_id,
            LLMConfig.user_id == user_id  # 权限检查
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise PermissionError("无权访问此配置")
    
    return config
```

## 相关文件

### API 路由
- [`backend/app/api/routers/llm_config.py`](../api/routers/llm_config.md) - LLM 配置 API

### 服务层
- [`backend/app/services/llm_config_service.py`](../services/llm_config_service.md) - 配置管理服务
- [`backend/app/services/llm_service.py`](../services/llm_service.md) - LLM 调用服务

### 数据模型
- [`backend/app/models/user.py`](user.md) - 用户模型

### Schema
- [`backend/app/schemas/llm_config.py`](../schemas/llm_config.md) - 配置 Schema

## 最佳实践

### 1. 配置命名规范

```python
# ✅ 好的命名
"OpenAI GPT-4"
"Claude 3 Opus"
"本地 LLaMA 模型"

# ❌ 不好的命名
"配置1"
"test"
"aaa"
```

### 2. 测试频率

```python
# 建议：创建后立即测试
config = await create_config(session, data)
await test_config(session, config.id)

# 