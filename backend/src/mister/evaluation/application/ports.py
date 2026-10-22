"""Application ports of the Evaluation context.

Evaluation compares a finished run with what really happened, so it needs the real history of
the season. `HistoricalOutcomeProvider` is its own port with its own DTOs: the adapter in
`evaluation/infrastructure` translates from the Catalog published language
(`catalog.application.api`), which keeps the context free of Catalog types (ACL).

Deliberately minimal. Persisting the evaluation result is left to T5.1/T5.5, which own the
`MisterScore` and `Verdict` model it would store; adding that port is a contract change.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import CompetitionId, PlayableSeasonId


class HistoricalOutcomeNotFoundError(DomainError):
    """There is no real history for that season (API: `404 season_not_found`)."""

    code = "season_not_found"

    def __init__(self, season_id: PlayableSeasonId) -> None:
        super().__init__(f"no historical outcome for season {season_id}")
        self.season_id = season_id


class CompetitionKind(StrEnum):
    LEAGUE = "league"
    CUP = "cup"
    SUPER_CUP = "super_cup"
    CONTINENTAL_CUP = "continental_cup"


class CompetitionTier(StrEnum):
    """Weight class of a competition, which T5.1 uses to weigh titles."""

    DOMESTIC_LEAGUE = "domestic_league"
    DOMESTIC_CUP = "domestic_cup"
    DOMESTIC_SUPER_CUP = "domestic_super_cup"
    CONTINENTAL_PRIMARY = "continental_primary"
    CONTINENTAL_SECONDARY = "continental_secondary"


class ObjectiveKind(StrEnum):
    WIN = "win"
    FINISH_TOP = "finish_top"
    REACH_STAGE = "reach_stage"


@dataclass(frozen=True, slots=True)
class CompetitionHistory:
    """What really happened in one competition.

    A league has `final_position`; a knockout competition has `champion` or an elimination
    stage, given by its id and its display name together.
    """

    competition_id: CompetitionId
    competition_name: str
    kind: CompetitionKind
    tier: CompetitionTier
    champion: bool
    final_position: int | None = None
    eliminated_in_stage_id: str | None = None
    eliminated_in_stage_name: str | None = None

    def __post_init__(self) -> None:
        if (self.eliminated_in_stage_id is None) != (self.eliminated_in_stage_name is None):
            raise InvalidValueError("the elimination stage needs both an id and a name")
        if self.champion and self.eliminated_in_stage_id is not None:
            raise InvalidValueError("a champion cannot have been eliminated")


@dataclass(frozen=True, slots=True)
class BoardObjectiveSpec:
    """What the board expects in a competition (an input of the Mister score)."""

    id: str
    competition_id: CompetitionId
    kind: ObjectiveKind
    text: str
    target_position: int | None = None
    target_stage: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalSeasonOutcome:
    """The real history of a playable season: its manager and its competitions."""

    season_id: PlayableSeasonId
    club_name: str
    manager_display_name: str
    manager_alias_name: str
    competitions: tuple[CompetitionHistory, ...]
    board_objectives: tuple[BoardObjectiveSpec, ...]


class HistoricalOutcomeProvider(Protocol):
    """Read access to the real history of a season."""

    def get_historical_outcome(self, season_id: PlayableSeasonId) -> HistoricalSeasonOutcome:
        """The outcome; raises `HistoricalOutcomeNotFoundError` if the season is unknown."""
        ...
