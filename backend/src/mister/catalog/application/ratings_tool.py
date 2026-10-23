"""Use case behind `mister content ratings compute`: keep the stored ratings equal to the formula.

The formula lives in `catalog.domain.ratings`; this module orchestrates it over one club-season
through a `RatingSheetStore` port (ADR-006). The statistics are the input and the ratings the
output: a rating is never written by hand (rubric section 0, rule 4).
"""

from dataclasses import dataclass

from mister.catalog.application.ports import (
    ClubSeasonRatings,
    PlayerNotInSquadError,
    PlayerRatingSource,
    RatingSheetStore,
)
from mister.catalog.domain.rating_alerts import RatedPlayer, rating_alerts
from mister.catalog.domain.ratings import RatingResult, compute_rating, override_issue


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

    @property
    def notes(self) -> tuple[str, ...]:
        """Fallbacks used and statistics missing, as the rubric (section 5) asks to report."""
        missing = (f"missing: {', '.join(self.result.missing)}",) if self.result.missing else ()
        return (*self.result.notes, *missing)


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
        lines = tuple(_line(player) for player in sheet.players)
        rated = [
            RatedPlayer(line.player_id, line.expected, line.age)
            for line in lines
            if line.expected is not None
        ]
        warnings = tuple(
            f"{player.player_id}: joined or left in mid-season without available_matches_all"
            for player in sheet.players
            if player.partial_season and player.stats.available_matches_all is None
        )
        return RatingsReport(sheet.club_season, lines, (*rating_alerts(rated), *warnings))


def _line(player: PlayerRatingSource) -> PlayerRatingLine:
    result = compute_rating(player.stats, player.club)
    expected = result.rating
    problem: str | None = None
    if player.override_value is not None:
        expected = player.override_value
        problem = override_issue(result, player.override_value, player.override_sources)
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
