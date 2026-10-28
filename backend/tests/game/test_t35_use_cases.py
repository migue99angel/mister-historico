"""Application use cases for the durable Game run lifecycle."""

from datetime import UTC, datetime

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.game.application.ports import RunNotFoundError
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import (
    GetRun,
    RunSnapshot,
    StartRun,
    TakeDecision,
)
from mister.game.domain.board import GoalProgress, GoalStatus
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import InMemoryRunStore, InMemoryUnitOfWork
from mister.game.infrastructure.in_memory.run_tokens import FakeRunTokenGenerator
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.shared_kernel.clock import FixedClock
from mister.shared_kernel.events import InMemoryEventBus
from mister.shared_kernel.ids import DilemmaId, OptionId, PlayableSeasonId, RunId
from mister.shared_kernel.seed import Seed


class _Provider:
    def __init__(self, season: object) -> None:
        self.season = season
        self.calls = 0

    def get_playable_season(self, season_id: PlayableSeasonId) -> object:
        self.calls += 1
        assert self.season.id == season_id
        return self.season


def _setup():
    season = build_expected_test_fc_season()
    provider = _Provider(season)
    content = CatalogRunContentAdapter(provider)  # type: ignore[arg-type]
    store = InMemoryRunStore()
    uow = InMemoryUnitOfWork(store)
    clock = FixedClock(datetime(2026, 10, 28, tzinfo=UTC))
    tokens = FakeRunTokenGenerator()
    hasher = Sha256RunTokenHasher()
    bus = InMemoryEventBus()
    published: list[object] = []
    bus.subscribe(object, published.append)  # type: ignore[arg-type]
    rules = RulesConfiguration.a_profile()
    start = StartRun(
        uow=uow,
        capture_game=content.capture_game,
        clock=clock,
        event_bus=bus,
        token_generator=tokens,
        token_hasher=hasher,
        seed_factory=lambda: Seed(42),
        run_id_factory=lambda: RunId.parse("00000000-0000-4000-8000-000000000001"),
        rules=rules,
    )
    restore = CatalogRunContentAdapter.restore_game
    get = GetRun(uow=uow, token_hasher=hasher)
    take = TakeDecision(
        uow=uow,
        clock=clock,
        event_bus=bus,
        token_hasher=hasher,
        restore_game=restore,
    )
    return season, provider, store, published, start, get, take


def test_start_run_captures_once_and_stores_recoverable_initial_snapshot() -> None:
    season, provider, store, events, start, get, _ = _setup()

    created = start.execute(season.id)
    record = store.runs[created.run_id]

    assert provider.calls == 1
    assert record.seed == Seed(42)
    assert record.replay_inputs.rules_configuration_json == RulesConfiguration.a_profile().canonical_json()
    assert RunSnapshot.decode(record.snapshot).run.id == created.run_id
    assert RunSnapshot.decode(record.snapshot).goals == tuple(
        GoalProgress(goal.goal_id, GoalStatus.PENDING)
        for goal in CatalogRunContentAdapter.restore_game(record.replay_inputs.content, RulesConfiguration.a_profile()).goals
    )
    assert events  # RunStarted is published after the transaction commits.
    assert get.execute(created.run_id, created.token).run.id == created.run_id


def test_get_run_authenticates_without_returning_a_token_hash() -> None:
    season, _, _, _, start, get, _ = _setup()
    created = start.execute(season.id)

    with pytest.raises(RunNotFoundError):
        get.execute(created.run_id, "wrong-token")
    view = get.execute(created.run_id, created.token)
    assert view.run.id == created.run_id
    assert not hasattr(view, "run_token_hash")


def test_take_decision_is_idempotent_and_conflicts_on_different_command() -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    option = dilemma.options[0]

    first = take.execute(
        created.run_id, created.token, "decision-key-0001", dilemma.id, option.id
    )
    replay = take.execute(
        created.run_id, created.token, "decision-key-0001", dilemma.id, option.id
    )
    assert replay == first
    assert len(store.runs[created.run_id].decisions) == 1
    assert len(store.replies) == 1

    other = dilemma.options[-1]
    if other.id == option.id:
        pytest.skip("fixture dilemma exposes only one distinct option")
    from mister.game.application.use_cases import IdempotencyConflictError

    with pytest.raises(IdempotencyConflictError):
        take.execute(created.run_id, created.token, "decision-key-0001", dilemma.id, other.id)

