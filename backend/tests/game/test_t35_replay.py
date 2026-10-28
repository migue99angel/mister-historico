"""A run can be verified from its immutable replay inputs without side effects."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from tests.game.test_t35_use_cases import _setup

from mister.catalog.application.api import PlayableSeasonDTO
from mister.game.application import ports
from mister.game.application.closure import advance_snapshot
from mister.game.application.ports import (
    BlockSimulationRequest,
    BlockSimulationResult,
    PlayerOutcome,
    RunNotFoundError,
)
from mister.game.application.replay import ReplayResult, ReplayRun
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import RunAccessDeniedError, RunSnapshot
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import (
    InMemoryRunStore,
    InMemoryUnitOfWork,
)
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId, RunId
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


def test_replay_closed_test_fc_run_with_the_real_simulation_engine() -> None:
    season, _, store, _, start, _, take = _setup()
    created = start.execute(season.id)
    rules = RulesConfiguration.a_profile()
    record = store.runs[created.run_id]
    captured = CatalogRunContentAdapter.restore_game(record.replay_inputs.content, rules)
    simulator = SimulationServiceAdapter(SimulationService())
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
        current = store.runs[created.run_id]
        closed, _events = advance_snapshot(
            RunSnapshot.decode(current.snapshot),
            captured,
            simulator,
            rules,
            datetime(2026, 10, 28, tzinfo=UTC),
        )
        persisted = replace(
            current,
            snapshot=closed.encode(),
            status=ports.RunStatus(closed.run.status.value),
            version=current.version + 1,
        )
        store.runs[created.run_id] = persisted
        if closed.run.status.value != "in_progress":
            break

    persisted = store.runs[created.run_id]
    assert len(RunSnapshot.decode(persisted.snapshot).run.block_records) == len(captured.blocks)

    result = _replay(store, simulator).execute(created.run_id, created.token)

    assert result.reconstructed == RunSnapshot.decode(persisted.snapshot)
    assert result.reconstructed.run.status.value == "finished"
    assert len(result.reconstructed.run.block_records) == len(captured.blocks)
    assert store.runs[created.run_id] == persisted


def test_replay_reconstructs_a_sacked_terminal_prefix() -> None:
    base_rules = RulesConfiguration.a_profile()
    rules = replace(base_rules, board=replace(base_rules.board, sacking_threshold=100))
    season, _, store, _, start, _, take = _setup(rules)
    created = start.execute(season.id)
    record = store.runs[created.run_id]
    captured = CatalogRunContentAdapter.restore_game(record.replay_inputs.content, rules)
    for index, dilemma in enumerate(captured.blocks[0].dilemmas):
        take.execute(
            created.run_id,
            created.token,
            f"sack-choice-{index:04d}",
            store.runs[created.run_id].version,
            dilemma.id,
            dilemma.options[0].id,
        )

    record = store.runs[created.run_id]
    simulator = _OutcomeSimulator()
    terminal, _events = advance_snapshot(
        RunSnapshot.decode(record.snapshot),
        captured,
        simulator,
        rules,
        datetime(2026, 10, 28, tzinfo=UTC),
    )
    assert terminal.run.status.value == "sacked"
    persisted = replace(
        record,
        snapshot=terminal.encode(),
        status=ports.RunStatus(terminal.run.status.value),
        version=record.version + 1,
    )
    store.runs[created.run_id] = persisted

    result = _replay(store, simulator).execute(created.run_id, created.token)

    assert result.reconstructed == terminal
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
