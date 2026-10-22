import httpx
import pytest

from mister.entrypoints.api.app import create_app

pytestmark = pytest.mark.anyio


async def test_health_returns_ok() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
