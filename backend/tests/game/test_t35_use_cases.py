"""Application use cases for the durable Game run lifecycle."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Barrier

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.application.api import (
    MoraleEffectDTO,
    PlayableSeasonDTO,
    PlayableSeasonSummaryDTO,
)
from mister.game.application.content_model import CapturedSeason
from mister.game.application.ports import (
    ConcurrencyError,
    RunNotFoundError,
    RunStatus,
)
from mister.game.application.rules import RulesConfiguration
from mister.game.application.run_content import RunContentSnapshot
from mister.game.application.use_cases import (
    GetRun,
    IdempotencyConflictError,
    RunAccessDeniedError,
    RunSnapshot,
    RunView,
    StartRun,
    TakeDecision,
)
from mister.game.domain.board import GoalProgress, GoalStatus
from mister.game.domain.effects import PlayerMoraleEffect
from mister.game.domain.errors import AlreadyDecidedError
from mister.game.domain.events import DecisionTaken, RunStarted
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import InMemoryRunStore, InMemoryUnitOfWork
from mister.game.infrastructure.in_memory.run_tokens import FakeRunTokenGenerator
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.shared_kernel.clock import FixedClock
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.events import DomainEvent, InMemoryEventBus
from mister.shared_kernel.ids import DilemmaId, OptionId, PlayableSeasonId, RunId
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


def _setup(
    rules: RulesConfiguration | None = None,
) -> tuple[
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
    rules = rules or RulesConfiguration.a_profile()
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

    with pytest.raises(RunAccessDeniedError) as error:
        get.execute(created.run_id, "wrong-token")
    assert error.value.code == "run_token_invalid"
    view = get.execute(created.run_id, created.token)
    assert view.run.id == created.run_id
    assert not hasattr(view, "run_token_hash")


def test_get_run_rejects_unknown_run() -> None:
    _, _, _, _, _, get, _ = _setup()

    with pytest.raises(RunNotFoundError):
        get.execute(RunId.parse("00000000-0000-4000-8000-000000000002"), "token")


def test_unknown_run_is_reported_before_invalid_decision_body() -> None:
    season, _, _, _, _, _, take = _setup()
    dilemma = season.dilemmas[0]

    with pytest.raises(RunNotFoundError):
        take.execute(
            RunId.parse("00000000-0000-4000-8000-000000000002"),
            "irrelevant-token",
            "decision-key-0001",
            True,
            dilemma.id,
            dilemma.options[0].id,
        )


def test_existing_run_authentication_precedes_invalid_decision_body() -> None:
    season, _, _, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]

    with pytest.raises(RunAccessDeniedError):
        take.execute(
            created.run_id,
            "wrong-token",
            "decision-key-0001",
            True,
            dilemma.id,
            dilemma.options[0].id,
        )


def test_get_run_rejects_unsupported_engine_revision() -> None:
    season, _, store, _, start, get, _ = _setup()
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    store.runs[created.run_id] = replace(
        record,
        replay_inputs=replace(record.replay_inputs, engine_revision="future-engine"),
    )

    with pytest.raises(InvalidValueError, match="not supported"):
        get.execute(created.run_id, created.token)


def test_start_run_rejects_unsupported_rules_revision() -> None:
    rules = replace(RulesConfiguration.a_profile(), revision="future-rules")

    with pytest.raises(InvalidValueError, match="not supported"):
        _setup(rules)


def test_get_run_rejects_rules_json_revision_mismatch() -> None:
    season, _, store, _, start, get, _ = _setup()
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    changed_rules = replace(RulesConfiguration.a_profile(), revision="a-provisional-2")
    store.runs[created.run_id] = replace(
        record,
        replay_inputs=replace(
            record.replay_inputs,
            rules_configuration_json=changed_rules.canonical_json(),
        ),
    )

    with pytest.raises(InvalidValueError, match="does not match"):
        get.execute(created.run_id, created.token)


def test_get_run_rejects_snapshot_decision_log_mismatch() -> None:
    season, _, store, _, start, get, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    take.execute(
        created.run_id,
        created.token,
        "decision-log-check-001",
        0,
        dilemma.id,
        dilemma.options[0].id,
    )
    record = store.runs[created.run_id]
    store.runs[created.run_id] = replace(record, decisions=())

    with pytest.raises(InvalidValueError, match="append-only log"):
        get.execute(created.run_id, created.token)


def test_get_run_rejects_snapshot_status_mismatch() -> None:
    season, _, store, _, start, get, _ = _setup()
    created = start.execute(season.id)
    store.runs[created.run_id] = replace(
        store.runs[created.run_id], status=RunStatus.FINISHED
    )

    with pytest.raises(InvalidValueError, match="identity or status"):
        get.execute(created.run_id, created.token)


def test_get_run_rejects_snapshot_seed_mismatch() -> None:
    season, _, store, _, start, get, _ = _setup()
    created = start.execute(season.id)
    store.runs[created.run_id] = replace(store.runs[created.run_id], seed=Seed(43))

    with pytest.raises(InvalidValueError, match="identity or status"):
        get.execute(created.run_id, created.token)


def test_get_run_rejects_snapshot_blocks_that_differ_from_captured_content() -> None:
    season, _, store, _, start, get, _ = _setup()
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    snapshot = RunSnapshot.decode(record.snapshot)
    changed_run = replace(
        snapshot.run,
        blocks=(replace(snapshot.run.blocks[0], dilemmas=()), *snapshot.run.blocks[1:]),
    )
    store.runs[created.run_id] = replace(
        record,
        snapshot=replace(snapshot, run=changed_run).encode(),
    )

    with pytest.raises(InvalidValueError, match="captured content"):
        get.execute(created.run_id, created.token)


def test_get_run_rejects_invalid_initial_state_envelope() -> None:
    season, _, store, _, start, get, _ = _setup()
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    store.runs[created.run_id] = replace(
        record,
        replay_inputs=replace(record.replay_inputs, initial_state_json="{}"),
    )

    with pytest.raises(InvalidValueError, match="initial state"):
        get.execute(created.run_id, created.token)


def test_get_run_rejects_initial_state_that_differs_from_capture() -> None:
    season, _, store, _, start, get, _ = _setup()
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    initial = RunSnapshot.decode(json.loads(record.replay_inputs.initial_state_json))
    changed_initial = replace(initial, run=replace(initial.run, seed=Seed(43)))
    initial_json = json.dumps(
        changed_initial.encode(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    store.runs[created.run_id] = replace(
        record,
        replay_inputs=replace(record.replay_inputs, initial_state_json=initial_json),
    )

    with pytest.raises(InvalidValueError, match="initial state snapshot"):
        get.execute(created.run_id, created.token)


def test_get_run_rejects_goal_progress_missing_a_captured_goal() -> None:
    season, _, store, _, start, get, _ = _setup()
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    snapshot = RunSnapshot.decode(record.snapshot)
    store.runs[created.run_id] = replace(
        record,
        snapshot=replace(snapshot, goals=snapshot.goals[:-1]).encode(),
    )

    with pytest.raises(InvalidValueError, match="goal progress"):
        get.execute(created.run_id, created.token)


def test_invalid_expected_version_is_rejected_after_run_authentication() -> None:
    season, _, _, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]

    with pytest.raises(InvalidValueError, match="expected_version"):
        take.execute(
            created.run_id,
            created.token,
            "decision-key-0001",
            True,
            dilemma.id,
            dilemma.options[0].id,
        )


def test_take_decision_rejects_unknown_dilemma() -> None:
    season, _, _, _, start, _, take = _setup()
    created = start.execute(season.id)
    option_id = season.dilemmas[0].options[0].id

    with pytest.raises(InvalidValueError, match="current block"):
        take.execute(
            created.run_id,
            created.token,
            "decision-key-0001",
            0,
            DilemmaId("unknown-dilemma"),
            option_id,
        )


def test_take_decision_rejects_unknown_option() -> None:
    season, _, _, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]

    with pytest.raises(InvalidValueError, match="selected dilemma"):
        take.execute(
            created.run_id,
            created.token,
            "decision-key-0001",
            0,
            dilemma.id,
            OptionId("unknown-option"),
        )


def test_run_snapshot_rejects_unknown_envelope_fields() -> None:
    _season, _, _, _, start, _, _ = _setup()
    created = start.execute(_season.id)
    snapshot = created.view.run
    encoded = RunSnapshot(snapshot, created.view.goals).encode()
    encoded["unexpected"] = True

    with pytest.raises(InvalidValueError, match="envelope"):
        RunSnapshot.decode(encoded)


def test_run_snapshot_rejects_boolean_format_version() -> None:
    season, _, _, _, start, _, _ = _setup()
    created = start.execute(season.id)
    encoded = RunSnapshot(created.view.run, created.view.goals).encode()
    encoded["format_version"] = True

    with pytest.raises(InvalidValueError, match="format"):
        RunSnapshot.decode(encoded)


def test_run_snapshot_requires_goal_list() -> None:
    season, _, _, _, start, _, _ = _setup()
    created = start.execute(season.id)
    encoded = RunSnapshot(created.view.run, created.view.goals).encode()
    encoded["goals"] = {}

    with pytest.raises(InvalidValueError, match="goals must be a list"):
        RunSnapshot.decode(encoded)


def test_run_snapshot_rejects_duplicate_goal_ids() -> None:
    season, _, _, _, start, _, _ = _setup()
    created = start.execute(season.id)
    encoded = RunSnapshot(created.view.run, created.view.goals).encode()
    goals = encoded["goals"]
    assert isinstance(goals, list)
    assert goals
    goals.append(goals[0])

    with pytest.raises(InvalidValueError, match="unique"):
        RunSnapshot.decode(encoded)


def test_run_snapshot_rejects_malformed_goal_entry() -> None:
    season, _, _, _, start, _, _ = _setup()
    created = start.execute(season.id)
    encoded = RunSnapshot(created.view.run, created.view.goals).encode()
    encoded["goals"] = ["invalid"]

    with pytest.raises(InvalidValueError, match="goal progress"):
        RunSnapshot.decode(encoded)


def test_run_snapshot_rejects_unknown_goal_status() -> None:
    season, _, _, _, start, _, _ = _setup()
    created = start.execute(season.id)
    encoded = RunSnapshot(created.view.run, created.view.goals).encode()
    goals = encoded["goals"]
    assert isinstance(goals, list)
    goals[0] = {"goal_id": "goal", "status": "unknown"}

    with pytest.raises(InvalidValueError, match="goal progress"):
        RunSnapshot.decode(encoded)


def test_same_key_concurrent_decisions_return_the_committed_reply_once() -> None:
    season, _, store, events, start, _, _ = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    option = dilemma.options[0]
    barrier = Barrier(2)
    clock = FixedClock(datetime(2026, 10, 28, tzinfo=UTC))
    hasher = Sha256RunTokenHasher()
    race_bus = InMemoryEventBus()
    race_events: list[DomainEvent] = []
    race_bus.subscribe(DomainEvent, race_events.append)

    class RacingUnitOfWork(InMemoryUnitOfWork):
        def commit(self) -> None:
            barrier.wait(timeout=5)
            super().commit()

    def build_take() -> TakeDecision:
        return TakeDecision(
            uow=RacingUnitOfWork(store),
            clock=clock,
            event_bus=race_bus,
            token_hasher=hasher,
            restore_game=CatalogRunContentAdapter.restore_game,
        )

    left, right = build_take(), build_take()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(
            future.result(timeout=10)
            for future in (
                pool.submit(
                    left.execute,
                    created.run_id,
                    created.token,
                    "decision-race-0001",
                    0,
                    dilemma.id,
                    option.id,
                ),
                pool.submit(
                    right.execute,
                    created.run_id,
                    created.token,
                    "decision-race-0001",
                    0,
                    dilemma.id,
                    option.id,
                ),
            )
        )

    assert results[0] == results[1]
    assert len(store.runs[created.run_id].decisions) == 1
    assert len(store.replies) == 1
    assert len(events) == 1  # the original start event
    assert len(race_events) == 1  # one event after the winning transaction commits


def test_concurrent_different_commands_with_same_key_conflict() -> None:
    season, _, store, _, start, _, _ = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    if len(dilemma.options) == 1:
        pytest.skip("fixture dilemma exposes only one distinct option")
    barrier = Barrier(2)

    class RacingUnitOfWork(InMemoryUnitOfWork):
        def commit(self) -> None:
            barrier.wait(timeout=5)
            super().commit()

    def execute(option_index: int) -> RunView:
        take = TakeDecision(
            uow=RacingUnitOfWork(store),
            clock=FixedClock(datetime(2026, 10, 28, tzinfo=UTC)),
            event_bus=InMemoryEventBus(),
            token_hasher=Sha256RunTokenHasher(),
            restore_game=CatalogRunContentAdapter.restore_game,
        )
        return take.execute(
            created.run_id,
            created.token,
            "decision-race-0002",
            0,
            dilemma.id,
            dilemma.options[option_index].id,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (pool.submit(execute, 0), pool.submit(execute, -1))
        results: list[RunView] = []
        conflicts = 0
        for future in futures:
            try:
                results.append(future.result(timeout=10))
            except IdempotencyConflictError:
                conflicts += 1

    assert len(results) == 1
    assert conflicts == 1
    assert len(store.runs[created.run_id].decisions) == 1
    assert len(store.replies) == 1


def test_effect_failure_rolls_back_decision_and_emits_no_event() -> None:
    season, _, store, events, start, _, _ = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    option = dilemma.options[0]

    def invalid_effects(
        snapshot: RunContentSnapshot, rules: RulesConfiguration
    ) -> CapturedSeason:
        captured = CatalogRunContentAdapter.restore_game(snapshot, rules)
        own = set(
            captured.initial_state.squad_registry.squad_on(
                captured.managed_club_season_id, captured.blocks[0].start
            )
        )
        outside_player = next(
            item.player_id for item in captured.players if item.player_id not in own
        )
        blocks = list(captured.blocks)
        first_block = blocks[0]
        dilemmas = list(first_block.dilemmas)
        first_dilemma = dilemmas[0]
        options = tuple(
            replace(item, effects=(PlayerMoraleEffect(outside_player, 1),))
            if item.id == option.id
            else item
            for item in first_dilemma.options
        )
        dilemmas[0] = replace(first_dilemma, options=options)
        blocks[0] = replace(first_block, dilemmas=tuple(dilemmas))
        return replace(captured, blocks=tuple(blocks))

    failing_events: list[DomainEvent] = []
    failing_bus = InMemoryEventBus()
    failing_bus.subscribe(DomainEvent, failing_events.append)
    failing = TakeDecision(
        uow=InMemoryUnitOfWork(store),
        clock=FixedClock(datetime(2026, 10, 28, tzinfo=UTC)),
        event_bus=failing_bus,
        token_hasher=Sha256RunTokenHasher(),
        restore_game=invalid_effects,
    )
    with pytest.raises(InvalidValueError):
        failing.execute(
            created.run_id,
            created.token,
            "decision-failure-0001",
            0,
            dilemma.id,
            option.id,
        )

    assert store.runs[created.run_id].version == 0
    assert not store.runs[created.run_id].decisions
    assert not store.replies
    assert len(events) == 1  # RunStarted only
    assert not failing_events


def test_already_decided_error_precedes_effect_evaluation() -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    option = dilemma.options[0]
    take.execute(
        created.run_id, created.token, "decision-first-0001", 0, dilemma.id, option.id
    )

    def invalid_effects(
        snapshot: RunContentSnapshot, rules: RulesConfiguration
    ) -> CapturedSeason:
        captured = CatalogRunContentAdapter.restore_game(snapshot, rules)
        own = set(
            captured.initial_state.squad_registry.squad_on(
                captured.managed_club_season_id, captured.blocks[0].start
            )
        )
        non_member = next(
            item.player_id for item in captured.players if item.player_id not in own
        )
        first_block = captured.blocks[0]
        first_dilemma = first_block.dilemmas[0]
        changed_dilemma = replace(
            first_dilemma,
            options=tuple(
                replace(item, effects=(PlayerMoraleEffect(non_member, 1),))
                if item.id == option.id
                else item
                for item in first_dilemma.options
            ),
        )
        return replace(
            captured,
            blocks=(
                replace(
                    first_block,
                    dilemmas=(changed_dilemma, *first_block.dilemmas[1:]),
                ),
                *captured.blocks[1:],
            ),
        )

    failing = TakeDecision(
        uow=InMemoryUnitOfWork(store),
        clock=FixedClock(datetime(2026, 10, 28, tzinfo=UTC)),
        event_bus=InMemoryEventBus(),
        token_hasher=Sha256RunTokenHasher(),
        restore_game=invalid_effects,
    )
    with pytest.raises(AlreadyDecidedError):
        failing.execute(
            created.run_id,
            created.token,
            "decision-repeat-0001",
            1,
            dilemma.id,
            option.id,
        )


def test_take_decision_replays_original_reply_after_later_decision() -> None:
    season, _, store, events, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    option = dilemma.options[0]
    first = take.execute(
        created.run_id, created.token, "decision-key-0001", 0, dilemma.id, option.id
    )
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
    replay = take.execute(
        created.run_id, created.token, "decision-key-0001", 0, dilemma.id, option.id
    )

    assert replay == first
    assert len(store.runs[created.run_id].decisions) == 2
    assert len(store.replies) == 2
    assert len(events) == 3  # start plus one event per new decision


def test_take_decision_applies_option_effect_without_moving_the_state_cursor() -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    morale_option = next(
        item
        for item in dilemma.options
        if any(isinstance(effect, MoraleEffectDTO) for effect in item.effects)
    )
    morale_effect = next(
        effect for effect in morale_option.effects if isinstance(effect, MoraleEffectDTO)
    )

    take.execute(
        created.run_id,
        created.token,
        "decision-effect-0001",
        0,
        dilemma.id,
        morale_option.id,
    )

    stored_run = RunSnapshot.decode(store.runs[created.run_id].snapshot).run
    assert stored_run.run_state.team_morale == 50 + morale_effect.delta
    assert stored_run.run_state.state_as_of == season.blocks[0].start


def test_take_decision_rejects_idempotency_key_reused_for_another_command() -> None:
    season, _, _, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    if len(dilemma.options) == 1:
        pytest.skip("fixture dilemma exposes only one distinct option")
    take.execute(
        created.run_id,
        created.token,
        "decision-key-0001",
        0,
        dilemma.id,
        dilemma.options[0].id,
    )
    with pytest.raises(IdempotencyConflictError):
        take.execute(
            created.run_id,
            created.token,
            "decision-key-0001",
            0,
            dilemma.id,
            dilemma.options[-1].id,
        )


def test_take_decision_rejects_idempotency_key_reused_with_another_version() -> None:
    season, _, _, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    option = dilemma.options[0]
    take.execute(
        created.run_id, created.token, "decision-key-0001", 0, dilemma.id, option.id
    )
    with pytest.raises(IdempotencyConflictError):
        take.execute(
            created.run_id, created.token, "decision-key-0001", 1, dilemma.id, option.id
        )


def test_take_decision_rejects_a_stale_expected_version() -> None:
    season, _, _, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    take.execute(
        created.run_id,
        created.token,
        "decision-key-0001",
        0,
        dilemma.id,
        dilemma.options[0].id,
    )
    second_dilemma = next(
        item
        for item in season.dilemmas
        if item.block_id == dilemma.block_id and item.id != dilemma.id
    )
    with pytest.raises(ConcurrencyError):
        take.execute(
            created.run_id,
            created.token,
            "decision-key-stale-0001",
            0,
            second_dilemma.id,
            second_dilemma.options[0].id,
        )


def test_invalid_idempotency_key_is_rejected_before_version_check() -> None:
    season, _, _, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]

    with pytest.raises(InvalidValueError, match="idempotency key"):
        take.execute(
            created.run_id,
            created.token,
            "",
            99,
            dilemma.id,
            dilemma.options[0].id,
        )

