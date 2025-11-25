# Arboris Novel - PyQt 桌面版

AI 辅助长篇小说创作桌面应用，开箱即用，无需登录。

## ✨ 特性

- 🚀 **开箱即用**：无需注册登录，启动即可使用
- 🎨 **界面配置**：所有 LLM 设置在应用内完成，无需修改配置文件
- 💬 **智能对话**：AI 辅助梳理创意，生成完整小说蓝图
- 📖 **章节生成**：自动生成多个版本，AI 评审辅助选择
- 🔧 **灵活配置**：支持多个 LLM 提供商，随时切换
- 💾 **本地存储**：所有数据存储在本地，完全私密

## 📁 目录结构

```
pyqt项目迁移/
├── backend/              # FastAPI 后端服务
│   ├── app/             # 应用代码
│   ├── prompts/         # LLM 提示词
│   ├── storage/         # 数据存储（自动创建）
│   ├── start.bat        # 启动脚本
│   └── README.md        # 后端文档
│
├── frontend/            # PyQt6 桌面前端
│   ├── ui/             # UI 组件和页面
│   │   ├── components.py      # 专业UI组件库
│   │   ├── styles.py          # 设计系统
│   │   ├── main_window_v2.py  # 主窗口V2
│   │   ├── sidebar.py         # 侧边栏导航
│   │   └── pages/             # 页面组件
│   ├── api/            # API 客户端
│   ├── main_v2.py      # 专业UI入口
│   ├── start_v2.bat    # 启动专业UI
│   ├── start.bat       # 启动简易UI
│   └── README.md       # 前端文档
│
├── start_all.bat       # ⭐ 一键启动前后端
├── stop_all.bat        # 停止所有服务
├── STARTUP_GUIDE.md    # 启动脚本详细说明
├── QUICK_START.md      # 快速上手指南
├── NO_AUTH_UPDATE.md   # 无认证更新说明
└── README.md           # 本文件
```

## 🚀 一键启动（推荐）

### 方式一：自动启动前后端

```bash
# 双击运行或命令行执行
start_all.bat
```

**启动流程**：
1. 自动启动后端服务（新窗口）
2. 健康检查（等待后端就绪）
3. 自动启动前端UI（专业版V2）
4. 享受创作！

**预计时间**：10-20秒

### 方式二：手动分别启动

#### 1. 启动后端（终端1）

```bash
cd backend
start.bat
```

首次启动会自动安装依赖，等待看到：
```
INFO:     Uvicorn running on http://127.0.0.1:8123
```

#### 2. 启动前端（终端2）

```bash
cd frontend
start_v2.bat  # 专业UI版本
# 或
start.bat     # 简易UI版本
```

应用窗口会自动打开。

### 3. 配置 LLM（在应用界面）

1. 点击左侧 **"⚙️ LLM配置"**
2. 点击 **"➕ 新建配置"**
3. 填写 API Key 等信息
4. 点击 **"✅ 激活此配置"**

✅ 完成！开始创作您的第一部小说

## 📖 详细文档

- **一键启动**：[STARTUP_GUIDE.md](STARTUP_GUIDE.md) - 启动脚本详细说明
- **新手必读**：[QUICK_START.md](QUICK_START.md) - 5分钟上手指南
- **专业UI**：[frontend/V2_QUICKSTART.md](frontend/V2_QUICKSTART.md) - 专业UI使用指南
- **前端使用**：[frontend/README.md](frontend/README.md) - UI功能说明
- **后端配置**：[backend/README.md](backend/README.md) - API和配置
- **开发进度**：[frontend/V2_PROGRESS.md](frontend/V2_PROGRESS.md) - UI重构进展
- **更新日志**：[NO_AUTH_UPDATE.md](NO_AUTH_UPDATE.md) - 版本变更

## 🎯 使用流程

```
创建项目 → 概念对话 → 生成蓝图 → 生成章节 → 导出作品
   ↓          ↓          ↓          ↓          ↓
 输入标题   与AI交流   查看大纲   多版本选择   TXT文件
```

## 💻 系统要求

- Windows 10/11
- Python 3.10 或更高版本
- 8GB 内存（推荐）
- 网络连接（调用 LLM API）

## 🔧 支持的 LLM

- ✅ OpenAI (GPT-3.5, GPT-4)
- ✅ 通义千问
- ✅ 智谱 ChatGLM
- ✅ 百度文心一言
- ✅ Moonshot (Kimi)
- ✅ Ollama（本地部署）
- ✅ 所有 OpenAI 兼容接口

**配置方法**：在应用的"LLM配置"页面添加对应的 Base URL 和 API Key

## ❓ 常见问题

### 如何获取 API Key？

- **OpenAI**：https://platform.openai.com/api-keys
- **国内服务**：2API、API2D 等中转服务
- **本地部署**：安装 Ollama 使用本地模型

### 启动失败？

1. 检查 Python 版本：`python --version`（需要 3.10+）
2. 查看后端日志：`backend/storage/debug.log`
3. 确保端口 8123 未被占用

### 生成速度慢？

1. 使用更快的模型（gpt-3.5-turbo）
2. 使用国内中转服务
3. 检查网络连接

### 内容质量不满意？

1. 概念对话阶段提供更详细信息
2. 调整温度参数（在 LLM 配置中）
3. 多生成几个版本对比选择
4. 手动编辑完善

## 🎨 界面预览

### 专业UI V2（推荐）

**启动方式**：`start_all.bat` 或 `frontend/start_v2.bat`

**特性**：
- 渐变Header（靛蓝→紫色）
- 侧边栏导航（5个页面）
- 项目列表页（网格卡片布局）
- 悬浮效果和阴影动画
- 状态徽章和进度条
- 还原度约90%的Web版设计

**布局**：
```
┌─────────────────────────────────────────┐
│ 📖 Arboris Novel (渐变Header)            │
├──────────┬──────────────────────────────┤
│ 📚 项目列表│ ┌────┐ ┌────┐ ┌────┐         │
│ 💡 概念对话│ │Card│ │Card│ │Card│         │
│ 📋 蓝图编辑│ └────┘ └────┘ └────┘         │
│ ✍️ 章节写作│ [状态徽章] [进度条]            │
│ ⚙️ LLM配置│                              │
└──────────┴──────────────────────────────┘
```

### 简易UI V1

**启动方式**：`frontend/start.bat`

**特性**：
- 基础功能完整
- 界面简洁
- 适合快速测试

### 页面功能

#### LLM 配置页面
- 添加多个 LLM 配置
- 一键切换激活配置
- 导入/导出配置
- 测试连接功能

#### 概念对话页面
- 气泡式对话界面（V2开发中）
- 实时 AI 交互
- 对话历史记录

#### 蓝图编辑页面
- 标签页显示（概览、世界观、角色、章节）
- 可视化编辑
- 一键重新生成

#### 写作台页面
- 章节列表管理
- 多版本对比
- AI 评审辅助
- 在线编辑

## 📝 示例项目

创建一个科幻小说示例：

```
项目名称：星际迷航-量子危机
创作方向：2200年，量子通讯网络崩溃，主角需要找出真相

概念对话：
1. 讨论世界观（科技水平、社会结构）
2. 设计主角（背景、性格、目标）
3. 确定冲突（主要矛盾、反派）
4. 规划章节（30章，每章5000字）

生成蓝图 → 生成章节 → 完成作品
```

## 🛠️ 开发说明

### 技术栈

**后端**：
- FastAPI 0.110.0
- SQLAlchemy 2.0.44（异步ORM）
- SQLite/MySQL（可选）
- OpenAI API

**前端**：
- PyQt6 6.6.1
- Python 3.10+
- 专业UI设计系统（基于Web版Tailwind CSS）

**UI组件库**：
- GradientButton（渐变按钮）
- LoadingSpinner（加载动画）
- StatusBadge（状态徽章）
- Card（卡片容器）
- ProgressBar（进度条）
- EmptyState（空状态）

### 架构

```
前端 (PyQt6) ←→ HTTP API ←→ 后端 (FastAPI) ←→ 数据库 (SQLite)
                                    ↓
                               LLM API (OpenAI兼容)
```

### 数据流

```
用户输入 → API客户端 → 后端路由 → 业务逻辑 → LLM服务 → 返回结果
```

## 🔐 隐私和安全

- ✅ 所有数据存储在本地
- ✅ 不收集任何用户信息
- ✅ API Key 仅存储在本地数据库
- ✅ 不上传任何创作内容（除了发送给 LLM）

## 📄 许可证

与主项目相同

## 🙏 致谢

基于 Arboris Novel 原项目开发，专为单机桌面使用优化。

---

**立即开始**：双击 `start_all.bat` 一键启动！

**详细文档**：查看 [STARTUP_GUIDE.md](STARTUP_GUIDE.md)

**问题反馈**：查看日志文件或联系开发者
