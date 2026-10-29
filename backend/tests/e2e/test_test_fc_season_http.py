"""Backend E2E: play Test FC over HTTP with the production composition, PostgreSQL and the engine.

Only the seed is pinned, so the season can be compared with the synthetic golden.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

from mister import bootstrap as composition
from mister.bootstrap import bootstrap
from mister.catalog.infrastructure.sqlalchemy.catalog import SqlCatalogLoader
from mister.entrypoints.api.app import create_app
from mister.game.application.replay import ReplayRun
from mister.game.domain.run import RunStatus
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.game.infrastructure.sqlalchemy.uow import SqlUnitOfWork
from mister.settings import Settings
from mister.shared_kernel.ids import RunId
from mister.simulation.application.api import SimulationService
from tests.golden.season_play import (
    GOLDEN_SEED,
    advance,
    decide,
    load_golden,
    play_block,
    play_to_the_end,
    start_run,
    transcript,
)

_BACKEND = Path(__file__).resolve().parents[2]
_CONTENT = _BACKEND / "tests" / "fixtures" / "content"
_ALEMBIC = _BACKEND / "alembic.ini"


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer("postgres:16.15", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(_ALEMBIC))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        engine = sa.create_engine(url)
        try:
            SqlCatalogLoader(engine).load(_CONTENT)
        finally:
            engine.dispose()
        yield url


@pytest.fixture
def golden_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the server-side seed of new runs; everything else stays production wiring."""
    monkeypatch.setattr(composition, "secrets", SimpleNamespace(randbits=lambda _: GOLDEN_SEED))


@asynccontextmanager
async def _client(database_url: str) -> AsyncIterator[AsyncClient]:
    """A fresh production composition, as after a server restart or a page reload."""
    app = create_app(bootstrap(Settings(database_url=database_url)))
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


@pytest.mark.anyio
@pytest.mark.usefixtures("golden_seed")
async def test_full_season_over_http_and_sql_reproduces_the_synthetic_golden(
    database_url: str,
) -> None:
    async with _client(database_url) as client:
        run = await start_run(client)
        await play_to_the_end(client, run)

    assert run.view["status"] == "finished"
    assert transcript(run) == load_golden()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "operation"),
    [("GET", ""), ("POST", "/decisions"), ("POST", "/advance")],
)
async def test_every_run_operation_requires_its_run_token(
    database_url: str, method: str, operation: str
) -> None:
    async with _client(database_url) as client:
        run = await start_run(client)
        url = f"/api/runs/{run.run_id}{operation}"
        idempotency = {"Idempotency-Key": "token-check-0001"} if method == "POST" else {}

        missing = await client.request(method, url, headers=idempotency)
        wrong = await client.request(
            method, url, headers={**idempotency, "Authorization": "Bearer not-the-run-token"}
        )

    assert (missing.status_code, missing.json()["code"]) == (401, "run_token_required")
    assert (wrong.status_code, wrong.json()["code"]) == (403, "run_token_invalid")


@pytest.mark.anyio
@pytest.mark.usefixtures("golden_seed")
async def test_retrying_every_command_with_its_key_leaves_the_golden_season_unchanged(
    database_url: str,
) -> None:
    async with _client(database_url) as client:
        run = await start_run(client)
        while run.view["status"] == "in_progress":
            block = run.view["block"]["number"]
            for dilemma in run.view["pendingDilemmas"]:
                body = {
                    "expectedVersion": run.view["version"],
                    "dilemmaId": dilemma["id"],
                    "optionId": dilemma["options"][0]["id"],
                }
                key = f"retry-decide-{block}-{dilemma['id']}"
                await decide(client, run, dilemma, key)
                retry = await client.post(
                    f"/api/runs/{run.run_id}/decisions",
                    json=body,
                    headers={**run.headers, "Idempotency-Key": key},
                )
                assert retry.status_code == 200
                assert retry.json() == run.view
            body = {"expectedVersion": run.view["version"]}
            key = f"retry-advance-{block}"
            await advance(client, run, key)
            retry = await client.post(
                f"/api/runs/{run.run_id}/advance",
                json=body,
                headers={**run.headers, "Idempotency-Key": key},
            )
            assert retry.status_code == 200
            assert retry.json() == run.view

    assert transcript(run) == load_golden()


@pytest.mark.anyio
async def test_advancing_with_pending_dilemmas_conflicts_without_changing_the_run(
    database_url: str,
) -> None:
    async with _client(database_url) as client:
        run = await start_run(client)
        assert run.view["pendingDilemmas"]

        early = await client.post(
            f"/api/runs/{run.run_id}/advance",
            json={"expectedVersion": run.view["version"]},
            headers={**run.headers, "Idempotency-Key": "early-advance-0001"},
        )
        current = await client.get(f"/api/runs/{run.run_id}", headers=run.headers)

    assert (early.status_code, early.json()["code"]) == (409, "pending_dilemmas")
    assert current.json() == run.view


@pytest.mark.anyio
async def test_a_command_on_a_stale_version_conflicts_without_changing_the_run(
    database_url: str,
) -> None:
    async with _client(database_url) as client:
        run = await start_run(client)
        stale_version = run.view["version"]
        await play_block(client, run)
        dilemma = run.view["pendingDilemmas"][0]

        stale = await client.post(
            f"/api/runs/{run.run_id}/decisions",
            json={
                "expectedVersion": stale_version,
                "dilemmaId": dilemma["id"],
                "optionId": dilemma["options"][0]["id"],
            },
            headers={**run.headers, "Idempotency-Key": "stale-decision-0001"},
        )
        current = await client.get(f"/api/runs/{run.run_id}", headers=run.headers)

    assert (stale.status_code, stale.json()["code"]) == (409, "version_conflict")
    assert current.json() == run.view


@pytest.mark.anyio
@pytest.mark.usefixtures("golden_seed")
async def test_a_reloaded_client_recovers_the_run_and_finishes_the_golden_season(
    database_url: str,
) -> None:
    async with _client(database_url) as client:
        run = await start_run(client)
        await play_block(client, run)
        await play_block(client, run)

    async with _client(database_url) as reloaded:
        recovered = await reloaded.get(f"/api/runs/{run.run_id}", headers=run.headers)
        assert recovered.status_code == 200
        assert recovered.json() == run.view
        await play_to_the_end(reloaded, run)

    assert transcript(run) == load_golden()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "command_body"),
    [
        ("/advance", {}),
        pytest.param(
            "/decisions",
            {"dilemmaId": "d01", "optionId": "a"},
            marks=pytest.mark.xfail(
                reason=(
                    "TakeDecision checks the dilemma against the current block before the "
                    "terminal status, so it answers 422 invalid_option instead of the "
                    "contract's 409 run_already_finished"
                ),
            ),
        ),
    ],
)
async def test_a_finished_run_stays_readable_and_rejects_further_commands(
    database_url: str, operation: str, command_body: dict[str, str]
) -> None:
    async with _client(database_url) as client:
        run = await start_run(client)
        await play_to_the_end(client, run)

        rejected = await client.post(
            f"/api/runs/{run.run_id}{operation}",
            json={"expectedVersion": run.view["version"], **command_body},
            headers={**run.headers, "Idempotency-Key": "after-the-end-0001"},
        )
        current = await client.get(f"/api/runs/{run.run_id}", headers=run.headers)

    assert run.view["status"] == "finished"
    assert run.view["pendingDilemmas"] == []
    assert (rejected.status_code, rejected.json()["code"]) == (409, "run_already_finished")
    assert current.json() == run.view


@pytest.mark.anyio
async def test_a_finished_run_replays_exactly_from_its_persisted_inputs(
    database_url: str,
) -> None:
    async with _client(database_url) as client:
        run = await start_run(client)
        await play_to_the_end(client, run)

    engine = sa.create_engine(database_url)
    try:
        replay = ReplayRun(
            uow=SqlUnitOfWork(engine),
            token_hasher=Sha256RunTokenHasher(),
            restore_game=CatalogRunContentAdapter.restore_game,
            simulator=SimulationServiceAdapter(SimulationService()),
        )
        result = replay.execute(RunId.parse(run.run_id), run.token)
    finally:
        engine.dispose()

    assert result.verified
    assert result.reconstructed.run.status is RunStatus.FINISHED
