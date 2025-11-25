
# backend/app/db/init_db.py - 数据库初始化

## 文件概述

负责应用启动时的数据库初始化工作，包括确保数据库存在、创建表结构、初始化默认用户、同步系统配置、加载默认提示词等。这是应用生命周期中的关键环节。

**文件路径：** `backend/app/db/init_db.py`  
**代码行数：** 126 行  
**复杂度：** ⭐⭐⭐ 重要

## 核心功能

### 1. 主初始化函数（init_db）

```python
async def init_db() -> None:
    """初始化数据库结构并确保默认桌面用户存在（PyQt版）。"""
    
    # 1. 确保数据库存在
    await _ensure_database_exists()
    
    # 2. 创建所有表结构
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 3. 初始化数据
    async with AsyncSessionLocal() as session:
        # 创建默认用户
        # 同步系统配置
        # 加载默认提示词
```

**初始化流程：**

```
应用启动
    ↓
检查数据库是否存在
    ↓
创建所有表结构
    ↓
创建默认桌面用户
    ↓
同步系统配置到数据库
    ↓
加载默认提示词
    ↓
初始化完成
```

### 2. 数据库创建（_ensure_database_exists）

```python
async def _ensure_database_exists() -> None:
    """在首次连接前确认数据库存在，针对不同驱动做最小化准备工作。"""
    
    url = make_url(settings.sqlalchemy_database_uri)
    
    if url.get_backend_name() == "sqlite":
        # SQLite：确保目录存在
        db_path = Path(url.database or "").expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # MySQL：执行 CREATE DATABASE
        admin_engine = create_async_engine(admin_url)
        async with admin_engine.begin() as conn:
            await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database}`"))
```

**支持的数据库：**
- **SQLite**：自动创建数据库文件目录
- **MySQL**：自动创建数据库（如果不存在）

### 3. 默认用户创建

```python
# 检查是否存在默认桌面用户
desktop_user_exists = await session.execute(
    select(User).where(User.username == "desktop_user")
)

if not desktop_user_exists.scalars().first():
    desktop_user = User(
        username="desktop_user",
        email="desktop@example.com",
        hashed_password=hash_password("desktop"),
        is_admin=False,  # 桌面版不需要管理员
    )
    session.add(desktop_user)
    await session.commit()
```

**默认用户信息：**
- **用户名**：`desktop_user`
- **邮箱**：`desktop@example.com`
- **密码**：`desktop`（实际不会使用）
- **管理员**：`False`

### 4. 系统配置同步

```python
for entry in SYSTEM_CONFIG_DEFAULTS:
    value = entry.value_getter(settings)
    if value is None:
        continue
    
    existing = await session.get(SystemConfig, entry.key)
    if existing:
        # 更新描述（如果变化）
        if entry.description and existing.description != entry.description:
            existing.description = entry.description
        continue
    
    # 创建新配置
    session.add(
        SystemConfig(
            key=entry.key,
            value=value,
            description=entry.description,
        )
    )
```

**同步的配置项：**
- LLM API 配置（api_key, base_url, model）
- SMTP 邮件配置
- 认证配置（注册开关、OAuth）
- 写作配置（章节版本数）

### 5. 提示词加载（_ensure_default_prompts）

```python
async def _ensure_default_prompts(session: AsyncSession) -> None:
    """加载 backend/prompts/ 目录下的所有 .md 文件到数据库"""
    
    prompts_dir = Path(__file__).resolve().parents[2] / "prompts"
    
    # 获取已存在的提示词
    result = await session.execute(select(Prompt.name))
    existing_names = set(result.scalars().all())
    
    # 遍历 .md 文件
    for prompt_file in sorted(prompts_dir.glob("*.md")):
        name = prompt_file.stem
        if name in existing_names:
            continue
        
        content = prompt_file.read_text(encoding="utf-8")
        session.add(Prompt(name=name, content=content))
```

**默认提示词文件：**
- `concept.md` - 概念设计
- `evaluation.md` - 评估
- `extraction.md` - 提取
- `outline.md` - 大纲
- `part_outline.md` - 部分大纲
- `screenwriting.md` - 剧本
- `writing.md` - 写作

## 详细流程图

```
┌─────────────────────────────────────┐
│      应用启动 (FastAPI lifespan)     │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│    1. _ensure_database_exists()     │
│    ┌─────────────────────────────┐  │
│    │ SQLite? → 创建目录          │  │
│    │ MySQL?  → CREATE DATABASE   │  │
│    └─────────────────────────────┘  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│   2. Base.metadata.create_all()     │
│   创建所有表结构：                   │
│   - novel                            │
│   - user                             │
│   - llmconfig                        │
│   - partoutline                      │
│   - prompt                           │
│   - systemconfig                     │
│   - 等...                            │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│   3. 检查并创建 desktop_user        │
│   ┌─────────────────────────────┐  │
│   │ SELECT * FROM user          │  │
│   │ WHERE username='desktop_...'│  │
│   │                             │  │
│   │ 不存在? → INSERT user       │  │
│   └─────────────────────────────┘  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│   4. 同步系统配置                    │
│   遍历 SYSTEM_CONFIG_DEFAULTS：     │
│   ┌─────────────────────────────┐  │
│   │ llm.api_key                 │  │
│   │ llm.base_url                │  │
│   │ llm.model                   │  │
│   │ smtp.*                      │  │
│   │ auth.*                      │  │
│   │ linuxdo.*                   │  │
│   │ writer.*                    │  │
│   └─────────────────────────────┘  │
│   存在? → 更新描述                  │
│   不存在? → INSERT                  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│   5. _ensure_default_prompts()      │
│   扫描 backend/prompts/*.md：       │
│   ┌─────────────────────────────┐  │
│   │ concept.md                  │  │
│   │ evaluation.md               │  │
│   │ extraction.md               │  │
│   │ outline.md                  │  │
│   │ part_outline.md             │  │
│   │ screenwriting.md            │  │
│   │ writing.md                  │  │
│   └─────────────────────────────┘  │
│   存在? → 跳过                      │
│   不存在? → INSERT                  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│        数据库初始化完成              │
│        应用可以正常使用              │
└─────────────────────────────────────┘
```

## 使用示例

### 1. 在应用启动时调用

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.app.db.init_db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    yield
    # 关闭时的清理工作（如果有）

app = FastAPI(lifespan=lifespan)
```

### 2. 手动初始化

```python
import asyncio
from backend.app.db.init_db import init_db

async def main():
    """手动初始化数据库"""
    await init_db()
    print("数据库初始化完成")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. 测试环境初始化

```python
import pytest
from backend.app.db.init_db import init_db

@pytest.fixture(scope="session")
async def setup_database():
    """测试前初始化数据库"""
    await init_db()
    yield
    # 测试后清理（可选）
```

## SQLite 路径处理

### 路径解析逻辑

```python
db_path = Path(url.database or "").expanduser()

if not db_path.is_absolute():
    # 相对路径：基于项目根目录
    project_root = Path(__file__).resolve().parents[2]
    db_path = (project_root / db_path).resolve()

# 创建父目录
db_path.parent.mkdir(parents=True, exist_ok=True)
```

**路径示例：**

| 配置 | 解析结果 |
|------|---------|
| `sqlite:///storage/arboris.db` | `项目根/storage/arboris.db` |
| `sqlite:////tmp/test.db` | `/tmp/test.db`（绝对路径） |
| `sqlite:///~/data/app.db` | `用户目录/data/app.db` |

### 目录创建

```python
db_path.parent.mkdir(parents=True, exist_ok=True)
```

**功能：**
- `parents=True`：创建所有中间目录
- `exist_ok=True`：目录存在时不报错

**示例：**
```
配置: sqlite:///storage/data/arboris.db

创建:
项目根/
  └─ storage/         ← 创建
      └─ data/        ← 创建
          └─ arboris.db  ← 数据库文件
```

## MySQL 数据库创建

### 管理员连接

```python
admin_url = URL.create(
    drivername=url.drivername,
    username=url.username,
    password=url.password,
    host=url.host,
    port=url.port,
    database=None,  # 连接到服务器而非特定数据库
    query=url.query,
)

admin_engine = create_async_engine(
    admin_url.render_as_string(hide_password=False),
    isolation_level="AUTOCOMMIT",  # 自动提交模式
)
```

### 创建数据库

```python
async with admin_engine.begin() as conn:
    await conn.execute(
        text(f"CREATE DATABASE IF NOT EXISTS `{database}`")
    )
```

**SQL 语句：**
```sql
CREATE DATABASE IF NOT EXISTS `arboris_novel`;
```

**注意事项：**
- 使用反引号包裹数据库名（防止关键字冲突）
- `IF NOT EXISTS`：避免重复创建错误
- 自动提交模式：不需要手动 COMMIT

## 表结构创建

```python
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

**创建的表：**

| 表名 | 说明 | 模型类 |
|------|------|--------|
| `novel` | 小说项目 | `Novel` |
| `user` | 用户 | `User` |
| `llmconfig` | LLM 配置 | `LLMConfig` |
| `partoutline` | 部分大纲 | `PartOutline` |
| `prompt` | 提示词 | `Prompt` |
| `systemconfig` | 系统配置 | `SystemConfig` |
| `adminsetting` | 管理设置 | `AdminSetting` |
| `updatelog` | 更新日志 | `UpdateLog` |
| `usagemetric` | 使用统计 | `UsageMetric` |
| `userdailyrequest` | 用户请求统计 | `UserDailyRequest` |

**特点：**
- `Base.metadata.create_all` 会创建所有继承自 `Base` 的模型对应的表
- 如果表已存在，不会重复创建
- 会自动创建索引和外键约束

## 默认用户设计

### PyQt 桌面版特点

```python
desktop_user = User(
    username="desktop_user",
    email="desktop@example.com",
    hashed_password=hash_password("desktop"),
    is_admin=False,  # 桌面版不需要管理员权限
)
```

**设计理念：**
- 桌面应用是单用户环境
- 不需要真正的身份验证
- 简化用户体验
- 与 Web 版代码兼容

### 并发创建保护

```python
try:
    await session.commit()
    logger.info("默认桌面用户创建完成：desktop_user")
except IntegrityError:
    await session.rollback()
    logger.exception("默认桌面用户创建失败，可能是并发启动导致")
```

**保护机制：**
- 捕获 `IntegrityError`（唯一约束冲突）
- 