# AFN 云端部署（Docker Compose）

文档生成：2026-02-02（Codex）

本目录提供一套 **WebUI（Nginx 静态托管）+ 后端（FastAPI/Uvicorn）** 的云端部署脚本：
- WebUI 通过同源路径 `/api` 反代到后端，避免跨域问题，并兼容 **SSE** 与 **HttpOnly Cookie 登录**。
- 登录开关由部署方在部署前决定（环境变量或 `storage/config.json`），不会在 WebUI 设置中暴露开关。

> 适用场景：你只有一台 Ubuntu 服务器（可带 GUI，也可纯命令行），希望用一套命令把 AFN Web 版跑起来。

## 0) 你需要准备的信息

- 服务器公网 IP：例如 `1.2.3.4`
- 服务器登录用户：例如 `ubuntu`（需要 sudo 权限）
- （可选）域名：例如 `afn.example.com`（如果你之后要上 HTTPS）

## 1) SSH 登录服务器

在你的本地电脑上执行：

```bash
ssh <user>@<server-ip>
```

登录后建议先确认系统版本：

```bash
lsb_release -a || cat /etc/os-release
```

## 2) 安装 Docker + Compose（Ubuntu）

在服务器执行（推荐使用 Docker 官方 apt 仓库）：

```bash
sudo apt update
sudo apt -y upgrade
sudo apt -y install ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker

docker --version
docker compose version
```

（可选）把当前用户加入 docker 组，避免每次都要 sudo：

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 3) 把代码放到服务器

你有两种常见方式：

### 方式 A：服务器可访问 Git 仓库（推荐）

```bash
sudo mkdir -p /opt/AFN
sudo chown -R $USER:$USER /opt/AFN
cd /opt/AFN
git clone <你的仓库地址> AFN
cd AFN
```

### 方式 B：从 Windows 电脑上传（scp/WinSCP）

先在服务器创建目录：

```bash
sudo mkdir -p /opt/AFN
sudo chown -R $USER:$USER /opt/AFN
```

然后在 Windows（PowerShell）执行（把路径/IP/用户名替换成你的）：

```powershell
scp -r "E:\code\AFN" <user>@<server-ip>:/opt/AFN/AFN
```

上传完成后在服务器进入目录：

```bash
cd /opt/AFN/AFN
```

## 4) 配置（部署前决定：是否启用登录）

### 4.1 复制并编辑 deploy/.env

```bash
cp deploy/.env.example deploy/.env
nano deploy/.env
```

你至少要改：
- `SECRET_KEY`（生产环境必须改成随机强密钥）

可选登录（部署前决定，修改后需重启容器）：
- `AFN_AUTH_ENABLED=true|false`
- `AFN_AUTH_ALLOW_REGISTRATION=true|false`

### 4.2 注意：storage/config.json 可能覆盖环境变量

后端启动时会读取 `storage/config.json`，其中的字段可能覆盖 `.env` 环境变量。

检查一下是否已存在：

```bash
ls -la storage || true
cat storage/config.json || true
```

如果你想让“部署配置只由 `.env` 决定”，请确保 `storage/config.json` 里**没有** `auth_enabled` / `auth_allow_registration` 这两个字段（或直接删除该文件后重启）。

## 5) 启动/停止

启动（会自动 build 并后台运行）：

```bash
deploy/scripts/up.sh
```

停止：

```bash
deploy/scripts/down.sh
```

查看日志：

```bash
deploy/scripts/logs.sh
```

## 6) 验证（在服务器本机）

先确认容器状态：

```bash
cd deploy
docker compose --env-file .env -f docker-compose.yml ps
```

健康检查：

```bash
http_port="$(grep -E '^AFN_HTTP_PORT=' deploy/.env | tail -n 1 | cut -d= -f2- | tr -d '\r' | tr -d '"' | tr -d "'" || true)"
if [[ -z "${http_port}" ]]; then
  http_port="80"
fi
curl -fsS "http://127.0.0.1:${http_port}/api/health"
curl -fsS "http://127.0.0.1:${http_port}/health"
```

浏览器访问（在你本地电脑打开）：
- `http://<server-ip>:<AFN_HTTP_PORT>`
- `http://<server-ip>:<AFN_HTTP_PORT>/docs`

## 7) 放行端口（UFW / 云安全组）

如果你用 UFW：

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw enable
sudo ufw status
```

如果你在 `deploy/.env` 改了端口，比如 `AFN_HTTP_PORT=8080`，对应放行 `8080/tcp`。

同时记得在云厂商“安全组/防火墙”放行同样端口。

## 7.1) 绑定域名 + HTTPS（Caddy 自动证书，推荐）

### 第一步：DNS 解析

把你的域名（例如 `afn.example.com`）加一条 A 记录指向服务器公网 IP。

在服务器验证（可能需要等待 DNS 生效）：

```bash
dig +short <你的域名> A
```

输出应包含你的服务器公网 IP。

### 第二步：放行 80/443

UFW 放行：

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status
```

云厂商安全组也要放行 80/443。

### 第三步：配置 .env

编辑 `deploy/.env`，设置：
- `AFN_DOMAIN=<你的域名>`
- `AFN_EMAIL=<你的邮箱>`（Let's Encrypt 证书通知用）

### 第四步：启动 HTTPS 版本

```bash
deploy/scripts/up_https_caddy.sh
```

查看日志（重点看 caddy 是否成功签发证书）：

```bash
deploy/scripts/logs_https_caddy.sh
```

访问：
- `https://<你的域名>/`
- `https://<你的域名>/api/health`
- `https://<你的域名>/docs`

如果你之前跑了 HTTP 版本（`deploy/scripts/up.sh`），建议先停掉：

```bash
deploy/scripts/down.sh
deploy/scripts/up_https_caddy.sh
```

## 8) 登录模式验证

- `AFN_AUTH_ENABLED=false`：打开 WebUI 应直接进入首页（不要求登录）。
- `AFN_AUTH_ENABLED=true`：打开 WebUI 应进入登录页；默认管理员：
  - 用户名：`desktop_user`
  - 密码：`desktop`

## 9) 更新版本

如果你用 git：

```bash
cd /opt/AFN/AFN
git pull
deploy/scripts/up.sh
```

如果你用 scp 上传：重新上传覆盖后执行 `deploy/scripts/up.sh` 即可。

## 10) 备份与恢复

备份数据库+配置（默认不包含模型缓存）：

```bash
deploy/scripts/backup.sh
```

包含模型缓存（体积大，不建议频繁）：

```bash
deploy/scripts/backup.sh --with-models
```

恢复（示例）：

```bash
deploy/scripts/down.sh
tar -xzf storage/backups/<你的备份文件>.tar.gz -C storage
deploy/scripts/up.sh
```

## 11) 常见问题排查

- 端口被占用：把 `deploy/.env` 的 `AFN_HTTP_PORT` 改成其它端口（如 8080），再 `deploy/scripts/up.sh`
- 没权限运行 docker：确认已加入 docker 组并重新登录；或临时用 `sudo docker ...`
- 访问返回 502：看 `deploy/scripts/logs.sh`，重点看 backend 是否启动、是否报错；以及 `storage/afn.db` 是否可写
- SSE/流式响应卡住：确认你是通过 Nginx 同源访问（`/api`），不要绕开直接访问后端端口
