
# backend/app/api/routers/__init__.py - API 路由聚合

## 文件概述

负责聚合所有 API 路由模块，为 FastAPI 应用提供统一的路由入口。桌面版（PyQt）不包含认证相关路由，直接使用默认用户访问所有功能。

**文件路径：** `backend/app/api/routers/__init__.py`  
**代码行数：** 16 行  
**复杂度：** ⭐ 简单

## 核心功能

### 路由聚合

```python
from fastapi import APIRouter
from . import llm_config, novels, writer

# 创建主路由器
api_router = APIRouter()

# 桌面版路由（无需认证）
api_router.include_router(novels.router)
api_router.include_router(writer.router)
api_router.include_router(llm_config.router)
```

**包含的路由模块：**

| 模块 | 路由前缀 | 说明 |
|------|---------|------|
| `novels` | `/api/novels` | 小说项目管理 |
| `writer` | `/api/writer` | 章节写作和评估 |
| `llm_config` | `/api/llm-config` | LLM 配置管理 |

## 路由结构

### API 路由树

```
/api/
├── novels/
│   ├── GET    /                    # 获取小说列表
│   ├── POST   /                    # 创建新小说
│   ├── GET    /{novel_id}          # 获取小说详情
│   ├── PUT    /{novel_id}          # 更新小说信息
│   ├── DELETE /{novel_id}          # 删除小说
│   ├── POST   /{novel_id}/outline  # 生成大纲
│   ├── GET    /{novel_id}/chapters # 获取章节列表
│   └── ...
│
├── writer/
│   ├── POST   /write-chapter       # 写作章节
│   ├── POST   /evaluate-chapter    # 评估章节
│   ├── POST   /regenerate-chapter  # 重新生成
│   └── ...
│
└── llm-config/
    ├── GET    /                    # 获取 LLM 配置
    ├── POST   /                    # 创建配置
    ├── PUT    /{config_id}         # 更新配置
    ├── DELETE /{config_id}         # 删除配置
    └── POST   /test                # 测试连接
```

## 桌面版 vs Web 版

### 桌面版（当前）

```python
# 桌面版不包含认证路由
api_router.include_router(novels.router)
api_router.include_router(writer.router)
api_router.include_router(llm_config.router)
```

**特点：**
- ❌ 无认证路由（auth）
- ❌ 无管理后台路由（admin）
- ✅ 直接访问所有功能
- ✅ 使用默认桌面用户

### Web 版（对比）

```python
# Web 版包含完整路由
api_router.include_router(auth.router)      # 认证路由
api_router.include_router(admin.router)     # 管理路由
api_router.include_router(novels.router)    # 小说路由
api_router.include_router(writer.router)    # 写作路由
api_router.include_router(llm_config.router)# 配置路由
```

**特点：**
- ✅ 用户认证和注册
- ✅ 管理后台
- ✅ 权限控制
- ✅ 多用户支持

## 使用示例

### 1. 在主应用中使用

```python
# backend/app/main.py

from fastapi import FastAPI
from .api.routers import api_router

app = FastAPI()

# 包含所有 API 路由
app.include_router(api_router)
```

**生成的路由：**
- `POST /api/novels/` - 创建小说
- `GET /api/novels/{novel_id}` - 获取小说
- `POST /api/writer/write-chapter` - 写作章节
- `GET /api/llm-config/` - 获取配置

### 2. 添加全局路由前缀

```python
app.include_router(api_router, prefix="/api/v1")
```

**生成的路由：**
- `POST /api/v1/novels/`
- `GET /api/v1/novels/{novel_id}`
- `POST /api/v1/writer/write-chapter`

### 3. 添加全局标签

```python
app.include_router(api_router, tags=["API"])
```

**OpenAPI 文档中：**
```
API
├── Novels
├── Writer
└── LLM Config
```

## 路由模块详解

### 1. novels 路由

```python
from . import novels

api_router.include_router(novels.router)
```

**功能：**
- 小说项目的 CRUD 操作
- 大纲生成和管理
- 章节列表查询
- 项目状态管理

**详细文档：** [`novels.md`](novels.md)

### 2. writer 路由

```python
from . import writer

api_router.include_router(writer.router)
```

**功能：**
- 章节写作（AI 生成）
- 章节评估
- 重新生成章节
- 版本管理

**详细文档：** [`writer.md`](writer.md)

### 3. llm_config 路由

```python
from . import llm_config

api_router.include_router(llm_config.router)
```

**功能：**
- LLM 配置管理
- API 连接测试
- 配置切换

**详细文档：** [`llm_config.md`](llm_config.md)

## 路由设计模式

### 1. 模块化路由

每个功能模块独立定义路由：

```python
# novels.py
router = APIRouter(prefix="/api/novels", tags=["Novels"])

@router.get("/")
async def list_novels():
    pass

# writer.py
router = APIRouter(prefix="/api/writer", tags=["Writer"])

@router.post("/write-chapter")
async def write_chapter():
    pass
```

### 2. 路由聚合

在 `__init__.py` 中聚合：

```python
api_router = APIRouter()
api_router.include_router(novels.router)
api_router.include_router(writer.router)
```

### 3. 分层路由

```
应用层 (main.py)
    ↓
聚合层 (__init__.py)
    ↓
模块层 (novels.py, writer.py)
    ↓
端点层 (@router.get, @router.post)
```

## FastAPI 路由特性

### 1. 路由前缀

```python
# 模块级别前缀
router = APIRouter(prefix="/api/novels")

@router.get("/")           # → /api/novels/
@router.get("/{id}")       # → /api/novels/{id}
```

### 2. 路由标签

```python
router = APIRouter(tags=["Novels"])

# OpenAPI 文档中分组显示
```

### 3. 依赖注入

```python
router = APIRouter(dependencies=[Depends(verify_token)])

# 所有端点自动应用依赖
```

### 4. 响应模型

```python
router = APIRouter(response_model=NovelResponse)

# 所有端点自动验证响应
```

## 桌面版路由特点

### 1. 无认证要求

```python
# ✅ 桌面版：直接访问
@router.get("/novels/")
async def list_novels(session: AsyncSession = Depends(get_session)):
    # 使用默认用户
    pass

# ❌ Web 版：需要认证
@router.get("/novels/")
async def list_novels(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # 使用当前登录用户
    pass
```

### 2. 简化的依赖

```python
# backend/app/core/dependencies.py

async def get_default_user(
    session: AsyncSession = Depends(get_session)
) -> User:
    """桌面版：返回默认用户"""
    result = await session.execute(
        select(User).where(User.username == "desktop_user")
    )
    return result.scalar_one()
```

### 3. 单用户环境

所有操作都归属于 `desktop_user`：

```python
@router.post("/novels/")
async def create_novel(
    data: NovelCreate,
    user: User = Depends(get_default_user),
    session: AsyncSession = Depends(get_session)
):
    novel = Novel(
        title=data.title,
        user_id=user.id,  # 总是 desktop_user.id
    )
    # ...
```

## 路由注册顺序

### 注册顺序很重要

```python
# ✅ 正确：从具体到通用
@router.get("/novels/recent")      # 先注册
@router.get("/novels/{novel_id}")  # 后注册

# ❌ 错误：通用路由在前
@router.get("/novels/{novel_id}")  # {novel_id} 会匹配 "recent"
@router.get("/novels/recent")      # 永远不会匹配
```

### 当前路由顺序

```python
api_router.include_router(novels.router)     # 1
api_router.include_router(writer.router)     # 2
api_router.include_router(llm_config.router) # 3
```

**影响：**
- 路由匹配按顺序进行
- 相同路径时，先注册的优先

## 相关文件

### 路由模块
- [`backend/app/api/routers/novels.py`](novels.md) - 小说项目路由
- [`backend/app/api/routers/writer.py`](writer.md) - 章节写作路由
- [`backend/app/api/routers/llm_config.py`](llm_config.md) - LLM 配置路由

### 应用入口
- [`backend/app/main.py`](../../main.md) - FastAPI 应用主文件

### 依赖注入
- [`backend/app/core/dependencies.py`](../../core/dependencies.md) - 依赖注入函数

## 扩展路由

### 添加新路由模块

1. **创建路由模块：**

```python
# backend/app/api/routers/analytics.py

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"]
)

@router.get("/stats")
async def get_stats():
    return {"total_novels": 100}
```

2. **在 `__init__.py` 中注册：**

```python
from . import llm_config, novels, writer, analytics

api_router.include_router(novels.router)
api_router.include_router(writer.router)
api_router.include_router(llm_config.router)
api_router.include_router(analytics.router)  # 新增
```

3. **访问新路由：**

```
GET /api/analytics/stats
```

## 测试路由

### 1. 使用 FastAPI 测试客户端

```python
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_list_novels():
    response = client.get("/api/novels/")
    assert response.status_code == 200
```

### 2. 查看所有路由

```python
from backend.app.main import app

for route in app.routes:
    print(f"{route.methods} {route.path}")
```

**输出示例：**
```
{'GET'} /api/novels/
{'POST'} /api/novels/
{'GET'} /api/novels/{novel_id}
{'POST'} /api/writer/write-chapter
{'GET'} /api/llm-config/
```

### 3. OpenAPI 文档

访问自动生成的 API 文档：

```
http://localhost:8000/docs          # Swagger UI
http://localhost:8000/redoc         # ReDoc
http://localhost:8000/openapi.json  # OpenAPI Schema
```

## 注意事项

### 1. 循环导入

⚠️ **避免循环导入**

```python
# ❌ 错误：在模块间相互导入
# novels.py
from .writer import some_function

# writer.py
from .novels import another_function
```

**解决方案：**
- 共享代码放到 services 或 utils
- 使用依赖注入传递功能

### 2. 路由冲突

⚠️ **避免路由路径冲突**

```python
# ❌ 冲突
# novels.py
@router.get("/status")

# writer.py
@router.get("/status")

# 两个都是 /api/status，会冲突
```

**解决方案：**
```python
# ✅ 使用前缀区分
# novels.py: /api/novels/status
# writer.py: /api/writer/status
```

### 3. 依赖顺序

⚠️ **注意依赖注入的顺序**

```python
# 数据库会话必须在需要它的依赖之前
async def get_novel(
    novel_id: int,
    session: AsyncSession = Depends(get_session),  # 先
    user: User = Depends(get_default_user),         # 后（依赖 session）
):
    pass
```

## 总结

`__init__.py` 虽然代码简洁（仅 16 行），但是 API 路由架构的核心：

**核心职责：**
1. ✅ 聚合所有路由模块
2. ✅ 提供统一的路由入口
3. ✅ 