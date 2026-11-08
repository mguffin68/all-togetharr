# Stage 1: Build frontend
FROM node:24-bookworm-slim AS frontend

RUN npm install -g pnpm@10.34.6

WORKDIR /build

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ .
RUN pnpm build

# Stage 2: Build backend
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS backend

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src/ ./src/
RUN uv sync --frozen --no-dev --no-editable

# Stage 3: Runtime
FROM python:3.12-slim-bookworm

ENV PATH=/app/.venv/bin:$PATH
ENV STATIC_DIR=/app/static
ENV CONFIG_DIR=/config
ENV DATA_DIR=/data
ENV PUID=1000
ENV PGID=1000
ENV UMASK=022
ENV PYTHONUNBUFFERED=1

COPY --from=backend /app/.venv /app/.venv
COPY --from=frontend /build/dist /app/static

VOLUME ["/config", "/data"]

EXPOSE 8080

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=2).status == 200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
