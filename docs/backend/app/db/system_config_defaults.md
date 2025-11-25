
# backend/app/db/system_config_defaults.py - 系统配置默认值

## 文件概述

定义系统配置项的默认值映射，将环境变量配置（Settings）与数据库存储的系统配置（SystemConfig）关联起来。这是配置管理的桥梁层，用于在应用启动时自动同步配置到数据库。

**文件路径：** `backend/app/db/system_config_defaults.py`  
**代码行数：** 110 行  
**复杂度：** ⭐⭐ 中等

## 核心数据结构

### 1. SystemConfigDefault 类

```python
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass(frozen=True)
class SystemConfigDefault:
    key: str
    value_getter: Callable[[Settings], Optional[str]]
    description: Optional[str] = None
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `key` | `str` | 配置键名（如 `llm.api_key`） |
| `value_getter` | `Callable` | 从 Settings 获取值的函数 |
| `description` | `Optional[str]` | 配置项的描述文本 |

**特点：**
- `frozen=True`：不可变对象，确保配置定义安全
- 使用 lambda 函数延迟获取配置值
- 支持可选的描述信息

### 2. SYSTEM_CONFIG_DEFAULTS 列表

```python
SYSTEM_CONFIG_DEFAULTS: list[SystemConfigDefault] = [
    SystemConfigDefault(
        key="llm.api_key",
        value_getter=lambda config: config.openai_api_key,
        description="默认 LLM API Key，用于后台调用大模型。",
    ),
    # ... 更多配置项
]
```

**配置项总数：** 17 个

## 配置项分类

### 1. LLM 配置（3 项）

```python
# 1. API Key
SystemConfigDefault(
    key="llm.api_key",
    value_getter=lambda config: config.openai_api_key,
    description="默认 LLM API Key，用于后台调用大模型。",
)

# 2. Base URL
SystemConfigDefault(
    key="llm.base_url",
    value_getter=lambda config: _to_optional_str(config.openai_base_url),
    description="默认大模型 API Base URL。",
)

# 3. 模型名称
SystemConfigDefault(
    key="llm.model",
    value_getter=lambda config: config.openai_model_name,
    description="默认 LLM 模型名称。",
)
```

**用途：**
- AI 模型调用的基础配置
- 支持自定义 API 端点
- 可配置不同的模型

### 2. SMTP 邮件配置（5 项）

```python
# SMTP 服务器
SystemConfigDefault(
    key="smtp.server",
    value_getter=lambda config: config.smtp_server,
    description="用于发送邮件验证码的 SMTP 服务器地址。",
)

# SMTP 端口
SystemConfigDefault(
    key="smtp.port",
    value_getter=lambda config: _to_optional_str(config.smtp_port),
    description="SMTP 服务端口。",
)

# SMTP 用户名
SystemConfigDefault(
    key="smtp.username",
    value_getter=lambda config: config.smtp_username,
    description="SMTP 登录用户名。",
)

# SMTP 密码
SystemConfigDefault(
    key="smtp.password",
    value_getter=lambda config: config.smtp_password,
    description="SMTP 登录密码。",
)

# 发件人
SystemConfigDefault(
    key="smtp.from",
    value_getter=lambda config: config.email_from,
    description="邮件显示的发件人名称或邮箱。",
)
```

**用途：**
- 发送验证码邮件
- 发送通知邮件
- （Web 版使用，桌面版可能不需要）

### 3. 认证配置（2 项）

```python
# 注册开关
SystemConfigDefault(
    key="auth.allow_registration",
    value_getter=lambda config: _bool_to_text(config.allow_registration),
    description="是否允许用户自助注册。",
)

# Linux.do OAuth
SystemConfigDefault(
    key="auth.linuxdo_enabled",
    value_getter=lambda config: _bool_to_text(config.enable_linuxdo_login),
    description="是否启用 Linux.do OAuth 登录。",
)
```

**用途：**
- 控制用户注册
- 第三方登录集成
- （桌面版不使用认证功能）

### 4. Linux.do OAuth 配置（6 项）

```python
# Client ID
SystemConfigDefault(
    key="linuxdo.client_id",
    value_getter=lambda config: config.linuxdo_client_id,
    description="Linux.do OAuth Client ID。",
)

# Client Secret
SystemConfigDefault(
    key="linuxdo.client_secret",
    value_getter=lambda config: config.linuxdo_client_secret,
    description="Linux.do OAuth Client Secret。",
)

# Redirect URI
SystemConfigDefault(
    key="linuxdo.redirect_uri",
    value_getter=lambda config: _to_optional_str(config.linuxdo_redirect_uri),
    description="Linux.do OAuth 回调地址。",
)

# Auth URL
SystemConfigDefault(
    key="linuxdo.auth_url",
    value_getter=lambda config: _to_optional_str(config.linuxdo_auth_url),
    description="Linux.do OAuth 授权地址。",
)

# Token URL
SystemConfigDefault(
    key="linuxdo.token_url",
    value_getter=lambda config: _to_optional_str(config.linuxdo_token_url),
    description="Linux.do OAuth Token 获取地址。",
)

# User Info URL
SystemConfigDefault(
    key="linuxdo.user_info_url",
    value_getter=lambda config: _to_optional_str(config.linuxdo_user_info_url),
    description="Linux.do 用户信息接口地址。",
)
```

**用途：**
- Linux.do 社区 OAuth 登录
- （Web 版功能，桌面版不使用）

### 5. 写作配置（1 项）

```python
SystemConfigDefault(
    key="writer.chapter_versions",
    value_getter=lambda config: _to_optional_str(config.writer_chapter_versions),
    description="每次生成章节的候选版本数量。",
)
```

**用途：**
- 控制 AI 生成章节时产生多少个候选版本
- 用户可以选择最佳版本

## 工具函数

### 1. _to_optional_str

```python
def _to_optional_str(value: Optional[object]) -> Optional[str]:
    return str(value) if value is not None else None
```

**功能：**
- 将任意类型转换为字符串
- 如果值为 None，返回 None
- 用于处理可选配置项

**示例：**
```python
_to_optional_str(8080)        # "8080"
_to_optional_str("localhost") # "localhost"
_to_optional_str(None)        # None
```

### 2. _bool_to_text

```python
def _bool_to_text(value: bool) -> str:
    return "true" if value else "false"
```

**功能：**
- 将布尔值转换为字符串 "true"/"false"
- 数据库存储为文本格式

**示例：**
```python
_bool_to_text(True)   # "true"
_bool_to_text(False)  # "false"
```

## 配置同步流程

### 在数据库初始化时使用

```python
# backend/app/db/init_db.py

from .system_config_defaults import SYSTEM_CONFIG_DEFAULTS

async def init_db():
    async with AsyncSessionLocal() as session:
        # 遍历所有默认配置
        for entry in SYSTEM_CONFIG_DEFAULTS:
            # 1. 从 Settings 获取值
            value = entry.value_getter(settings)
            
            # 2. 跳过空值
            if value is None:
                continue
            
            # 3. 检查数据库中是否存在
            existing = await session.get(SystemConfig, entry.key)
            
            if existing:
                # 4. 更新描述（如果变化）
                if entry.description and existing.description != entry.description:
                    existing.description = entry.description
            else:
                # 5. 创建新配置
                session.add(
                    SystemConfig(
                        key=entry.key,
                        value=value,
                        description=entry.description,
                    )
                )
        
        await session.commit()
```

**流程图：**

```
开始同步
    ↓
遍历 SYSTEM_CONFIG_DEFAULTS
    ↓
┌─────────────────────────┐
│ entry.value_getter()    │ ← 从 Settings 获取值
└───────────┬─────────────┘
            ↓
        值是 None?
       ╱          ╲
     是             否
      ↓              ↓
   跳过         检查数据库
                    ↓
              配置已存在?
             ╱          ╲
           是             否
            ↓              ↓
      更新描述        创建新配置
            ↓              ↓
        ────┴──────────────┘
            ↓
      下一个配置
            ↓
      同步完成
```

## 使用示例

### 1. 添加新配置项

如果需要添加新的系统配置：

```python
SYSTEM_CONFIG_DEFAULTS.append(
    SystemConfigDefault(
        key="ai.max_tokens",
        value_getter=lambda config: _to_optional_str(config.ai_max_tokens),
        description="AI 生成的最大 token 数量。",
    )
)
```

### 2. 修改配置描述

更新配置项的描述：

```python
SystemConfigDefault(
    key="llm.api_key",
    value_getter=lambda config: config.openai_api_key,
    description="OpenAI API Key，用于调用 GPT 模型。",  # 更新描述
)
```

### 3. 使用复杂转换

对于需要特殊处理的配置：

```python
def _format_url(url: Optional[str]) -> Optional[str]:
    """确保 URL 以 / 结尾"""
    if url and not url.endswith('/'):
        return url + '/'
    return url

SystemConfigDefault(
    key="llm.base_url",
    value_getter=lambda config: _format_url(config.openai_base_url),
    description="LLM API 基础 URL。",
)
```

## 配置键命名规范

### 命名约定

使用点号分隔的层级结构：

```
<模块>.<子模块>.<配置项>

示例：
- llm.api_key           (LLM 模块的 API Key)
- smtp.server           (SMTP 模块的服务器)
- auth.allow_registration (认证模块的注册开关)
- linuxdo.client_id     (Linux.do 模块的客户端 ID)
```

### 层级结构

```
llm/
  ├─ api_key
  ├─ base_url
  └─ model

smtp/
  ├─ server
  ├─ port
  ├─ username
  ├─ password
  └─ from

auth/
  ├─ allow_registration
  └─ linuxdo_enabled

linuxdo/
  ├─ client_id
  ├─ client_secret
  ├─ redirect_uri
  ├─ auth_url
  ├─ token_url
  └─ user_info_url

writer/
  └─ chapter_versions
```

## 与其他模块的关系

### 1. Settings 配置类

```python
# backend/app/core/config.py

class Settings(BaseSettings):
    # LLM 配置
    openai_api_key: str
    openai_base_url: Optional[str] = None
    openai_model_name: str = "gpt-4"
    
    # SMTP 配置
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    # ...
```

**关系：**
- Settings 从环境变量读取配置
- SystemConfigDefault 将 Settings 映射到数据库

### 2. SystemConfig 模型

```python
# backend/app/models/system_config.py

class SystemConfig(Base):
    __tablename__ = "systemconfig"
    
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
```

**关系：**
- SystemConfigDefault 定义如何填充 SystemConfig 表
- 数据库存储可运行时修改的配置

### 3. 初始化流程

```python
# backend/app/db/init_db.py

from .system_config_defaults import SYSTEM_CONFIG_DEFAULTS

async def init_db():
    # 使用 SYSTEM_CONFIG_DEFAULTS 同步配置
    for entry in SYSTEM_CONFIG_DEFAULTS:
        # ...
```

**关系：**
- init_db 使用此文件同步配置
- 应用启动时自动执行

## 配置优先级

### 配置来源优先级

```
1. 数据库配置（SystemConfig 表）
   ↓
2. 环境变量（Settings）
   ↓
3. 默认值（Settings 中的默认值）
```

**示例：**

```python
# 1. 环境变量（.env 文件）
OPENAI_API_KEY=sk-xxx

# 2. 启动时同步到数据库
llm.api_key = sk-xxx

# 3. 运行时可以在数据库中修改
UPDATE systemconfig SET value='sk-yyy' WHERE key='llm.api_key';

# 4. 下次重启时，数据库的值保持不变（不会被环境变量覆盖）
```

## 桌面版 vs Web 版

### 桌面版（当前）

**使用的配置：**
- ✅ LLM 配置（api_key, base_url, model）
- ✅ 写作配置（chapter_versions）
- ❌ SMTP 配置（不发送邮件）
- ❌ 认证配置（无需认证）
- ❌ Linux.do OAuth（无需 OAuth）

### Web 版

**使用的配置：**
- ✅ 所有配置项都使用
- ✅ SMTP 用于发送验证码
- 