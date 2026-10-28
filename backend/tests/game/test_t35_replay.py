"""A run can be verified from its immutable replay inputs without side effects."""

from dataclasses import replace

import pytest
from tests.game.test_t35_use_cases import _setup

from mister.game.application.use_cases import RunAccessDeniedError, RunSnapshot
from mister.game.application.replay import ReplayResult, ReplayRun
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.run_repository import InMemoryUnitOfWork
from mister.game.infrastructure.security.run_tokens import Sha256RunTokenHasher
from mister.game.application.ports import RunNotFoundError
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import RunId


class _UnusedSimulator:
    def simulate_block(self, request: object) -> object:
        raise AssertionError("an open block must not be simulated during replay")


def _replay(store: object) -> ReplayRun:
    return ReplayRun(
        uow=InMemoryUnitOfWork(store),  # type: ignore[arg-type]
        token_hasher=Sha256RunTokenHasher(),
        restore_game=CatalogRunContentAdapter.restore_game,
        simulator=_UnusedSimulator(),  # type: ignore[arg-type]
    )


def test_replay_reconstructs_an_open_run_without_simulating_or_writing() -> None:
    season, provider, store, events, start, _, _ = _setup()
    created = start.execute(season.id)
    persisted = store.runs[created.run_id]
    replies_before = dict(store.replies)
    events_before = tuple(events)
    provider.get_playable_season = lambda _season_id: (_ for _ in ()).throw(
        AssertionError("replay must use the captured season")
    )  # type: ignore[method-assign]

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
