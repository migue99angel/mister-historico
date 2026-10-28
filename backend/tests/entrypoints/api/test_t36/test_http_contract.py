from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from mister.entrypoints.api.app import create_app


class _Presented:
    def __init__(self, value):
        self.value = value

    def to_json(self):
        return self.value


class _Started:
    token = "secret-run-token"
    run = _Presented({"id": "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11", "version": 0})


class _GameApi:
    def list_seasons(self):
        return (_Presented({"id": "test-fc-2000-01"}),)

    def get_season(self, season_id):
        return _Presented({"id": season_id.value})

    def start_run(self, season_id):
        return _Started()

    def authenticate(self, run_id, token):
        return None

    def get_run(self, run_id, token):
        return _Presented({"id": str(run_id)})

    def take_decision(self, *args):
        return _Presented({"version": 1})

    def advance_block(self, *args):
        return _Presented({"version": 1})


@pytest.fixture
async def client():
    runtime = SimpleNamespace(api=lambda: _GameApi())
    app = create_app(SimpleNamespace(settings=None, engine=None))
    app.state.runtime = runtime
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


@pytest.mark.anyio
async def test_seasons_http_routes_return_presentation(client):
    assert (await client.get("/api/seasons")).json() == [{"id": "test-fc-2000-01"}]
    assert (await client.get("/api/seasons/test-fc-2000-01")).json() == {"id": "test-fc-2000-01"}


@pytest.mark.anyio
async def test_run_commands_authenticate_before_parsing_request_body(client):
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(f"/api/runs/{run}/advance", content="not-json")
    assert response.status_code == 401
    assert response.json()["code"] == "run_token_required"


@pytest.mark.anyio
async def test_invalid_json_after_authentication_is_a_bad_request(client):
    run = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"
    response = await client.post(
        f"/api/runs/{run}/advance", content="not-json",
        headers={"Authorization": "Bearer token", "Idempotency-Key": "12345678"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_openapi_exposes_only_the_six_f3_operations():
    app = create_app(SimpleNamespace(settings=None, engine=None))
    schema = app.openapi()
    operations = {
        operation["operationId"]
        for path, methods in schema["paths"].items()
        for operation in methods.values()
        if isinstance(operation, dict) and "operationId" in operation
        and path.startswith("/api/")
    }
    assert operations == {"listSeasons", "getSeason", "startRun", "getRun", "takeDecision", "advanceBlock"}
