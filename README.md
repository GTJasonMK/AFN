# AFN (Agents for Novel)

> AI 辅助长篇小说创作桌面应用 | 开箱即用 | 无需登录 | 本地存储

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6.1-41CD52.svg)
![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [创作流程](#创作流程)
- [项目结构](#项目结构)
- [技术架构](#技术架构)
- [配置指南](#配置指南)
- [常见问题](#常见问题)

---

## 功能特性

### 核心创作流程

| 功能 | 说明 |
|:-----|:-----|
| **灵感对话** | 与 AI 交互式构建小说概念，通过多轮对话逐步明确故事方向 |
| **蓝图生成** | 基于对话内容一键生成完整蓝图：世界观、角色设定、人物关系、故事梗概 |
| **分层大纲** | 长篇(>=50章)支持「分部大纲 + 章节大纲」双层结构，短篇直接生成章节大纲 |
| **多版本生成** | 每章并行生成多个版本，AI 对比评审辅助用户选择最佳版本 |
| **RAG 增强** | 三层上下文（必需/重要/参考）、角色状态追踪、伏笔管理、时序感知检索 |
| **正文优化** | Agent 逐段分析章节内容，检测逻辑漏洞、角色一致性、时间线问题 |

### 扩展能力

| 功能 | 说明 |
|:-----|:-----|
| **漫画分镜生成** | 4步流水线架构：信息提取 → 页面规划 → 分镜设计 → 提示词构建 |
| **图片生成** | 集成 OpenAI DALL-E / Stability AI / ComfyUI 多厂商 |
| **角色立绘** | 基于角色设定生成人物立绘，支持作为分镜参考图 |
| **外部导入** | 导入已有 TXT 小说，智能分析反推蓝图和大纲 |
| **主角档案** | 独立管理主角信息，支持隐式追踪和同步更新 |

### 界面特性

| 功能 | 说明 |
|:-----|:-----|
| **深色/浅色主题** | 一键切换（Ctrl+T），支持自定义主题配置 |
| **透明模式** | Windows DWM Acrylic 毛玻璃效果，支持背景图片和透明度调节 |
| **LRU 页面缓存** | 最多缓存 10 个页面，自动淘汰最久未使用的页面 |
| **高 DPI 支持** | 响应式布局，适配不同分辨率屏幕 |

---

## 快速开始

### 一键启动（推荐）

```bash
python run_app.py
```

首次运行自动完成：
1. 检测 Python 版本（需要 3.10+）
2. 安装 [uv](https://github.com/astral-sh/uv) 包管理器（比 pip 快 10-100 倍）
3. 创建前后端独立虚拟环境
4. 安装依赖（自动检测已安装的核心包）
5. 自动处理端口占用（8123）
6. 启动后端服务和前端 GUI

### 手动启动

```bash
# 后端（端口 8123）
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8123

# 前端（新终端）
cd frontend
.venv\Scripts\activate
python main.py
```

### 配置 LLM

1. 启动应用后，点击右下角进入 **设置**
2. 进入 **LLM 配置** → **新建配置**
3. 填写 Base URL（如 `https://api.openai.com/v1`）和 API Key
4. 点击 **测试连接** 验证后 **激活此配置**

完成！开始创作您的第一部小说。

---

## 创作流程

### 项目状态机

```mermaid
stateDiagram-v2
    [*] --> DRAFT: 创建项目

    DRAFT --> BLUEPRINT_READY: 生成蓝图
    BLUEPRINT_READY --> DRAFT: 回退重新对话

    BLUEPRINT_READY --> PART_OUTLINES_READY: 生成分部大纲<br/>(>=50章)
    BLUEPRINT_READY --> CHAPTER_OUTLINES_READY: 生成章节大纲<br/>(<50章)

    PART_OUTLINES_READY --> CHAPTER_OUTLINES_READY: 生成章节大纲
    PART_OUTLINES_READY --> BLUEPRINT_READY: 回退

    CHAPTER_OUTLINES_READY --> WRITING: 开始写作
    CHAPTER_OUTLINES_READY --> PART_OUTLINES_READY: 回退(长篇)
    CHAPTER_OUTLINES_READY --> BLUEPRINT_READY: 回退(短篇)

    WRITING --> COMPLETED: 全部完成
    WRITING --> CHAPTER_OUTLINES_READY: 回退修改大纲

    COMPLETED --> WRITING: 继续编辑

    state DRAFT {
        [*] --> 灵感对话
    }

    state BLUEPRINT_READY {
        [*] --> 编辑蓝图
        编辑蓝图 --> 世界观
        编辑蓝图 --> 角色设定
        编辑蓝图 --> 人物关系
    }

    state WRITING {
        [*] --> 生成章节
        生成章节 --> 版本选择
        版本选择 --> 下一章
    }
```

**状态说明**：
| 状态 | 说明 |
|:-----|:-----|
| `DRAFT` | 灵感对话进行中 |
| `BLUEPRINT_READY` | 蓝图生成完成，可编辑世界观、角色、关系 |
| `PART_OUTLINES_READY` | 分部大纲就绪（仅长篇 >=50 章）|
| `CHAPTER_OUTLINES_READY` | 章节大纲就绪，可进入写作 |
| `WRITING` | 章节写作中，支持回退到大纲阶段 |
| `COMPLETED` | 全部章节完成 |

### 章节生成流程

```mermaid
flowchart TB
    subgraph 构建上下文["1. 构建上下文"]
        A1[蓝图核心信息] --> B1[RAG 多维检索]
        A2[当前章节大纲] --> B1
        A3[前章结尾摘录] --> B1
        B1 --> C1[角色状态追踪]
        B1 --> C2[活跃伏笔列表]
        C1 --> D1[三层分级构建]
        C2 --> D1
        D1 --> E1[Token 智能压缩]
    end

    subgraph 并行生成["2. 并行生成"]
        E1 --> F1[版本 1]
        E1 --> F2[版本 2]
        E1 --> F3[版本 3]
        F1 --> G1[LLM 流式生成]
        F2 --> G1
        F3 --> G1
    end

    subgraph 评审选择["3. 评审选择"]
        G1 --> H1[AI 对比分析]
        H1 --> H2[用户选择最佳版本]
    end

    subgraph 后处理["4. 后处理"]
        H2 --> I1[向量化入库]
        I1 --> I2[章节深度分析]
        I2 --> I3[更新角色状态索引]
        I2 --> I4[更新伏笔追踪索引]
    end

    style 构建上下文 fill:#e1f5fe
    style 并行生成 fill:#fff3e0
    style 评审选择 fill:#e8f5e9
    style 后处理 fill:#fce4ec
```

### RAG 上下文分层

```mermaid
flowchart LR
    subgraph 必需层["必需层 (Must Have)"]
        M1[蓝图核心摘要]
        M2[角色名称列表]
        M3[当前章节大纲]
        M4[前章结尾 500 字]
    end

    subgraph 重要层["重要层 (Important)"]
        I1[涉及角色详情]
        I2[高优先级伏笔]
        I3[近期角色状态]
    end

    subgraph 参考层["参考层 (Reference)"]
        R1[世界观设定]
        R2[向量检索片段]
        R3[历史摘要]
    end

    必需层 --> 生成提示词
    重要层 --> 生成提示词
    参考层 -.->|Token不足时裁剪| 生成提示词

    style 必需层 fill:#ffcdd2
    style 重要层 fill:#fff9c4
    style 参考层 fill:#c8e6c9
```

### 漫画分镜生成流程

```mermaid
flowchart TB
    subgraph Input["输入"]
        I1[章节内容]
        I2[风格/页数设置]
        I3[角色立绘]
    end

    subgraph Step1["Step 1: 信息提取"]
        E1[角色信息<br/>外观/性格/关系]
        E2[对话信息<br/>说话人/内容/情绪]
        E3[场景信息<br/>地点/时间/氛围]
        E4[事件信息<br/>动作/冲突/转折]
    end

    subgraph Step2["Step 2: 页面规划"]
        P1[全局页数分配]
        P2[事件到页面映射]
        P3[节奏控制<br/>快/中/慢]
        P4[页面角色<br/>开场/发展/高潮/结尾]
    end

    subgraph Step3["Step 3: 分镜设计"]
        S1[画格数量和布局]
        S2[画格大小/形状]
        S3[镜头类型<br/>特写/中景/远景]
        S4[对话气泡/音效位置]
    end

    subgraph Step4["Step 4: 提示词构建"]
        B1[英文/中文双语提示词]
        B2[负面提示词]
        B3[角色外观描述注入]
        B4[参考图路径]
    end

    subgraph Output["输出"]
        O1[MangaPromptResult]
        O2[页面列表 + 画格提示词]
    end

    Input --> Step1
    Step1 -->|ChapterInfo| Step2
    Step2 -->|PagePlanResult| Step3
    Step3 -->|StoryboardResult| Step4
    Step4 --> Output

    style Input fill:#e3f2fd
    style Step1 fill:#fff3e0
    style Step2 fill:#e8f5e9
    style Step3 fill:#fce4ec
    style Step4 fill:#f3e5f5
    style Output fill:#e0f7fa
```

**漫画风格支持**：
| 风格 | 说明 |
|:-----|:-----|
| `manga` | 日式漫画风格（右到左阅读）|
| `anime` | 动漫截图风格 |
| `comic` | 美式漫画风格 |
| `webtoon` | 条漫风格（上到下阅读）|

---

## 项目结构

```
AFN/
├── run_app.py                 # 统一启动入口
├── build.bat                  # PyInstaller 打包脚本
├── CLAUDE.md                  # Claude Code 开发指南
│
├── backend/                   # FastAPI 异步后端
│   ├── app/
│   │   ├── main.py            # 应用入口
│   │   ├── exceptions.py      # 统一异常体系
│   │   ├── api/routers/
│   │   │   ├── novels/        # 项目管理
│   │   │   └── writer/        # 写作阶段
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── chapter_generation/  # 章节生成
│   │   │   ├── rag/           # RAG 检索增强
│   │   │   ├── manga_prompt/  # 漫画分镜生成
│   │   │   │   ├── extraction/    # 信息提取
│   │   │   │   ├── planning/      # 页面规划
│   │   │   │   ├── storyboard/    # 分镜设计
│   │   │   │   ├── prompt_builder/# 提示词构建
│   │   │   │   └── core/          # 核心服务
│   │   │   └── ...
│   │   ├── models/            # SQLAlchemy ORM
│   │   ├── schemas/           # Pydantic 模型
│   │   ├── repositories/      # 数据访问层
│   │   └── core/              # 状态机/依赖注入
│   ├── prompts/               # LLM 提示词模板
│   └── storage/               # 数据存储
│
├── frontend/                  # PyQt6 桌面前端
│   ├── main.py                # 应用入口
│   ├── api/client/            # API 客户端 (Mixin)
│   ├── windows/               # 页面模块
│   ├── components/            # 通用 UI 组件
│   ├── themes/                # 主题系统
│   └── utils/                 # 工具类
│
└── docs/
    └── ARCHITECTURE.md        # 详细架构图
```

---

## 技术架构

### 技术栈

| 层级 | 技术 | 说明 |
|:-----|:-----|:-----|
| 前端框架 | PyQt6 6.6.1 | 桌面 GUI，Fusion 样式 |
| 后端框架 | FastAPI 0.110.0 | 全异步 API，SSE 流式响应 |
| ORM | SQLAlchemy 2.0 | 异步操作，aiosqlite 驱动 |
| 数据库 | SQLite | 本地存储，无需额外服务 |
| 向量库 | ChromaDB | RAG 检索 |
| LLM | OpenAI 兼容 API | 多厂商支持 |

### 分层架构

```mermaid
flowchart TB
    subgraph Frontend["PyQt6 前端"]
        direction LR
        FP1[HomePage]
        FP2[InspirationMode]
        FP3[NovelDetail]
        FP4[WritingDesk]
        FP5[Settings]
    end

    subgraph FrontendCore["前端核心"]
        direction LR
        FC1[API Client<br/>Mixin 架构]
        FC2[AsyncWorker]
        FC3[SSEWorker]
        FC4[ThemeManager]
    end

    subgraph Backend["FastAPI 后端"]
        direction TB
        subgraph Routes["路由层"]
            R1[/api/novels/*]
            R2[/api/writer/*]
            R3[/api/*-configs]
        end
        subgraph Services["服务层"]
            S1[NovelService]
            S2[ChapterGeneration]
            S3[RAGServices]
            S4[LLMService]
            S5[MangaPromptService]
        end
        subgraph Repos["Repository 层"]
            RP1[BaseRepository]
            RP2[NovelRepo]
            RP3[ChapterRepo]
        end
    end

    subgraph Storage["存储层"]
        direction LR
        DB1[(SQLite<br/>afn.db)]
        DB2[(ChromaDB<br/>vectors)]
        DB3[/LLM APIs/]
    end

    Frontend --> FrontendCore
    FrontendCore -->|HTTP REST / SSE| Backend
    Routes --> Services
    Services --> Repos
    Repos --> Storage
    Services --> DB3

    style Frontend fill:#e3f2fd
    style FrontendCore fill:#bbdefb
    style Backend fill:#fff8e1
    style Storage fill:#f3e5f5
```

### 数据流

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端 (PyQt6)
    participant B as 后端 (FastAPI)
    participant L as LLM API
    participant D as SQLite
    participant V as ChromaDB

    U->>F: 点击生成章节
    F->>B: POST /api/writer/chapters/generate

    B->>D: 获取蓝图/大纲
    B->>V: RAG 检索相关内容
    B->>B: 构建三层上下文

    loop 并行生成 N 个版本
        B->>L: 流式请求 LLM
        L-->>B: SSE 返回 tokens
        B-->>F: SSE 转发 tokens
        F-->>U: 实时显示生成内容
    end

    B-->>F: 返回所有版本
    U->>F: 选择最佳版本
    F->>B: POST /api/writer/chapters/select

    B->>D: 保存选定版本
    B->>V: 向量化入库
    B->>B: 更新角色/伏笔索引
    B-->>F: 返回成功
```

---

## 配置指南

### LLM 配置

支持 OpenAI 兼容 API：

| 提供商 | Base URL |
|:-------|:---------|
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Moonshot | `https://api.moonshot.cn/v1` |
| Ollama | `http://localhost:11434/v1` |
| 中转服务 | 2API / API2D / OpenRouter 等 |

### 嵌入配置（RAG 功能）

| 类型 | 说明 |
|:-----|:-----|
| OpenAI 兼容接口 | 远程嵌入 API |
| Ollama 本地模型 | 本地部署嵌入模型 |

### 图片生成配置

| 服务类型 | 说明 |
|:---------|:-----|
| OpenAI 兼容接口 | DALL-E 3 / Gemini 等 |
| Stability AI | Stable Diffusion XL |
| 本地 ComfyUI | 自定义工作流 |

---

## 常见问题

### 启动问题

**Q: 启动失败？**
1. 检查 Python 版本：`python --version`（需要 3.10+）
2. 查看日志：
   - `storage\app.log` - 启动入口日志
   - `storage\debug.log` - 后端详细日志
3. 端口占用：`netstat -ano -p TCP | findstr 8123`

**Q: 端口 8123 被占用？**
- `run_app.py` 会自动尝试关闭占用进程
- 手动处理：`taskkill /F /PID <pid>`

**Q: 依赖安装失败？**
- 删除 `backend\.venv` 和 `frontend\.venv` 目录
- 重新运行 `python run_app.py`

### 功能问题

**Q: LLM 调用失败？**
- 设置页点击 **测试连接** 验证配置
- 检查 API Key 是否正确
- 确认 Base URL 格式（以 `/v1` 结尾）

**Q: RAG/向量检索不工作？**
- 需要先配置嵌入服务（设置 → 嵌入配置）

**Q: 透明效果不生效？**
- 仅 Windows 10/11 支持
- 设置 → 主题设置 → 启用透明模式

---

## 系统要求

| 项目 | 要求 |
|:-----|:-----|
| 操作系统 | Windows 10/11 |
| Python | 3.10+ |
| 内存 | 8GB（推荐 16GB）|
| 网络 | 需要连接 LLM API |

---

## 相关链接

- [API 文档](http://localhost:8123/docs) - 后端启动后访问 Swagger UI
- [详细架构图](docs/ARCHITECTURE.md) - 完整技术架构和数据模型
- [开发指南](CLAUDE.md) - Claude Code 开发规范

---

## 许可证

[MIT License](LICENSE)
