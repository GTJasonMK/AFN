# Arboris Novel - 功能文档

AI驱动的长篇小说创作助手，提供从灵感到成稿的完整创作工作流。

## 目录

- [项目概述](#项目概述)
- [核心创作流程](#核心创作流程)
- [功能详解](#功能详解)
  - [首页](#首页)
  - [灵感对话](#灵感对话)
  - [项目工作台](#项目工作台)
  - [项目详情](#项目详情)
  - [写作台](#写作台)
  - [设置](#设置)
- [技术特性](#技术特性)
- [快捷键](#快捷键)

---

## 项目概述

Arboris Novel是一款基于PyQt6的桌面应用，专为个人本地使用设计。核心特点：

- **开箱即用**：一键启动，无需复杂配置
- **无需登录**：完全本地化，数据存储在本地SQLite数据库
- **AI驱动**：支持OpenAI兼容API，包括Gemini、Claude等模型
- **完整工作流**：从灵感梳理到章节生成的全流程支持

---

## 核心创作流程

```
1. 灵感对话 (DRAFT)
   ↓ 多轮AI对话，梳理创意

2. 生成蓝图 (BLUEPRINT_READY)
   ↓ 自动生成世界观、角色、章节规划

3a. 短篇流程 (<50章)
   ↓ 直接生成章节大纲

3b. 长篇流程 (≥50章)
   ↓ 先生成分部大纲（每25章一部分）
   ↓ 再生成详细章节大纲

4. 章节大纲就绪 (CHAPTER_OUTLINES_READY)
   ↓

5. 章节写作 (WRITING)
   ↓ 为每章生成3个候选版本
   ↓ RAG检索提供上下文
   ↓ 用户选择最佳版本

6. 完成创作 (COMPLETED)
   → 导出TXT文件
```

---

## 功能详解

### 首页

**路径**：应用启动默认页面

**功能**：
- 展示应用品牌和入口
- 浮动粒子动画背景
- 标题呼吸动画效果
- 快速导航到灵感模式和创作工作台

**操作**：
- 点击"灵感涌现"进入灵感对话
- 点击"创作工作台"查看所有项目
- 点击"设置"配置LLM

---

### 灵感对话

**路径**：首页 → 灵感涌现

**功能**：
- 与AI进行多轮对话，梳理创作灵感
- 打字机效果显示AI回复
- 自动创建新项目
- 对话完成状态检测

**操作流程**：
1. 输入初始创意想法
2. AI引导用户完善故事元素：
   - 故事类型和题材
   - 主要角色设定
   - 核心冲突和主题
   - 故事背景和世界观
   - 预期章节数
3. 对话完成后点击"生成蓝图"
4. 确认蓝图内容，跳转到项目详情

**注意事项**：
- 如果对话未完成就生成蓝图，会弹出警告
- 建议至少进行5轮对话，或等待AI标记对话完成以获得高质量蓝图

---

### 项目工作台

**路径**：首页 → 创作工作台

**功能**：
- 网格展示所有小说项目
- 项目卡片显示：
  - 标题和类型
  - 完成进度条
  - 最后编辑时间
  - 状态标签
- 鼠标悬停显示操作按钮

**操作**：
- 点击"创建新项目"卡片开始新创作
- 查看详情：进入项目详情页
- 继续创作：直接进入写作台
- 删除：删除项目（不可恢复）

---

### 项目详情

**路径**：工作台 → 查看详情

**功能模块**：

#### 概览区域
- 项目标题和一句话简介
- 项目状态
- 总章节数
- 创建/更新时间

#### 世界观设置
- 故事背景描述
- 时代/地点设定
- 社会/文化背景

#### 角色管理
- 角色列表（姓名、身份、性格）
- 角色目标和能力
- 与主角关系

#### 角色关系
- 角色间关系描述
- 关系网络可视化

#### 章节大纲
- 各章节标题和摘要
- 生成/重新生成大纲按钮

#### 章节列表
- 章节编号和标题
- 生成状态（未生成/生成中/已完成/失败）
- 字数统计

**操作**：
- 生成章节大纲（首次）
- 重新生成章节大纲
- 生成分部大纲（长篇小说）
- 点击章节进入写作台

---

### 写作台

**路径**：项目详情 → 点击章节

**功能**：

#### 侧边栏
- 章节列表导航
- 章节状态指示
- 快速切换章节

#### 工作区
- 章节大纲显示
- 生成章节按钮
- 版本选择器（最多3个版本）
- 内容编辑器
- 字数统计

**操作流程**：
1. 查看当前章节大纲
2. 点击"生成章节"
3. AI生成3个候选版本
4. 预览和比较各版本
5. 选择最满意的版本
6. 可手动编辑微调
7. 保存并继续下一章

**RAG上下文增强**：
- 自动检索前文相关内容
- 前3章内容摘要
- 角色发展和关系追踪
- 确保故事连贯性

---

### 设置

**路径**：首页 → 设置

**功能**：

#### LLM配置管理
- 添加新配置
- 编辑现有配置
- 删除配置
- 激活/停用配置
- 测试连接

**配置项**：
- 配置名称（如"Gemini 2.5 Flash"）
- API Base URL
- API Key
- 模型名称

**支持的LLM服务**：
- OpenAI API
- Google Gemini（通过兼容API）
- Anthropic Claude（通过兼容API）
- 本地模型（如Ollama）
- 其他OpenAI兼容服务

---

## 技术特性

### 主题系统
- **深色/亮色主题切换**：点击右下角按钮或Ctrl+T
- **响应式设计**：适配不同屏幕尺寸
- **DPI感知**：高分屏适配
- **玻璃态效果**：现代化UI设计

### 异步处理
- 非阻塞API调用
- 加载动画反馈
- 后台任务支持长时间操作

### 数据安全
- 本地SQLite存储
- 无云端同步
- 数据完全在用户控制下

### 导出功能
- TXT格式导出
- 保留章节结构
- 支持批量导出

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+T` | 切换深色/亮色主题 |
| `Backspace` / `Alt+←` | 返回上一页 |
| `F5` | 刷新当前页面 |

---

## 状态说明

### 项目状态

| 状态 | 中文名 | 说明 |
|------|--------|------|
| `draft` | 草稿 | 灵感对话进行中 |
| `blueprint_ready` | 蓝图就绪 | 蓝图生成完成 |
| `part_outlines_ready` | 部分大纲就绪 | 分部大纲生成完成（长篇） |
| `chapter_outlines_ready` | 章节大纲就绪 | 章节大纲生成完成 |
| `writing` | 写作中 | 章节创作进行中 |
| `completed` | 已完成 | 所有章节完成 |

### 章节状态

| 状态 | 中文名 | 说明 |
|------|--------|------|
| `not_generated` | 未生成 | 等待生成 |
| `generating` | 生成中 | AI正在生成 |
| `evaluating` | 评审中 | AI正在评审版本 |
| `selecting` | 选择中 | 正在选择最佳版本 |
| `successful` | 已完成 | 生成完成 |
| `failed` | 失败 | 生成失败 |
| `evaluation_failed` | 评审失败 | 评审过程失败 |
| `waiting_for_confirm` | 等待确认 | 等待用户确认 |

---

## API端点概览

### 项目管理
- `GET /api/novels` - 获取所有项目
- `POST /api/novels` - 创建新项目
- `GET /api/novels/{id}` - 获取项目详情
- `DELETE /api/novels` - 批量删除项目

### 灵感对话
- `POST /api/novels/{id}/inspiration/converse` - 灵感对话

### 蓝图管理
- `POST /api/novels/{id}/blueprint/generate` - 生成蓝图
- `PATCH /api/novels/{id}/blueprint` - 更新蓝图

### 大纲生成

**分部大纲（长篇小说）**
- `POST /api/writer/novels/{id}/parts/generate` - 生成分部大纲
- `POST /api/writer/novels/{id}/part-outlines/regenerate` - 重新生成分部大纲
- `POST /api/writer/novels/{id}/parts/{part_number}/chapters` - 为指定部分生成章节大纲
- `POST /api/writer/novels/{id}/parts/batch-generate` - 批量生成章节大纲
- `POST /api/writer/novels/{id}/parts/{part_number}/cancel` - 取消部分生成
- `GET /api/writer/novels/{id}/parts/progress` - 获取生成进度

**章节大纲（首次生成）**
- `POST /api/novels/{id}/chapter-outlines/generate` - 一键生成所有章节大纲（用于项目初始化阶段）

**章节大纲（灵活管理）**
- `POST /api/writer/novels/{id}/chapter-outlines/generate-by-count` - 增量生成章节大纲（body: `{count, start_from?}`）
- `DELETE /api/writer/novels/{id}/chapter-outlines/delete-latest` - 删除最新N章大纲（body: `{count}`）
- `POST /api/writer/novels/{id}/chapter-outlines/{chapter_number}/regenerate` - 重新生成指定章节大纲（body: `{prompt?}`）

> **说明**：章节大纲生成提供两种方式：
> - **首次生成**（`/api/novels`路由）：项目初始化时一键生成所有章节大纲，适合短篇小说或确定结构的创作
> - **灵活管理**（`/api/writer`路由）：写作阶段的增量调整，支持按数量生成、删除最新、单章重新生成，适合长篇小说或迭代式创作

### 章节写作

**章节生成**
- `POST /api/writer/novels/{id}/chapters/generate` - 生成章节（3个版本）（body: `{chapter_number}`）
- `POST /api/writer/novels/{id}/chapters/retry-version` - 重试生成版本（body: `{chapter_number, version_index}`）

**章节管理**
- `POST /api/writer/novels/{id}/chapters/select` - 选择最佳版本（body: `{chapter_number, version_index}`）
- `POST /api/writer/novels/{id}/chapters/evaluate` - 评审章节版本
- `POST /api/writer/novels/{id}/chapters/edit` - 编辑章节内容（body: `{chapter_number, content}`）
- `POST /api/writer/novels/{id}/chapters/update-outline` - 更新章节大纲
- `POST /api/writer/novels/{id}/chapters/delete` - 删除章节（body: `{chapter_numbers: [...]}`）

### 配置管理
- `GET /api/llm-configs` - 获取LLM配置列表
- `POST /api/llm-configs` - 创建LLM配置
- `PUT /api/llm-configs/{id}` - 更新LLM配置
- `DELETE /api/llm-configs/{id}` - 删除LLM配置
- `POST /api/llm-configs/{id}/activate` - 激活配置
- `POST /api/llm-configs/{id}/test` - 测试连接

---

## 常见问题

### 1. 蓝图生成失败（500错误）
**原因**：灵感对话轮数过少，AI无法获取足够信息
**解决**：继续对话，提供更多故事细节后再生成

### 2. LLM连接失败
**原因**：API配置错误或网络问题
**解决**：在设置页面测试连接，检查API Key和URL

### 3. 章节生成超时
**原因**：模型响应慢或网络不稳定
**解决**：检查网络，或尝试更快的模型

### 4. 主题切换后数据丢失
**已修复**：v2025-11-20版本已修复此问题

---

## 版本信息

- **当前版本**：1.0.0-pyqt
- **最后更新**：2025-11-20
- **技术栈**：Python 3.10+ / FastAPI / PyQt6 / SQLite

---

## 反馈与支持

如有问题或建议，请访问：
https://github.com/anthropics/claude-code/issues
