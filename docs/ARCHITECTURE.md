# AFN 技术架构图

本文档描述 AFN (Agents for Novel) 项目的完整技术架构。

## 目录

- [系统总览](#系统总览)
- [整体架构图](#整体架构图)
- [后端架构](#后端架构)
- [前端架构](#前端架构)
- [数据模型](#数据模型)
- [核心业务流程](#核心业务流程)
- [RAG系统架构](#rag系统架构)
- [通信机制](#通信机制)

---

## 系统总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AFN 系统架构总览                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        PyQt6 桌面前端                                 │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │  首页    │ │灵感对话  │ │项目详情  │ │ 写作台   │ │  设置    │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  │                              ↓                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │     API Client (HTTP/SSE)  +  AsyncWorker  +  SSEWorker     │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                          HTTP REST API (Port 8123)                          │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI 后端服务                               │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │                      API 路由层                               │    │   │
│  │  │   novels/  │  writer/  │  llm_config  │  embedding_config    │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                              ↓                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │                      服务层 (Services)                        │    │   │
│  │  │  NovelService │ LLMService │ RAGServices │ ChapterGeneration │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                              ↓                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │                   Repository层 (数据访问)                     │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         ↓                          ↓                          ↓            │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐         │
│  │   SQLite    │          │ Vector Store│          │  LLM APIs   │         │
│  │  (afn.db)   │          │  (ChromaDB) │          │(OpenAI等)   │         │
│  └─────────────┘          └─────────────┘          └─────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 整体架构图

```mermaid
graph TB
    subgraph Frontend["前端 (PyQt6)"]
        MW[MainWindow<br/>页面导航容器]
        HP[HomePage<br/>首页]
        IM[InspirationMode<br/>灵感对话]
        ND[NovelDetail<br/>项目详情]
        WD[WritingDesk<br/>写作台]
        ST[Settings<br/>设置]

        MW --> HP
        MW --> IM
        MW --> ND
        MW --> WD
        MW --> ST

        subgraph Utils["工具层"]
            AC[APIClient<br/>HTTP客户端]
            AW[AsyncWorker<br/>异步任务]
            SW[SSEWorker<br/>流式响应]
            TM[ThemeManager<br/>主题管理]
        end
    end

    subgraph Backend["后端 (FastAPI)"]
        subgraph Routers["API路由层"]
            NR[novels/<br/>项目管理]
            WR[writer/<br/>写作阶段]
            CR[configs/<br/>配置管理]
        end

        subgraph Services["服务层"]
            NS[NovelService]
            LS[LLMService]
            IS[InspirationService]
            BS[BlueprintService]
            CGS[ChapterGenerationService]
            RS[RAG Services]
        end

        subgraph Repos["Repository层"]
            BR[BaseRepository]
            NRep[NovelRepository]
            CRep[ChapterRepository]
        end
    end

    subgraph Storage["存储层"]
        DB[(SQLite<br/>afn.db)]
        VS[(Vector Store<br/>ChromaDB)]
        LLM[("LLM APIs<br/>OpenAI/Gemini等")]
    end

    Frontend -->|HTTP/SSE| Backend
    Services --> Repos
    Repos --> DB
    RS --> VS
    LS --> LLM
```

---

## 后端架构

### 分层架构图

```mermaid
graph TB
    subgraph API["API路由层"]
        direction LR
        subgraph Novels["novels/ 项目管理"]
            INS[inspiration.py<br/>灵感对话]
            BLP[blueprints.py<br/>蓝图管理]
            OUT[outlines.py<br/>大纲生成]
            EXP[export.py<br/>导出功能]
        end

        subgraph Writer["writer/ 写作阶段"]
            CG[chapter_generation.py<br/>章节生成]
            CM[chapter_management.py<br/>章节管理]
            CO[chapter_outlines.py<br/>章节大纲]
            PO[part_outlines.py<br/>分部大纲]
            RQ[rag_query.py<br/>RAG查询]
            OPT[content_optimization.py<br/>内容优化]
        end

        subgraph Config["配置管理"]
            LC[llm_config.py]
            EC[embedding_config.py]
            SET[settings.py]
        end
    end

    subgraph Services["服务层"]
        subgraph Core["核心服务"]
            NovelSvc[NovelService<br/>项目管理]
            LLMSvc[LLMService<br/>LLM调用]
            PromptSvc[PromptService<br/>提示词管理]
        end

        subgraph Inspiration["灵感模块"]
            InsSvc[InspirationService]
            ConvSvc[ConversationService]
        end

        subgraph Blueprint["蓝图模块"]
            BlueSvc[BlueprintService]
            AvatarSvc[AvatarService]
        end

        subgraph ChapterGen["章节生成模块"]
            CGSvc[ChapterGenerationService]
            CGCtx[Context]
            CGPrompt[PromptBuilder]
            CGVersion[VersionProcessor]
            CGWorkflow[Workflow]
        end

        subgraph RAG["RAG模块"]
            QB[QueryBuilder<br/>查询构建]
            CB[ContextBuilder<br/>上下文构建]
            CC[ContextCompressor<br/>压缩]
            TR[TemporalRetriever<br/>时序检索]
            OR[OutlineRetriever<br/>大纲检索]
            SE[SceneExtractor<br/>场景提取]
        end

        subgraph Vector["向量化模块"]
            EmbSvc[EmbeddingService]
            VSSvc[VectorStoreService]
            CISvc[ChapterIngestService]
            IdxSvc[IncrementalIndexer]
        end

        subgraph Analysis["分析模块"]
            CASvc[ChapterAnalysisService]
            CESvc[ChapterEvaluationService]
            FSSvc[ForeshadowingService]
        end
    end

    subgraph Repository["Repository层"]
        BaseRepo[BaseRepository<br/>通用CRUD]
        NovelRepo[NovelRepository]
        ChapterRepo[ChapterRepository]
        OutlineRepo[OutlineRepository]
        ConfigRepo[ConfigRepository]
    end

    API --> Services
    Services --> Repository
```

### 服务层详细结构

```
backend/app/services/
├── 核心服务
│   ├── novel_service.py          # 项目CRUD、状态管理
│   ├── llm_service.py            # LLM调用（流式/非流式）
│   └── prompt_service.py         # 提示词加载和缓存
│
├── 灵感对话
│   ├── inspiration_service.py    # 灵感对话业务逻辑
│   └── conversation_service.py   # 对话历史管理
│
├── 蓝图生成
│   ├── blueprint_service.py      # 蓝图生成和优化
│   └── avatar_service.py         # SVG头像生成
│
├── 大纲生成
│   ├── part_outline_service.py   # 分部大纲服务
│   └── part_outline/             # 分部大纲子模块
│       ├── service.py
│       └── workflow.py
│
├── 章节生成 (chapter_generation/)
│   ├── service.py                # 生成服务入口
│   ├── workflow.py               # 完整生成工作流
│   ├── context.py                # 上下文数据结构
│   ├── prompt_builder.py         # 提示词构建
│   └── version_processor.py      # 版本结果处理
│
├── RAG系统 (rag/)
│   ├── query_builder.py          # 多维查询构建
│   ├── context_builder.py        # 分层上下文构建
│   ├── context_compressor.py     # Token限制下的压缩
│   ├── temporal_retriever.py     # 时序感知向量检索
│   ├── outline_retriever.py      # 大纲阶段RAG
│   ├── scene_extractor.py        # 场景状态提取
│   └── utils.py                  # 公共工具
│
├── 向量化和索引
│   ├── embedding_service.py      # 嵌入向量生成
│   ├── vector_store_service.py   # 向量库操作
│   ├── chapter_ingest_service.py # 章节向量化入库
│   └── incremental_indexer.py    # 增量索引更新
│
├── 分析服务
│   ├── chapter_analysis_service.py   # 章节内容分析
│   ├── chapter_evaluation_service.py # 版本评审
│   ├── chapter_context_service.py    # 章节上下文
│   ├── chapter_version_service.py    # 版本管理
│   └── foreshadowing_service.py      # 伏笔追踪
│
└── 配置服务
    ├── llm_config_service.py         # LLM配置CRUD
    └── embedding_config_service.py   # 嵌入配置CRUD
```

---

## 前端架构

### 页面导航系统

```mermaid
graph TB
    subgraph MainWindow["MainWindow (QMainWindow)"]
        PS[QStackedWidget<br/>页面容器]
        FT[FloatingToolbar<br/>主题切换]
        NH[Navigation History<br/>导航历史栈]
        PC[Page Cache<br/>LRU缓存]
    end

    subgraph Pages["页面模块"]
        HP[HomePage<br/>首页]

        subgraph IM["InspirationMode 灵感对话"]
            IM_Main[main.py]
            IM_Chat[chat_bubble.py]
            IM_Input[conversation_input.py]
            IM_State[conversation_state.py]
            IM_Blueprint[blueprint_display.py]
        end

        subgraph ND["NovelDetail 项目详情"]
            ND_Main[main.py]
            ND_Overview[overview_section.py]
            ND_World[world_setting_section.py]
            ND_Chars[characters_section.py]
            ND_Rels[relationships_section.py]
            ND_Chapters[chapters_section.py]
            ND_Outline[chapter_outline/]
        end

        subgraph WD["WritingDesk 写作台"]
            WD_Main[main.py]
            WD_Header[header.py]
            WD_Sidebar[sidebar.py]
            WD_Workspace[workspace.py]
            WD_Panels[panels/]
            WD_Assistant[assistant_panel.py]
        end

        subgraph ST["Settings 设置"]
            ST_View[view.py]
            ST_LLM[llm_settings_widget.py]
            ST_Embed[embedding_settings_widget.py]
            ST_Adv[advanced_settings_widget.py]
        end
    end

    PS --> HP
    PS --> IM
    PS --> ND
    PS --> WD
    PS --> ST

    MainWindow -->|navigateTo| Pages
    MainWindow -->|goBack| NH
```

### 前端目录结构

```
frontend/
├── main.py                       # 应用入口
├── api/
│   ├── client.py                 # AFNAPIClient HTTP封装
│   ├── manager.py                # API客户端单例管理
│   └── exceptions.py             # API异常定义
│
├── windows/
│   ├── main_window.py            # 主窗口（页面导航容器）
│   │
│   ├── inspiration_mode/         # 灵感对话模块
│   │   ├── main.py              # 主页面
│   │   ├── chat_bubble.py       # 聊天气泡组件
│   │   ├── conversation_input.py # 输入框组件
│   │   ├── conversation_state.py # 对话状态管理
│   │   ├── blueprint_display.py  # 蓝图展示
│   │   ├── blueprint_confirmation.py # 蓝图确认对话框
│   │   └── inspired_option_card.py # 灵感选项卡片
│   │
│   ├── novel_detail/             # 项目详情模块
│   │   ├── main.py              # 主页面
│   │   ├── overview_section.py  # 概览区域
│   │   ├── world_setting_section.py # 世界观设置
│   │   ├── characters_section.py # 角色管理
│   │   ├── relationships_section.py # 角色关系
│   │   ├── chapters_section.py  # 章节列表
│   │   └── chapter_outline/     # 章节大纲子模块
│   │       ├── main.py
│   │       ├── chapter_card.py
│   │       ├── part_outline_card.py
│   │       └── ...
│   │
│   ├── writing_desk/             # 写作台模块
│   │   ├── main.py              # 主页面
│   │   ├── header.py            # 顶部栏
│   │   ├── sidebar.py           # 章节侧边栏
│   │   ├── workspace.py         # 工作区
│   │   ├── chapter_card.py      # 章节卡片
│   │   ├── assistant_panel.py   # AI助手面板
│   │   ├── panels/              # 功能面板
│   │   │   ├── version_panel.py # 版本选择
│   │   │   ├── review_panel.py  # 评审面板
│   │   │   ├── analysis_panel.py # 分析面板
│   │   │   ├── content_panel.py # 内容编辑
│   │   │   └── summary_panel.py # 摘要面板
│   │   └── components/          # 写作台专用组件
│   │
│   └── settings/                 # 设置模块
│       ├── view.py              # 设置主视图
│       ├── llm_settings_widget.py # LLM配置
│       ├── embedding_settings_widget.py # 嵌入配置
│       └── advanced_settings_widget.py # 高级设置
│
├── pages/
│   └── home_page.py              # 首页
│
├── components/                   # 通用组件库
│   ├── base/
│   │   └── theme_aware_widget.py # 主题感知基类
│   └── ...
│
├── themes/                       # 主题系统
│   ├── theme_manager.py          # 主题管理器
│   ├── modern_effects.py         # 现代效果
│   └── svg_icons.py              # SVG图标
│
└── utils/                        # 工具类
    ├── async_worker.py           # 异步任务Worker
    ├── sse_worker.py             # SSE流式响应Worker
    ├── dpi_utils.py              # DPI感知工具
    ├── page_registry.py          # 页面注册表
    └── error_handler.py          # 错误处理
```

---

## 数据模型

### 实体关系图

```mermaid
erDiagram
    User ||--o{ NovelProject : owns
    NovelProject ||--o| NovelBlueprint : has
    NovelProject ||--o{ NovelConversation : has
    NovelProject ||--o{ BlueprintCharacter : has
    NovelProject ||--o{ BlueprintRelationship : has
    NovelProject ||--o{ PartOutline : has
    NovelProject ||--o{ ChapterOutline : has
    NovelProject ||--o{ Chapter : has
    NovelProject ||--o{ CharacterStateIndex : has
    NovelProject ||--o{ ForeshadowingIndex : has

    Chapter ||--o{ ChapterVersion : has
    Chapter ||--o| ChapterVersion : selected
    Chapter ||--o{ ChapterEvaluation : has
    ChapterVersion ||--o{ ChapterEvaluation : evaluated

    User {
        int id PK
        string username
        string email
        datetime created_at
    }

    NovelProject {
        string id PK
        int user_id FK
        string title
        string initial_prompt
        string status
        datetime created_at
        datetime updated_at
    }

    NovelBlueprint {
        string project_id PK,FK
        string title
        string genre
        string style
        string tone
        string one_sentence_summary
        text full_synopsis
        json world_setting
        bool needs_part_outlines
        int total_chapters
        string avatar_svg
    }

    NovelConversation {
        int id PK
        string project_id FK
        int seq
        string role
        text content
        json metadata
    }

    BlueprintCharacter {
        int id PK
        string project_id FK
        string name
        string identity
        text personality
        text goals
        text abilities
        int position
    }

    BlueprintRelationship {
        int id PK
        string project_id FK
        string character_from
        string character_to
        text description
        int position
    }

    PartOutline {
        int id PK
        string project_id FK
        int part_number
        string title
        text summary
        int start_chapter
        int end_chapter
    }

    ChapterOutline {
        int id PK
        string project_id FK
        int chapter_number
        string title
        text summary
    }

    Chapter {
        int id PK
        string project_id FK
        int chapter_number
        string status
        int word_count
        int selected_version_id FK
        json analysis_data
    }

    ChapterVersion {
        int id PK
        int chapter_id FK
        string version_label
        string provider
        text content
        json metadata
    }

    ChapterEvaluation {
        int id PK
        int chapter_id FK
        int version_id FK
        string decision
        text feedback
        float score
    }

    CharacterStateIndex {
        int id PK
        string project_id FK
        int chapter_number
        string character_name
        string location
        text status
        json changes
    }

    ForeshadowingIndex {
        int id PK
        string project_id FK
        text description
        string category
        string priority
        int planted_chapter
        int resolved_chapter
        string status
    }

    LLMConfig {
        int id PK
        int user_id FK
        string name
        string base_url
        string api_key
        string model_name
        bool is_active
    }

    EmbeddingConfig {
        int id PK
        int user_id FK
        string name
        string provider_type
        string base_url
        string api_key
        string model_name
        bool is_active
    }

    Prompt {
        int id PK
        string name
        text content
        string category
    }
```

### 模型层级关系

```
NovelProject (项目主表)
├── NovelBlueprint (蓝图) [1:1]
├── NovelConversation (对话记录) [1:N]
├── BlueprintCharacter (角色) [1:N]
├── BlueprintRelationship (关系) [1:N]
├── PartOutline (分部大纲) [1:N]
├── ChapterOutline (章节大纲) [1:N]
├── Chapter (章节) [1:N]
│   ├── ChapterVersion (版本) [1:N]
│   │   └── ChapterEvaluation (评审) [1:N]
│   └── selected_version -> ChapterVersion [N:1]
├── CharacterStateIndex (角色状态索引) [1:N]
└── ForeshadowingIndex (伏笔索引) [1:N]

配置相关
├── LLMConfig (LLM配置)
├── EmbeddingConfig (嵌入配置)
├── User (用户)
└── Prompt (提示词模板)
```

---

## 核心业务流程

### 创作状态机

```mermaid
stateDiagram-v2
    [*] --> DRAFT: 创建项目
    DRAFT --> DRAFT: 灵感对话
    DRAFT --> BLUEPRINT_READY: 生成蓝图

    BLUEPRINT_READY --> PART_OUTLINES_READY: 生成分部大纲<br/>(>=50章)
    BLUEPRINT_READY --> CHAPTER_OUTLINES_READY: 生成章节大纲<br/>(<50章)

    PART_OUTLINES_READY --> CHAPTER_OUTLINES_READY: 生成章节大纲

    CHAPTER_OUTLINES_READY --> WRITING: 开始写作
    CHAPTER_OUTLINES_READY --> BLUEPRINT_READY: 重新生成蓝图

    WRITING --> WRITING: 生成/选择章节
    WRITING --> COMPLETED: 全部章节完成
    WRITING --> CHAPTER_OUTLINES_READY: 修改大纲

    COMPLETED --> WRITING: 继续编辑
    COMPLETED --> [*]: 导出作品
```

### 章节生成流程

```mermaid
sequenceDiagram
    participant UI as 前端UI
    participant API as API路由
    participant CGS as ChapterGenerationService
    participant RAG as RAG系统
    participant LLM as LLMService
    participant DB as 数据库

    UI->>API: POST /chapters/generate
    API->>CGS: generate_chapter()

    Note over CGS: 1. 准备生成上下文
    CGS->>DB: 获取项目、大纲、蓝图
    CGS->>RAG: 检索相关上下文

    Note over RAG: QueryBuilder构建多维查询
    RAG->>RAG: TemporalRetriever时序检索
    RAG->>RAG: ContextBuilder分层构建
    RAG->>RAG: ContextCompressor压缩
    RAG-->>CGS: 返回压缩后的上下文

    Note over CGS: 2. 构建提示词
    CGS->>CGS: PromptBuilder.build()

    Note over CGS: 3. 并行生成多版本
    loop 每个版本 (默认3个)
        CGS->>LLM: get_llm_response()
        LLM-->>CGS: 章节内容
    end

    Note over CGS: 4. 处理生成结果
    CGS->>CGS: VersionProcessor.process()
    CGS->>DB: 保存章节版本

    CGS-->>API: 返回生成结果
    API-->>UI: 章节版本列表
```

### 灵感对话流程

```mermaid
sequenceDiagram
    participant UI as 前端UI
    participant SSE as SSEWorker
    participant API as API路由
    participant IS as InspirationService
    participant LLM as LLMService
    participant DB as 数据库

    UI->>SSE: 发起SSE连接
    SSE->>API: POST /inspiration/converse-stream
    API->>IS: converse_stream()

    IS->>DB: 获取对话历史
    IS->>IS: 构建系统提示词
    IS->>LLM: get_llm_response_stream()

    loop 流式响应
        LLM-->>API: token
        API-->>SSE: SSE event: token
        SSE-->>UI: 显示文字
    end

    LLM-->>API: 完成
    API->>DB: 保存对话记录
    API-->>SSE: SSE event: complete
    SSE-->>UI: 对话完成
```

---

## RAG系统架构

### RAG数据流

```mermaid
flowchart TB
    subgraph Input["输入"]
        CV[章节选择版本]
        CN[章节号]
        OL[当前大纲]
    end

    subgraph Ingest["向量化入库"]
        CIS[ChapterIngestService]
        ES[EmbeddingService]
        VS[VectorStoreService]
        RC[(rag_chunks表)]
    end

    subgraph Analysis["章节分析"]
        CAS[ChapterAnalysisService]
        LLM[LLMService]
        AD[analysis_data字段]
    end

    subgraph Index["索引更新"]
        II[IncrementalIndexer]
        CSI[(character_state_index)]
        FI[(foreshadowing_index)]
    end

    subgraph Retrieval["检索阶段"]
        QB[QueryBuilder<br/>多维查询构建]
        TR[TemporalRetriever<br/>时序感知检索]
        CB[ContextBuilder<br/>分层上下文]
        CC[ContextCompressor<br/>Token压缩]
    end

    subgraph Output["输出"]
        CTX[生成上下文]
    end

    CV --> CIS
    CIS --> ES
    ES --> VS
    VS --> RC

    CV --> CAS
    CAS --> LLM
    LLM --> AD

    AD --> II
    II --> CSI
    II --> FI

    CN --> QB
    OL --> QB
    QB --> TR
    TR --> RC
    TR --> CB
    CSI --> CB
    FI --> CB
    CB --> CC
    CC --> CTX
```

### RAG上下文分层

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAG上下文分层结构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 必需层 (Required) - 始终包含                             │   │
│  │  • 蓝图核心信息（标题、类型、风格、基调）                    │   │
│  │  • 角色名称列表                                          │   │
│  │  • 当前章节大纲                                          │   │
│  │  • 前一章结尾片段 (500-1000字)                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 重要层 (Important) - 优先包含                            │   │
│  │  • 本章涉及角色的详细信息                                  │   │
│  │  • 高优先级待回收伏笔                                     │   │
│  │  • 前3章压缩摘要                                         │   │
│  │  • RAG检索的高相关度片段                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 参考层 (Reference) - Token允许时包含                     │   │
│  │  • 世界观设定                                            │   │
│  │  • 中等优先级伏笔                                        │   │
│  │  • RAG检索的中等相关度片段                                │   │
│  │  • 角色关系网络                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Token限制: 根据模型上下文窗口动态调整 (默认约8000 tokens)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### RAG组件职责

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `QueryBuilder` | 构建多维检索查询 | 大纲、角色、伏笔 | 查询向量列表 |
| `TemporalRetriever` | 时序感知的向量检索 | 查询向量、章节号 | 带权重的片段列表 |
| `ContextBuilder` | 分层构建上下文 | 蓝图、检索结果、分析数据 | 结构化上下文 |
| `ContextCompressor` | 压缩至Token限制 | 完整上下文、Token限制 | 压缩后的上下文 |
| `OutlineRetriever` | 大纲阶段的RAG | 已有大纲、蓝图 | 相关大纲片段 |
| `SceneExtractor` | 提取场景状态 | 章节内容 | 场景状态数据 |

---

## 通信机制

### HTTP REST API

```
前端 (AFNAPIClient)  ────────────────>  后端 (FastAPI)
                     HTTP Request

        • GET/POST/PUT/DELETE
        • JSON请求/响应
        • 超时配置 (10-600秒)
        • 自动重试 (502/503/504)
        • 异常类型映射
```

### SSE (Server-Sent Events)

```
前端 (SSEWorker)  <────────────────  后端 (StreamingResponse)
                   SSE Events

事件类型:
├── token     : {"token": "字符"}        # 流式文本
├── thinking  : {"content": "..."}       # 思考过程
├── complete  : {"is_complete": true}    # 完成信号
└── error     : {"message": "..."}       # 错误信息
```

### 前端异步处理

```mermaid
sequenceDiagram
    participant UI as UI线程
    participant AW as AsyncWorker
    participant API as APIClient

    UI->>AW: 创建Worker(task_func)
    UI->>AW: start()

    Note over AW: 在后台线程执行
    AW->>API: 执行API调用
    API-->>AW: 返回结果

    alt 成功
        AW-->>UI: success.emit(result)
    else 失败
        AW-->>UI: error.emit(message)
        AW-->>UI: error_detail.emit(details)
    end
```

---

## 依赖注入

### FastAPI依赖图

```mermaid
graph TB
    subgraph Dependencies["core/dependencies.py"]
        GS[get_session<br/>数据库会话]
        GDU[get_default_user<br/>默认用户]
        GVS[get_vector_store<br/>向量库]

        GNS[get_novel_service]
        GLS[get_llm_service]
        GPS[get_prompt_service]
        GCS[get_conversation_service]
        GIS[get_inspiration_service]
        GPOS[get_part_outline_service]
        GCGS[get_chapter_generation_service]
        GVIS[get_vector_ingestion_service]
    end

    GS --> GDU
    GS --> GNS
    GS --> GLS
    GS --> GPS
    GS --> GCS

    GLS --> GIS
    GPS --> GIS
    GS --> GIS

    GLS --> GPOS
    GPS --> GPOS
    GNS --> GPOS
    GVS --> GPOS

    GS --> GCGS
    GLS --> GCGS

    GLS --> GVIS
    GVS --> GVIS
```

---

## 技术栈总结

| 层级 | 技术 | 版本 |
|------|------|------|
| **前端框架** | PyQt6 | 6.6.1 |
| **后端框架** | FastAPI | 0.110.0 |
| **ORM** | SQLAlchemy | 2.0 (异步) |
| **数据库驱动** | aiosqlite | - |
| **数据库** | SQLite | - |
| **向量库** | ChromaDB | - |
| **HTTP客户端** | requests | - |
| **异步运行时** | asyncio | - |
| **LLM集成** | OpenAI兼容API | - |

---

## 文件索引

### 后端关键文件

| 文件 | 说明 |
|------|------|
| `backend/app/main.py` | FastAPI应用入口 |
| `backend/app/core/dependencies.py` | 依赖注入 |
| `backend/app/core/state_machine.py` | 项目状态机 |
| `backend/app/exceptions.py` | 统一异常体系 |
| `backend/app/models/novel.py` | 核心数据模型 |
| `backend/app/services/llm_service.py` | LLM调用封装 |
| `backend/app/services/chapter_generation/service.py` | 章节生成服务 |
| `backend/app/services/rag/context_builder.py` | RAG上下文构建 |

### 前端关键文件

| 文件 | 说明 |
|------|------|
| `frontend/main.py` | PyQt6应用入口 |
| `frontend/windows/main_window.py` | 主窗口导航 |
| `frontend/api/client.py` | API客户端 |
| `frontend/utils/async_worker.py` | 异步任务处理 |
| `frontend/utils/sse_worker.py` | SSE流式响应 |
| `frontend/themes/theme_manager.py` | 主题管理 |

---

*文档生成时间: 2024年*
*项目版本: 1.0.0-pyqt*
