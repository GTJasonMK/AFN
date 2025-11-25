# backend/app/main.py - FastAPI 应用入口

## 文件概述

这是 Arboris-Novel PyQt 桌面版的 FastAPI 后端应用入口文件，负责装配路由、依赖项注入和生命周期管理。此版本专为 PyQt 桌面应用设计，不包含管理后台功能。

## 主要功能

### 1. 日志配置

**关键特性：**
- 使用 `dictConfig` 进行详细的日志配置
- 支持控制台和文件双输出（`storage/debug.log`）
- 配置多个日志命名空间：`backend`、`app`、`backend.app`、`backend.api`、`backend.services` 等
- 日志级别从 `settings.logging_level` 读取

**重要说明：**
```python
# 重要：必须先配置 logging，再导入 api_router
# 否则 router 模块中的 logger 会在配置完成前被创建，导致日志无法正常输出
```

日志配置包括：
- 格式化器：`"%(asctime)s [%(levelname)s] %(name)s - %(message)s"`
- 处理器：控制台输出 + 文件输出（UTF-8编码）
- 根日志级别：WARNING

### 2. 应用生命周期管理

**`lifespan()` 函数（第98-105行）：**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库，并预热提示词缓存"""
    await init_db()
    async with AsyncSessionLocal() as session:
        prompt_service = PromptService(session)
        await prompt_service.preload()
    yield
```

**功能说明：**
1. **数据库初始化：** 调用 `init_db()` 创建表结构并确保默认用户存在
2. **提示词预热：** 通过 `PromptService.preload()` 将提示词加载到缓存，提升响应速度
3. **生命周期管理：** 使用 `yield` 实现启动和关闭逻辑的分离

### 3. FastAPI 应用配置

**应用实例（第108-113行）：**
```python
app = FastAPI(
    title=f"{settings.app_name} - PyQt Desktop Edition",
    debug=settings.debug,
    version="1.0.0-pyqt",
    lifespan=lifespan,
)
```

**配置特点：**
- 标题包含 "PyQt Desktop Edition" 标识
- 版本号：`1.0.0-pyqt`
- Debug模式：从配置读取
- 关联生命周期管理函数

### 4. CORS 中间件配置

**桌面版 CORS 配置（第115-122行）：**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**说明：**
- 允许来源：仅本地地址（`localhost` 和 `127.0.0.1`）
- 允许凭证：支持携带 Cookie
- 允许所有 HTTP 方法和请求头

### 5. 路由注册

**第124行：**
```python
app.include_router(api_router)
```

从 `backend.app.api.routers` 导入并注册所有 API 路由。

### 6. 健康检查接口

**端点（第128-137行）：**
```python
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """健康检查接口，返回应用状态。"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0-pyqt",
        "edition": "Desktop (PyQt)",
    }
```

**功能：**
- 提供两个健康检查端点：`/health` 和 `/api/health`
- 返回应用状态、名称、版本和版本类型

## 依赖项

### 核心模块
- `fastapi`：Web 框架
- `fastapi.middleware.cors`：CORS 支持
- `logging`：日志记录
- `contextlib.asynccontextmanager`：异步上下文管理

### 内部模块
- `.core.config.settings`：应用配置
- `.db.init_db.init_db`：数据库初始化
- `.services.prompt_service.PromptService`：提示词服务
- `.db.session.AsyncSessionLocal`：数据库会话工厂
- `.api.routers.api_router`：API 路由聚合

## 启动流程

1. **加载配置：** 从环境变量或 `.env` 文件读取配置
2. **配置日志：** 设置日志处理器、格式化器和级别
3. **导入路由：** 在日志配置完成后导入 `api_router`
4. **创建应用：** 实例化 FastAPI 应用
5. **注册中间件：** 添加 CORS 中间件
6. **注册路由：** 包含所有 API 路由
7. **生命周期启动：**
   - 初始化数据库表结构
   - 创建默认桌面用户
   - 预加载提示词到缓存
8. **应用就绪：** 开始接受请求

## 日志输出示例

启动时会输出：
```
================================================================================
Arboris-Novel PyQt版 后端服务启动，logging 配置已完成
日志级别: INFO
日志文件: backend/storage/debug.log
================================================================================
```

## 注意事项

1. **日志配置顺序：** 必须在导入路由之前完成日志配置
2. **桌面版特性：** 此版本无需用户认证，使用默认桌面用户
3. **CORS 限制：** 仅允许本地访问，不支持远程连接
4. **数据库初始化：** 启动时自动创建表和默认用户
5. **提示词缓存：** 启动时预加载，提升首次请求速度

## 相关文件

- `backend/app/core/config.py` - 应用配置
- `backend/app/db/init_db.py` - 数据库初始化
- `backend/app/api/routers/__init__.py` - 路由聚合
- `backend/app/services/prompt_service.py` - 提示词服务