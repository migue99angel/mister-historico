"""Golden test: a fixed seed and decision policy give the exact same Test FC season over HTTP.

Regenerate the golden only after an intended engine or presentation change, with
`MISTER_UPDATE_GOLDEN=1 uv run pytest --no-cov tests/golden`, and review its diff.
"""

import os
from datetime import UTC, datetime
from functools import cache
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from mister.bootstrap import Container
from mister.catalog.infrastructure.yaml_loader import YamlSeasonContentProvider
from mister.entrypoints.api.app import create_app
from mister.game.application.api import GameApi
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import AdvanceBlock, GetRun, StartRun, TakeDecision
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import (
    InMemoryRunStore,
    InMemoryUnitOfWork,
)
from mister.game.infrastructure.in_memory.run_tokens import FakeRunTokenGenerator
from mister.game.infrastructure.presentation_adapter import CatalogPresentationAdapter
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.settings import Settings
from mister.shared_kernel.clock import FixedClock
from mister.shared_kernel.events import InMemoryEventBus
from mister.shared_kernel.ids import RunId
from mister.shared_kernel.seed import Seed
from mister.simulation.application.api import SimulationService
from tests.golden.season_play import (
    GOLDEN_SEED,
    JsonObject,
    load_golden,
    play_to_the_end,
    start_run,
    transcript,
    write_golden,
)

_CONTENT = Path(__file__).resolve().parents[1] / "fixtures" / "content"
_STABILITY_RUNS = 10


@cache
def _content_provider() -> YamlSeasonContentProvider:
    """Read-only synthetic content, parsed once and shared by every golden run."""
    return YamlSeasonContentProvider(_CONTENT)


class _InMemoryRuntime:
    """Request-scoped Game API over in-memory runs, YAML content and the real engine."""

    def __init__(self) -> None:
        self._store = InMemoryRunStore()
        self._provider = _content_provider()

    def api(self) -> GameApi:
        uow = InMemoryUnitOfWork(self._store)
        hasher = Sha256RunTokenHasher()
        content = CatalogRunContentAdapter(self._provider)
        presentation = CatalogPresentationAdapter(self._provider, Settings())
        clock, bus = FixedClock(datetime(2000, 8, 1, tzinfo=UTC)), InMemoryEventBus()
        return GameApi(
            start_run=StartRun(
                uow=uow,
                capture_game=content.capture_game,
                clock=clock,
                event_bus=bus,
                token_generator=FakeRunTokenGenerator(),
                token_hasher=hasher,
                seed_factory=lambda: Seed(GOLDEN_SEED),
                run_id_factory=lambda: RunId.parse("00000000-0000-4000-8000-000000002000"),
                rules=RulesConfiguration.a_profile(),
            ),
            get_run=GetRun(uow=uow, token_hasher=hasher, restore_game=content.restore_game),
            take_decision=TakeDecision(
                uow=uow,
                clock=clock,
                event_bus=bus,
                token_hasher=hasher,
                restore_game=content.restore_game,
            ),
            advance_block=AdvanceBlock(
                uow=uow,
                clock=clock,
                event_bus=bus,
                token_hasher=hasher,
                restore_game=content.restore_game,
                simulator=SimulationServiceAdapter(SimulationService()),
            ),
            uow=uow,
            token_hasher=hasher,
            presentation=presentation,
            seasons=presentation,
        )


async def _play_golden_season() -> list[JsonObject]:
    app = create_app(Container(Settings()))
    app.state.runtime = _InMemoryRuntime()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run = await start_run(client)
        await play_to_the_end(client, run)
    return transcript(run)


@pytest.mark.anyio
async def test_fixed_seed_and_first_option_policy_reproduce_the_golden_season() -> None:
    played = await _play_golden_season()
    if os.environ.get("MISTER_UPDATE_GOLDEN") == "1":
        write_golden(played)

    assert played == load_golden()


@pytest.mark.anyio
async def test_golden_season_is_stable_across_ten_runs() -> None:
    golden = load_golden()

    for _ in range(_STABILITY_RUNS):
        assert await _play_golden_season() == golden
