# backend/app/models/admin_setting.py - 管理员设置模型

## 文件概述

定义后台管理配置项的数据模型，使用简单的键值对（Key-Value）结构存储管理后台的配置信息。与 [`SystemConfig`](system_config.md) 不同，此模型专门用于后台管理界面的配置。

**文件路径：** `backend/app/models/admin_setting.py`  
**代码行数：** 13 行  
**复杂度：** ⭐ 简单

## 数据模型定义

### AdminSetting 类

```python
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from ..db.base import Base

class AdminSetting(Base):
    """后台配置项，采用简单的 KV 结构。"""
    
    __tablename__ = "admin_settings"
    
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
```

## 字段详解

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `key` | `String(64)` | 主键 | 配置键名（最长64字符）|
| `value` | `Text` | 非空 | 配置值（支持长文本）|

## 数据库表结构

```sql
CREATE TABLE admin_settings (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT NOT NULL
);
```

## 配置项类型

### 1. 界面配置

| Key | 说明 | 示例值 |
|-----|------|--------|
| `theme` | 主题样式 | `light/dark` |
| `logo_url` | Logo URL | `/static/logo.png` |
| `site_title` | 站点标题 | `Arboris Novel 管理后台` |

### 2. 功能开关

| Key | 说明 | 示例值 |
|-----|------|--------|
| `maintenance_mode` | 维护模式 | `true/false` |
| `debug_panel` | 调试面板 | `true/false` |
| `analytics_enabled` | 统计分析 | `true/false` |

### 3. 通知配置

| Key | 说明 | 示例值 |
|-----|------|--------|
| `notification.email` | 通知邮箱 | `admin@example.com` |
| `notification.webhook` | Webhook URL | `https://hooks.example.com` |

## 使用示例

### 1. 创建配置

```python
from backend.app.models.admin_setting import AdminSetting

async def create_admin_setting(session: AsyncSession, key: str, value: str):
    """创建管理员配置"""
    setting = AdminSetting(key=key, value=value)
    session.add(setting)
    await session.commit()
    return setting
```

### 2. 查询配置

```python
async def get_admin_setting(session: AsyncSession, key: str) -> Optional[str]:
    """查询配置值"""
    setting = await session.get(AdminSetting, key)
    return setting.value if setting else None
```

### 3. 更新配置

```python
async def update_admin_setting(session: AsyncSession, key: str, value: str):
    """更新配置（不存在则创建）"""
    setting = await session.get(AdminSetting, key)
    if setting:
        setting.value = value
    else:
        setting = AdminSetting(key=key, value=value)
        session.add(setting)
    await session.commit()
```

### 4. 删除配置

```python
async def delete_admin_setting(session: AsyncSession, key: str):
    """删除配置"""
    setting = await session.get(AdminSetting, key)
    if setting:
        await session.delete(setting)
        await session.commit()
```

### 5. 批量查询

```python
async def get_all_admin_settings(session: AsyncSession) -> dict[str, str]:
    """获取所有配置"""
    result = await session.execute(select(AdminSetting))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}
```

## 与 SystemConfig 的区别

| 特性 | AdminSetting | SystemConfig |
|------|--------------|--------------|
| **用途** | 后台管理界面配置 | 系统级全局配置 |
| **Key 长度** | 最长 64 字符 | 最长 100 字符 |
| **Description** | ❌ 无 | ✅ 有 |
| **配置示例** | 主题、Logo、通知 | API Key、SMTP、认证 |
| **初始化** | 手动创建 | 从环境变量同步 |

## 典型应用场景

### 1. 维护模式控制

```python
async def is_maintenance_mode(session: AsyncSession) -> bool:
    """检查是否处于维护模式"""
    value = await get_admin_setting(session, "maintenance_mode")
    return value == "true"

async def toggle_maintenance(session: AsyncSession, enabled: bool):
    """切换维护模式"""
    await update_admin_setting(
        session, 
        "maintenance_mode", 
        "true" if enabled else "false"
    )
```

### 2. 站点信息管理

```python
async def get_site_info(session: AsyncSession) -> dict:
    """获取站点信息"""
    return {
        "title": await get_admin_setting(session, "site_title"),
        "logo": await get_admin_setting(session, "logo_url"),
        "theme": await get_admin_setting(session, "theme"),
    }
```

## 相关文件

- [`backend/app/models/system_config.py`](system_config.md) - 系统配置模型（相似但用途不同）
- [`backend/app/repositories/admin_setting_repository.py`](../repositories/admin_setting_repository.md) - 数据访问层
- [`backend/app/services/admin_setting_service.py`](../services/admin_setting_service.md) - 业务逻辑层

## 注意事项

1. **Key 长度限制**：最长 64 字符，超过会导致数据库错误
2. **无描述字段**：不支持 description，需要在代码或文档中说明配置含义
3. **类型安全**：value 存储为 Text，使用时需要自行转换类型
4. **并发安全**：更新时建议使用乐观锁或事务

---

**文档版本：** v1.0.0  
**最后更新：** 2025-11-06