"""Game-owned model of the immutable season inputs needed to start and close a run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mister.game.domain.run import BlockDefinition, DecisionOption, DilemmaDefinition

if TYPE_CHECKING:
    from datetime import date

    from mister.game.application.run_content import RunContentSnapshot
    from mister.game.domain.board import GoalDefinition
    from mister.game.domain.effects import Effect
    from mister.game.domain.state import PlayerState, RunState
    from mister.shared_kernel.ids import (
        BlockId,
        ClubSeasonId,
        CompetitionId,
        DilemmaId,
        OptionId,
        PlayableSeasonId,
    )


@dataclass(frozen=True, slots=True)
class CapturedOption:
    id: OptionId
    effects: tuple[Effect, ...]


@dataclass(frozen=True, slots=True)
class CapturedDilemma:
    id: DilemmaId
    block_id: BlockId
    historical_option: OptionId
    options: tuple[CapturedOption, ...]

    def definition(self) -> DilemmaDefinition:
        return DilemmaDefinition(
            self.id, tuple(DecisionOption(option.id) for option in self.options)
        )


@dataclass(frozen=True, slots=True)
class CapturedBlock:
    id: BlockId
    start: date
    end: date
    dilemmas: tuple[CapturedDilemma, ...]


@dataclass(frozen=True, slots=True)
class CompetitionMetadata:
    id: CompetitionId
    kind: str
    tier: str
    participants: tuple[ClubSeasonId, ...]
    stages: tuple[StageMetadata, ...]


@dataclass(frozen=True, slots=True)
class StageMetadata:
    id: str
    round: str
    legs: int
    away_goals_rule: bool
    extra_time: bool
    penalties: bool
    groups: tuple[tuple[str, tuple[ClubSeasonId, ...]], ...]
    advance_per_group: int | None


@dataclass(frozen=True, slots=True)
class CapturedRealResult:
    goals_for: int
    goals_against: int
    extra_time: bool
    penalties_for: int | None
    penalties_against: int | None


@dataclass(frozen=True, slots=True)
class FixtureMetadata:
    id: str
    date: date
    competition_id: CompetitionId
    opponent: ClubSeasonId
    venue: str
    round: int | None
    stage_id: str | None
    group_id: str | None
    leg: int | None
    key: bool
    real_result: CapturedRealResult | None


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeMetadata:
    competition_id: CompetitionId
    champion: bool
    final_position: int | None
    eliminated_in: str | None


@dataclass(frozen=True, slots=True)
class StandingRowMetadata:
    club_season_id: ClubSeasonId
    position: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    points: int


@dataclass(frozen=True, slots=True)
class StandingCutoffMetadata:
    competition_id: CompetitionId
    date: date
    stage_id: str | None
    group_id: str | None
    rows: tuple[StandingRowMetadata, ...]


@dataclass(frozen=True, slots=True)
class CapturedSeason:
    """Complete Game-owned inputs, with no Catalog DTO references."""

    snapshot: RunContentSnapshot
    playable_season_id: PlayableSeasonId
    managed_club_season_id: ClubSeasonId
    season_label: str
    initial_state: RunState
    blocks: tuple[CapturedBlock, ...]
    competitions: tuple[CompetitionMetadata, ...]
    goals: tuple[GoalDefinition, ...]
    fixtures: tuple[FixtureMetadata, ...]
    historical_outcomes: tuple[HistoricalOutcomeMetadata, ...]
    standings: tuple[StandingCutoffMetadata, ...]

    @property
    def run_blocks(self) -> tuple[BlockDefinition, ...]:
        """Domain block definitions used to construct Run."""
        return tuple(
            BlockDefinition(block.id, tuple(item.definition() for item in block.dilemmas))
            for block in self.blocks
        )

    @property
    def players(self) -> tuple[PlayerState, ...]:
        """All known players, including market and rival players."""
        return self.initial_state.players
