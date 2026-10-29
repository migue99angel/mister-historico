# syntax=docker/dockerfile:1
#
# API image (FastAPI). Build context: `backend/`.
#
#   docker build -f infra/docker/api.Dockerfile --target dev  backend
#   docker build -f infra/docker/api.Dockerfile --target prod backend
#
# Stages:
#   dev  -> runtime + dev dependencies, project installed in editable mode
#           (`backend/src` is mounted on top for hot reload).
#   prod -> runtime only, no uv, non-root user.

ARG PYTHON_IMAGE=python:3.12.15-slim-bookworm

FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
COPY --from=uv /uv /uvx /bin/
WORKDIR /app

# ---------------------------------------------------------------------------
FROM base AS dev
# Dependency layer: only rebuilt when pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen
ENV PATH="/opt/venv/bin:${PATH}"
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn mister.entrypoints.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload --reload-dir src"]

# ---------------------------------------------------------------------------
FROM base AS builder
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS prod
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"
RUN groupadd --system --gid 10001 mister \
    && useradd --system --uid 10001 --gid mister --no-create-home --shell /usr/sbin/nologin mister
WORKDIR /app
# The venv holds the installed (non-editable) `mister` package: no `src/` needed.
COPY --from=builder /opt/venv /opt/venv
# Migrations run as a release step (`alembic upgrade head`), not on startup.
COPY alembic.ini ./
COPY migrations ./migrations
USER mister
EXPOSE 8000
CMD ["uvicorn", "mister.entrypoints.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
