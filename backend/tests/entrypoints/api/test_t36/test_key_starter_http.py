"""T3.9 `POST /runs/{runId}/key-starter`: shape, authentication order and public errors."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar, cast

import pytest
from httpx import ASGITransport, AsyncClient
from tests.entrypoints.api.test_t36.test_http_contract import (
    _assert_contract_response,
    _GameApi,
    _Presented,
    _PublicError,
    _run_json,
)

from mister.entrypoints.api.app import create_app
from mister.shared_kernel.ids import FixtureId, PlayerId, RunId

if TYPE_CHECKING:
    from mister.bootstrap import Container

RUN = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
PATH = f"/api/runs/{RUN}/key-starter"
HEADERS = {"Authorization": "Bearer fixture", "Idempotency-Key": "select-123"}
BODY = {"fixtureId": "tfc-super-final", "playerId": "tfc-12", "expectedVersion": 0}


class _KeyStarterApi(_GameApi):
    calls: ClassVar[list[tuple[Any, ...]]] = []

    def select_key_starter(self, *args: Any) -> _Presented:
        _KeyStarterApi.calls.append(args)
        player = args[-1]
        if player.value == "invalid":
            raise _PublicError("invalid_key_starter")
        if player.value == "again":
            raise _PublicError("key_starter_already_selected")
        if player.value == "late":
            raise _PublicError("run_already_finished")
        if player.value == "stale":
            raise _PublicError("version_conflict")
        value = _run_json()
        value["version"] = 1
        return _Presented(value)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    _KeyStarterApi.calls = []
    container = cast("Container", SimpleNamespace(settings=None, engine=None))
    app = create_app(container)
    app.state.runtime = SimpleNamespace(api=_KeyStarterApi)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


@pytest.mark.anyio
async def test_a_selection_returns_the_run_view_and_passes_typed_fields(
    client: AsyncClient,
) -> None:
    response = await client.post(PATH, json=BODY, headers=HEADERS)

    assert response.status_code == 200
    _assert_contract_response(response, "/runs/{runId}/key-starter", "post", 200)
    assert _KeyStarterApi.calls == [
        (
            RunId.parse(RUN),
            "fixture",
            "select-123",
            0,
            FixtureId("tfc-super-final"),
            PlayerId("tfc-12"),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("player", "status", "code"),
    [
        ("invalid", 422, "invalid_key_starter"),
        ("again", 409, "key_starter_already_selected"),
        ("late", 409, "run_already_finished"),
        ("stale", 409, "version_conflict"),
    ],
)
async def test_selection_errors_keep_their_public_codes(
    client: AsyncClient, player: str, status: int, code: str
) -> None:
    response = await client.post(PATH, json={**BODY, "playerId": player}, headers=HEADERS)

    assert response.status_code == status
    assert response.json()["code"] == code
    _assert_contract_response(response, "/runs/{runId}/key-starter", "post", status)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        {**BODY, "date": "2000-08-20"},
        {"fixtureId": "tfc-super-final", "playerId": "tfc-12"},
        {**BODY, "playerId": "Not A Slug"},
        {**BODY, "expectedVersion": -1},
        [],
    ],
)
async def test_invalid_bodies_are_validation_errors(client: AsyncClient, body: object) -> None:
    response = await client.post(PATH, json=body, headers=HEADERS)

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert _KeyStarterApi.calls == []


@pytest.mark.anyio
async def test_the_idempotency_key_is_required(client: AsyncClient) -> None:
    response = await client.post(PATH, json=BODY, headers={"Authorization": "Bearer fixture"})

    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_required"


@pytest.mark.anyio
async def test_the_token_is_checked_before_the_body(client: AsyncClient) -> None:
    response = await client.post(PATH, json=[], headers={"Idempotency-Key": "select-123"})

    assert response.status_code == 401
    assert response.json()["code"] == "run_token_required"
