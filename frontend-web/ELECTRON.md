** 🎯 Electron 说明 **

当前仓库已经为 `frontend-web` 增加了 Electron 壳，保留原有
`Vite + React + FastAPI` 结构，不改前端业务请求路径。


** 🚀 常用命令 **

1. 安装依赖：`cd frontend-web && npm install`
2. 开发模式：`cd frontend-web && npm run electron:dev`
3. 运行构建产物：`cd frontend-web && npm run build && npm run electron:start`
4. 生成安装包：`cd frontend-web && npm run electron:dist`


** 🔧 运行方式 **

- 开发模式：
  Electron 会自动拉起本地 FastAPI 后端和 Vite 开发服务器。
- 生产模式：
  Electron 会加载 `dist/` 静态资源，并在本地启动一个轻量 HTTP
  服务，把 `/api` 请求转发到 FastAPI。
- 数据目录：
  Electron 会把后端 `storage` 重定向到系统用户目录，避免安装版写回源码目录。


** ⚠️ 当前限制 **

- 当前打包默认会把 `backend/` 源码带进 Electron 包内。
- Python 解释器和后端依赖不会自动变成完全独立的运行时。
- 因此，如果目标机器没有可用的 Python 环境，应用仍然无法单独运行。

如果你下一步要做“真正可分发给别人双击即用”的安装包，建议继续补一层：
把 Python 运行时和后端依赖一起封进安装包，或把后端单独打成可执行文件。
