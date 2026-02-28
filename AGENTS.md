# Repository Guidelines

本指南帮助贡献者快速定位模块、运行项目、提交变更。开始前建议先通读 `README.md`、`backend/README.md` 与 `deploy/README.md`。

## 项目结构

- `backend/app/`: FastAPI 后端源码（按既有分层修改：`api/` → `services/` → `repositories/` → `models/`）。
- `frontend/`: PyQt6 桌面端 UI（入口：`frontend/main.py`；窗口/面板多在 `frontend/windows/`）。
- `frontend-web/src/`: React + Vite Web UI（入口：`frontend-web/src/main.tsx`；页面在 `frontend-web/src/pages/`；组件在 `frontend-web/src/components/`）。
- `deploy/`: Docker / 反向代理部署文件；`test/`: 脚本测试；`tools/`: 工具脚本。
- 运行时数据统一写入 `storage/`（DB、向量、日志、配置），不要提交到 Git。

## 构建、测试与本地开发命令

- 桌面端一键启动（自动准备环境，启动后端 + PyQt）：`python run_app.py`
- 强制重建环境并重装依赖：`python setup_env.py --force`
- 仅启动后端（热重载，默认端口 `8123`）：`cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8123`
- 启动 Web 开发环境（自动选择空闲端口并打印 URL）：`python start_web.py`（或：`cd frontend-web && npm run dev`）
- Web 校验：`cd frontend-web && npm run lint`、`npm run build`
- 部署（Docker Compose 脚本）：`deploy/scripts/up.sh` / `deploy/scripts/down.sh` / `deploy/scripts/logs.sh`

## 代码风格与命名规范

- Python：4 空格缩进；尽量补齐类型标注；保持分层（避免把 UI/IO 逻辑塞进 `backend/app/services/`）。
- React/TSX：2 空格缩进；组件文件使用 `PascalCase.tsx`；使用 ESLint（`npm run lint`）。
- Web 页面/Hook：避免“巨石组件”，重复状态逻辑优先抽到 `frontend-web/src/hooks/` 或 `frontend-web/src/utils/`。
- 命名：Python 模块 `snake_case.py`；避免过度缩写，优先可读性。

## 测试指南

- 当前以脚本形式为主：`python test/chunkSplitTest/test_semantic_chunker.py`
- Web 改动需确保 `cd frontend-web && npm run lint` 与 `npm run build` 均通过（依赖安装完成后再执行）。

## 常见工作流

- 新环境初始化：`python setup_env.py --force`（Python 依赖）+ `cd frontend-web && npm install`（Web 依赖）
- 本地快速回归：`python -m compileall backend/app frontend`（语法检查）+ 关键脚本用例（见 `test/`）
- Web 调试：`cd frontend-web && npm run dev` 后优先看浏览器 Console / Network；接口问题再看后端日志

## 配置与数据

- 桌面端设置通常会落到 `storage/config.json`；手动编辑时请保持为合法 JSON，避免启动期读取失败。
- 示例环境变量：`backend/.env.example`、`deploy/.env.example`（不要提交真实 `.env`）。
- 不要提交到 Git：`backend/.env`、`deploy/.env`、`storage/`、`*.db`、`node_modules/`。

## 提交与 PR 规范

- Commit 多为中文短句（常见“优化/修复/添加…”），一次提交聚焦一个主题。
- PR 需包含：做了什么/为什么、如何验证（命令 + 预期结果）、以及 UI 变更截图/GIF（如适用）。
