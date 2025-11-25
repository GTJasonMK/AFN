# Repositories - 仓储层

## 概述

仓储层（Repository Layer）负责封装数据访问逻辑，提供统一的数据操作接口。所有仓储类都继承自 `BaseRepository`，实现了标准的CRUD操作。

## 仓储列表

### 核心仓储

1. **[BaseRepository](base.md)** - 通用仓储基类
   - 封装常见的增删改查操作
   - 使用泛型支持任意数据模型
   - 提供统一的数据访问接口

2. **[NovelRepository](novel_repository.md)** - 小说项目仓储
   - 项目查询与关联加载
   - 用户项目列表
   - 预加载所有关联数据

3. **[PartOutlineRepository](part_outline_repository.md)** - 分层大纲仓储
   - 部分大纲的CRUD操作
   - 批量创建和状态更新
   - 待生成部分查询

4. **[PromptRepository](prompt_repository.md)** - 提示词仓储
   - 提示词查询与列表
   - 按名称索引

### 配置相关仓储

5. **[LLMConfigRepository](llm_config_repository.md)** - LLM配置仓储
   - 多配置管理
   - 激活状态切换
   - 按用户和名称查询

6. **[SystemConfigRepository](system_config_repository.md)** - 系统配置仓储
   - 系统级配置存储
   - 按键查询

7. **[AdminSettingRepository](admin_setting_repository.md)** - 管理员配置仓储
   - 管理员KV配置
   - 值获取与设置

### 用户相关仓储

8. **[UserRepository](user_repository.md)** - 用户仓储
   - 用户查询（用户名、邮箱、外部ID）
   - 每日请求配额管理
   - 用户统计

9. **[UsageMetricRepository](usage_metric_repository.md)** - 使用统计仓储
   - 通用计数器
   - 自动创建机制

10. **[UpdateLogRepository](update_log_repository.md)** - 更新日志仓储
    - 日志列表查询
    - 按时间排序

## 设计模式

### 仓储模式（Repository Pattern）

仓储层采用经典的Repository模式，提供以下优势：

1. **关注点分离**：业务逻辑与数据访问分离
2. **可测试性**：易于Mock和单元测试
3. **可维护性**：数据访问逻辑集中管理
4. **复用性**：通用操作继承自基类

### 继承结构

```
BaseRepository (泛型基类)
    ├── NovelRepository
    ├── PartOutlineRepository
    ├── PromptRepository
    ├── LLMConfigRepository
    ├── SystemConfigRepository
    ├── AdminSettingRepository
    ├── UserRepository
    ├── UsageMetricRepository
    └── UpdateLogRepository
```

### 基类提供的通用方法

```python
class BaseRepository(Generic[ModelType]):
    async def get(**filters) -> Optional[ModelType]
    async def list(*, filters=None) -> Iterable[ModelType]
    async def add(instance) -> ModelType
    async def delete(instance) -> None
    async def update_fields(instance, **values) -> ModelType
```

## 使用示例

### 基本查询

```python
# 按ID查询
user = await user_repo.get(id=1)

# 按条件查询
config = await llm_config_repo.get(user_id=1, is_active=True)

# 列表查询
all_prompts = await prompt_repo.list()
user_configs = await llm_config_repo.list(filters={"user_id": 1})
```

### 创建和更新

```python
# 创建
new_user = User(username="john", email="john@example.com")
await user_repo.add(new_user)
await session.commit()

# 更新字段
await user_repo.update_fields(user, email="new@example.com")
await session.commit()

# 删除
await user_repo.delete(user)
await session.commit()
```

### 自定义方法

```python
# 各仓储类提供的专用方法
active_config = await llm_config_repo.get_active_config(user_id=1)
daily_count = await user_repo.get_daily_request(user_id=1)
project = await novel_repo.get_by_id(project_id="uuid")
```

## 最佳实践

### 1. 在Service层使用Repository

```python
class NovelService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.novel_repo = NovelRepository(session)
    
    async def get_user_projects(self, user_id: int):
        projects = await self.novel_repo.list_by_user(user_id)
        return [ProjectSchema.from_orm(p) for p in projects]
```

### 2. 事务管理

```python
# Repository负责数据操作，Service负责事务
async def create_with_transaction():
    novel_repo = NovelRepository(session)
    
    # Repository只做flush，不commit
    novel = await novel_repo.add(Novel(...))
    
    # Service层统一commit
    await session.commit()
```

### 3. 关联加载优化

```python
# 使用selectinload预加载关联数据
stmt = (
    select(NovelProject)
    .options(
        selectinload(NovelProject.chapters),
        selectinload(NovelProject.characters)
    )
)
```

## 性能优化

### 批量操作

```python
# 批量创建
part_outlines = [PartOutline(...) for _ in range(10)]
await part_outline_repo.batch_create(part_outlines)
```

### 索引使用

```python
# 确保查询字段有索引
await user_repo.get_by_username("john")  # username字段有索引
await user_repo.get_by_email("john@example.com")  # email字段有索引
```

### 查询优化

```python
# 只查询需要的字段
stmt = select(User.id, User.username).where(User.is_active == True)

# 使用count而不是len(list)
count = await user_repo.count_users()
```

## 相关文档

- **服务层**: [`backend/app/services/`](../services/)
- **数据模型**: [`backend/app/models/`](../models/)
- **数据库会话**: [`backend/app/db/session.py`](../db/session.md)