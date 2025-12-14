# AFN (Agents for Novel) - AI 辅助长篇小说创作工具

AI 辅助长篇小说创作桌面应用，开箱即用，无需登录。

## 特性

- **开箱即用**：无需注册登录，启动即可使用
- **界面配置**：所有 LLM 设置在应用内完成，无需修改配置文件
- **智能对话**：AI 辅助梳理创意，生成完整小说蓝图
- **章节生成**：自动生成多个版本，AI 评审辅助选择
- **灵活配置**：支持多个 LLM 提供商，随时切换
- **本地存储**：所有数据存储在本地，完全私密
- **RAG 增强**：智能检索上下文，确保故事连贯性
- **漫画转化**：将章节内容智能分割为漫画场景，生成 AI 绘图提示词
- **图片生成**：集成多厂商图片生成 API，一键生成场景插图
- **PDF 导出**：将生成的图片导出为 PDF，方便分享和打印

## 目录结构

```
AFN/
├── backend/              # FastAPI 后端服务
│   ├── app/             # 应用代码
│   │   ├── api/routers/ # API 路由
│   │   ├── services/    # 业务逻辑层
│   │   │   ├── chapter_generation/  # 章节生成
│   │   │   ├── image_generation/    # 图片生成
│   │   │   ├── manga_prompt/        # 漫画提示词
│   │   │   └── rag/                 # RAG 检索
│   │   ├── models/      # SQLAlchemy 模型
│   │   └── schemas/     # Pydantic 数据模型
│   ├── prompts/         # LLM 提示词模板
│   ├── storage/         # 数据存储（自动创建）
│   │   ├── afn.db       # SQLite 数据库
│   │   └── generated_images/  # 生成的图片
│   └── README.md        # 后端文档
│
├── frontend/            # PyQt6 桌面前端
│   ├── windows/         # 页面窗口
│   │   ├── writing_desk/  # 写作台
│   │   └── settings/      # 设置页面
│   ├── components/      # UI 组件库
│   ├── themes/          # 主题系统
│   ├── api/client.py    # API 客户端
│   ├── main.py          # 应用入口
│   └── README.md        # 前端文档
│
├── docs/                # 项目文档
├── run_app.py           # 统一启动入口（推荐）
├── build.bat            # 打包脚本
└── README.md            # 本文件
```

## 快速启动

### 方式一：一键启动（推荐）

```bash
# 首次运行会自动创建虚拟环境并安装依赖
python run_app.py
```

脚本会自动完成：
1. 检查 Python 版本（需要 3.10+）
2. 创建前后端虚拟环境
3. 安装所有依赖
4. 启动后端服务
5. 启动前端 GUI

### 方式二：分别启动

#### 1. 启动后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8123
```

等待看到：
```
INFO: Uvicorn running on http://127.0.0.1:8123
```

#### 2. 启动前端

```bash
cd frontend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 3. 配置 LLM

1. 点击右下角设置按钮进入设置页面
2. 选择 "LLM 配置"
3. 点击 "新建配置"
4. 填写 API Key 等信息
5. 点击 "激活此配置"

完成！开始创作您的第一部小说。

## 使用流程

```
创建项目 -> 灵感对话 -> 生成蓝图 -> 生成大纲 -> 章节写作 -> 导出作品
   |          |          |          |          |          |
 输入标题   与AI交流   查看设定   章节纲要   多版本选择   TXT文件
                                              |
                                              v
                                     漫画提示词 -> 生成图片 -> PDF导出
                                         |          |          |
                                     场景分割   AI绘图服务   分享打印
```

## 系统要求

- Windows 10/11
- Python 3.10+
- 8GB 内存（推荐）
- 网络连接（调用 LLM API）

## 支持的 LLM

- OpenAI (GPT-3.5, GPT-4, GPT-4o)
- 通义千问
- 智谱 ChatGLM
- 百度文心一言
- Moonshot (Kimi)
- DeepSeek
- Ollama（本地部署）
- 所有 OpenAI 兼容接口

**配置方法**：在应用的"LLM配置"页面添加对应的 Base URL 和 API Key

## 支持的图片生成服务

- **OpenAI 兼容接口**：nano-banana-pro、DALL-E 2/3、Gemini 等
- **Stability AI**：Stable Diffusion XL 等
- **本地 ComfyUI**：支持自定义工作流

**配置方法**：在应用的"生图模型"页面添加配置

### 图片生成功能说明

1. **漫画提示词生成**：在写作台的"漫画"标签页，点击"生成提示词"将章节内容分割为多个场景
2. **场景图片生成**：每个场景卡片有"生成图片"按钮，点击即可调用配置的图片生成服务
3. **图片管理**：生成的图片按 `项目/章节/场景` 结构存储在 `storage/generated_images/` 目录
4. **PDF导出**：选择多张图片导出为 PDF 文件，支持自定义布局

## 技术栈

**后端**：
- FastAPI 0.110.0
- SQLAlchemy 2.0 (异步 ORM)
- SQLite / MySQL
- OpenAI API 兼容接口
- RAG 检索增强
- ReportLab (PDF 生成)

**前端**：
- PyQt6 6.6.1
- 响应式主题系统
- DPI 感知布局

## 常见问题

### 如何获取 API Key？

- **OpenAI**：https://platform.openai.com/api-keys
- **国内服务**：2API、API2D 等中转服务
- **本地部署**：安装 Ollama 使用本地模型

### 如何配置图片生成服务？

1. 进入设置页面，选择"生图模型"
2. 点击"新增配置"
3. 选择服务类型（OpenAI兼容/Stability/ComfyUI）
4. 填写 API 地址和密钥
5. 选择默认模型和风格
6. 点击"激活"启用配置

推荐使用 nano-banana-pro 或 DALL-E 3 获得最佳效果。

### 启动失败？

1. 检查 Python 版本：`python --version`（需要 3.10+）
2. 查看后端日志：`backend/storage/debug.log`
3. 确保端口 8123 未被占用

### 生成速度慢？

1. 使用更快的模型（gpt-3.5-turbo）
2. 使用国内中转服务
3. 检查网络连接

## 隐私和安全

- 所有数据存储在本地
- 不收集任何用户信息
- API Key 仅存储在本地数据库
- 不上传任何创作内容（除了发送给 LLM）

## 许可证

MIT License

---

**立即开始**：运行 `python run_app.py` 一键启动！
