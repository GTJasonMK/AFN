#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STORAGE_DIR="${ROOT_DIR}/storage"
BACKUP_DIR="${ROOT_DIR}/storage/backups"

mkdir -p "${BACKUP_DIR}"

ts="$(date +%Y%m%d_%H%M%S)"
out="${BACKUP_DIR}/afn_backup_${ts}.tar.gz"

include_models=false
if [[ "${1:-}" == "--with-models" ]]; then
  include_models=true
fi

items=()
[[ -f "${STORAGE_DIR}/afn.db" ]] && items+=("afn.db")
[[ -f "${STORAGE_DIR}/config.json" ]] && items+=("config.json")
[[ -d "${STORAGE_DIR}/logs" ]] && items+=("logs")

if $include_models && [[ -d "${STORAGE_DIR}/models" ]]; then
  items+=("models")
fi

if [[ ${#items[@]} -eq 0 ]]; then
  echo "[!] storage 下未找到可备份文件（afn.db/config.json 等）" >&2
  exit 1
fi

(cd "${STORAGE_DIR}" && tar -czf "${out}" "${items[@]}")

echo "[+] 备份完成：${out}"
if ! $include_models; then
  echo "[i] 如需包含模型缓存，请使用：deploy/scripts/backup.sh --with-models"
fi

