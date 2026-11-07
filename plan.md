# All-Togetharr Build Plan

Source of truth: `all-togetharr.prd`. Stack: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, React, TypeScript, Vite.

## How we work

- Each task is written test-first: tests go in `backend/tests/test_taskNN_*.py` and start red.
- A task is done when its tests pass, `uv run ruff check .` is clean, and every earlier test still passes.
- Run everything from `backend/`: `uv run pytest`.
- OpenCode writes all implementation code, including fixes. If it cannot finish after 2 attempts, stop and ask Mike. Nobody else patches the code to get past that limit.
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

### [x] Task 4: Alembic baseline

- Files: `backend/alembic.ini`, `backend/src/all_togetharr/migrations/`, `backend/src/all_togetharr/models.py`, `backend/src/all_togetharr/platform/migrations.py`, `platform/db.py`, `main.py`
- Acceptance:
  - Migrations live inside the package so the Docker image ships them.
  - `platform/db.py` defines `Base` with a naming convention for `ix`, `uq`, `ck`, `fk` and `pk`.
  - `all_togetharr/models.py` imports every model module, so `Base.metadata` is complete. Later tasks add their models there.
  - `run_migrations(engine)` upgrades to head on that engine, and `alembic_config()` builds the config without `alembic.ini`.
  - The app lifespan runs migrations on startup against `app.state.engine`. A failed migration stops startup.
  - Running migrations twice changes nothing.
  - A test fails if models and migrations drift apart.
  - `alembic upgrade head` from `backend/` uses the environment settings.
- Test: `uv run pytest tests/test_task04_migrations.py`

### [x] Task 5: Structured logs

- Files: `backend/src/all_togetharr/platform/logging.py`, `main.py`
- Acceptance:
  - `configure_logging(settings)` sends logs to stdout as one JSON object per line with `time` (ISO 8601, UTC), `level`, `logger`, `message`, any `extra` fields, and `exception` when there is a traceback.
  - `LOG_LEVEL` filters output, and calling `configure_logging` twice does not duplicate lines.
  - The app lifespan configures logging before running migrations.
  - Uvicorn logs go through the same JSON output, and its access log is off.
  - `httpx` and `httpcore` log at WARNING or above, because their INFO lines contain full URLs, which can include API keys.
  - Each request logs `method`, `path`, `status` and `duration_ms` on logger `all_togetharr.request`. Query strings are never logged.
  - A route that raises logs status 500.
  - `/api/health` logs at DEBUG, because Docker polls it. Every other request logs at INFO.
- Test: `uv run pytest tests/test_task05_logging.py`

### [x] Task 6: Persistent job table

- Files: `backend/src/all_togetharr/platform/jobs/__init__.py`, `platform/jobs/models.py`, `platform/jobs/queue.py`, `platform/db.py`, `models.py`, a new migration
- Acceptance:
  - `platform/db.py` adds a `UtcDateTime` column type: it rejects naive values, stores UTC and always returns timezone-aware UTC. All later models use it.
  - `Job` (table `jobs`) stores name, payload, status, attempts, max attempts, run-at time, last error, and created, started and finished times.
  - Status is one of `pending`, `running`, `succeeded`, `failed`, enforced by a database check.
  - `enqueue` adds a job in the caller's transaction and validates its input.
  - `claim_next` atomically takes the earliest due job, commits, and returns it, or returns `None`.
  - One job cannot be claimed twice, even by concurrent workers.
- Test: `uv run pytest tests/test_task06_job_table.py`

### [x] Task 7: In-process job runner

- Files: `backend/src/all_togetharr/platform/jobs/runner.py`, `main.py`
- Acceptance:
  - `JobRunner` runs jobs one at a time on a single background thread. It starts and stops with the app lifespan, and stopping waits for the running job.
  - Handlers are registered by name and receive `(session, payload)`. Their database work commits with the job's success, and rolls back if they raise.
  - Failed jobs retry with exponential backoff (30 s, doubling, capped at 1 hour) until max attempts, then stay failed with the error stored.
  - A job with no handler fails at once, with no retry.
  - Jobs left `running` by a crash are requeued on startup, or failed if they have no attempts left. A crash counts as an attempt, so a job that kills the app cannot loop forever.
  - Recurring jobs are registered with `every(name, interval)`. The next run is worked out from the job table, so schedules survive restarts and a job is never queued twice.
  - An unexpected error in the loop is logged and does not stop the runner.
- Test: `uv run pytest tests/test_task07_job_runner.py`

### [x] Task 8: Users and password hashing

- Files: `backend/src/all_togetharr/platform/auth/__init__.py`, `platform/auth/models.py`, `platform/auth/passwords.py`, `platform/auth/users.py`, `models.py`, a new migration
- Acceptance:
  - `User` (table `users`) has name, role (Admin, Manager, Requester, Viewer), auth source (local, Jellyfin, OIDC), password hash and created time. Quotas and notification preferences wait for the features that use them.
  - Names are unique regardless of case, using a `name_key` column.
  - Passwords are hashed with Argon2id and never stored in plain text. Passwords must be 8 to 1024 characters.
  - `verify_password` returns `False` on a wrong password or corrupt hash, and `needs_rehash` flags hashes with outdated settings.
  - `create_user` validates input and adds the user in the caller's transaction.
  - Only local users have a password hash, and the database enforces that local users must have one.
- Test: `uv run pytest tests/test_task08_users.py`

### [x] Task 9: Login, sessions, role checks

- Files: `backend/src/all_togetharr/platform/auth/models.py`, `platform/auth/sessions.py`, `platform/auth/users.py`, `platform/auth/deps.py`, `platform/auth/routes.py`, `platform/settings.py`, `main.py`, a new migration
- Acceptance:
  - First-run setup creates the first Admin once and logs them in, then returns 409.
  - `POST /api/v1/auth/login` sets an HttpOnly, SameSite=Lax session cookie that lasts 30 days. `COOKIE_SECURE` adds the `Secure` flag.
  - Sessions are stored in the `sessions` table as a hash of the token. Logout ends the session and clears the cookie.
  - Wrong passwords and unknown users get the same response, and both cost one hash check.
  - Login upgrades outdated password hashes.
  - `get_current_user` returns 401 with no valid session. `require_role(role)` allows that role and above, and returns 403 otherwise.
  - Role order, lowest first: Viewer, Requester, Manager, Admin.
  - `/api/health` and `/api/docs` stay public.
- Test: `uv run pytest tests/test_task09_auth.py`

### [x] Task 10: Encrypted settings store

- Files: `backend/src/all_togetharr/platform/secrets.py`, `platform/settings_store.py`, `platform/settings_routes.py`, `models.py`, `main.py`, a new migration
- Acceptance:
  - On startup a Fernet key is created at `CONFIG_DIR/secret.key` with owner-only permissions, then reused. Loose permissions are tightened.
  - A corrupt key stops startup and is never replaced, because a new key would orphan every saved secret.
  - Settings are a defined list with a type and default. The first two are `tmdb.api_key` (secret) and `tmdb.language` (default `en-US`). Unknown keys are rejected.
  - Secret values are encrypted in the database. The API shows only `is_set`, never any part of the value.
  - Only Admins can read or change settings under `/api/v1/settings`.
  - Backups (later) must include `secret.key`, or saved secrets cannot be restored.
- Test: `uv run pytest tests/test_task10_settings_store.py`

### [x] Task 10a: Safe validation errors

- Files: `backend/src/all_togetharr/main.py`, `platform/auth/routes.py`
- Acceptance:
  - Validation errors return only `type`, `loc` and `msg`. They never echo the rejected input, so passwords are never sent back.
  - The handler cannot crash on error details that are not JSON-safe.
  - Invalid Unicode in a request body still returns 422.
  - The `_accept_utf8` validators are removed if Pydantic already rejects that input.
- Test: `uv run pytest tests/test_task10a_validation_errors.py`

### [x] Task 11: Catalog models

- Files: `backend/src/all_togetharr/catalog/models.py`, `backend/src/all_togetharr/migrations/versions/0006_catalog.py`, `backend/src/all_togetharr/models.py`
- Acceptance:
  - `Title`, `Season`, `Episode`, `MediaFile` match the PRD core data model.
  - `Title` also has `name`, `year` and `added_at`, which Tasks 13 and 14 need for display, search and sort.
  - `Title.status` allows only the PRD pipeline values: Requested, Approved, Searching, Downloading, Importing, Available.
  - `tmdb_id` plus `type` is unique, and `tmdb_id` is required.
  - `quality_profile_id` and `root_folder_id` are plain nullable integers until their tables exist.
  - `Episode` points at its season through a composite foreign key on `title_id` and `season_number`.
  - `MediaFile` has `title_id` so movies can own files, and `link_key` (device:inode) so hardlinks can be recognised.
  - Deleting a title removes its rows. Deleting a file clears `Episode.file_id` and keeps the episode.
- Test: `uv run pytest tests/test_task11_catalog_models.py`

### [x] Task 12: TMDB client

- Files: `backend/src/all_togetharr/metadata/tmdb.py`, `backend/pyproject.toml`, `backend/uv.lock`
- Acceptance:
  - Search movies and series, and fetch details, including seasons and episodes.
  - The API key comes from the settings store.
  - Rate-limit and network errors raise one typed error, `TmdbError`, with a `kind`.
  - The API key never appears in an error or a log line.
  - Tests use fixtures and never call the real TMDB. The fixtures are hand-written from the TMDB response shape, because we have no API key to record real responses.
- Test: `uv run pytest tests/test_task12_tmdb.py`

### [x] Task 12a: Tidy the TMDB client

- Files: `backend/src/all_togetharr/metadata/tmdb.py`
- Acceptance:
  - `from None` appears only inside `except` blocks.
  - A blank `tvdb_id` gives None, the same as null.
  - `details` shares its common parsing with `_search_result` and is split into small functions.
  - No behaviour changes otherwise.
- Test: `uv run pytest tests/test_task12_tmdb.py`

### [x] Task 13: Add a title from TMDB

- Files: `backend/src/all_togetharr/catalog/service.py`, `catalog/routes.py`, `catalog/models.py`, `backend/src/all_togetharr/migrations/versions/0007_title_metadata.py`, `main.py`
- Acceptance:
  - `GET /api/v1/search/metadata` returns TMDB results marked with whether each is in the library. Requester and above.
  - `POST /api/v1/titles` stores the movie or series, with seasons and episodes. Manager and above.
  - Adding the same title twice returns 409, including when two adds race.
  - `Title.overview`, `Title.poster_path` and `Episode.name` are stored, so Task 16 can show metadata without refetching.
  - A TMDB failure returns a clear HTTP error with a `code`, and stores nothing.
- Test: `uv run pytest tests/test_task13_add_title.py`

### [x] Task 14: Catalog browse API

- Files: `backend/src/all_togetharr/catalog/routes.py`, `backend/src/all_togetharr/catalog/service.py`
- Acceptance:
  - `GET /api/v1/titles` supports paging (`page`, `page_size`), `type` and `status` filters, `sort` and `order`, and text search (`q`). Any logged-in user.
  - `GET /api/v1/titles/{id}` returns the title with seasons and episodes.
  - Listing 10,000 seeded titles returns in under 1 s.
- Test: `uv run pytest tests/test_task14_browse.py`

### [x] Task 15: Frontend scaffold

- Files: `frontend/` (Vite, React, TypeScript, TanStack Query, Tailwind, Vitest)
- Acceptance:
  - `frontend/` has its own `package.json` and lockfile, and pins pnpm 10.34.6 in `packageManager` and `frontend/mise.toml`.
  - The dev server proxies `/api` to the backend.
  - A smoke test renders the app shell with dark and light themes.
  - The shell shows the API version from `/api/health`, or that the API is offline.
- Test: `cd frontend && pnpm test && pnpm build`. If `pnpm` isn't set up, use `mise exec pnpm@10.34.6 -- pnpm test`.

### [x] Task 16a: First-run setup and sign-in screens

- Files: `frontend/src/` (App, auth screens, a small API helper), tests `frontend/src/auth.test.tsx`, test helper `frontend/src/test/fakeApi.ts`
- Acceptance:
  - With no users, the app shows "Create the admin account". It checks the 8-character password minimum before calling the API, shows the server's error message, and moves to sign in after a 409.
  - Otherwise it checks `/api/v1/auth/me`: a valid session goes straight in, and a 401 shows "Sign in".
  - A wrong password shows "Invalid name or password". "Sign out" ends the session.
  - When the server can't be reached, the app says so instead of showing a form.
  - The app shell (name, theme toggle, API status) stays on every screen.
- Test: `cd frontend && pnpm test && pnpm build`

### [ ] Task 16b: Library page

- Files: `frontend/src/` (adds `react-router`)
- Acceptance:
  - Lists titles from `GET /api/v1/titles`, with type, status and search filters and next/previous paging.
  - Filters and the page number are in the URL.
  - Works at phone width (one column, no horizontal scroll).
- Test: `cd frontend && pnpm test && pnpm build`

### [ ] Task 16c: Title page

- Files: `frontend/src/`
- Acceptance:
  - `/titles/:id` shows the title's metadata, and its seasons with episodes.
  - Shows a not-found message for an unknown title.
- Test: `cd frontend && pnpm test && pnpm build`

### [ ] Task 17: Docker image

- Files: `docker/Dockerfile`, `docker/entrypoint.sh`, `docker/compose.example.yml`
- Acceptance:
  - One image serves the API and the built SPA on port 8080.
  - It runs as non-root using `PUID`, `PGID` and `UMASK`, with volumes `/config` and `/data`.
  - The container health check calls `/api/health`.
  - Uvicorn starts with `log_config=None`, so its first lines before app startup are JSON too. Add an integration check: every line of container output parses as JSON.
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
