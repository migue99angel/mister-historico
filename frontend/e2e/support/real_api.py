"""Real API for the frontend E2E: production composition, PostgreSQL and the engine.

Started by `playwright.config.ts` with `uv run --project ../backend`. It mirrors the backend
E2E (`backend/tests/e2e/test_test_fc_season_http.py`): a throwaway PostgreSQL container with
the migrations and the synthetic Test FC content, and only the server-side seed pinned, so
the season the browser plays is the golden one. Never a production entrypoint.
"""

import os
import signal
import sys
from pathlib import Path
from types import FrameType, SimpleNamespace

import sqlalchemy as sa
import uvicorn
from alembic import command
from alembic.config import Config
from testcontainers.community.postgres import PostgresContainer

_BACKEND = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(_BACKEND))

from tests.golden.season_play import GOLDEN_SEED  # noqa: E402

from mister import bootstrap as composition  # noqa: E402
from mister.bootstrap import bootstrap  # noqa: E402
from mister.catalog.infrastructure.sqlalchemy.catalog import SqlCatalogLoader  # noqa: E402
from mister.entrypoints.api.app import create_app  # noqa: E402
from mister.settings import Settings  # noqa: E402

_CONTENT = _BACKEND / "tests" / "fixtures" / "content"
_ALEMBIC = _BACKEND / "alembic.ini"


def _prepare(database_url: str) -> None:
    config = Config(str(_ALEMBIC))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    engine = sa.create_engine(database_url)
    try:
        SqlCatalogLoader(engine).load(_CONTENT)
    finally:
        engine.dispose()


def _exit_on_sigterm(signum: int, frame: FrameType | None) -> None:
    raise SystemExit(0)


def main() -> None:
    port = int(os.environ.get("E2E_API_PORT", "8010"))
    # uvicorn re-raises the SIGTERM it captured once it has shut down; without a handler of
    # our own that kills the process before the `with` below removes the container.
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    with PostgresContainer("postgres:16.15", driver="psycopg") as postgres:
        database_url = postgres.get_connection_url()
        _prepare(database_url)
        composition.secrets = SimpleNamespace(randbits=lambda _: GOLDEN_SEED)  # type: ignore[attr-defined,assignment]
        app = create_app(bootstrap(Settings(database_url=database_url)))
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
