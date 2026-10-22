"""Use case behind `mister content ratings compute`: keep the stored ratings equal to the formula.

The formula lives in `catalog.domain.ratings`; this module orchestrates it over one club-season
through a `RatingSheetStore` port (ADR-006). The statistics are the input and the ratings the
output: a rating is never written by hand (rubric section 0, rule 4).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from mister.catalog.domain.rating_alerts import RatedPlayer, rating_alerts
from mister.catalog.domain.ratings import (
    ClubContext,
    PlayerStats,
    RatingResult,
    compute_rating,
    override_problem,
)
from mister.shared_kernel.errors import DomainError


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
    """A player as the formula sees him, with the rating currently stored."""

    player_id: str
    display_name: str
    stats: PlayerStats
    stored_rating: int | None
    override_value: int | None
    override_sources: int = 0
    """How many distinct sources back the override."""


@dataclass(frozen=True, slots=True)
class ClubSeasonRatings:
    """Everything needed to rate the players of one club-season."""

    club_season: str
    club: ClubContext
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


@dataclass(frozen=True, slots=True)
class PlayerRatingLine:
    """What the formula says about one player, next to what is stored."""

    player_id: str
    display_name: str
    stored: int | None
    expected: int | None
    result: RatingResult
    override_value: int | None
    problem: str | None
    age: int | None

    @property
    def overridden(self) -> bool:
        return self.override_value is not None

    @property
    def stale(self) -> bool:
        """The stored rating is not the expected one."""
        return self.stored != self.expected

    @property
    def discrepancy(self) -> bool:
        return self.stale or self.problem is not None


@dataclass(frozen=True, slots=True)
class RatingsReport:
    club_season: str
    lines: tuple[PlayerRatingLine, ...]
    alerts: tuple[str, ...]
    written: bool = False

    @property
    def discrepancies(self) -> tuple[PlayerRatingLine, ...]:
        return tuple(line for line in self.lines if line.discrepancy)

    @property
    def problems(self) -> tuple[PlayerRatingLine, ...]:
        """Lines that writing the ratings cannot fix (an override outside its limits)."""
        return tuple(line for line in self.lines if line.problem is not None)


class RatingsTool:
    def __init__(self, store: RatingSheetStore) -> None:
        self._store = store

    def check(self, club_season: str) -> RatingsReport:
        """Compare the stored ratings with the formula; nothing is written."""
        return self._report(self._store.load(club_season))

    def compute(self, club_season: str) -> RatingsReport:
        """Write the expected rating of every player whose stored rating differs."""
        report = self._report(self._store.load(club_season))
        stale = {line.player_id: line.expected for line in report.lines if line.stale}
        if not stale:
            return report
        self._store.save(club_season, stale)
        return RatingsReport(report.club_season, report.lines, report.alerts, written=True)

    def explain(self, club_season: str, player_id: str) -> PlayerRatingLine:
        """The breakdown of one player's rating."""
        for line in self._report(self._store.load(club_season)).lines:
            if line.player_id == player_id:
                return line
        raise PlayerNotInSquadError(club_season, player_id)

    @staticmethod
    def _report(sheet: ClubSeasonRatings) -> RatingsReport:
        lines = tuple(_line(player, sheet.club) for player in sheet.players)
        rated = [
            RatedPlayer(line.player_id, line.expected, line.age)
            for line in lines
            if line.expected is not None
        ]
        return RatingsReport(sheet.club_season, lines, rating_alerts(rated))


def _line(player: PlayerRatingSource, club: ClubContext) -> PlayerRatingLine:
    result = compute_rating(player.stats, club)
    expected = result.rating
    problem: str | None = None
    if player.override_value is not None:
        expected = player.override_value
        if result.rating is None:
            problem = (
                "an override cannot replace a missing statistic; "
                f"statistics are missing: {', '.join(result.missing)}"
            )
        else:
            problem = override_problem(
                result.rating, player.override_value, player.override_sources
            )
    return PlayerRatingLine(
        player_id=player.player_id,
        display_name=player.display_name,
        stored=player.stored_rating,
        expected=expected,
        result=result,
        override_value=player.override_value,
        problem=problem,
        age=player.stats.age,
    )
