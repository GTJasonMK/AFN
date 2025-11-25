# Admin Setting Service - 管理员配置服务

## 文件概述

**文件路径**: `backend/app/services/admin_setting_service.py`  
**代码行数**: 27行  
**核心职责**: 管理员配置项服务，提供简单的KV（键值对）操作

## 核心功能

### 1. 获取配置值

```python
async def get(self, key: str, default: Optional[str] = None) -> Optional[str]
```

**使用示例**：
```python
admin_setting_service = AdminSettingService(session)

# 获取配置值
value = await admin_setting_service.get("maintenance_mode")
if value == "true":
    print("系统维护中")

# 使用默认值
smtp_server = await admin_setting_service.get("smtp.server", default="smtp.gmail.com")
print(f"SMTP服务器: {smtp_server}")
```

### 2. 设置配置值

```python
async def set(self, key: str, value: str) -> None
```

**特性**：
- 如果配置键已存在，则更新
- 如果配置键不存在，则创建

**使用示例**：
```python
# 开启维护模式
await admin_setting_service.set("maintenance_mode", "true")

# 设置公告信息
await admin_setting_service.set("announcement", "系统将于今晚22:00进行维护")

# 设置功能开关
await admin_setting_service.set("feature.new_ui", "enabled")
```

## 完整使用示例

### 维护模式管理

```python
async def enable_maintenance_mode(reason: str = "系统维护"):
    """开启维护模式"""
    admin_setting_service = AdminSettingService(session)
    
    await admin_setting_service.set("maintenance_mode", "true")
    await admin_setting_service.set("maintenance_reason", reason)
    
    print("维护模式已开启")

async def disable_maintenance_mode():
    """关闭维护模式"""
    admin_setting_service = AdminSettingService(session)
    
    await admin_setting_service.set("maintenance_mode", "false")
    await admin_setting_service.set("maintenance_reason", "")
    
    print("维护模式已关闭")

async def check_maintenance_mode():
    """检查维护模式状态"""
    admin_setting_service = AdminSettingService(session)
    
    is_maintenance = await admin_setting_service.get("maintenance_mode")
    if is_maintenance == "true":
        reason = await admin_setting_service.get("maintenance_reason", "系统维护中")
        raise HTTPException(status_code=503, detail=reason)
```

### 功能开关管理

```python
async def is_feature_enabled(feature_name: str) -> bool:
    """检查功能是否启用"""
    admin_setting_service = AdminSettingService(session)
    
    status = await admin_setting_service.get(f"feature.{feature_name}", "disabled")
    return status == "enabled"

async def toggle_feature(feature_name: str, enabled: bool):
    """切换功能开关"""
    admin_setting_service = AdminSettingService(session)
    
    status = "enabled" if enabled else "disabled"
    await admin_setting_service.set(f"feature.{feature_name}", status)
    
    print(f"功能 {feature_name} 已{'启用' if enabled else '禁用'}")

# 使用示例
if await is_feature_enabled("new_ui"):
    # 使用新UI
    pass
else:
    # 使用旧UI
    pass
```

### 系统配置管理

```python
async def get_system_info():
    """获取系统配置信息"""
    admin_setting_service = AdminSettingService(session)
    
    return {
        "version": await admin_setting_service.get("system.version", "1.0.0"),
        "environment": await admin_setting_service.get("system.env", "production"),
        "max_users": await admin_setting_service.get("system.max_users", "1000"),
        "backup_enabled": await admin_setting_service.get("backup.enabled", "true"),
    }

async def update_system_config(key: str, value: str):
    """更新系统配置"""
    admin_setting_service = AdminSettingService(session)
    
    # 验证配置键
    allowed_keys = [
        "system.version",
        "system.max_users",
        "backup.enabled",
        "maintenance_mode",
    ]
    
    if key not in allowed_keys:
        raise HTTPException(status_code=400, detail="不允许修改此配置")
    
    await admin_setting_service.set(key, value)
    print(f"配置 {key} 已更新为 {value}")
```

### 公告管理

```python
async def set_announcement(title: str, content: str):
    """设置系统公告"""
    admin_setting_service = AdminSettingService(session)
    
    await admin_setting_service.set("announcement.title", title)
    await admin_setting_service.set("announcement.content", content)
    await admin_setting_service.set("announcement.enabled", "true")

async def get_announcement() -> Optional[dict]:
    """获取系统公告"""
    admin_setting_service = AdminSettingService(session)
    
    enabled = await admin_setting_service.get("announcement.enabled")
    if enabled != "true":
        return None
    
    return {
        "title": await admin_setting_service.get("announcement.title", ""),
        "content": await admin_setting_service.get("announcement.content", ""),
    }

async def clear_announcement():
    """清除系统公告"""
    admin_setting_service = AdminSettingService(session)
    
    await admin_setting_service.set("announcement.enabled", "false")
```

## 推荐的配置键命名

```python
# 系统配置
"system.version"           # 系统版本
"system.env"               # 运行环境
"system.max_users"         # 最大用户数
"maintenance_mode"         # 维护模式
"maintenance_reason"       # 维护原因

# 功能开关
"feature.new_ui"           # 新UI
"feature.advanced_search"  # 高级搜索
"feature.export"           # 导出功能

# 公告配置
"announcement.enabled"     # 公告启用
"announcement.title"       # 公告标题
"announcement.content"     # 公告内容

# 备份配置
"backup.enabled"           # 备份启用
"backup.schedule"          # 备份计划
"backup.retention_days"    # 保留天数

# 邮件配置
"email.notifications"      # 邮件通知
"email.digest_time"        # 摘要发送时间
```

## 与SystemConfig的区别

### AdminSetting（本服务）
- **用途**：管理员内部配置
- **访问权限**：仅管理员
- **配置性质**：系统级、运维级配置
- **示例**：维护模式、功能开关、内部标志

### SystemConfig（ConfigService）
- **用途**：应用配置
- **访问权限**：可能对外暴露部分配置
- **配置性质**：应用级、业务级配置
- **示例**：LLM配置、SMTP配置、认证配置

**使用建议**：
```python
# 使用AdminSetting
await admin_setting_service.set("maintenance_mode", "true")  # 维护模式
await admin_setting_service.set("feature.beta", "enabled")   # 功能开关

# 使用SystemConfig
await config_service.upsert_config(
    SystemConfigCreate(
        key="llm.api_key",
        value="sk-xxxx",
        description="LLM API密钥"
    )
)
```

## 依赖关系

### 内部依赖
- [`AdminSettingRepository`](../repositories/admin_setting_repository.md) - 数据库操作
- [`AdminSetting`](../models/admin_setting.md) - 数据模型

### 调用方
- 管理后台API路由
- 中间件（维护模式检查）
- 系统监控服务

## 最佳实践

### 1. 使用有意义的键名

```python
# 好的做法：清晰的层级结构
"feature.new_ui"
"maintenance.mode"
"backup.enabled"

# 不推荐：扁平无结构
"newui"
"maint"
"backup"
```

### 2. 布尔值使用字符串

```python
# 好的做法：使用 "true"/"false"
await admin_setting_service.set("feature.enabled", "true")

# 检查时转换
enabled = await admin_setting_service.get("feature.enabled") == "true"

# 不推荐：混用多种表示
await admin_setting_service.set("feature.enabled", "1")  # 不一致
```

### 3. 提供默认值

```python
# 好的做法：总是提供合理的默认值
value = await admin_setting_service.get("max_users", default="1000")

# 不推荐：不处理None
value = await admin_setting_service.get("max_users")
if value is None:
    # 需要额外处理
    pass
```

## 相关文件

- **数据模型**: `backend/app/models/admin_setting.py`
- **仓储层**: `backend/app/repositories/admin_setting_repository.py`
- **系统配置服务**: [`config_service.py`](config_service.md)