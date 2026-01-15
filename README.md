# AFN - Agents for Narrative

> **AI驱动的一站式文字创作平台**
>
> 小说只是起点，我们的目标是解决一切文字问题

---

## 愿景：一站式文字解决方案

**AFN 不只是一个AI小说工具，而是一个文字创作的操作系统。**

我们相信：无论是百万字的长篇小说、一幕话剧、一篇散文、还是一份技术文档——所有文字创作的本质都是**结构化思维的表达**。不同文体只是结构和约束的差异，底层的创作工作流管理是相通的。

```mermaid
flowchart TB
    subgraph Genre["文体层"]
        Novel["小说 (已实现)"]
        Script["剧本 (规划中)"]
        Essay["散文 (规划中)"]
        Poetry["诗歌 (规划中)"]
    end

    subgraph Engine["核心引擎"]
        Agent["Agent系统"]
        RAG["RAG引擎"]
        State["状态机"]
    end

    subgraph Assistant["辅助系统"]
        Manga["漫画分镜 (已实现)"]
        Coding["编程辅助 (已实现)"]
        Doc["文档生成 (规划中)"]
    end

    Novel --> Engine
    Script --> Engine
    Essay --> Engine
    Poetry --> Engine

    Engine --> Manga
    Engine --> Coding
    Engine --> Doc

    style Novel fill:#4CAF50,color:#fff
    style Manga fill:#4CAF50,color:#fff
    style Coding fill:#4CAF50,color:#fff
    style Script fill:#FF9800,color:#fff
    style Essay fill:#FF9800,color:#fff
    style Poetry fill:#FF9800,color:#fff
    style Doc fill:#FF9800,color:#fff
```

## 为什么市场需要 AFN？

当前的AI文字工具存在明显的**碎片化**问题：

| 需求 | 现状 | 问题 |
|------|------|------|
| 写小说 | Novelcrafter、Sudowrite、NovelAI... | 每个工具一套逻辑，数据不互通 |
| 写剧本 | Final Draft AI、Dramatron... | 又是另一套工具和学习成本 |
| 写文档 | Notion AI、Jasper... | 再换一个平台 |
| 写代码注释 | Copilot、Cursor... | 还要再来一个 |

**用户的痛点**：
- 每种文体都要学一个新工具
- 创作资产（角色、世界观、风格）无法跨文体复用
- 订阅费用叠加（$10 + $15 + $20... / 月）
- 数据分散在各个云端，迁移困难

**AFN的答案**：一个平台，解决所有文字问题。

## 当前已实现功能

### 小说创作系统（核心功能）

**状态机驱动的创作工作流**：

```mermaid
flowchart LR
    A["灵感对话"] --> B["蓝图设计"]
    B --> C["卷大纲"]
    C --> D["章大纲"]
    D --> E["正文写作"]
    E --> F["完成"]

    F -.->|回溯| E
    E -.->|回溯| D
    D -.->|回溯| C
    C -.->|回溯| B

    style A fill:#2196F3,color:#fff
    style B fill:#2196F3,color:#fff
    style C fill:#2196F3,color:#fff
    style D fill:#2196F3,color:#fff
    style E fill:#2196F3,color:#fff
    style F fill:#4CAF50,color:#fff
```

- **可回溯**：发现第三卷大纲有问题？回退重新生成，下游自动标记需更新
- **状态持久化**：关闭应用，明天继续，一切状态都在
- **阶段隔离**：每个阶段有明确的输入输出契约

**ReAct Agent 多智能体系统**：

```mermaid
flowchart LR
    subgraph Loop["ReAct 循环"]
        Think["思考"] --> Act["行动"]
        Act --> Observe["观察"]
        Observe --> Think
    end

    subgraph Tools["工具箱 14+"]
        T1["RETRIEVE_CONTEXT"]
        T2["CHECK_CHARACTER"]
        T3["DEEP_CHECK"]
        T4["REWRITE_PARAGRAPH"]
        T5["TRACK_FORESHADOW"]
    end

    Act --> Tools
    Tools --> Observe
```

Agent 会根据当前段落的问题，**自主决定**调用哪些工具、以什么顺序调用，而不是机械地执行预设流程。

**RAG 驱动的长期记忆**：

```mermaid
flowchart LR
    Query["当前段落"] --> Search["RAG检索"]

    subgraph VectorDB["向量库"]
        V1["第1章"]
        V2["第2章"]
        V3["..."]
        V49["第49章"]
    end

    VectorDB --> Search

    subgraph Results["检索结果"]
        R1["语义相关段落"]
        R2["角色状态历史"]
        R3["未解决伏笔"]
    end

    Search --> Results
    Results --> Context["增强上下文"]

    style Query fill:#E91E63,color:#fff
    style Context fill:#4CAF50,color:#fff
```

- 向量化存储：所有已完成章节自动入库
- 时序感知检索：不只是语义相似，还考虑时间线
- 角色状态追踪：自动维护每个角色在每章的状态

### 漫画分镜系统

将小说章节转换为漫画分镜，支持后续AI绘图：

```mermaid
flowchart LR
    A["章节文本"] --> B["信息提取"]
    B --> C["页面规划"]
    C --> D["分镜设计"]
    D --> E["绘图提示词"]

    B -.-> B1["角色/场景"]
    C -.-> C1["每页事件"]
    D -.-> D1["镜头构图"]
    E -.-> E1["SD/MJ Prompt"]

    style A fill:#9C27B0,color:#fff
    style E fill:#4CAF50,color:#fff
```

- **断点续传**：每个阶段可独立暂停/恢复
- **阶段重跑**：对某阶段不满意可单独重新生成
- **可视化编辑**：每个分镜都可查看和调整

### 编程辅助系统

不只是文学创作，AFN还能辅助技术写作：

```mermaid
flowchart LR
    A["需求描述"] --> B["架构设计"]
    B --> C["模块划分"]
    C --> D["目录规划"]
    D --> E["文件Prompt"]

    D <-.->|ReAct| Agent["目录规划Agent"]

    style A fill:#607D8B,color:#fff
    style E fill:#4CAF50,color:#fff
    style Agent fill:#FF5722,color:#fff
```

- **目录规划Agent**：根据需求自动设计项目结构
- **文件Prompt生成**：为每个代码文件生成详细的实现指南
- **代码审查Prompt**：生成测试和审查清单

## 规划中的功能

### 剧本创作系统（开发中）

```mermaid
flowchart LR
    A["故事概念"] --> B["人物小传"]
    B --> C["场景大纲"]
    C --> D["分场剧本"]
    D --> E["对白润色"]
    E --> F["定稿"]

    style A fill:#FF9800,color:#fff
    style F fill:#FF9800,color:#fff
```

**支持格式**：
- 电影剧本（标准好莱坞格式）
- 话剧剧本（舞台剧格式）
- 短视频脚本（分镜+台词+动作）
- 播客/音频剧本

**特色功能**：
- 角色声音一致性检查（确保每个角色说话风格统一）
- 场景节奏分析（控制情绪起伏曲线）
- 对白自然度评估
- 与小说系统共享角色库和世界观

### 散文/随笔系统（规划中）

```mermaid
flowchart LR
    A["主题构思"] --> B["素材收集"]
    B --> C["结构编排"]
    C --> D["初稿生成"]
    D --> E["风格打磨"]

    style A fill:#FF9800,color:#fff
    style E fill:#FF9800,color:#fff
```

**支持类型**：叙事散文（游记、回忆录）、议论散文（杂文、评论）、抒情散文（随笔、心情文字）

**特色功能**：风格模仿、意象库管理、节奏感分析

### 更多文体支持（远期规划）

| 文体 | 状态 | 核心功能点 |
|------|------|-----------|
| 诗歌 | 规划中 | 韵律检查、意象推荐、格律约束 |
| 学术论文 | 规划中 | 文献管理、论证结构、引用格式 |
| 商业文案 | 规划中 | A/B测试变体、情感分析、转化率预测 |
| 新闻稿件 | 规划中 | 倒金字塔结构、事实核查、风格规范 |
| 翻译润色 | 规划中 | 多语言支持、本地化建议、术语一致性 |

### 跨文体功能（平台级能力）

```mermaid
flowchart TB
    subgraph Pool["共享资源池"]
        Characters["角色库"]
        World["世界观库"]
        Style["风格模板库"]
    end

    Novel["小说项目"] <--> Characters
    Script["剧本项目"] <--> Characters
    Script <--> World
    Essay["散文项目"] <--> Style

    Note["一次创建 处处复用"]

    style Pool fill:#E3F2FD
    style Note fill:#FFF9C4
```

**核心理念**：小说里的主角可以直接出演话剧，小说的世界观可以直接用于剧本背景。

## 与现有工具的对比

### 小说创作领域

| 功能 | AFN | Novelcrafter | Sudowrite | AI_NovelGenerator | KoboldAI |
|------|-----|--------------|-----------|-------------------|----------|
| 多阶段工作流 | 6阶段状态机 | 有 | 有限 | 4阶段 | 无 |
| 状态回溯 | 完整支持 | 部分 | 部分 | 无 | 无 |
| ReAct Agent | 多Agent协作 | 无 | 无 | 无 | 无 |
| RAG长期记忆 | 时序感知检索 | Codex手动 | Story Bible | 有 | 有限 |
| 漫画分镜 | 完整流水线 | 无 | 无 | 无 | 无 |
| 本地部署 | 完全本地 | 云端 | 云端 | 本地 | 本地/云端 |
| 开源 | 是 | 否 | 否 | 是 | 是 |
| 多文体扩展 | 平台化设计 | 仅小说 | 仅小说 | 仅小说 | 仅小说 |

### 平台级对比

| 维度 | AFN | 传统方案（多工具组合） |
|------|-----|----------------------|
| 工具数量 | 1个平台 | 小说+剧本+文档=3+个工具 |
| 学习成本 | 一次学习 | 每个工具各学一遍 |
| 数据互通 | 原生支持 | 手动导出导入 |
| 资产复用 | 角色/世界观跨文体 | 重新创建 |
| 月费 | $0（自备API） | $50+（多订阅叠加） |
| 数据所有权 | 完全本地 | 分散在各云端 |

## 技术架构

### 整体架构

```mermaid
flowchart LR
    subgraph F["前端"]
        F1["小说"] & F2["编程"] & F3["设置"]
    end

    subgraph B["后端服务"]
        subgraph N["小说系统"]
            N1["管理"] & N2["蓝图"] & N3["大纲"] & N4["生成"] & N5["优化Agent"]
        end
        subgraph M["漫画系统"]
            M1["提取"] & M2["规划"] & M3["分镜"] & M4["提示词"]
        end
        subgraph C["编程系统"]
            C1["架构"] & C2["目录Agent"] & C3["Prompt"]
        end
    end

    subgraph E["引擎"]
        E1["LLM"] & E2["RAG"] & E3["向量"]
    end

    subgraph S["存储"]
        S1[("SQLite")] & S2[("Chroma")] & S3["API"]
    end

    F --> B --> E --> S

    style N5 fill:#E91E63,color:#fff
    style C2 fill:#E91E63,color:#fff
```

### 小说创作流程

```mermaid
flowchart LR
    A["创意"] --> B["灵感"] --> C["蓝图"] --> D["卷纲"] --> E["章纲"] --> F["正文"] --> G["优化Agent"]

    G --> H["RAG/角色/深检/重写/伏笔"]
    H --> I["章节"]
    I --> J["漫画"]

    style G fill:#E91E63,color:#fff
```

### 漫画分镜流程

```mermaid
flowchart LR
    A["章节"] --> B["提取<br/>角色/场景/事件"] --> C["规划<br/>页数/分配/节奏"] --> D["分镜<br/>布局/镜头/构图"] --> E["Prompt<br/>SD/MJ/Comfy"]

    style B fill:#9C27B0,color:#fff
    style C fill:#673AB7,color:#fff
    style D fill:#3F51B5,color:#fff
    style E fill:#2196F3,color:#fff
```

### 编程辅助流程

```mermaid
flowchart LR
    A["需求"] --> B["分析"] --> C["设计"] --> D["模块"] --> E["目录Agent"]
    E --> F["目录/文件Prompt/审查"]

    style E fill:#FF5722,color:#fff
```

### 数据流

```mermaid
flowchart LR
    A["点击"] --> B["UI"] --> C["Worker"] --> D["路由"] --> E["服务"] --> F["Agent"]
    F --> G["LLM"] & H["向量库"] & I["DB"]
    F --> J["SSE"] --> B
```

### 核心组件

| 组件 | 说明 | 实现 |
|------|------|------|
| LLM服务 | 大模型调用 | OpenAI/DeepSeek/通义/Ollama |
| RAG检索 | 时序向量检索 | ChromaDB + 时序权重 |
| 提示词 | 版本管理 | MD文件 + DB同步 |
| 向量化 | 文本嵌入 | sentence-transformers |
| 任务队列 | 异步处理 | 内存队列 + SSE |
| 图片生成 | AI绘图 | SD/ComfyUI/MJ |

## 快速开始

```bash
# 克隆项目
git clone https://github.com/your-repo/AFN.git
cd AFN

# 一键启动（自动配置环境、安装依赖）
python run_app.py
```

**系统要求**：
- Windows 10/11
- Python 3.10+
- 8GB内存（推荐16GB）
- 需配置LLM API（支持OpenAI、DeepSeek、通义千问、Ollama本地等）

## 适用场景

**AFN 适合你，如果你：**
- 是需要处理多种文体的创作者（小说家、编剧、自媒体...）
- 厌倦了为每种需求订阅不同的工具
- 希望创作资产（角色、世界观、风格）能跨项目复用
- 重视数据隐私，希望一切存储在本地
- 喜欢开源、可定制的解决方案
- 有技术背景，愿意参与平台的扩展开发

**AFN 可能不适合，如果你：**
- 只需要快速生成短篇内容
- 偏好开箱即用的云端服务
- 不想管理本地环境和API配置

## 开发路线图

```mermaid
gantt
    title AFN 开发路线图
    dateFormat YYYY-MM

    section 已完成
    小说创作核心工作流           :done, 2024-10, 2024-12
    多Agent内容优化系统          :done, 2024-11, 2024-12
    RAG向量检索集成              :done, 2024-11, 2024-12
    漫画分镜生成流水线           :done, 2025-01, 2025-03
    编程Prompt生成系统           :done, 2025-01, 2025-03

    section 进行中
    剧本创作系统                 :active, 2025-04, 2025-06
    跨文体角色库                 :active, 2025-04, 2025-06
    风格模板系统                 :2025-05, 2025-06

    section 规划中
    散文随笔系统                 :2025-07, 2025-09
    世界观共享库                 :2025-07, 2025-09
    插件系统架构                 :2025-08, 2025-09
    诗歌创作系统                 :2025-10, 2025-12
    多语言支持                   :2025-10, 2025-12

    section 远期
    学术写作系统                 :2026-01, 2026-06
    商业文案系统                 :2026-01, 2026-06
```

## 参与贡献

AFN 是一个开放的平台，我们欢迎：

- **文体扩展**：为新的文体类型开发适配器
- **Agent工具**：为Agent系统添加新的工具
- **提示词优化**：改进各环节的提示词质量
- **UI/UX改进**：提升用户体验
- **文档翻译**：帮助项目走向国际

## 许可证

MIT License

---

## 致谢

- [AI_NovelGenerator](https://github.com/YILING0013/AI_NovelGenerator) - 多章节生成的灵感来源
- [KoboldAI](https://github.com/KoboldAI/KoboldAI-Client) - 本地模型支持的先驱
- [Novelcrafter](https://www.novelcrafter.com/) - Codex知识库概念的启发
- [StoryCraftr](https://github.com/raestrada/storycraftr) - CLI工作流的参考

## 参考资料

- [GitHub AI小说项目盘点](https://zhuanlan.zhihu.com/p/1888262970552862495)
- [Novelcrafter 评测](https://kindlepreneur.com/novelcrafter-review/)
- [Sudowrite vs Novelcrafter 对比](https://sudowrite.com/blog/sudowrite-vs-novelcrafter-the-ultimate-ai-showdown-for-novelists/)
- [2025-2026 最佳AI写作工具](https://kindlepreneur.com/best-ai-writing-tools/)
