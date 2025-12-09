# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 快速命令参考

```bash
# 一键启动（推荐）
start_all.bat

# 分别启动
cd backend && start.bat       # 后端 http://localhost:8123
cd frontend && python main.py # 前端

# 停止服务
stop_all.bat  # 或在后端窗口按Ctrl+C

# 依赖安装
cd backend && .venv\Scripts\activate && pip install -r requirements.txt
cd frontend && .venv\Scripts\activate && pip install -r requirements.txt

# 数据库迁移（修改SQLAlchemy模型后必须执行）
cd backend && .venv\Scripts\activate && alembic revision --autogenerate -m "描述变更" && alembic upgrade head

# 查看日志
type backend\storage\debug.log

# 健康检查
curl http://localhost:8123/health

# 数据库调试
sqlite3 backend\storage\arboris.db ".tables"
sqlite3 backend\storage\arboris.db "SELECT * FROM novels LIMIT 5;"
```

**关键文件路径**：
- 后端入口：`backend/app/main.py`
- 前端入口：`frontend/main.py`
- API客户端：`frontend/api/client.py`
- 默认用户依赖：`backend/app/core/dependencies.py`
- 项目状态机：`backend/app/core/state_machine.py`
- 提示词模板：`backend/prompts/`
- 自定义异常：`backend/app/exceptions.py`
- 主题管理：`frontend/themes/theme_manager.py`
- RAG模块：`backend/app/services/rag/`

## 项目概述

Arboris Novel PyQt桌面版是AI辅助长篇小说创作的单机桌面应用。核心特点：**开箱即用、无需登录、本地存储**。

## 核心技术栈

- **后端**: Python 3.10+ + FastAPI 0.110.0 + SQLAlchemy 2.0 (异步) + aiosqlite
- **前端**: PyQt6 6.6.1 (桌面GUI应用)
- **数据库**: SQLite (本地存储于 `backend/storage/`)
- **LLM集成**: OpenAI API兼容接口
- **通信**: HTTP REST API (端口固定 8123)

**架构特点**：
- 后端全异步：所有数据库操作和LLM调用使用 `async/await`
- 前端异步处理：使用 `AsyncWorker` 和 `QThread` 避免UI冻结
- 无认证系统：使用固定默认用户 `desktop_user`

## 后端架构

分层结构：`API路由 -> Service -> Repository -> SQLAlchemy模型 -> 数据库`

```
backend/app/
├── api/routers/          # API路由
│   ├── novels/           # 小说项目路由（灵感对话、蓝图、大纲、导出）
│   ├── writer/           # 写作阶段路由（章节生成、版本管理）
│   ├── llm_config.py     # LLM配置管理
│   └── settings.py       # 应用设置
├── core/
│   ├── dependencies.py   # 依赖注入（get_default_user, get_session, get_*_service）
│   ├── state_machine.py  # 项目状态机
│   └── config.py         # 配置管理
├── models/               # SQLAlchemy ORM模型
├── schemas/              # Pydantic数据模型
├── repositories/         # 数据访问层（继承BaseRepository）
├── services/             # 业务逻辑层
│   ├── novel_service.py           # 项目管理、灵感对话、蓝图生成
│   ├── llm_service.py             # LLM调用（支持流式和非流式）
│   ├── chapter_context_service.py # 增强型章节上下文（RAG检索）
│   ├── chapter_generation_service.py  # 章节生成核心逻辑
│   ├── chapter_analysis_service.py    # 章节分析（LLM提取元数据）
│   ├── chapter_ingest_service.py      # 章节入库（向量化）
│   ├── foreshadowing_service.py       # 伏笔追踪管理
│   ├── incremental_indexer.py         # 增量索引（角色状态/伏笔）
│   └── rag/                           # RAG增强模块
│       ├── query_builder.py           # 多维查询构建
│       ├── temporal_retriever.py      # 时序感知检索
│       ├── context_builder.py         # 分层上下文构建
│       └── context_compressor.py      # 上下文压缩
└── utils/
    ├── exception_helpers.py  # 统一异常处理工具
    └── json_utils.py         # JSON处理
```

## 前端架构（PyQt6单页面应用）

基于QStackedWidget的导航系统：

```
frontend/
├── main.py               # 应用入口
├── windows/              # 页面窗口
│   ├── main_window.py        # 主窗口（导航容器）
│   ├── inspiration_mode/     # 灵感对话模块
│   ├── novel_detail/         # 项目详情模块
│   └── writing_desk/         # 写作台模块
├── pages/home_page.py    # 首页（项目卡片网格）
├── components/           # UI组件库
├── themes/               # 主题系统
├── api/client.py         # API客户端
└── utils/
    ├── async_worker.py       # 异步任务
    ├── sse_worker.py         # SSE流式响应处理
    ├── error_handler.py      # @handle_errors装饰器
    ├── message_service.py    # 消息显示服务
    └── formatters.py         # 状态/字数格式化
```

**页面导航**：`MainWindow.navigateTo(page_type, params)` / `goBack()`
**页面类型**：`HOME`, `INSPIRATION`, `WORKSPACE`, `DETAIL`, `WRITING_DESK`, `SETTINGS`
**生命周期钩子**：`refresh(**params)`, `onShow()`, `onHide()`

## 核心开发约定

### 1. 项目状态机
```
DRAFT -> BLUEPRINT_READY -> [PART_OUTLINES_READY] -> CHAPTER_OUTLINES_READY -> WRITING -> COMPLETED
```
- 长篇（>=50章）：先生成分部大纲（每25章一部分），再生成章节大纲
- 短篇（<50章）：直接生成章节大纲

### 2. 前端异步操作
```python
from utils.async_worker import AsyncWorker

worker = AsyncWorker(lambda: client.generate_blueprint(project_id))
worker.finished.connect(on_success)
worker.error.connect(on_error)
worker.start()
```

### 3. 前端SSE流式响应
```python
from utils.sse_worker import SSEWorker

worker = SSEWorker(url, payload)
worker.token_received.connect(lambda token: self.text_edit.insertPlainText(token))
worker.complete.connect(on_complete)
worker.error.connect(on_error)
worker.start()
```

### 4. 后端流式响应
```python
# 非流式
response = await llm_service.get_llm_response(user_id, system_prompt, user_prompt, payload)

# 流式
async for chunk in llm_service.get_llm_response_stream(user_id, system_prompt, user_prompt, payload):
    yield chunk
```

### 5. 主题系统
继承 `ThemeAwareWidget` 实现主题感知组件：
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

### 6. 事务管理
**标准模式**：Service层用 `flush()` 不commit，Route层统一 `commit()`
**例外**：状态管理方法、长任务状态跟踪、配置CRUD可以commit

### 7. 异常处理
```python
from app.utils.exception_helpers import log_exception
from app.exceptions import ResourceNotFoundError

if not project:
    raise ResourceNotFoundError("项目", project_id)
```

### 8. 前端错误处理
```python
from utils.error_handler import handle_errors
from utils.message_service import MessageService, confirm

@handle_errors("加载项目")
def loadProject(self):
    self.project = self.api_client.get_novel(self.project_id)

MessageService.show_success(self, "操作成功")

if confirm(self, "确定要删除吗？", "确认删除"):
    self.delete()
```

## 项目特殊约定

1. **不使用emoji**：代码、注释、日志中避免emoji，防止编码错误
2. **中文注释**：所有代码注释和文档使用中文
3. **同步更新**：修改API时必须同步更新前后端
4. **灵感对话术语**：使用"灵感对话"(inspiration)而非"概念对话"(concept)
5. **禁止通配符导入**：`from PyQt6.QtWidgets import *` 不允许
6. **端口配置**：后端固定端口 `8123`，修改需同步更改：`start_all.bat`、`frontend/api/client.py`、`backend/start.bat`

## RAG增强系统

章节生成时使用增强型RAG检索，确保故事连贯性：

```
章节生成请求
    |
查询构建（QueryBuilder）
├── 主查询：章节标题+摘要+写作要点
├── 角色查询：提取涉及角色的历史
├── 伏笔查询：待回收伏笔的相关内容
└── 场景查询：场景历史事件
    |
时序感知检索（TemporalRetriever）
├── 向量相似度检索
├── 时序权重加成（临近章节优先）
└── 综合得分排序
    |
上下文构建（ContextBuilder）
├── 必需层：蓝图核心、角色名、当前大纲、前章结尾
├── 重要层：涉及角色详情、高优先级伏笔、RAG摘要
└── 参考层：世界观、检索片段、其他伏笔
    |
上下文压缩（ContextCompressor）
└── 按优先级截断，确保不超token限制
    |
LLM生成章节
```

**关键数据流**：
- 章节选择版本 -> `chapter_ingest_service`（文本切分、向量化） -> `rag_chunks`表
- 章节选择版本 -> `chapter_analysis_service`（LLM分析） -> `analysis_data`字段
- 分析完成 -> `incremental_indexer`（更新索引） -> `character_state_index` + `foreshadowing_index`

## 常用API端点

```bash
# 项目管理
POST   /api/novels                           # 创建项目
GET    /api/novels                           # 项目列表
GET    /api/novels/{id}                      # 项目详情
DELETE /api/novels/{id}                      # 删除项目

# 灵感对话与蓝图
POST   /api/novels/{id}/inspiration/converse # 灵感对话
POST   /api/novels/{id}/blueprint/generate   # 生成蓝图
GET    /api/novels/{id}/blueprint            # 获取蓝图

# 大纲生成
POST   /api/novels/{id}/chapter-outlines/generate              # 短篇章节大纲
POST   /api/writer/novels/{id}/parts/generate                  # 长篇部分大纲
POST   /api/writer/novels/{id}/chapter-outlines/generate-by-count  # 增量章节大纲

# 章节写作
POST   /api/writer/novels/{id}/chapters/{num}/generate  # 生成章节版本
POST   /api/writer/novels/{id}/chapters/select          # 选择版本
GET    /api/writer/novels/{id}/chapters                 # 章节列表

# LLM配置
GET    /api/llm-configs                      # 配置列表
POST   /api/llm-configs                      # 创建配置
POST   /api/llm-configs/{id}/activate        # 激活配置
POST   /api/llm-configs/test                 # 测试连接
```

## 数据库Schema

核心表：`users`、`novels`、`novel_conversations`、`novel_blueprints`、`part_outlines`、`chapters`、`chapter_versions`、`llm_configs`、`prompts`、`rag_chunks`、`rag_summaries`、`character_state_index`、`foreshadowing_index`

## 故障排查

| 问题 | 排查步骤 |
|------|----------|
| 后端启动失败 | 检查虚拟环境、重新安装依赖、检查端口占用、查看日志 |
| 前端无法连接 | 确认后端启动、检查端口配置、查看防火墙 |
| LLM调用失败 | 在设置页测试连接、检查API Key、查看后端日志 |

## 相关文档

- `backend/docs/RAG_OPTIMIZATION_PLAN.md` - RAG系统优化计划（包含Phase 1-2已实现的架构）
