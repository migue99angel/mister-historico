"""Exercise production HTTP composition with the real SQL catalog and run repository."""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

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
async def test_real_http_composition_starts_and_recovers_a_private_run(database_url: str):  # noqa: PLR0915
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

        wrong_token = await client.post(
            f"/api/runs/{run_id}/advance",
            content="not-json",
            headers={"Authorization": "Bearer wrong", "Idempotency-Key": "invalid-auth-001"},
        )
        assert wrong_token.status_code == 403
        assert wrong_token.json()["code"] == "run_token_invalid"
        unknown_run = await client.post(
            f"/api/runs/{uuid4()}/advance",
            content="not-json",
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "unknown-run-001"},
        )
        assert unknown_run.status_code == 404
        assert unknown_run.json()["code"] == "run_not_found"

        headers = {"Authorization": f"Bearer {token}"}
        read = await client.get(f"/api/runs/{run_id}", headers=headers)
        assert read.status_code == 200
        assert read.json() == payload["run"]
        serialized = str(read.json()).lower()
        for private_name in ("seed", "run_token_hash", "historical_option", "effects"):
            assert private_name not in serialized

        assert container.api() is not container.api()
        view = read.json()
        pending = view["pendingDilemmas"]
        if pending:
            early_advance = await client.post(
                f"/api/runs/{run_id}/advance",
                json={"expectedVersion": view["version"]},
                headers={**headers, "Idempotency-Key": "early-advance-001"},
            )
            assert early_advance.status_code == 409
            assert early_advance.json()["code"] == "pending_dilemmas"
            unchanged = await client.get(f"/api/runs/{run_id}", headers=headers)
            assert unchanged.json()["version"] == view["version"]

            first = pending[0]
            first_choice = first["options"][0]
            first_decision = {
                "expectedVersion": view["version"],
                "dilemmaId": first["id"],
                "optionId": first_choice["id"],
            }
            decision_key = "same-decision-001"
            decision_headers = {**headers, "Idempotency-Key": decision_key}

            async def take_first_decision():
                return await client.post(
                    f"/api/runs/{run_id}/decisions",
                    json=first_decision,
                    headers=decision_headers,
                )

            same_key_retries = await asyncio.gather(take_first_decision(), take_first_decision())
            assert [item.status_code for item in same_key_retries] == [200, 200]
            assert same_key_retries[0].json() == same_key_retries[1].json()
            view = same_key_retries[0].json()
            assert view["version"] == 1

            for index, dilemma in enumerate(view["pendingDilemmas"]):
                selected = dilemma["options"][0]
                next_decision = await client.post(
                    f"/api/runs/{run_id}/decisions",
                    json={
                        "expectedVersion": view["version"],
                        "dilemmaId": dilemma["id"],
                        "optionId": selected["id"],
                    },
                    headers={**headers, "Idempotency-Key": f"more-decisions-{index:03}"},
                )
                assert next_decision.status_code == 200
                view = next_decision.json()

            duplicate_decision = await client.post(
                f"/api/runs/{run_id}/decisions",
                json={
                    "expectedVersion": view["version"],
                    "dilemmaId": first["id"],
                    "optionId": first_choice["id"],
                },
                headers={**headers, "Idempotency-Key": "duplicate-decision-001"},
            )
            assert duplicate_decision.status_code == 409
            assert duplicate_decision.json()["code"] == "dilemma_already_decided"

            cross_operation_reuse = await client.post(
                f"/api/runs/{run_id}/advance",
                json={"expectedVersion": view["version"]},
                headers=decision_headers,
            )
            assert cross_operation_reuse.status_code == 422
            assert cross_operation_reuse.json()["code"] == "idempotency_key_conflict"

            invalid = await client.post(
                f"/api/runs/{run_id}/decisions",
                json={
                    "expectedVersion": view["version"],
                    "dilemmaId": "unknown-dilemma",
                    "optionId": "unknown-option",
                },
                headers={**headers, "Idempotency-Key": "invalid-option-001"},
            )
            assert invalid.status_code == 422
            assert invalid.json()["code"] == "invalid_option"
            unchanged = await client.get(f"/api/runs/{run_id}", headers=headers)
            assert unchanged.json()["version"] == view["version"]

        # Distinct keys compete at one version; only one can commit the simulation.
        expected_version = view["version"]
        advance_body = {"expectedVersion": expected_version}

        async def advance(key: str):
            return await client.post(
                f"/api/runs/{run_id}/advance",
                json=advance_body,
                headers={**headers, "Idempotency-Key": key},
            )

        different_key_race = await asyncio.gather(
            advance("advance-race-alpha"), advance("advance-race-bravo")
        )
        assert sorted(item.status_code for item in different_key_race) == [200, 409]
        successful_advance_index = next(
            index for index, item in enumerate(different_key_race) if item.status_code == 200
        )
        successful_advance_key = (
            "advance-race-alpha" if successful_advance_index == 0 else "advance-race-bravo"
        )
        advance_retry = await advance(successful_advance_key)
        assert advance_retry.status_code == 200
        assert advance_retry.json() == different_key_race[successful_advance_index].json()
        stale_response = await client.post(
            f"/api/runs/{run_id}/decisions",
            json={
                "expectedVersion": 0,
                "dilemmaId": "unknown-dilemma",
                "optionId": "unknown-option",
            },
            headers={**headers, "Idempotency-Key": "stale-command-001"},
        )
        assert stale_response.status_code == 409
        assert stale_response.json()["code"] == "version_conflict"

        if pending:
            original_retry = await client.post(
                f"/api/runs/{run_id}/decisions",
                json=first_decision,
                headers=decision_headers,
            )
            assert original_retry.status_code == 200
            assert original_retry.json() == same_key_retries[0].json()
            changed_body_retry = await client.post(
                f"/api/runs/{run_id}/decisions",
                json={**first_decision, "optionId": first["options"][1]["id"]},
                headers=decision_headers,
            )
            assert changed_body_retry.status_code == 422
            assert changed_body_retry.json()["code"] == "idempotency_key_conflict"
