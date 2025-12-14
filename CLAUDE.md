# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 快速命令参考

```bash
# 一键启动（推荐）- 自动处理环境配置、依赖安装、启动服务
python run_app.py

# 分别启动（需要先手动配置环境）
cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8123
cd frontend && .venv\Scripts\activate && python main.py

# 数据库迁移（修改SQLAlchemy模型后必须执行）
cd backend && .venv\Scripts\activate && alembic revision --autogenerate -m "描述变更" && alembic upgrade head

# 测试
cd backend && .venv\Scripts\activate && pytest tests/ -v                    # 运行所有测试
cd backend && .venv\Scripts\activate && pytest tests/test_novel.py -v       # 运行单个文件
cd backend && .venv\Scripts\activate && pytest tests/test_novel.py::test_create -v  # 运行单个测试

# 查看日志
type storage\app.log           # 统一入口日志
type backend\storage\debug.log  # 后端详细日志

# 健康检查
curl http://localhost:8123/health

# 数据库调试
sqlite3 backend\storage\afn.db ".tables"
sqlite3 backend\storage\afn.db "SELECT * FROM novels LIMIT 5;"

# 依赖管理
cd backend && .venv\Scripts\activate && pip install -r requirements.txt
cd frontend && .venv\Scripts\activate && pip install -r requirements.txt

# 打包发布
build.bat
```

## 项目概述

AFN (Agents for Novel) 是AI辅助长篇小说创作的单机桌面应用。核心特点：**开箱即用、无需登录、本地存储**。

**技术栈**：
- 后端: Python 3.10+ / FastAPI 0.110.0 / SQLAlchemy 2.0 (异步) / aiosqlite
- 前端: PyQt6 6.6.1
- 数据库: SQLite (`backend/storage/afn.db`)
- 通信: HTTP REST API (端口 8123)

**架构特点**：
- 后端全异步：所有数据库操作和LLM调用使用 `async/await`
- 前端异步处理：使用 `AsyncWorker` 和 `QThread` 避免UI冻结
- 无认证系统：使用固定默认用户 `desktop_user`
- 嵌入服务：支持 OpenAI 兼容接口和 Ollama 本地模型

## 关键文件路径

| 类别 | 路径 | 说明 |
|------|------|------|
| 后端入口 | `backend/app/main.py` | FastAPI应用 |
| 前端入口 | `frontend/main.py` | PyQt6应用 |
| API客户端 | `frontend/api/client.py` | 前端HTTP封装 |
| 依赖注入 | `backend/app/core/dependencies.py` | get_session, get_*_service |
| 状态机 | `backend/app/core/state_machine.py` | 项目状态流转 |
| 异常定义 | `backend/app/exceptions.py` | 统一异常体系 |
| 提示词模板 | `backend/prompts/` | inspiration.md, writing.md等 |
| 主题管理 | `frontend/themes/theme_manager.py` | 深色/亮色主题 |
| 主题基类 | `frontend/components/base/theme_aware_widget.py` | UI组件主题感知 |

## 后端架构

分层结构：`API路由 -> Service -> Repository -> SQLAlchemy模型 -> 数据库`

```
backend/app/
├── api/routers/
│   ├── novels/              # 项目管理路由（灵感对话、蓝图、大纲）
│   └── writer/              # 写作阶段路由（章节生成、版本管理、RAG查询）
├── services/
│   ├── novel_service.py     # 项目管理、灵感对话
│   ├── llm_service.py       # LLM调用（流式/非流式）
│   ├── chapter_generation/  # 章节生成模块
│   │   ├── service.py       # 生成服务入口
│   │   ├── workflow.py      # 生成工作流
│   │   ├── context.py       # 上下文构建
│   │   ├── prompt_builder.py # 提示词构建
│   │   └── version_processor.py # 版本处理
│   ├── part_outline/        # 分部大纲模块
│   │   ├── service.py       # 大纲服务入口
│   │   └── workflow.py      # 生成工作流
│   ├── rag/                 # RAG增强模块
│   │   ├── query_builder.py     # 多维查询构建
│   │   ├── context_builder.py   # 分层上下文
│   │   ├── context_compressor.py # 上下文压缩
│   │   ├── temporal_retriever.py # 时序感知检索
│   │   ├── outline_retriever.py  # 大纲RAG检索
│   │   ├── scene_extractor.py    # 场景状态提取
│   │   └── utils.py              # 公共工具函数
│   ├── embedding_service.py # 嵌入服务（OpenAI兼容/Ollama）
│   └── incremental_indexer.py # 增量索引
├── repositories/            # 数据访问层（继承BaseRepository）
├── models/                  # SQLAlchemy ORM模型
├── schemas/                 # Pydantic数据模型
└── utils/
    ├── json_utils.py        # LLM响应JSON解析
    ├── sse_helpers.py       # SSE事件工具
    └── content_normalizer.py # 内容规范化
```

## 前端架构

基于QStackedWidget的单页面导航：

```
frontend/
├── windows/
│   ├── main_window.py       # 主窗口（导航容器）
│   ├── inspiration_mode/    # 灵感对话模块
│   ├── novel_detail/        # 项目详情模块
│   └── writing_desk/        # 写作台模块
├── pages/home_page.py       # 首页（项目卡片）
├── components/              # UI组件库
├── themes/                  # 主题系统
└── utils/
    ├── async_worker.py      # 异步任务
    └── sse_worker.py        # SSE流式响应
```

**页面导航**：`MainWindow.navigateTo(page_type, params)` / `goBack()`
**页面类型**：`HOME`, `INSPIRATION`, `WORKSPACE`, `DETAIL`, `WRITING_DESK`, `SETTINGS`
**生命周期钩子**：`refresh(**params)`, `onShow()`, `onHide()`

## 项目状态机

```
DRAFT -> BLUEPRINT_READY -> [PART_OUTLINES_READY] -> CHAPTER_OUTLINES_READY -> WRITING -> COMPLETED
```

**状态说明**：
- `DRAFT`：灵感对话进行中
- `BLUEPRINT_READY`：蓝图生成完成
- `PART_OUTLINES_READY`：分部大纲就绪（仅长篇>=50章）
- `CHAPTER_OUTLINES_READY`：章节大纲就绪
- `WRITING`：章节写作中
- `COMPLETED`：全部章节完成

**回退机制**：状态机支持回退，如 `WRITING -> CHAPTER_OUTLINES_READY` 允许修改大纲后重新生成

## 核心开发模式

### 前端异步操作
```python
from utils.async_worker import AsyncWorker

worker = AsyncWorker(lambda: client.generate_blueprint(project_id))
worker.success.connect(on_success)       # 成功信号
worker.error.connect(on_error)           # 错误信息（字符串）
worker.error_detail.connect(on_detail)   # 详细错误（包含status_code, response_json等）
worker.start()
# 取消任务：worker.cancel()
```

### 前端SSE流式响应
```python
from utils.sse_worker import SSEWorker

worker = SSEWorker(url, payload)
worker.token_received.connect(lambda token: self.text_edit.insertPlainText(token))
worker.complete.connect(on_complete)
worker.error.connect(on_error)
worker.start()
```

**SSE事件类型**（后端 -> 前端）：
- `token`: 流式文本 `{"token": "字符"}`
- `complete`: 完成 `{"ui_control": {...}, "is_complete": bool}`
- `error`: 错误 `{"message": "错误描述"}`

**后端SSE工具**（`backend/app/utils/sse_helpers.py`）：
```python
from app.utils.sse_helpers import sse_event
yield sse_event("token", {"token": char})
yield sse_event("complete", {"is_complete": True})
```

### 后端LLM调用
```python
# 非流式
response = await llm_service.get_llm_response(user_id, system_prompt, user_prompt, payload)

# 流式
async for chunk in llm_service.get_llm_response_stream(user_id, system_prompt, user_prompt, payload):
    yield chunk
```

### JSON解析工具
```python
from app.utils.json_utils import parse_llm_json_or_fail, parse_llm_json_safe, extract_llm_content

# Router层：解析失败抛HTTPException
blueprint_data = parse_llm_json_or_fail(llm_response, "蓝图生成失败")

# Service层：解析失败返回None，不中断
data = parse_llm_json_safe(record.content)

# 提取内容和元数据
content, metadata = extract_llm_content(llm_response, content_key="content")
```
自动处理：`<think>`标签移除、Markdown代码块提取、中文引号替换

### 主题感知组件
```python
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager

class MyComponent(ThemeAwareWidget):
    def __init__(self, parent=None):
        self.my_label = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        layout = QVBoxLayout(self)
        self.my_label = QLabel("Hello")
        layout.addWidget(self.my_label)

    def _apply_theme(self):
        if self.my_label:
            self.my_label.setStyleSheet(f"color: {theme_manager.TEXT_PRIMARY};")
```

### 异常处理
后端使用统一异常体系（`backend/app/exceptions.py`），所有异常继承自 `AFNException`：
```python
from app.exceptions import (
    # 4xx 客户端错误
    ResourceNotFoundError,        # 404 - 资源不存在
    PermissionDeniedError,        # 403 - 权限不足
    InvalidParameterError,        # 400 - 参数错误
    InvalidStateTransitionError,  # 400 - 非法状态转换
    ConflictError,               # 409 - 资源冲突
    # 5xx 服务端错误
    LLMServiceError,             # 503 - LLM服务错误
    LLMConfigurationError,       # 500 - LLM配置错误
    VectorStoreError,            # 503 - 向量库错误
    DatabaseError,               # 500 - 数据库错误
    JSONParseError,              # 500 - JSON解析错误
    # 业务逻辑异常
    BlueprintNotReadyError,      # 400 - 蓝图未生成
    ChapterNotGeneratedError,    # 400 - 章节未生成
    GenerationCancelledError,    # 400 - 生成任务被取消
    PromptTemplateNotFoundError, # 500 - 提示词模板不存在
    ConversationExtractionError, # 400 - 对话历史提取失败
)
```

前端错误处理：
```python
from utils.error_handler import handle_errors
from utils.message_service import MessageService, confirm

@handle_errors("加载项目")
def loadProject(self):
    self.project = self.api_client.get_novel(self.project_id)
```

### 事务管理
**标准模式**：Service层用 `flush()` 不commit，Route层统一 `commit()`
**例外**：状态管理方法、长任务状态跟踪、配置CRUD可以commit

### Repository模式
所有Repository继承`BaseRepository`，已封装常见CRUD操作：
```python
from app.repositories.base import BaseRepository

class NovelRepository(BaseRepository[Novel]):
    model = Novel

# 基类提供的方法：
# await repo.get(id=novel_id)                    # 单条查询
# await repo.list(filters={"user_id": user_id}) # 条件查询
# await repo.list_all()                          # 全部查询
# await repo.add(instance)                       # 添加（自动flush）
# await repo.delete(instance)                    # 删除
# await repo.update_fields(instance, **values)   # 更新字段
# await repo.bulk_add(instances)                 # 批量添加
# await repo.bulk_delete_by_ids(ids)             # 批量删除
# await repo.delete_by_project_id(project_id)    # 按项目ID级联删除
# await repo.delete_by_field(field_name, value)  # 按字段删除
# await repo.count_by_field(field_name, value)   # 按字段计数
```

## 嵌入服务配置

支持两种嵌入服务：
- **OpenAI兼容接口**：使用远程API（如OpenAI、中转站服务）
- **Ollama本地模型**：使用本地部署的嵌入模型

配置在设置页面的"嵌入配置"中完成，支持动态切换。

## 项目约定

1. **不使用emoji**：代码、注释、日志中避免emoji，防止编码错误
2. **中文注释**：所有代码注释和文档使用中文
3. **同步更新**：修改API时必须同步更新前后端（schemas、路由、API客户端）
4. **灵感对话术语**：使用"灵感对话"(inspiration)而非"概念对话"(concept)
5. **禁止通配符导入**：禁止 `from PyQt6.QtWidgets import *`
6. **端口配置**：后端固定端口 `8123`，修改需同步更改 `run_app.py` 和 `frontend/api/client.py`
7. **复用优先**：新建文件或服务前，先搜索是否已有可复用的组件
8. **API文档**：运行后可访问 `http://localhost:8123/docs` 查看完整API文档

## RAG增强系统

章节生成时使用增强型RAG检索，确保故事连贯性：

```
章节生成请求 -> QueryBuilder（多维查询）-> TemporalRetriever（时序检索）
    -> ContextBuilder（分层构建）-> ContextCompressor（压缩）-> LLM生成
```

**核心组件**：
- `EnhancedQueryBuilder`：基于大纲、角色、伏笔构建多维查询
- `TemporalAwareRetriever`：时序感知的向量检索
- `SmartContextBuilder`：分层上下文构建
- `ContextCompressor`：智能压缩以适应token限制
- `OutlineRAGRetriever`：大纲生成阶段的RAG检索
- `SceneStateExtractor`：从章节内容提取场景状态

**上下文分层**：
- 必需层：蓝图核心、角色名、当前大纲、前章结尾
- 重要层：涉及角色详情、高优先级伏笔、RAG摘要
- 参考层：世界观、检索片段、其他伏笔

**数据流**：
- 章节选择版本 -> `chapter_ingest_service`（向量化）-> `rag_chunks`表
- 章节选择版本 -> `chapter_analysis_service`（LLM分析）-> `analysis_data`字段
- 分析完成 -> `incremental_indexer` -> `character_state_index` + `foreshadowing_index`

## 常用API端点

| 功能 | 端点 |
|------|------|
| 项目CRUD | `GET/POST /api/novels`, `DELETE /api/novels/{id}` |
| 灵感对话(流式) | `POST /api/novels/{id}/inspiration/converse-stream` |
| 生成蓝图 | `POST /api/novels/{id}/blueprint/generate` |
| 章节大纲 | `POST /api/novels/{id}/chapter-outlines/generate` |
| 分部大纲 | `POST /api/writer/novels/{id}/parts/generate` |
| 增量大纲 | `POST /api/writer/novels/{id}/chapter-outlines/generate-by-count` |
| 生成章节 | `POST /api/writer/novels/{id}/chapters/{num}/generate` |
| 选择版本 | `POST /api/writer/novels/{id}/chapters/select` |
| LLM配置 | `GET/POST /api/llm-configs`, `POST /api/llm-configs/{id}/activate` |

完整API列表见 `docs/FEATURES.md`

## 数据库核心表

`novels`, `novel_conversations`, `novel_blueprints`, `part_outlines`, `chapters`, `chapter_versions`, `llm_configs`, `prompts`, `rag_chunks`, `character_state_index`, `foreshadowing_index`

## 故障排查

| 问题 | 排查步骤 |
|------|----------|
| 后端启动失败 | 检查虚拟环境、端口8123占用、查看 `backend/storage/debug.log` |
| 前端无法连接 | 确认后端启动、检查端口配置 |
| LLM调用失败 | 设置页测试连接、检查API Key |

## 相关文档

- `docs/FEATURES.md` - 功能特性和完整API列表
- `docs/SSE_STREAMING_IMPLEMENTATION.md` - SSE流式输出实现
- `backend/docs/RAG_OPTIMIZATION_PLAN.md` - RAG系统优化计划

## 支持的LLM服务

- OpenAI (GPT-3.5, GPT-4, GPT-4o)
- 通义千问
- 智谱 ChatGLM
- 百度文心一言
- Moonshot (Kimi)
- DeepSeek
- Ollama（本地部署）
- 所有 OpenAI 兼容接口（如2API、API2D等中转服务）
