"""Application use cases for the durable Game run lifecycle."""

from datetime import UTC, datetime

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.application.api import PlayableSeasonDTO, PlayableSeasonSummaryDTO
from mister.game.application.ports import ConcurrencyError, RunNotFoundError
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import (
    GetRun,
    IdempotencyConflictError,
    RunAccessDeniedError,
    RunSnapshot,
    StartRun,
    TakeDecision,
)
from mister.game.domain.board import GoalProgress, GoalStatus
from mister.game.domain.events import DecisionTaken, RunStarted
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import InMemoryRunStore, InMemoryUnitOfWork
from mister.game.infrastructure.in_memory.run_tokens import FakeRunTokenGenerator
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.shared_kernel.clock import FixedClock
from mister.shared_kernel.events import DomainEvent, InMemoryEventBus
from mister.shared_kernel.ids import PlayableSeasonId, RunId
from mister.shared_kernel.seed import Seed


class _Provider:
    def __init__(self, season: PlayableSeasonDTO) -> None:
        self.season = season
        self.calls = 0

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        self.calls += 1
        assert self.season.id == season_id
        return self.season

    def list_playable_seasons(self) -> tuple[PlayableSeasonSummaryDTO, ...]:
        return ()


def _setup() -> tuple[
    PlayableSeasonDTO,
    _Provider,
    InMemoryRunStore,
    list[DomainEvent],
    StartRun,
    GetRun,
    TakeDecision,
]:
    season = build_expected_test_fc_season()
    provider = _Provider(season)
    content = CatalogRunContentAdapter(provider)
    store = InMemoryRunStore()
    uow = InMemoryUnitOfWork(store)
    clock = FixedClock(datetime(2026, 10, 28, tzinfo=UTC))
    tokens = FakeRunTokenGenerator()
    hasher = Sha256RunTokenHasher()
    bus = InMemoryEventBus()
    published: list[DomainEvent] = []

    def observe(event: DomainEvent) -> None:
        published.append(event)
        if isinstance(event, (DecisionTaken, RunStarted)):
            assert event.run_id in store.runs

    bus.subscribe(DomainEvent, observe)
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
    get = GetRun(uow=uow, token_hasher=hasher, restore_game=restore)
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
    assert (
        record.replay_inputs.rules_configuration_json
        == RulesConfiguration.a_profile().canonical_json()
    )
    assert RunSnapshot.decode(record.snapshot).run.id == created.run_id
    restored = CatalogRunContentAdapter.restore_game(
        record.replay_inputs.content, RulesConfiguration.a_profile()
    )
    assert RunSnapshot.decode(record.snapshot).goals == tuple(
        GoalProgress(goal.goal_id, GoalStatus.PENDING)
        for goal in restored.goals
    )
    assert events  # RunStarted is published after the transaction commits.
    assert get.execute(created.run_id, created.token).run.id == created.run_id


def test_get_run_authenticates_without_returning_a_token_hash() -> None:
    season, _, _, _, start, get, _ = _setup()
    created = start.execute(season.id)

    with pytest.raises(RunAccessDeniedError):
        get.execute(created.run_id, "wrong-token")
    view = get.execute(created.run_id, created.token)
    assert view.run.id == created.run_id
    assert not hasattr(view, "run_token_hash")


def test_unknown_run_is_reported_before_invalid_decision_body() -> None:
    season, _, _, _, _, _, take = _setup()
    dilemma = season.dilemmas[0]

    with pytest.raises(RunNotFoundError):
        take.execute(
            RunId.parse("00000000-0000-4000-8000-000000000002"),
            "irrelevant-token",
            "decision-key-0001",
            True,  # type: ignore[arg-type]
            dilemma.id,
            dilemma.options[0].id,
        )


def test_take_decision_is_idempotent_and_conflicts_on_different_command() -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    option = dilemma.options[0]

    first = take.execute(
        created.run_id, created.token, "decision-key-0001", 0, dilemma.id, option.id
    )
    replay = take.execute(
        created.run_id, created.token, "decision-key-0001", 0, dilemma.id, option.id
    )
    assert replay == first
    assert len(store.runs[created.run_id].decisions) == 1
    assert len(store.replies) == 1

    second_dilemma = next(
        item
        for item in season.dilemmas
        if item.block_id == dilemma.block_id and item.id != dilemma.id
    )
    take.execute(
        created.run_id,
        created.token,
        "decision-key-0002",
        1,
        second_dilemma.id,
        second_dilemma.options[0].id,
    )
    assert len(store.runs[created.run_id].decisions) == 2
    assert take.execute(
        created.run_id, created.token, "decision-key-0001", 0, dilemma.id, option.id
    ) == first
    with pytest.raises(ConcurrencyError):
        take.execute(
            created.run_id,
            created.token,
            "decision-key-stale-0001",
            0,
            second_dilemma.id,
            second_dilemma.options[0].id,
        )

    other = dilemma.options[-1]
    if other.id == option.id:
        pytest.skip("fixture dilemma exposes only one distinct option")
    with pytest.raises(IdempotencyConflictError):
        take.execute(created.run_id, created.token, "decision-key-0001", 0, dilemma.id, other.id)
    with pytest.raises(IdempotencyConflictError):
        take.execute(created.run_id, created.token, "decision-key-0001", 1, dilemma.id, option.id)

