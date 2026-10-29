"""Play the synthetic Test FC season over HTTP with a fixed decision policy.

Shared by the golden test (in-memory composition) and the backend E2E (production composition
over PostgreSQL), so both runs can be compared against the same golden transcript.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from httpx import AsyncClient

TEST_FC_SEASON = "test-fc-2000-01"
GOLDEN_SEED = 2000
GOLDEN_PATH = Path(__file__).with_name("test_fc_2000_01.golden.json")

JsonObject = dict[str, Any]


@dataclass(slots=True)
class PlayedRun:
    """Everything a client keeps while playing: the token and each view it received."""

    run_id: str
    token: str
    views: list[JsonObject] = field(default_factory=list)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    @property
    def view(self) -> JsonObject:
        return self.views[-1]


async def start_run(client: AsyncClient) -> PlayedRun:
    response = await client.post("/api/runs", json={"seasonId": TEST_FC_SEASON})
    assert response.status_code == 201, response.text
    payload = response.json()
    return PlayedRun(payload["run"]["runId"], payload["runToken"], [payload["run"]])


async def decide(client: AsyncClient, run: PlayedRun, dilemma: JsonObject, key: str) -> None:
    """Choose the first option of `dilemma`, the deterministic policy of the golden."""
    response = await client.post(
        f"/api/runs/{run.run_id}/decisions",
        json={
            "expectedVersion": run.view["version"],
            "dilemmaId": dilemma["id"],
            "optionId": dilemma["options"][0]["id"],
        },
        headers={**run.headers, "Idempotency-Key": key},
    )
    assert response.status_code == 200, response.text
    run.views.append(response.json())


async def advance(client: AsyncClient, run: PlayedRun, key: str) -> None:
    response = await client.post(
        f"/api/runs/{run.run_id}/advance",
        json={"expectedVersion": run.view["version"]},
        headers={**run.headers, "Idempotency-Key": key},
    )
    assert response.status_code == 200, response.text
    run.views.append(response.json())


async def play_block(client: AsyncClient, run: PlayedRun) -> None:
    """Decide every pending dilemma of the current block, then close it."""
    block = run.view["block"]["number"]
    for dilemma in run.view["pendingDilemmas"]:
        await decide(client, run, dilemma, f"decide-block-{block}-{dilemma['id']}")
    await advance(client, run, f"advance-block-{block}")


async def play_to_the_end(client: AsyncClient, run: PlayedRun) -> None:
    while run.view["status"] == "in_progress":
        await play_block(client, run)


def transcript(run: PlayedRun) -> list[JsonObject]:
    """The views a client saw, without the generated run id."""
    return [{key: value for key, value in view.items() if key != "runId"} for view in run.views]


def load_golden() -> list[JsonObject]:
    golden: list[JsonObject] = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    return golden


def write_golden(views: list[JsonObject]) -> None:
    text = json.dumps(views, ensure_ascii=False, indent=1, sort_keys=True)
    GOLDEN_PATH.write_text(f"{text}\n", encoding="utf-8")
