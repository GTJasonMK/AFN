# AFN 云端部署（Docker Compose）

文档生成：2026-02-02（Codex）

本目录提供一套 **WebUI（Nginx 静态托管）+ 后端（FastAPI/Uvicorn）** 的云端部署脚本：
- WebUI 通过同源路径 `/api` 反代到后端，避免跨域问题，并兼容 **SSE** 与 **HttpOnly Cookie 登录**。
- 登录开关由部署方在部署前决定（环境变量或 `storage/config.json`），不会在 WebUI 设置中暴露开关。

## 1) 前置条件

- 云主机：Linux（Ubuntu/Debian/CentOS 均可）
- 已安装：Docker + Docker Compose（`docker compose`）

## 2) 配置

在项目根目录执行：

1. 复制环境文件
   - `cp deploy/.env.example deploy/.env`
2. 编辑 `deploy/.env`（至少修改 `SECRET_KEY`）

可选登录（部署前决定，修改后需重启）：
- `AFN_AUTH_ENABLED=true|false`
- `AFN_AUTH_ALLOW_REGISTRATION=true|false`

## 3) 启动/停止

- 启动：`deploy/scripts/up.sh`
- 停止：`deploy/scripts/down.sh`
- 查看日志：`deploy/scripts/logs.sh`

默认监听端口：
- WebUI：`http://<server-ip>:80`
- API：`http://<server-ip>:80/api/health`
- Docs：`http://<server-ip>:80/docs`

端口可在 `deploy/.env` 里改 `AFN_HTTP_PORT`。

## 4) 数据持久化

`docker-compose.yml` 将宿主机的 `storage/` 挂载到容器 `/app/storage`：
- `storage/afn.db`：SQLite 数据库
- `storage/config.json`：部署配置（含可选登录开关）
- `storage/models/`：本地嵌入模型缓存（如启用 local embedding）
- `storage/logs/`：运行日志（如有）

## 5) 备份

- 备份数据库+配置：`deploy/scripts/backup.sh`
- 如需包含模型缓存：`deploy/scripts/backup.sh --with-models`

