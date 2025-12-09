# AFN Backend (Agents for Novel)

这是 AFN (Agents for Novel) 项目的后端服务，包含所有核心业务功能。

## 🎯 核心特性

### ✨ 开箱即用，无需登录
- ❌ 无需注册账号
- ❌ 无需登录认证
- ✅ 启动即可使用
- ✅ 自动创建默认用户
- ✅ 所有数据本地存储

桌面版专为单机使用设计，首次启动时自动创建默认用户（desktop_user），所有操作自动关联到该用户，无需任何认证流程。

## 与 Web 版的区别

### 包含的功能
- ✅ 小说项目管理
- ✅ 概念对话
- ✅ 蓝图生成
- ✅ 章节生成（Writer）
- ✅ LLM 配置管理
- ✅ 向量存储和 RAG 检索
- ✅ 提示词管理

### 移除的功能
- ❌ 用户注册/登录（开箱即用）
- ❌ Web 管理后台（Admin）
- ❌ 系统更新通知（Updates）
- ❌ 多用户支持（单机版）

## 目录结构

```
backend/
├── app/
│   ├── api/
│   │   └── routers/       # API 路由（auth, novels, writer, llm_config）
│   ├── core/              # 核心配置
│   ├── db/                # 数据库配置和迁移
│   ├── models/            # SQLAlchemy 模型
│   ├── repositories/      # 数据访问层
│   ├── schemas/           # Pydantic 数据模型
│   ├── services/          # 业务逻辑层
│   ├── utils/             # 工具函数
│   └── main.py            # FastAPI 应用入口
├── prompts/               # LLM 提示词模板
├── storage/               # 数据存储目录
├── requirements.txt       # Python 依赖
└── README.md             # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置必要的参数：

```bash
cp .env.example .env
```

关键配置项：
- `SECRET_KEY`: JWT 密钥（必须）
- `OPENAI_API_KEY`: LLM API 密钥（必须）
- `OPENAI_API_BASE_URL`: API 基础 URL（可选）
- `DB_PROVIDER`: 数据库类型（sqlite 或 mysql，默认 sqlite）

### 3. 启动后端服务

```bash
# 开发模式（带热重载）
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 或指定自定义端口
uvicorn app.main:app --reload --port 8001
```

服务启动后访问：
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

## PyQt 前端集成

PyQt 前端应该通过 HTTP 请求调用后端 API，**无需任何认证**：

```python
import requests

# 桌面版无需登录，直接调用API即可

# 示例：创建小说项目
response = requests.post(
    "http://127.0.0.1:8000/api/novels",
    json={"title": "我的小说", "initial_prompt": "科幻小说"}
)
project = response.json()

# 示例：获取项目列表
response = requests.get("http://127.0.0.1:8000/api/novels")
projects = response.json()

# 示例：生成蓝图
response = requests.post(
    f"http://127.0.0.1:8000/api/novels/{project['id']}/blueprint/generate"
)
blueprint = response.json()
```

**注意**：所有API都无需 `Authorization` 头，直接调用即可。

## 数据库

默认使用 SQLite，数据存储在 `storage/afn.db`。

如需使用 MySQL，配置以下环境变量：
```bash
DB_PROVIDER=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=afn
```

## 日志

日志文件存储在 `storage/debug.log`，包含所有业务逻辑的详细日志。

## API 端点

### 小说项目
- `POST /api/novels` - 创建项目
- `GET /api/novels` - 获取项目列表
- `GET /api/novels/{id}` - 获取项目详情
- `POST /api/novels/{id}/concept/converse` - 概念对话
- `POST /api/novels/{id}/blueprint/generate` - 生成蓝图

### 章节写作
- `POST /api/writer/novels/{id}/chapters/generate` - 生成章节
- `POST /api/writer/novels/{id}/chapters/select` - 选择版本
- `POST /api/writer/novels/{id}/chapters/evaluate` - 评审章节

### LLM 配置
- `GET /api/llm-configs` - 获取配置列表
- `POST /api/llm-configs` - 创建配置
- `POST /api/llm-configs/{id}/activate` - 激活配置

**所有API无需认证，可直接调用。**

完整 API 文档请访问 http://127.0.0.1:8000/docs

## 技术栈

- **Web 框架**: FastAPI 0.110.0
- **数据库 ORM**: SQLAlchemy 2.0.44
- **异步支持**: asyncmy（MySQL）/ aiosqlite（SQLite）
- **LLM 集成**: OpenAI API / Ollama
- **向量存储**: libsql
- **密码加密**: bcrypt（仅用于默认用户初始化）

## 开发说明

- 所有代码遵循项目规范，使用中文注释
- 数据库操作必须使用异步方法
- 路由层只负责请求解析，业务逻辑在 Service 层
- Repository 层封装所有数据库操作
- **桌面版无需任何认证，所有API直接调用**

## 许可

与主项目相同
