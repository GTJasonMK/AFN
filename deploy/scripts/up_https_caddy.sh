#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}/deploy"

if [[ ! -f .env ]]; then
  echo "[!] 未找到 deploy/.env，请先复制：cp deploy/.env.example deploy/.env" >&2
  exit 1
fi

domain="$(grep -E '^AFN_DOMAIN=' .env | tail -n 1 | cut -d= -f2- | tr -d '\r' | tr -d '"' | tr -d "'" || true)"
email="$(grep -E '^AFN_EMAIL=' .env | tail -n 1 | cut -d= -f2- | tr -d '\r' | tr -d '"' | tr -d "'" || true)"

if [[ -z "${domain}" ]]; then
  echo "[!] 请在 deploy/.env 设置 AFN_DOMAIN（你的域名）" >&2
  exit 1
fi
if [[ -z "${email}" ]]; then
  echo "[!] 请在 deploy/.env 设置 AFN_EMAIL（用于 Let's Encrypt 证书通知）" >&2
  exit 1
fi

docker compose --env-file .env -f docker-compose.yml -f docker-compose.https.caddy.yml up -d --build

echo ""
echo "[+] WebUI:  https://${domain}"
echo "[+] API:   https://${domain}/api/health"
echo "[+] Docs:  https://${domain}/docs"
echo "[i] 首次启动会自动申请证书，如失败请查看：deploy/scripts/logs_https_caddy.sh"

