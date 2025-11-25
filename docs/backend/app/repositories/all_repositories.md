# All Repositories - 所有仓储文档

本文档包含所有简单仓储类的说明。

---

## PartOutlineRepository - 分层大纲仓储

**文件**: `backend/app/repositories/part_outline_repository.py` (65行)

### 核心方法

```python
async def get_by_project_id(project_id: str) -> List[PartOutline]
async def get_by_part_number(project_id: str, part_number: int) -> Optional[PartOutline]
async def delete_by_project_id(project_id: str) -> None
async def batch_create(part_outlines: List[PartOutline]) -> List[PartOutline]
async def update_status(part_outline, status: str, progress: int) -> PartOutline
async def get_pending_parts(project_id: str) -> List[PartOutline]
```

### 使用示例

```python
# 获取项目的所有部分大纲
parts = await part_outline_repo.get_by_project_id("uuid-xxx")

# 批量创建
new_parts = [PartOutline(...) for _ in range(5)]
await part_outline_repo.batch_create(new_parts)

# 更新状态
await part_outline_repo.update_status(part, "completed", 100)

# 获取待生成的部分
pending = await part_outline_repo.get_pending_parts("uuid-xxx")
```

---

## PromptRepository - 提示词仓储

**文件**: `backend/app/repositories/prompt_repository.py` (19行)

### 核心方法

```python
async def get_by_name(name: str) -> Optional[Prompt]
async def list_all() -> Iterable[Prompt]
```

### 使用示例

```python
# 获取特定提示词
writing_prompt = await prompt_repo.get_by_name("writing")

# 获取所有提示词
all_prompts = await prompt_repo.list_all()
```

---

## LLMConfigRepository - LLM配置仓储

**文件**: `backend/app/repositories/llm_config_repository.py` (57行)

### 核心方法

```python
async def get_by_user(user_id: int) -> Optional[LLMConfig]
async def list_by_user(user_id: int) -> list[LLMConfig]
async def get_active_config(user_id: int) -> Optional[LLMConfig]
async def get_by_id(config_id: int, user_id: int) -> Optional[LLMConfig]
async def activate_config(config_id: int, user_id: int) -> None
async def get_by_name(user_id: int, config_name: str) -> Optional[LLMConfig]
```

### 使用示例

```python
# 获取激活的配置
active = await llm_config_repo.get_active_config(user_id=1)

# 获取所有配置
configs = await llm_config_repo.list_by_user(user_id=1)

# 激活配置（自动取消其他配置）
await llm_config_repo.activate_config(config_id=5, user_id=1)

# 按名称查询
config = await llm_config_repo.get_by_name(user_id=1, config_name="OpenAI GPT-4")
```

---

## UserRepository - 用户仓储

**文件**: `backend/app/repositories/user_repository.py` (62行)

### 核心方法

```python
async def get_by_username(username: str) -> Optional[User]
async def get_by_email(email: str) -> Optional[User]
async def get_by_external_id(external_id: str) -> Optional[User]
async def list_all() -> Iterable[User]
async def increment_daily_request(user_id: int) -> None
async def get_daily_request(user_id: int) -> int
async def count_users() -> int
```

### 使用示例

```python
# 多种查询方式
user = await user_repo.get_by_username("john")
user = await user_repo.get_by_email("john@example.com")
oauth_user = await user_repo.get_by_external_id("github:12345")

# 每日请求管理
await user_repo.increment_daily_request(user_id=1)
count = await user_repo.get_daily_request(user_id=1)

# 统计用户数
total = await user_repo.count_users()
```

---

## SystemConfigRepository - 系统配置仓储

**文件**: `backend/app/repositories/system_config_repository.py` (18行)

### 核心方法

```python
async def get_by_key(key: str) -> Optional[SystemConfig]
async def list_all() -> Iterable[SystemConfig]
```

### 使用示例

```python
# 获取配置
llm_key = await system_config_repo.get_by_key("llm.api_key")

# 获取所有配置
all_configs = await system_config_repo.list_all()
```

---

## AdminSettingRepository - 管理员配置仓储

**文件**: `backend/app/repositories/admin_setting_repository.py` (15行)

### 核心方法

```python
async def get_value(key: str) -> Optional[str]
```

### 使用示例

```python
# 获取配置值
maintenance = await admin_setting_repo.get_value("maintenance_mode")
```

---

## UsageMetricRepository - 使用统计仓储

**文件**: `backend/app/repositories/usage_metric_repository.py` (19行)

### 核心方法

```python
async def get_or_create(key: str) -> UsageMetric
```

### 使用示例

```python
# 自动创建或获取
counter = await usage_metric_repo.get_or_create("api.total_requests")
counter.value += 1
await session.commit()
```

---

## UpdateLogRepository - 更新日志仓储

**文件**: `backend/app/repositories/update_log_repository.py` (19行)

### 核心方法

```python
async def list() -> Iterable[UpdateLog]
async def list_latest(limit: int = 5) -> Iterable[UpdateLog]
```

### 使用示例

```python
# 获取所有日志
all_logs = await update_log_repo.list()

# 获取最新10条
latest = await update_log_repo.list_latest(limit=10)
```

---

## 通用模式

所有仓储都继承自 `BaseRepository`，因此都支持：

```python
# 基础CRUD
await repo.get(id=1)
await repo.list(filters={"active": True})
await repo.add(instance)
await repo.delete(instance)
await repo.update_fields(instance, field="value")
```

## 事务管理

```python
# 仓储只做flush，不做commit
await repo.add(instance)  # 内部调用flush

# Service层统一commit
await session.commit()
```

## 相关文档

- **基类**: [base.md](base.md)
- **服务层**: [`backend/app/services/`](../services/)
- **数据模型**: [`backend/app/models/`](../models/)