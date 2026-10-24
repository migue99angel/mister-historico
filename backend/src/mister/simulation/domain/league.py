"""Pure P2 league adjustment and ranking; these types are private to simulation."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from itertools import groupby

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.domain.league_types import ExternalResultsRequest, LeagueRow
from mister.simulation.domain.model import Score, Venue

_COUNTERS = ("played", "won", "drawn", "lost", "goals_for", "goals_against", "points")
_DIRECT_CRITERIA = frozenset(
    {
        "head_to_head_points",
        "head_to_head_goal_difference",
        "head_to_head_goals_for",
        "head_to_head_away_goals",
    }
)
_CRITERIA = _DIRECT_CRITERIA | {"goal_difference", "goals_for", "wins"}


def _require_tuple(name: str, value: object, item_type: type[object]) -> None:
    if not isinstance(value, tuple) or not all(isinstance(item, item_type) for item in value):
        raise InvalidValueError(f"{name} must be an immutable tuple of {item_type.__name__}")


def _require_sources(sources: tuple[str, ...]) -> None:
    _require_tuple("sources", sources, str)
    if not sources or any(not source.strip() for source in sources):
        raise InvalidValueError("explicit non-blank historical sources are required")


def _contribution(
    club: ClubSeasonId,
    goals_for: int,
    goals_against: int,
    request: ExternalResultsRequest,
) -> LeagueRow:
    won, drawn, lost = (
        int(goals_for > goals_against),
        int(goals_for == goals_against),
        int(goals_for < goals_against),
    )
    return LeagueRow(
        club,
        1,
        won,
        drawn,
        lost,
        goals_for,
        goals_against,
        won * request.points_per_win + drawn * request.points_per_draw,
    )


def _accumulate(totals: dict[ClubSeasonId, list[int]], contribution: LeagueRow) -> None:
    club = contribution.club_season_id
    totals[club] = [
        total + getattr(contribution, counter)
        for total, counter in zip(totals[club], _COUNTERS, strict=True)
    ]


class HistoricalExternalResults:
    """Project every call from the original cutoff baseline and accumulated replacements."""

    def standings(self, request: ExternalResultsRequest) -> tuple[LeagueRow, ...]:
        historical = {club: [0] * len(_COUNTERS) for club in request.participants}
        simulated = {club: [0] * len(_COUNTERS) for club in request.participants}
        for replacement in request.replacements:
            for home_side, club in ((True, replacement.home), (False, replacement.away)):
                for score, totals in (
                    (replacement.historical_score, historical),
                    (replacement.simulated_score, simulated),
                ):
                    goals_for, goals_against = (
                        (score.home, score.away) if home_side else (score.away, score.home)
                    )
                    _accumulate(totals, _contribution(club, goals_for, goals_against, request))
        residuals = {}
        for baseline in request.historical_rows:
            club = baseline.club_season_id
            residual = [
                getattr(baseline, counter) - amount
                for counter, amount in zip(_COUNTERS, historical[club], strict=True)
            ]
            if any(value < 0 for value in residual):
                raise InvalidValueError("historical contributions exceed the original baseline")
            residuals[club] = residual
        return tuple(
            LeagueRow(
                row.club_season_id,
                *(
                    value + amount
                    for value, amount in zip(
                        residuals[row.club_season_id], simulated[row.club_season_id], strict=True
                    )
                ),
            )
            for row in request.historical_rows
        )


@dataclass(frozen=True, slots=True)
class HeadToHeadFixture:
    """A match in a declared complete calendar through the evidence cutoff."""

    fixture_id: FixtureId
    date: date
    home: ClubSeasonId
    away: ClubSeasonId
    venue: Venue | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.fixture_id, FixtureId) or type(self.date) is not date:
            raise InvalidValueError("a historical fixture needs a FixtureId and a calendar date")
        if not isinstance(self.home, ClubSeasonId) or not isinstance(self.away, ClubSeasonId):
            raise InvalidValueError("historical sides must be ClubSeasonIds")
        if self.venue is not None and (not isinstance(self.venue, Venue) or self.venue is Venue.AWAY):
            raise InvalidValueError("a direct fixture venue must be HOME, NEUTRAL or None")
        if self.home == self.away:
            raise InvalidValueError("a historical fixture must have different sides")


@dataclass(frozen=True, slots=True)
class HeadToHeadResult:
    """A sourced historical regulation score, with explicit fixture identity and sides."""

    fixture_id: FixtureId
    date: date
    home: ClubSeasonId
    away: ClubSeasonId
    score: Score
    sources: tuple[str, ...]

    def __post_init__(self) -> None:
        HeadToHeadFixture(self.fixture_id, self.date, self.home, self.away)
        if not isinstance(self.score, Score):
            raise InvalidValueError("a historical result requires a Score")
        _require_sources(self.sources)


@dataclass(frozen=True, slots=True)
class HeadToHeadEvidence:
    """Declared complete history between covered clubs through an inclusive cutoff.

    `schedule=()` declares that there were no such matches; absent evidence is unknown.
    Sources support the calendar's declared completeness. Validation checks internal
    consistency, but cannot prove that a source did not omit a match. No future legs
    or a particular number of home/away fixtures are inferred.
    """

    competition_id: CompetitionId
    as_of: date
    covered_clubs: tuple[ClubSeasonId, ...]
    schedule: tuple[HeadToHeadFixture, ...]
    results: tuple[HeadToHeadResult, ...]
    sources: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.competition_id, CompetitionId) or type(self.as_of) is not date:
            raise InvalidValueError("head-to-head history needs a competition and calendar cutoff")
        _require_tuple("covered_clubs", self.covered_clubs, ClubSeasonId)
        _require_tuple("schedule", self.schedule, HeadToHeadFixture)
        _require_tuple("results", self.results, HeadToHeadResult)
        _require_sources(self.sources)
        if not self.covered_clubs or len(set(self.covered_clubs)) != len(self.covered_clubs):
            raise InvalidValueError("head-to-head coverage must contain distinct clubs")
        fixtures = {fixture.fixture_id: fixture for fixture in self.schedule}
        results = {result.fixture_id: result for result in self.results}
        if len(fixtures) != len(self.schedule) or len(results) != len(self.results):
            raise InvalidValueError("historical fixtures and results must have unique IDs")
        if fixtures.keys() != results.keys():
            raise InvalidValueError(
                "every declared fixture must have exactly one historical result"
            )
        for fixture in self.schedule:
            if fixture.date > self.as_of:
                raise InvalidValueError("historical fixtures cannot be later than the cutoff")
            if fixture.home not in self.covered_clubs or fixture.away not in self.covered_clubs:
                raise InvalidValueError("historical fixtures must be between covered clubs")
            result = results[fixture.fixture_id]
            if (result.date, result.home, result.away) != (
                fixture.date,
                fixture.home,
                fixture.away,
            ):
                raise InvalidValueError("historical result date and sides must match its fixture")


@dataclass(frozen=True, slots=True)
class LeagueTable:
    """Rank adjusted totals, preserving unresolved sporting ties explicitly.

    P2 final historical order applies to original points groups containing rivals only.
    A points group containing the managed club uses configured criteria for every
    subgroup. Direct criteria always use that original group's entire mini-league.
    Stable ID order inside an unresolved group is presentation order, not a tiebreaker.
    """

    request: ExternalResultsRequest
    adjusted_rows: tuple[LeagueRow, ...]
    tiebreakers: tuple[str, ...]
    historical_final_order: tuple[ClubSeasonId, ...]
    head_to_head: HeadToHeadEvidence | None = None
    rows: tuple[LeagueRow, ...] = field(init=False)
    unresolved_groups: tuple[tuple[ClubSeasonId, ...], ...] = field(init=False)

    def __post_init__(self) -> None:
        self._validate_inputs()
        ordered: list[LeagueRow] = []
        unresolved: list[tuple[ClubSeasonId, ...]] = []
        for _, point_rows in groupby(
            sorted(self.adjusted_rows, key=lambda row: row.points, reverse=True),
            key=lambda row: row.points,
        ):
            group = tuple(point_rows)
            groups = self._rank_points_group(group)
            for subgroup in groups:
                ordered.extend(subgroup)
                if len(subgroup) > 1:
                    unresolved.append(tuple(row.club_season_id for row in subgroup))
        object.__setattr__(self, "rows", tuple(ordered))
        object.__setattr__(self, "unresolved_groups", tuple(unresolved))

    def _validate_inputs(self) -> None:
        _require_tuple("adjusted_rows", self.adjusted_rows, LeagueRow)
        _require_tuple("tiebreakers", self.tiebreakers, str)
        _require_tuple("historical_final_order", self.historical_final_order, ClubSeasonId)
        participants = set(self.request.participants)
        for name, clubs in (
            ("adjusted rows", tuple(row.club_season_id for row in self.adjusted_rows)),
            ("historical final order", self.historical_final_order),
        ):
            if len(clubs) != len(set(clubs)) or set(clubs) != participants:
                raise InvalidValueError(f"{name} must cover all participants exactly once")
        if len(set(self.tiebreakers)) != len(self.tiebreakers) or any(
            criterion not in _CRITERIA for criterion in self.tiebreakers
        ):
            raise InvalidValueError("tiebreakers must be distinct supported criteria")
        if any(
            row.points
            != row.won * self.request.points_per_win + row.drawn * self.request.points_per_draw
            for row in self.adjusted_rows
        ):
            raise InvalidValueError("adjusted points must match configured scoring rules")
        if self.head_to_head is not None and (
            not isinstance(self.head_to_head, HeadToHeadEvidence)
            or self.head_to_head.competition_id != self.request.competition_id
            or self.head_to_head.as_of != self.request.as_of
            or not set(self.head_to_head.covered_clubs) <= participants
        ):
            raise InvalidValueError("head-to-head evidence must match the requested league cutoff")

    def _rank_points_group(
        self, original: tuple[LeagueRow, ...], *, require_venue: bool = False
    ) -> tuple[tuple[LeagueRow, ...], ...]:
        if self.request.managed_club_season_id not in {row.club_season_id for row in original}:
            positions = {club: index for index, club in enumerate(self.historical_final_order)}
            return tuple(
                (row,) for row in sorted(original, key=lambda row: positions[row.club_season_id])
            )
        groups: tuple[tuple[LeagueRow, ...], ...] = (original,)
        for criterion in self.tiebreakers:
            if all(len(group) == 1 for group in groups):
                break
            key = self._criterion_key(criterion, original)
            groups = tuple(
                tuple(equal_rows)
                for group in groups
                for _, equal_rows in groupby(sorted(group, key=key, reverse=True), key=key)
            )
        return tuple(
            tuple(sorted(group, key=lambda row: str(row.club_season_id))) for group in groups
        )

    def _criterion_key(
        self, criterion: str, original: tuple[LeagueRow, ...]
    ) -> Callable[[LeagueRow], int]:
        if criterion in _DIRECT_CRITERIA:
            mini_league, away_goals = self._mini_league(
                original, require_venue=criterion == "head_to_head_away_goals"
            )

            def direct_key(row: LeagueRow) -> int:
                mini = mini_league[row.club_season_id]
                if criterion == "head_to_head_points":
                    return mini.points
                if criterion == "head_to_head_goal_difference":
                    return mini.goals_for - mini.goals_against
                if criterion == "head_to_head_goals_for":
                    return mini.goals_for
                return away_goals[row.club_season_id]

            return direct_key
        if criterion == "goal_difference":
            return lambda row: row.goals_for - row.goals_against
        if criterion == "goals_for":
            return lambda row: row.goals_for
        return lambda row: row.won

    def _mini_league(
        self, original: tuple[LeagueRow, ...], *, require_venue: bool = False
    ) -> tuple[dict[ClubSeasonId, LeagueRow], dict[ClubSeasonId, int]]:
        clubs = {row.club_season_id for row in original}
        evidence = self.head_to_head
        if evidence is None or not clubs <= set(evidence.covered_clubs):
            raise InvalidValueError("head-to-head evidence must cover the original points group")
        totals = {club: [0] * len(_COUNTERS) for club in clubs}
        away_goals = dict.fromkeys(clubs, 0)
        replacements = {
            result.fixture_id: result
            for result in self.request.replacements
            if result.home in clubs and result.away in clubs
        }
        results = {
            result.fixture_id: result
            for result in evidence.results
            if result.home in clubs and result.away in clubs
        }
        for replacement in replacements.values():
            historical = results.get(replacement.fixture_id)
            if historical is None or (
                historical.date,
                historical.home,
                historical.away,
                historical.score,
            ) != (
                replacement.date,
                replacement.home,
                replacement.away,
                replacement.historical_score,
            ):
                raise InvalidValueError("managed replacement must match its historical fixture")
        calendar = {fixture.fixture_id: fixture for fixture in evidence.schedule}
        for result in results.values():
            venue = calendar[result.fixture_id].venue
            if require_venue and venue is None:
                raise InvalidValueError(
                    "away-goal criteria require a known venue for the original mini-league"
                )
            score = result.score
            if self.request.managed_club_season_id in (result.home, result.away):
                managed_replacement = replacements.get(result.fixture_id)
                if managed_replacement is None:
                    raise InvalidValueError("a managed historical fixture needs its replacement")
                score = managed_replacement.simulated_score
            for club, goals_for, goals_against in (
                (result.home, score.home, score.away),
                (result.away, score.away, score.home),
            ):
                _accumulate(totals, _contribution(club, goals_for, goals_against, self.request))
            if venue is Venue.HOME:
                away_goals[result.away] += score.away
        return {club: LeagueRow(club, *values) for club, values in totals.items()}, away_goals
