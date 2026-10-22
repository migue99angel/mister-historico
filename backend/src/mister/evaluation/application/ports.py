"""Application ports of the Evaluation context.

Evaluation compares a finished run with what really happened, so it needs the real history of
the season. `HistoricalOutcomeProvider` is its own port with its own DTOs: the adapter in
`evaluation/infrastructure` translates from the Catalog published language
(`catalog.application.api`), which keeps the context free of Catalog types (ACL).

Deliberately minimal. Persisting the evaluation result is left to T5.1/T5.5, which own the
`MisterScore` and `Verdict` model it would store; adding that port is a contract change.
"""

from dataclasses import dataclass
from typing import Protocol

from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import CompetitionId, PlayableSeasonId


class HistoricalOutcomeNotFoundError(DomainError):
    """There is no real history for that season (API: `404 season_not_found`)."""

    code = "season_not_found"

    def __init__(self, season_id: PlayableSeasonId) -> None:
        super().__init__(f"no historical outcome for season {season_id}")
        self.season_id = season_id


@dataclass(frozen=True, slots=True)
class CompetitionHistory:
    """What really happened in one competition.

    `kind` is the content kind (`league`, `cup`, `super_cup`, `continental_cup`). A league has
    `final_position`; a knockout competition has `champion` or `eliminated_in_stage_name`.
    """

    competition_id: CompetitionId
    competition_name: str
    kind: str
    champion: bool
    final_position: int | None = None
    eliminated_in_stage_name: str | None = None

    def __post_init__(self) -> None:
        if self.champion and self.eliminated_in_stage_name is not None:
            raise InvalidValueError("a champion cannot have been eliminated")


@dataclass(frozen=True, slots=True)
class HistoricalSeasonOutcome:
    """The real history of a playable season: its manager and its competitions."""

    season_id: PlayableSeasonId
    club_name: str
    manager_display_name: str
    manager_alias_name: str
    competitions: tuple[CompetitionHistory, ...]


class HistoricalOutcomeProvider(Protocol):
    """Read access to the real history of a season."""

    def get_historical_outcome(self, season_id: PlayableSeasonId) -> HistoricalSeasonOutcome:
        """The outcome; raises `HistoricalOutcomeNotFoundError` if the season is unknown."""
        ...
