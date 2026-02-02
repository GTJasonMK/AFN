#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}/deploy"

if [[ ! -f .env ]]; then
  echo "[!] 未找到 deploy/.env，请先复制：cp deploy/.env.example deploy/.env" >&2
  exit 1
fi

docker compose --env-file .env -f docker-compose.yml up -d --build

echo ""
echo "[+] WebUI:  http://<server-ip>:${AFN_HTTP_PORT:-80}"
echo "[+] API:   http://<server-ip>:${AFN_HTTP_PORT:-80}/api/health"
echo "[+] Docs:  http://<server-ip>:${AFN_HTTP_PORT:-80}/docs"

