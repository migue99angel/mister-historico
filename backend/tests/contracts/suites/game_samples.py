"""Builders of Game persistence and simulator DTOs shared by the contract suites."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from mister.game.application.ports import (
    BlockSimulationRequest,
    BlockSimulationResult,
    DecisionRecord,
    IdempotencyRecord,
    InjuryOutcome,
    MatchOutcome,
    Priority,
    RunRecord,
    RunStatus,
    SquadMemberState,
    TacticStyle,
    TacticSystem,
)
from mister.shared_kernel.ids import (
    BlockId,
    CompetitionId,
    DilemmaId,
    FixtureId,
    OptionId,
    PlayableSeasonId,
    PlayerId,
    RunId,
)
from mister.shared_kernel.seed import Seed

T0 = datetime(2026, 10, 22, 10, 0, tzinfo=UTC)


def make_decision(sequence: int = 1, *, option: str = "a") -> DecisionRecord:
    return DecisionRecord(
        sequence=sequence,
        block_id=BlockId("b1"),
        dilemma_id=DilemmaId(f"d{sequence:02d}"),
        option_id=OptionId(option),
        decided_at=T0 + timedelta(minutes=sequence),
    )


def make_run_record(
    *, run_number: int = 1, version: int = 0, decisions: int = 0, status: RunStatus | None = None
) -> RunRecord:
    """A run record; `run_number` gives it a stable, distinct id."""
    return RunRecord(
        run_id=RunId(uuid.UUID(int=run_number)),
        playable_season_id=PlayableSeasonId("test-fc-2000-01"),
        seed=Seed(12345),
        run_token_hash=f"hash-of-token-{run_number}",
        version=version,
        status=status or RunStatus.IN_PROGRESS,
        snapshot={"block": version, "morale": {"team": 60}, "squad": ["tfc-01", "tfc-02"]},
        decisions=tuple(make_decision(n) for n in range(1, decisions + 1)),
        created_at=T0,
        updated_at=T0 + timedelta(seconds=version),
    )


def next_version(record: RunRecord, *, extra_decisions: int = 0) -> RunRecord:
    """The record a use case would save after one more step."""
    decisions = record.decisions + tuple(
        make_decision(len(record.decisions) + n) for n in range(1, extra_decisions + 1)
    )
    return replace(
        record,
        version=record.version + 1,
        snapshot={**record.snapshot, "block": record.version + 1},
        decisions=decisions,
        updated_at=record.updated_at + timedelta(seconds=1),
    )


def make_idempotency_record(
    record: RunRecord, key: str = "idem-key-1", *, request_hash: str = "req-1"
) -> IdempotencyRecord:
    return IdempotencyRecord(
        run_id=record.run_id,
        key=key,
        request_hash=request_hash,
        response={"status": 200, "body": {"version": record.version + 1, "ok": True}},
        created_at=T0,
    )


def make_simulation_request(block: str = "b1") -> BlockSimulationRequest:
    return BlockSimulationRequest(
        playable_season_id=PlayableSeasonId("test-fc-2000-01"),
        seed=Seed(7),
        block_id=BlockId(block),
        squad=(
            SquadMemberState(PlayerId("tfc-01"), rating=60, morale=55, fitness=90, available=True),
            SquadMemberState(PlayerId("tfc-02"), rating=62, morale=70, fitness=40, available=False),
        ),
        tactic_style=TacticStyle.BALANCED,
        tactic_system=TacticSystem("4-4-2"),
        competition_priorities={CompetitionId("liga-test"): Priority.NORMAL},
    )


def make_simulation_result(block: str = "b1") -> BlockSimulationResult:
    return BlockSimulationResult(
        block_id=BlockId(block),
        matches=(
            MatchOutcome(
                FixtureId("tfc-liga-01"), CompetitionId("liga-test"), goals_for=2, goals_against=1
            ),
            MatchOutcome(
                FixtureId("tfc-copa-final"),
                CompetitionId("copa-test"),
                goals_for=1,
                goals_against=1,
                extra_time=True,
                penalties_for=4,
                penalties_against=3,
            ),
        ),
        injuries=(InjuryOutcome(PlayerId("tfc-02"), days=14),),
        minutes_played={PlayerId("tfc-01"): 180, PlayerId("tfc-02"): 90},
        league_positions={CompetitionId("liga-test"): 3},
    )
