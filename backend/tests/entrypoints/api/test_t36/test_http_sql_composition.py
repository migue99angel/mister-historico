"""Exercise production HTTP composition with the real SQL catalog and run repository."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

from mister.bootstrap import bootstrap
from mister.catalog.infrastructure.sqlalchemy.catalog import SqlCatalogLoader
from mister.entrypoints.api.app import create_app
from mister.settings import Settings

pytestmark = pytest.mark.integration
_BACKEND = Path(__file__).resolve().parents[4]
_CONTENT = _BACKEND / "tests" / "fixtures" / "content"
_ALEMBIC = _BACKEND / "alembic.ini"


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer("postgres:16.15", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(_ALEMBIC))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        yield url


@pytest.mark.anyio
async def test_real_http_composition_starts_and_recovers_a_private_run(database_url: str):
    container = bootstrap(Settings(database_url=database_url))
    assert container.engine is not None
    SqlCatalogLoader(container.engine).load(_CONTENT)
    app = create_app(container)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        seasons = await client.get("/api/seasons")
        assert seasons.status_code == 200
        assert seasons.json()["items"][0]["id"] == "test-fc-2000-01"

        started = await client.post("/api/runs", json={"seasonId": "test-fc-2000-01"})
        assert started.status_code == 201
        payload = started.json()
        token = payload["runToken"]
        run_id = payload["run"]["runId"]
        assert started.headers["location"] == f"/api/runs/{run_id}"

        read = await client.get(f"/api/runs/{run_id}", headers={"Authorization": f"Bearer {token}"})
        assert read.status_code == 200
        assert read.json() == payload["run"]
        serialized = str(read.json()).lower()
        for private_name in ("seed", "run_token_hash", "historical_option", "effects"):
            assert private_name not in serialized

        assert container.api() is not container.api()
