"""Application ports of the Catalog context.

`SeasonContentProvider` is the Catalog's outbound-facing port for other contexts. It is defined
next to the DTOs of the published language (`api.py`) because consumers import both from there;
it is re-exported here so that every context finds its ports in `application/ports.py`.

`RatingSheetStore` is the port of the ratings tool (ADR-006): it reads the statistics of a
club-season and saves the ratings computed from them.

`ContentValidator` validates the content root bound to its adapter, returning accumulated
application diagnostics and exposing operational failures separately.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from mister.catalog.application.api import SeasonContentProvider
from mister.catalog.application.validation_types import (
    ContentValidationReport,
    ContentValidationUnavailableError,
    ValidationIssue,
)
from mister.catalog.domain.ratings import ClubContext, PlayerStats
from mister.shared_kernel.errors import DomainError

__all__ = [
    "ClubSeasonRatings",
    "ClubSeasonRatingsUnavailableError",
    "ContentValidationReport",
    "ContentValidationUnavailableError",
    "ContentValidator",
    "PlayerNotInSquadError",
    "PlayerRatingSource",
    "RatingSheetStore",
    "SeasonContentProvider",
    "ValidationIssue",
]


class ClubSeasonRatingsUnavailableError(DomainError):
    """The club-season cannot be rated: it does not exist, has no squad or is invalid."""

    code = "club_season_ratings_unavailable"


class PlayerNotInSquadError(DomainError):
    """The player is not in the squad of the club-season."""

    code = "player_not_in_squad"

    def __init__(self, club_season: str, player_id: str) -> None:
        super().__init__(f"{player_id} is not in the squad of {club_season}")
        self.club_season = club_season
        self.player_id = player_id


@dataclass(frozen=True, slots=True)
class PlayerRatingSource:
    """A player as the formula sees him, with the club data of his own club and his stored rating.

    In a club squad every player shares the club of the squad; in a market squad each player
    carries the data of his real club.
    """

    player_id: str
    display_name: str
    stats: PlayerStats
    club: ClubContext
    stored_rating: int | None
    override_value: int | None
    override_sources: int = 0
    """How many distinct sources back the override."""
    partial_season: bool = False
    """The player joined or left in mid-season (`joined_on` or `left_on`)."""


@dataclass(frozen=True, slots=True)
class ClubSeasonRatings:
    """Everything needed to rate the players of one club-season (or of the market)."""

    club_season: str
    players: tuple[PlayerRatingSource, ...]


class RatingSheetStore(Protocol):
    """Reads the rating inputs of a club-season and saves the computed ratings."""

    def load(self, club_season: str) -> ClubSeasonRatings:
        """Raises `ClubSeasonRatingsUnavailableError` if the club-season cannot be rated."""
        ...

    def save(self, club_season: str, ratings: Mapping[str, int | None]) -> None:
        """Store the rating of each listed player; `None` leaves him unrated and pending.

        Raises `PlayerNotInSquadError` for a player that is not in the squad.
        """
        ...


class ContentValidator(Protocol):
    """Validates an adapter-bound content root without publishing infrastructure types."""

    def validate(self, *, release: bool) -> ContentValidationReport:
        """Return all content issues; release adds the existing stricter content rules.

        Repeated calls over unchanged content and the same mode return equal reports.
        A valid empty tree has zero seasons; invalid content has an unknown count.
        Raises `ContentValidationUnavailableError` for operational reading failures.
        """
        ...
