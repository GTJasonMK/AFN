#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}/deploy"

if [[ ! -f .env ]]; then
  echo "[!] 未找到 deploy/.env，请先复制：cp deploy/.env.example deploy/.env" >&2
  exit 1
fi

docker compose --env-file .env -f docker-compose.yml up -d --build

http_port="$(grep -E '^AFN_HTTP_PORT=' .env | tail -n 1 | cut -d= -f2- | tr -d '\r' | tr -d '"' | tr -d "'" || true)"
if [[ -z "${http_port}" ]]; then
  http_port="80"
fi

echo ""
echo "[+] WebUI:  http://<server-ip>:${http_port}"
echo "[+] API:   http://<server-ip>:${http_port}/api/health"
echo "[+] Docs:  http://<server-ip>:${http_port}/docs"
