# Repository Guidelines

## Project Structure & Module Organization

- `backend/`: FastAPI backend (`backend/app/` contains `api/`, `services/`, `repositories/`, `models/`).
- `frontend/`: PyQt6 desktop UI (entry: `frontend/main.py`).
- `frontend-web/`: React + Vite web UI (source: `frontend-web/src/`).
- `deploy/`: deployment scripts and notes; `tools/`: one-off utilities; `test/`: runnable test scripts.
- Runtime data lives in `storage/` (DB, vectors, logs, models) and is intentionally not committed.

## Build, Test, and Development Commands

- `python run_app.py`: one-click desktop start (creates venvs, installs deps, starts backend + PyQt UI).
- `python setup_env.py --force`: re-create environments and re-install dependencies.
- Backend only: `cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8123`
- Web dev: `python start_web.py` (prefers `8123`/`5173`, auto-picks free ports; prints actual URLs) or `cd frontend-web && npm run dev`
- Web build/lint: `cd frontend-web && npm run build` / `npm run lint`

## Coding Style & Naming Conventions

- Python: 4-space indentation, prefer type hints, keep changes within the existing layers (router → service → repository).
- React/TSX: follow existing formatting in `frontend-web/src/` (2-space indentation), components in `PascalCase.tsx`.
- Naming: Python modules in `snake_case.py`; avoid mixing UI logic into `backend/app/services/`.

## Testing Guidelines

- There is no single unified test runner today; use script-based checks under `test/`.
- Example: `python test/chunkSplitTest/test_semantic_chunker.py`
- For web changes, run `npm run lint` and ensure `npm run build` succeeds.

## Configuration Tips

- Backend runtime config is loaded from `backend/.env` (plus process env). To enable the WebUI user system: set `AFN_AUTH_ENABLED=true` (optional: `AFN_AUTH_ALLOW_REGISTRATION=true`), restart the backend, then check `GET /api/auth/status` (use `?debug=1` to print an `[AuthDebug]` line). Built-in admin username: `desktop_user` (recommended: set `AFN_INITIAL_ADMIN_PASSWORD`; Admin panel: `/admin/overview`).

## Commit & Pull Request Guidelines

- Commit history primarily uses short, action-oriented Chinese subjects (e.g., `修复…`, `添加…`, `优化…`) without Conventional Commits—keep it consistent and scoped.
- PRs should include: what/why, how to verify (commands + expected result), and screenshots/GIFs for UI changes.
- Never commit secrets or local data: `backend/.env`, `.env*`, `storage/`, `*.db`, `node_modules/`.
