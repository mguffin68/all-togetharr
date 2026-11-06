# All-Togetharr Build Plan

Source of truth: `all-togetharr.prd`. Stack: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, React, TypeScript, Vite.

## How we work

- Each task is written test-first: tests go in `backend/tests/test_taskNN_*.py` and start red.
- A task is done when its tests pass, `uv run ruff check .` is clean, and every earlier test still passes.
- Run everything from `backend/`: `uv run pytest`.
- Stage explicit paths only, such as `git add backend plan.md .gitignore`. Never use `git add -A` or `git commit -a`, because the old-app deletions belong to task L1.
- pytest prints a `StarletteDeprecationWarning` about `httpx` on every run. This is expected, so don't change dependencies to silence it.
- New code lives in `backend/` and `frontend/`. The old Next.js app stays out of this work: its main files are already gone from disk, and task L1 covers the leftovers.

## Phase 0: Foundation

Status key: `[ ]` not started, `[~]` tests written, `[x]` done.

### [x] Task 1: App factory, health check, API docs

- Files: `backend/src/all_togetharr/main.py`
- Acceptance:
  - `create_app()` returns a FastAPI app.
  - `GET /api/health` returns 200 JSON with `status: "ok"` and `version` equal to `all_togetharr.__version__`.
  - Docs are at `/api/docs`, the spec is at `/api/openapi.json`, and `/docs` and `/redoc` return 404.
- Test: `uv run pytest tests/test_task01_app_health.py`

### [x] Task 2: Settings

- Files: `backend/src/all_togetharr/platform/settings.py`, `main.py`
- Acceptance:
  - Pydantic settings read `CONFIG_DIR` (default `/config`), `DATA_DIR` (default `/data`), `DATABASE_URL`, `LOG_LEVEL`, `TZ`.
  - Fields are `config_dir`, `data_dir`, `database_url`, `log_level` and `tz`. `log_level` defaults to `INFO` and `tz` to `UTC`.
  - `DATABASE_URL` defaults to SQLite at `<CONFIG_DIR>/all-togetharr.db`.
  - Loading settings creates no files or directories.
  - An invalid `LOG_LEVEL` raises a validation error.
  - `create_app()` takes an optional settings object and stores it on `app.state.settings`. `conftest.py` builds one with `CONFIG_DIR` and `DATA_DIR` under `tmp_path`, so no test writes to `/config`.
- Test: `uv run pytest tests/test_task02_settings.py`

### [x] Task 3: Database engine and sessions

- Files: `backend/src/all_togetharr/platform/db.py`, `main.py`
- Acceptance:
  - `create_db_engine(settings)` returns an engine and creates the SQLite file's parent folder if it is missing.
  - SQLite connections use WAL mode and enforce foreign keys. Those pragmas run only on SQLite, so PostgreSQL still works.
  - `create_app` stores `app.state.engine` and `app.state.session_factory`, and disposes the engine on shutdown.
  - The `get_session` dependency yields a session from `app.state.session_factory` and closes it after the request, including when the route raises.
  - `/api/health` runs `SELECT 1` on `app.state.engine`. It returns 503 with `status: "error"` when the database is unreachable, and the body leaks no connection details.
- Test: `uv run pytest tests/test_task03_db.py`

### [ ] Task 4: Alembic baseline

- Files: `backend/alembic.ini`, `backend/migrations/`, `main.py`
- Acceptance:
  - Migrations run automatically on startup against the configured database.
  - Running them twice changes nothing.
  - A test fails if models and migrations drift apart.
- Test: `uv run pytest tests/test_task04_migrations.py`

### [ ] Task 5: Structured logs

- Files: `backend/src/all_togetharr/platform/logging.py`, `main.py`
- Acceptance:
  - Logs go to stdout as one JSON object per line with `time`, `level`, `logger`, `message`.
  - `LOG_LEVEL` filters output.
  - Each request logs method, path, status and duration.
- Test: `uv run pytest tests/test_task05_logging.py`

### [ ] Task 6: Persistent job table

- Files: `backend/src/all_togetharr/platform/jobs/models.py`, a new migration
- Acceptance:
  - `Job` stores name, payload, status, attempts, max attempts, run-at time, last error.
  - Enqueue and claim-next functions exist.
  - One job cannot be claimed twice.
- Test: `uv run pytest tests/test_task06_job_table.py`

### [ ] Task 7: In-process job runner

- Files: `backend/src/all_togetharr/platform/jobs/runner.py`, `main.py`
- Acceptance:
  - The runner starts and stops with the app lifespan.
  - Failed jobs retry with backoff until max attempts, then stay failed with the error stored.
  - Jobs left `running` by a crash are requeued on startup.
  - Recurring jobs can be registered with an interval.
- Test: `uv run pytest tests/test_task07_job_runner.py`

### [ ] Task 8: Users and password hashing

- Files: `backend/src/all_togetharr/platform/auth/models.py`, `passwords.py`, a new migration
- Acceptance:
  - `User` has name, role (Admin, Manager, Requester, Viewer) and auth source.
  - Passwords are hashed with Argon2 and never stored in plain text.
- Test: `uv run pytest tests/test_task08_users.py`

### [ ] Task 9: Login, sessions, role checks

- Files: `backend/src/all_togetharr/platform/auth/routes.py`, `deps.py`
- Acceptance:
  - First-run setup creates the first Admin once, then returns 409.
  - `POST /api/v1/auth/login` sets an HttpOnly session cookie; logout clears it.
  - A `require_role` dependency returns 401 with no session and 403 with too low a role.
  - `/api/health` stays public.
- Test: `uv run pytest tests/test_task09_auth.py`

### [ ] Task 10: Encrypted settings store

- Files: `backend/src/all_togetharr/platform/secrets.py`, `platform/settings_store.py`, `platform/settings_routes.py`, a new migration
- Acceptance:
  - A key is generated in `CONFIG_DIR` on first run and reused afterwards.
  - Secret values are encrypted in the database, and the API never returns them in full.
  - Only Admins can read or change settings under `/api/v1/settings`.
- Test: `uv run pytest tests/test_task10_settings_store.py`

### [ ] Task 11: Catalog models

- Files: `backend/src/all_togetharr/catalog/models.py`, a new migration
- Acceptance:
  - `Title`, `Season`, `Episode`, `MediaFile` match the PRD core data model.
  - `Title.status` allows only the PRD pipeline values: Requested, Approved, Searching, Downloading, Importing, Available.
  - `tmdb_id` plus `type` is unique.
- Test: `uv run pytest tests/test_task11_catalog_models.py`

### [ ] Task 12: TMDB client

- Files: `backend/src/all_togetharr/metadata/tmdb.py`
- Acceptance:
  - Search movies and series, and fetch details, including seasons and episodes.
  - The API key comes from the settings store.
  - Rate-limit and network errors raise one typed error.
  - Tests use recorded fixtures and never call the real TMDB.
- Test: `uv run pytest tests/test_task12_tmdb.py`

### [ ] Task 13: Add a title from TMDB

- Files: `backend/src/all_togetharr/catalog/service.py`, `catalog/routes.py`
- Acceptance:
  - `GET /api/v1/search/metadata` returns TMDB results marked with whether each is in the library.
  - `POST /api/v1/titles` stores the movie or series, with seasons and episodes.
  - Adding the same title twice returns 409.
- Test: `uv run pytest tests/test_task13_add_title.py`

### [ ] Task 14: Catalog browse API

- Files: `backend/src/all_togetharr/catalog/routes.py`
- Acceptance:
  - `GET /api/v1/titles` supports paging, type and status filters, sort and text search.
  - `GET /api/v1/titles/{id}` returns the title with seasons and episodes.
  - Listing 10,000 seeded titles returns in under 1 s.
- Test: `uv run pytest tests/test_task14_browse.py`

### [ ] Task 15: Frontend scaffold

- Files: `frontend/` (Vite, React, TypeScript, TanStack Query, Tailwind, Vitest)
- Acceptance:
  - `frontend/` has its own `package.json` and lockfile.
  - The dev server proxies `/api` to the backend.
  - A smoke test renders the app shell with dark and light themes.
- Test: `cd frontend && pnpm test && pnpm build`

### [ ] Task 16: Login and library pages

- Files: `frontend/src/`
- Acceptance:
  - First-run setup and login screens work against the API.
  - The library page lists titles with filters and paging, and works at phone width.
  - The title page shows metadata and seasons.
- Test: `cd frontend && pnpm test`

### [ ] Task 17: Docker image

- Files: `docker/Dockerfile`, `docker/entrypoint.sh`, `docker/compose.example.yml`
- Acceptance:
  - One image serves the API and the built SPA on port 8080.
  - It runs as non-root using `PUID`, `PGID` and `UMASK`, with volumes `/config` and `/data`.
  - The container health check calls `/api/health`.
  - Builds for amd64 and arm64.
- Test: `docker build -f docker/Dockerfile -t all-togetharr:dev . && docker run --rm -p 8080:8080 all-togetharr:dev`, then `curl localhost:8080/api/health`

### [ ] Task L1: Finish removing the old Next.js app (needs Mike's OK)

- Files:
  - Commit the deletions already on disk (`src/`, `prisma/`, `package.json`, `Dockerfile`, and so on).
  - Remove the leftovers: `.dockerignore`, `.env.example`, `.eslintrc.json`, `.github/copilot-instructions.md`, `.playwright-mcp/`, `.next/`, `.DS_Store`.
  - Replace the old entries in `.gitignore`.
- Acceptance: the repo holds only the PRD, `plan.md`, `backend/`, `frontend/`, `docker/` and repo config.
- Test: `git ls-files` shows no old files, and backend and frontend tests still pass.

## Later phases

Break each phase into tasks when the one before it is done.

- **Phase 1, Movies end-to-end:** indexers, decision engine, external qBittorrent client, import and rename, Jellyfin refresh. Replaces Radarr and Prowlarr.
- **Phase 2, Series:** episodes, calendar, season packs, daily series. Replaces Sonarr.
- **Phase 3, Requests:** discover, requests, approvals, Jellyfin sign-in, notifications. Replaces Seerr.
- **Phase 4, Embedded torrent engine:** full queue UI, seeding rules, VPN guard.
- **Phase 5, Polish:** anime, 4K profiles, import lists, sessions view, embedded player, API compatibility shims.

## Open PRD questions

None of these block Phase 0.

- Jellyfin: deep link or embedded player? Needed by Phase 1.
- VPN: route only torrent traffic, or the whole container? Needed by Phase 4.
- Usenet: out of scope, or keep a SABnzbd adapter on the roadmap? Needed by Phase 1, for the downloader abstraction.
- Anime and 4K: in v1 or later? Needed by Phase 2.
- Migration: which settings must carry over on day one? Needed before the migration wizard is planned.
