"""A run can be verified from its immutable replay inputs without side effects."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from tests.game.test_t35_use_cases import _setup

from mister.catalog.application.api import PlayableSeasonDTO
from mister.game.application import ports
from mister.game.application.block_codec import decode_block, encode_block
from mister.game.application.closure import advance_snapshot
from mister.game.application.content_model import CapturedSeason
from mister.game.application.ports import (
    BlockSimulationRequest,
    BlockSimulationResult,
    PlayerOutcome,
    RunNotFoundError,
)
from mister.game.application.replay import ReplayResult, ReplayRun
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import AdvanceBlock, RunAccessDeniedError, RunSnapshot
from mister.game.domain.board import GoalStatus
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import (
    InMemoryRunStore,
    InMemoryUnitOfWork,
)
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.shared_kernel.clock import FixedClock
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.events import InMemoryEventBus
from mister.shared_kernel.ids import ClubSeasonId, FixtureId, PlayableSeasonId, RunId
from mister.shared_kernel.seed import Seed
from mister.simulation.application.api import SimulationService


class _UnusedSimulator:
    def simulate_block(self, request: BlockSimulationRequest) -> BlockSimulationResult:
        raise AssertionError("an open block must not be simulated during replay")


class _OutcomeSimulator:
    def __init__(self) -> None:
        self.calls = 0

    def simulate_block(self, request: BlockSimulationRequest) -> BlockSimulationResult:
        self.calls += 1
        assert request.player_pool is not None
        return BlockSimulationResult(
            request.block_id,
            (),
            (),
            (),
            (),
            (),
            tuple(
                PlayerOutcome(player.player_id, player.fitness, player.injured_until)
                for player in request.player_pool
            ),
        )


class _SackAfterLossSimulator:
    def __init__(self, captured: CapturedSeason, managed_club: ClubSeasonId) -> None:
        self._captured = captured
        self._managed_club = managed_club
        self.calls = 0

    def simulate_block(self, request: BlockSimulationRequest) -> BlockSimulationResult:
        captured = self._captured
        assert request.player_pool is not None
        matches: tuple[ports.MatchOutcome, ...] = ()
        if self.calls == 1:
            fixture = next(
                item for item in captured.fixtures if request.start <= item.date <= request.end
            )
            at_home = fixture.venue == "home"
            home = self._managed_club if at_home else fixture.opponent
            away = fixture.opponent if at_home else self._managed_club
            matches = (
                ports.MatchOutcome(
                    FixtureId(fixture.id),
                    fixture.competition_id,
                    fixture.date,
                    home,
                    away,
                    ports.ScoreLine(0, 1) if at_home else ports.ScoreLine(1, 0),
                    ports.TeamVenue.HOME if at_home else ports.TeamVenue.AWAY,
                    fixture.opponent,
                    ports.UserResult.LOSS,
                    winner=ports.Side.AWAY if at_home else ports.Side.HOME,
                ),
            )
        self.calls += 1
        return BlockSimulationResult(
            request.block_id,
            matches,
            (),
            (),
            (),
            (),
            tuple(
                PlayerOutcome(player.player_id, player.fitness, player.injured_until)
                for player in request.player_pool
            ),
        )


def _replay(
    store: InMemoryRunStore,
    simulator: ports.SeasonSimulator | None = None,
) -> ReplayRun:
    return ReplayRun(
        uow=InMemoryUnitOfWork(store),
        token_hasher=Sha256RunTokenHasher(),
        restore_game=CatalogRunContentAdapter.restore_game,
        simulator=simulator or _UnusedSimulator(),
    )


def _advance(
    store: InMemoryRunStore,
    simulator: ports.SeasonSimulator,
) -> AdvanceBlock:
    return AdvanceBlock(
        uow=InMemoryUnitOfWork(store),
        clock=FixedClock(datetime(2026, 10, 28, tzinfo=UTC)),
        event_bus=InMemoryEventBus(),
        token_hasher=Sha256RunTokenHasher(),
        restore_game=CatalogRunContentAdapter.restore_game,
        simulator=simulator,
    )


def test_replay_reconstructs_an_open_run_without_simulating_or_writing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    season, provider, store, events, start, _, _ = _setup()
    created = start.execute(season.id)
    persisted = store.runs[created.run_id]
    replies_before = dict(store.replies)
    events_before = tuple(events)

    def fail_live_catalog(_season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        raise AssertionError("replay must use the captured season")

    monkeypatch.setattr(provider, "get_playable_season", fail_live_catalog)

    result = _replay(store).execute(created.run_id, created.token)

    assert isinstance(result, ReplayResult)
    assert result.run_id == created.run_id
    assert result.verified is True
    assert result.reconstructed == RunSnapshot.decode(persisted.snapshot)
    assert store.runs[created.run_id] == persisted
    assert store.replies == replies_before
    assert tuple(events) == events_before


def test_replay_stays_on_capture_a_after_provider_changes_and_new_run_captures_b() -> None:
    season_a, provider_a, store_a, _, start_a, _, _ = _setup()
    run_a = start_a.execute(season_a.id)
    capture_a = store_a.runs[run_a.run_id].replay_inputs.content
    provider_a.season = replace(season_a, season="Test FC alternate season")

    replay_a = _replay(store_a).execute(run_a.run_id, run_a.token)

    assert replay_a.reconstructed == RunSnapshot.decode(store_a.runs[run_a.run_id].snapshot)
    assert provider_a.calls == 1

    season_b, provider_b, store_b, _, start_b, _, _ = _setup()
    provider_b.season = replace(season_b, season="Test FC alternate season")
    run_b = start_b.execute(season_b.id)
    capture_b = store_b.runs[run_b.run_id].replay_inputs.content

    assert capture_b != capture_a
    assert provider_b.calls == 1
    assert ReplayRun(
        uow=InMemoryUnitOfWork(store_b),
        token_hasher=Sha256RunTokenHasher(),
        restore_game=CatalogRunContentAdapter.restore_game,
        simulator=_UnusedSimulator(),
    ).execute(run_b.run_id, run_b.token).reconstructed == RunSnapshot.decode(
        store_b.runs[run_b.run_id].snapshot
    )


def test_replay_applies_open_block_decisions_from_the_append_only_log() -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    dilemma = season.dilemmas[0]
    take.execute(
        created.run_id,
        created.token,
        "replay-choice-0001",
        0,
        dilemma.id,
        dilemma.options[0].id,
    )
    record = store.runs[created.run_id]

    result = _replay(store).execute(created.run_id, created.token)

    assert result.reconstructed == RunSnapshot.decode(record.snapshot)
    assert result.reconstructed.run.decisions[0].dilemma_id == dilemma.id


@given(data=st.data())
@settings(max_examples=6, deadline=None)
def test_replay_preserves_generated_choice_prefixes(data: st.DataObject) -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    first_block = season.blocks[0]
    dilemmas = tuple(item for item in season.dilemmas if item.block_id == first_block.id)
    for index, dilemma in enumerate(dilemmas):
        option_index = data.draw(
            st.integers(min_value=0, max_value=len(dilemma.options) - 1),
            label=f"option for {dilemma.id}",
        )
        take.execute(
            created.run_id,
            created.token,
            f"hypothesis-choice-{index:04d}",
            store.runs[created.run_id].version,
            dilemma.id,
            dilemma.options[option_index].id,
        )

    persisted = store.runs[created.run_id]
    result = _replay(store).execute(created.run_id, created.token)

    assert result.reconstructed == RunSnapshot.decode(persisted.snapshot)
    assert tuple(item.option_id for item in result.reconstructed.run.decisions) == tuple(
        item.option_id for item in persisted.decisions
    )


def test_replay_reconstructs_decisions_and_a_closed_block_prefix() -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    first_block = season.blocks[0]
    first_dilemmas = tuple(item for item in season.dilemmas if item.block_id == first_block.id)
    for index, dilemma in enumerate(first_dilemmas):
        take.execute(
            created.run_id,
            created.token,
            f"close-choice-{index:04d}",
            index,
            dilemma.id,
            dilemma.options[0].id,
        )

    record = store.runs[created.run_id]
    before_close = RunSnapshot.decode(record.snapshot)
    captured = CatalogRunContentAdapter.restore_game(
        record.replay_inputs.content, RulesConfiguration.a_profile()
    )
    simulator = _OutcomeSimulator()
    closed, _events = advance_snapshot(
        before_close,
        captured,
        simulator,
        RulesConfiguration.a_profile(),
        datetime(2026, 10, 28, tzinfo=UTC),
    )
    store.runs[created.run_id] = replace(
        record,
        snapshot=closed.encode(),
        status=ports.RunStatus(closed.run.status.value),
        version=record.version + 1,
    )
    persisted = store.runs[created.run_id]
    simulator.calls = 0

    result = _replay(store, simulator).execute(created.run_id, created.token)

    assert result.reconstructed == closed
    assert len(result.reconstructed.run.block_records) == 1
    assert result.reconstructed.run.block_index == 1
    assert result.reconstructed.run.cursor == first_block.end
    assert simulator.calls == 1
    assert store.runs[created.run_id] == persisted


@pytest.mark.parametrize("tamper", ["payload", "cursor", "goals"])
def test_replay_rejects_tampered_closed_result_state(tamper: str) -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    first_block = season.blocks[0]
    dilemmas = tuple(item for item in season.dilemmas if item.block_id == first_block.id)
    for index, dilemma in enumerate(dilemmas):
        take.execute(
            created.run_id,
            created.token,
            f"tamper-choice-{index:04d}",
            store.runs[created.run_id].version,
            dilemma.id,
            dilemma.options[0].id,
        )

    record = store.runs[created.run_id]
    rules = RulesConfiguration.a_profile()
    captured = CatalogRunContentAdapter.restore_game(record.replay_inputs.content, rules)
    result, _events = advance_snapshot(
        RunSnapshot.decode(record.snapshot),
        captured,
        _OutcomeSimulator(),
        rules,
        datetime(2026, 10, 28, tzinfo=UTC),
    )
    changed = result
    if tamper == "payload":
        closure = changed.run.block_records[0]
        payload = decode_block(closure.payload)
        first = payload.player_states[0]
        replacement = replace(first, fitness=max(0, first.fitness - 1))
        changed_outcomes = replace(
            payload,
            player_states=(replacement, *payload.player_states[1:]),
        )
        records = (replace(closure, payload=encode_block(changed_outcomes)),)
        changed = replace(changed, run=replace(changed.run, block_records=records))
    elif tamper == "cursor":
        assert changed.run.cursor is not None
        changed = replace(
            changed,
            run=replace(
                changed.run,
                cursor=changed.run.cursor.fromordinal(changed.run.cursor.toordinal() + 1),
            ),
        )
    else:
        goal = changed.goals[0]
        status = GoalStatus.MET if goal.status is not GoalStatus.MET else GoalStatus.PENDING
        changed = replace(
            changed,
            goals=(replace(goal, status=status), *changed.goals[1:]),
        )
    store.runs[created.run_id] = replace(record, snapshot=changed.encode())

    with pytest.raises(InvalidValueError):
        _replay(store, _OutcomeSimulator()).execute(created.run_id, created.token)


def test_replay_closed_test_fc_run_with_the_real_simulation_engine() -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    rules = RulesConfiguration.a_profile()
    record = store.runs[created.run_id]
    captured = CatalogRunContentAdapter.restore_game(record.replay_inputs.content, rules)
    simulator = SimulationServiceAdapter(SimulationService())
    advance = _advance(store, simulator)
    for block_index, block in enumerate(captured.blocks):
        current = store.runs[created.run_id]
        assert RunSnapshot.decode(current.snapshot).run.block_index < len(captured.blocks)
        for index, dilemma in enumerate(block.dilemmas):
            take.execute(
                created.run_id,
                created.token,
                f"engine-{block_index}-{index:04d}",
                store.runs[created.run_id].version,
                dilemma.id,
                dilemma.options[0].id,
            )
        view = advance.execute(
            created.run_id,
            created.token,
            f"engine-close-{block_index:04d}",
            store.runs[created.run_id].version,
        )
        if view.run.status.value != "in_progress":
            break

    persisted = store.runs[created.run_id]
    assert len(RunSnapshot.decode(persisted.snapshot).run.block_records) == len(captured.blocks)

    result = _replay(store, simulator).execute(created.run_id, created.token)

    assert result.reconstructed == RunSnapshot.decode(persisted.snapshot)
    assert result.reconstructed.run.status.value == "finished"
    assert len(result.reconstructed.run.block_records) == len(captured.blocks)
    assert store.runs[created.run_id] == persisted


def test_replay_reconstructs_a_sacked_middle_block() -> None:
    base_rules = RulesConfiguration.a_profile()
    rules = replace(
        base_rules,
        board=replace(
            base_rules.board,
            sacking_threshold=98,
            objective_met_delta=0,
            objective_missed_delta=0,
        ),
        initial_state=replace(base_rules.initial_state, board_confidence=100),
    )
    season, _, store, _, start, _, take = _setup(rules)
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    captured = CatalogRunContentAdapter.restore_game(record.replay_inputs.content, rules)
    simulator = _SackAfterLossSimulator(captured, season.club_season_id)
    advance = _advance(store, simulator)

    for block_index, block in enumerate(captured.blocks[:2]):
        for index, dilemma in enumerate(block.dilemmas):
            take.execute(
                created.run_id,
                created.token,
                f"middle-sack-choice-{block_index}-{index}",
                store.runs[created.run_id].version,
                dilemma.id,
                dilemma.options[0].id,
            )
        result = advance.execute(
            created.run_id,
            created.token,
            f"middle-sack-close-{block_index}",
            store.runs[created.run_id].version,
        )
        if result.run.status.value == "sacked":
            break

    persisted = store.runs[created.run_id]
    terminal = RunSnapshot.decode(persisted.snapshot)
    assert terminal.run.status.value == "sacked"
    assert len(terminal.run.block_records) == 2
    simulator.calls = 0

    replayed = _replay(store, simulator).execute(created.run_id, created.token)

    assert replayed.reconstructed == terminal
    assert simulator.calls == 2


@given(data=st.data(), seed=st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=10, deadline=None)
def test_replay_reconstructs_generated_sacked_runs(data: st.DataObject, seed: int) -> None:
    base_rules = RulesConfiguration.a_profile()
    rules = replace(base_rules, board=replace(base_rules.board, sacking_threshold=100))
    season, _, store, _, start, _, take = _setup(rules)
    start._seed_factory = lambda: Seed(seed)
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    captured = CatalogRunContentAdapter.restore_game(record.replay_inputs.content, rules)
    for index, dilemma in enumerate(captured.blocks[0].dilemmas):
        option_index = data.draw(
            st.integers(min_value=0, max_value=len(dilemma.options) - 1),
            label=f"sacked option for {dilemma.id}",
        )
        take.execute(
            created.run_id,
            created.token,
            f"sack-choice-{index:04d}",
            store.runs[created.run_id].version,
            dilemma.id,
            dilemma.options[option_index].id,
        )

    simulator = SimulationServiceAdapter(SimulationService())
    view = _advance(store, simulator).execute(
        created.run_id,
        created.token,
        "sacked-close-0001",
        store.runs[created.run_id].version,
    )
    assert view.run.status.value == "sacked"
    persisted = store.runs[created.run_id]

    result = _replay(store, simulator).execute(created.run_id, created.token)

    assert result.reconstructed == RunSnapshot.decode(persisted.snapshot)
    assert len(result.reconstructed.run.block_records) == 1
    assert store.runs[created.run_id] == persisted


def test_replay_rejects_unknown_runs_and_invalid_tokens() -> None:
    season, _, store, _, start, _, _ = _setup()
    created = start.execute(season.id)
    replay = _replay(store)

    with pytest.raises(RunNotFoundError):
        replay.execute(RunId.parse("00000000-0000-4000-8000-000000000002"), created.token)

    with pytest.raises(RunAccessDeniedError):
        _replay(store).execute(created.run_id, "wrong-token")


def test_replay_rejects_tampered_snapshot_against_its_capture() -> None:
    season, _, store, _, start, _, _ = _setup()
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    snapshot = RunSnapshot.decode(record.snapshot)
    changed_state = replace(
        snapshot.run.run_state,
        team_morale=snapshot.run.run_state.team_morale - 1,
    )
    changed_snapshot = replace(snapshot, run=replace(snapshot.run, run_state=changed_state))
    store.runs[created.run_id] = replace(record, snapshot=changed_snapshot.encode())

    with pytest.raises(InvalidValueError):
        _replay(store).execute(created.run_id, created.token)


def test_replay_rejects_an_unknown_engine_revision() -> None:
    season, _, store, _, start, _, _ = _setup()
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    incompatible_inputs = replace(record.replay_inputs, engine_revision="future-engine")
    store.runs[created.run_id] = replace(record, replay_inputs=incompatible_inputs)

    with pytest.raises(InvalidValueError, match="revision"):
        _replay(store).execute(created.run_id, created.token)
