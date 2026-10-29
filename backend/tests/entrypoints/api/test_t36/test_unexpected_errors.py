"""Unexpected facade failures remain diagnosable without exposing internals over HTTP."""

import logging
from types import SimpleNamespace
from typing import TYPE_CHECKING, NoReturn, cast

import pytest
from httpx import ASGITransport, AsyncClient

from mister.entrypoints.api.app import create_app

if TYPE_CHECKING:
    from mister.bootstrap import Container

_RUN = "0b6f3a52-6c0e-4d3e-8d0a-3f1f6e2b9c11"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "path", "operation", "body"),
    [
        ("GET", "/api/seasons", "list_seasons", None),
        ("GET", "/api/seasons/test-fc-2000-01", "get_season", None),
        ("POST", "/api/runs", "start_run", {"seasonId": "test-fc-2000-01"}),
        ("GET", f"/api/runs/{_RUN}", "authenticate", None),
        ("GET", f"/api/runs/{_RUN}", "get_run", None),
        (
            "POST",
            f"/api/runs/{_RUN}/decisions",
            "take_decision",
            {"expectedVersion": 0, "dilemmaId": "test-dilemma", "optionId": "test-option"},
        ),
        ("POST", f"/api/runs/{_RUN}/advance", "advance_block", {"expectedVersion": 0}),
        ("GET", "/api/seasons", "api", None),
    ],
)
async def test_unexpected_api_failure_logs_traceback_and_returns_private_problem(
    method: str,
    path: str,
    operation: str,
    body: dict[str, object] | None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    failure = RuntimeError("private database connection failure")

    def fail(*_: object) -> NoReturn:
        raise failure

    api = SimpleNamespace(authenticate=lambda *_: None)
    setattr(api, operation, fail)
    runtime = SimpleNamespace(
        settings=None, engine=None, api=fail if operation == "api" else lambda: api
    )
    app = create_app(cast("Container", runtime))
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        with caplog.at_level(logging.ERROR):
            response = await client.request(
                method,
                path,
                json=body,
                headers={"Authorization": "Bearer fixture", "Idempotency-Key": "failure-001"},
            )

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "internal_error"
    assert response.json()["detail"] == "An internal error occurred."
    assert str(failure) not in response.text
    records = [record for record in caplog.records if record.exc_info]
    assert len(records) == 1
    assert records[0].exc_info is not None
    assert records[0].exc_info[1] is failure
    assert records[0].exc_info[2] is not None
    assert "Traceback (most recent call last)" in caplog.text
