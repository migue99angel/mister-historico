"""Private immutable inputs and accumulated rows for pure league strategies.

These values carry no current or final ranking. Historical rows keep their original cutoff
order; LeagueTable receives the evidenced final historical order separately for P2 ties.
"""

from dataclasses import dataclass
from datetime import date

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.domain.model import Score

_MIN_PARTICIPANTS = 2


def _require_non_negative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidValueError(f"{name} must be a non-negative integer")


def _require_tuple(name: str, value: object, item_type: type[object]) -> None:
    if not isinstance(value, tuple) or not all(isinstance(item, item_type) for item in value):
        raise InvalidValueError(f"{name} must be an immutable tuple of {item_type.__name__}")


@dataclass(frozen=True, slots=True)
class LeagueRow:
    """Accumulated league totals, without a calculated or historical position."""

    club_season_id: ClubSeasonId
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    points: int

    def __post_init__(self) -> None:
        if not isinstance(self.club_season_id, ClubSeasonId):
            raise InvalidValueError("a league row needs a ClubSeasonId")
        for name in ("played", "won", "drawn", "lost", "goals_for", "goals_against", "points"):
            _require_non_negative_integer(name, getattr(self, name))
        if self.played != self.won + self.drawn + self.lost:
            raise InvalidValueError("played must equal won + drawn + lost")


@dataclass(frozen=True, slots=True)
class ResultReplacement:
    """One managed fixture's original and simulated regulation scores, home side first.

    The caller selects fixtures of the requested competition only. A missing historical or
    simulated result cannot be represented by zero goals or an omitted replacement.
    """

    fixture_id: FixtureId
    date: date
    home: ClubSeasonId
    away: ClubSeasonId
    historical_score: Score
    simulated_score: Score

    def __post_init__(self) -> None:
        if not isinstance(self.fixture_id, FixtureId) or type(self.date) is not date:
            raise InvalidValueError("a replacement needs a FixtureId and a calendar date")
        if not isinstance(self.home, ClubSeasonId) or not isinstance(self.away, ClubSeasonId):
            raise InvalidValueError("replacement sides must be ClubSeasonIds")
        if self.home == self.away:
            raise InvalidValueError("a team cannot play itself")
        if not isinstance(self.historical_score, Score) or not isinstance(
            self.simulated_score, Score
        ):
            raise InvalidValueError("a replacement needs both historical and simulated scores")


@dataclass(frozen=True, slots=True)
class ExternalResultsRequest:
    """Original cutoff baseline plus ALL managed results accumulated through that cutoff.

    Every call starts from the original historical rows, never a previously adjusted table.
    Rows retain their original cutoff order and cover every participant exactly once. The
    caller must supply every managed fixture through `as_of` with both scores, selecting
    only this competition. Without a calendar this value cannot detect omitted fixtures or
    establish that an otherwise plausible table really is the original baseline.
    """

    competition_id: CompetitionId
    as_of: date
    managed_club_season_id: ClubSeasonId
    participants: tuple[ClubSeasonId, ...]
    points_per_win: int
    points_per_draw: int
    historical_rows: tuple[LeagueRow, ...]
    replacements: tuple[ResultReplacement, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.competition_id, CompetitionId) or type(self.as_of) is not date:
            raise InvalidValueError("a results request needs a CompetitionId and a calendar cutoff")
        if not isinstance(self.managed_club_season_id, ClubSeasonId):
            raise InvalidValueError("the managed team must be a ClubSeasonId")
        _require_non_negative_integer("points_per_win", self.points_per_win)
        _require_non_negative_integer("points_per_draw", self.points_per_draw)
        _require_tuple("participants", self.participants, ClubSeasonId)
        _require_tuple("historical_rows", self.historical_rows, LeagueRow)
        _require_tuple("replacements", self.replacements, ResultReplacement)
        self._validate_participants()
        self._validate_rows()
        self._validate_replacements()

    def _validate_participants(self) -> None:
        if (
            len(self.participants) < _MIN_PARTICIPANTS
            or len(set(self.participants)) != len(self.participants)
            or self.managed_club_season_id not in self.participants
        ):
            raise InvalidValueError(
                "a league needs distinct participants including the managed team"
            )

    def _validate_rows(self) -> None:
        clubs = tuple(row.club_season_id for row in self.historical_rows)
        if len(clubs) != len(set(clubs)) or set(clubs) != set(self.participants):
            raise InvalidValueError("historical rows must cover every participant exactly once")
        if any(
            row.points != row.won * self.points_per_win + row.drawn * self.points_per_draw
            for row in self.historical_rows
        ):
            raise InvalidValueError("historical points must match the competition's point rules")

    def _validate_replacements(self) -> None:
        fixtures = tuple(result.fixture_id for result in self.replacements)
        if len(fixtures) != len(set(fixtures)):
            raise InvalidValueError("a fixture can be replaced only once")
        for result in self.replacements:
            if result.date > self.as_of:
                raise InvalidValueError("a replacement cannot be later than the cutoff")
            if result.home not in self.participants or result.away not in self.participants:
                raise InvalidValueError("both replacement sides must participate in this league")
            if self.managed_club_season_id not in (result.home, result.away):
                raise InvalidValueError("every replacement must involve the managed team")
