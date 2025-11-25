# backend/app/models/system_config.py - 系统配置模型

## 文件概述

定义系统级配置项的数据模型，使用简单的键值对（Key-Value）结构存储系统全局配置，如LLM API Key、默认模型等。这些配置可以在运行时动态修改。

**文件路径：** `backend/app/models/system_config.py`  
**代码行数：** 14 行  
**复杂度：** ⭐ 简单

## 数据模型定义

### SystemConfig 类

```python
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

class SystemConfig(Base):
    """系统级配置项，例如默认 LLM API Key、模型名称等。"""
    
    __tablename__ = "system_configs"
    
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
```

## 字段详解

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `key` | `String(100)` | 主键 | 配置键名 |
| `value` | `Text` | 非空 | 配置值 |
| `description` | `String(255)` | 可选 | 配置说明 |

## 配置项类型

### 1. LLM 配置

| Key | 说明 | 示例值 |
|-----|------|--------|
| `llm.api_key` | LLM API密钥 | `sk-xxx` |
| `llm.base_url` | API基础URL | `https://api.openai.com/v1` |
| `llm.model` | 默认模型 | `gpt-4` |

### 2. SMTP 配置

| Key | 说明 | 示例值 |
|-----|------|--------|
| `smtp.server` | SMTP服务器 | `smtp.gmail.com` |
| `smtp.port` | SMTP端口 | `587` |
| `smtp.username` | SMTP用户名 | `user@example.com` |
| `smtp.password` | SMTP密码 | `password` |
| `smtp.from` | 发件人 | `Arboris Novel` |

### 3. 认证配置

| Key | 说明 | 示例值 |
|-----|------|--------|
| `auth.allow_registration` | 允许注册 | `true/false` |
| `auth.linuxdo_enabled` | Linux.do登录 | `true/false` |

### 4. 写作配置

| Key | 说明 | 示例值 |
|-----|------|--------|
| `writer.chapter_versions` | 章节版本数 | `3` |

## 数据库表结构

```sql
CREATE TABLE system_configs (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description VARCHAR(255)
);
```

## 使用示例

### 1. 创建配置

```python
from backend.app.models.system_config import SystemConfig

async def create_config(session: AsyncSession, key: str, value: str, description: str = None):
    config = SystemConfig(key=key, value=value, description=description)
    session.add(config)
    await session.commit()
```

### 2. 查询配置

```python
async def get_config(session: AsyncSession, key: str) -> Optional[str]:
    config = await session.get(SystemConfig, key)
    return config.value if config else None
```

### 3. 更新配置

```python
async def update_config(session: AsyncSession, key: str, value: str):
    config = await session.get(SystemConfig, key)
    if config:
        config.value = value
        await session.commit()
```

### 4. 批量查询

```python
async def get_configs_by_prefix(session: AsyncSession, prefix: str) -> dict[str, str]:
    result = await session.execute(
        select(SystemConfig).where(SystemConfig.key.like(f"{prefix}%"))
    )
    configs = result.scalars().all()
    return {c.key: c.value for c in configs}
```

## 初始化

配置在应用启动时从环境变量同步到数据库：

```python
# backend/app/db/init_db.py
from .system_config_defaults import SYSTEM_CONFIG_DEFAULTS

async def init_db():
    for entry in SYSTEM_CONFIG_DEFAULTS:
        value = entry.value_getter(settings)
        if value is None:
            continue
        
        existing = await session.get(SystemConfig, entry.key)
        if not existing:
            session.add(SystemConfig(
                key=entry.key,
                value=value,
                description=entry.description
            ))
```

## 相关文件

- [`backend/app/db/system_config_defaults.py`](../db/system_config_defaults.md) - 配置默认值映射
- [`backend/app/core/config.py`](../core/config.md) - 环境变量配置

---

**文档版本：** v1.0.0  
**最后更新：** 2025-11-06