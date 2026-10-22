"""Builders of Game persistence and simulator DTOs shared by the contract suites."""

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

from mister.game.application.ports import (
    BlockEvent,
    BlockSimulationRequest,
    BlockSimulationResult,
    DecisionRecord,
    EventKind,
    ForcedInjury,
    IdempotencyRecord,
    InjuryOutcome,
    MatchOutcome,
    PlayerOutcome,
    Position,
    Priority,
    RunRecord,
    RunStatus,
    ScoreLine,
    Side,
    SquadPlayerState,
    StandingRow,
    Standings,
    TacticSetup,
    TacticStyle,
    TacticSystem,
    TeamSquad,
    TeamVenue,
    UserResult,
)
from mister.shared_kernel.ids import (
    BlockId,
    ClubSeasonId,
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


BLOCK_START = date(2000, 8, 1)
BLOCK_END = date(2000, 9, 30)


def make_simulation_request(block: str = "b1") -> BlockSimulationRequest:
    own = ClubSeasonId("test-fc-2000-01")
    rival = ClubSeasonId("sample-united-2000-01")
    tactic = TacticSetup(TacticStyle.BALANCED, TacticSystem("4-4-2"))
    return BlockSimulationRequest(
        playable_season_id=PlayableSeasonId("test-fc-2000-01"),
        seed=Seed(7),
        block_id=BlockId(block),
        start=BLOCK_START,
        end=BLOCK_END,
        managed_team=TeamSquad(
            own,
            (
                SquadPlayerState(PlayerId("tfc-01"), Position.GK, 60, 25, 55, 90),
                SquadPlayerState(
                    PlayerId("tfc-02"),
                    Position.DF,
                    62,
                    None,
                    70,
                    40,
                    injured_until=date(2000, 9, 15),
                    youth_minutes=True,
                ),
            ),
            tactic,
        ),
        team_morale=58,
        team_overrides=(
            TeamSquad(
                rival,
                (SquadPlayerState(PlayerId("sam-01"), Position.FW, 70, 28, 50, 100),),
                TacticSetup(TacticStyle.COUNTER, TacticSystem("4-3-3")),
            ),
        ),
        competition_priorities={
            CompetitionId("liga-test"): Priority.NORMAL,
            CompetitionId("copa-test"): Priority.HIGH,
        },
        forced_injuries_from_effects=(ForcedInjury(PlayerId("tfc-01"), date(2000, 9, 20), 10),),
        prior_results=(),
    )


def make_simulation_result(block: str = "b1") -> BlockSimulationResult:
    """A result that is consistent with `make_simulation_request`."""
    own = ClubSeasonId("test-fc-2000-01")
    rival = ClubSeasonId("sample-united-2000-01")
    liga, copa = CompetitionId("liga-test"), CompetitionId("copa-test")
    return BlockSimulationResult(
        block_id=BlockId(block),
        matches=(
            MatchOutcome(
                fixture_id=FixtureId("tfc-liga-01"),
                competition_id=liga,
                date=date(2000, 9, 2),
                home=own,
                away=rival,
                regulation=ScoreLine(2, 1),
                venue=TeamVenue.HOME,
                opponent=rival,
                user_result=UserResult.WIN,
                winner=Side.HOME,
                round=1,
            ),
            MatchOutcome(
                fixture_id=FixtureId("tfc-copa-final"),
                competition_id=copa,
                date=date(2000, 9, 28),
                home=rival,
                away=own,
                regulation=ScoreLine(1, 1),
                venue=TeamVenue.NEUTRAL,
                opponent=rival,
                user_result=UserResult.WIN,
                extra_time=ScoreLine(0, 0),
                penalties=ScoreLine(3, 4),
                winner=Side.AWAY,
                key=True,
                stage_id="final",
                leg=None,
            ),
        ),
        key_matches=(FixtureId("tfc-copa-final"),),
        standings=(
            Standings(
                competition_id=liga,
                as_of=BLOCK_END,
                rows=(
                    StandingRow(own, 1, 1, 1, 0, 0, 2, 1, 3),
                    StandingRow(rival, 2, 1, 0, 0, 1, 1, 2, 0),
                ),
            ),
            Standings(
                competition_id=copa,
                as_of=BLOCK_END,
                stage_id="groups",
                group_id="a",
                rows=(StandingRow(own, 1, 1, 1, 0, 0, 1, 0, 3),),
            ),
        ),
        events=(
            BlockEvent(EventKind.CHAMPION, date(2000, 9, 28), own, copa, "final"),
            BlockEvent(EventKind.ADVANCED, date(2000, 9, 20), own, copa, "semifinal"),
            BlockEvent(EventKind.ELIMINATED, date(2000, 9, 21), rival, copa),
        ),
        injuries=(
            InjuryOutcome(PlayerId("tfc-02"), date(2000, 9, 10), 14),
            InjuryOutcome(PlayerId("tfc-01"), date(2000, 9, 20), 10, forced=True),
        ),
        player_states=(
            PlayerOutcome(PlayerId("tfc-01"), fitness=80, minutes_played=180),
            PlayerOutcome(
                PlayerId("tfc-02"), fitness=35, injured_until=date(2000, 9, 24), minutes_played=45
            ),
        ),
    )
