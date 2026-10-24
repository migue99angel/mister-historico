"""Four-club group ranking with explicit match evidence and unresolved residual ties."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import chain, groupby
from typing import TYPE_CHECKING

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.domain.league_types import LeagueRow
from mister.simulation.domain.model import FixtureSpec, Score, Venue

if TYPE_CHECKING:
    from collections.abc import Callable

_GROUP_SIZE = 4
_HEAD_TO_HEAD = frozenset(
    {
        "head_to_head_points",
        "head_to_head_goal_difference",
        "head_to_head_goals_for",
        "head_to_head_away_goals",
    }
)
_CRITERIA = _HEAD_TO_HEAD | {"goal_difference", "goals_for", "wins"}


@dataclass(frozen=True, slots=True)
class GroupRules:
    """Content criterion vocabulary with an explicit mini-table reapplication switch.

    Consecutive H2H criteria form a block, evaluated against the same tied set. When
    reapplication is enabled and that block splits the set, restart the entire block for
    each remaining tied subset before proceeding to the following overall criterion.
    This is a configurable game rule, not an assertion about any historical competition.
    """

    points_per_win: int
    points_per_draw: int
    tiebreakers: tuple[str, ...]
    advance_per_group: int
    reapply_head_to_head: bool

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (self.points_per_win, self.points_per_draw)
        ):
            raise InvalidValueError("group points must be non-negative integers")
        if type(self.advance_per_group) is not int or not 0 < self.advance_per_group < _GROUP_SIZE:
            raise InvalidValueError("qualifiers must be between one and three")
        if type(self.reapply_head_to_head) is not bool:
            raise InvalidValueError("mini-table reapplication needs an explicit boolean")
        if (
            not isinstance(self.tiebreakers, tuple)
            or not all(
                isinstance(criterion, str) and criterion in _CRITERIA
                for criterion in self.tiebreakers
            )
            or len(set(self.tiebreakers)) != len(self.tiebreakers)
        ):
            raise InvalidValueError("group tiebreakers must be distinct supported criterion names")


@dataclass(frozen=True, slots=True)
class GroupMatch:
    """One evidenced regulation score, including the exact scheduled fixture metadata."""

    fixture: FixtureSpec
    score: Score

    def __post_init__(self) -> None:
        if not isinstance(self.fixture, FixtureSpec) or not isinstance(self.score, Score):
            raise InvalidValueError("group evidence needs a fixture and regulation score")


@dataclass(frozen=True, slots=True)
class GroupEvidence:
    """Declared complete group calendar and evidenced scores through a cutoff.

    Unknown evidence is represented by None on GroupTable. Empty calendar/results declares
    that no fixtures are scheduled; it is never manufactured from missing managed fixtures.
    A caller must supply the whole group calendar, including third-party matches, from a
    trusted source. This value can detect missing results, but cannot prove calendar coverage.
    """

    as_of: date
    schedule: tuple[FixtureSpec, ...]
    results: tuple[GroupMatch, ...]

    def __post_init__(self) -> None:
        if type(self.as_of) is not date:
            raise InvalidValueError("group evidence needs a calendar cutoff")
        if (
            not isinstance(self.schedule, tuple)
            or not all(isinstance(fixture, FixtureSpec) for fixture in self.schedule)
            or not isinstance(self.results, tuple)
            or not all(isinstance(result, GroupMatch) for result in self.results)
        ):
            raise InvalidValueError("group calendar and results must be immutable tuples")
        for fixture in chain(self.schedule, (result.fixture for result in self.results)):
            if type(fixture.date) is not date:
                raise InvalidValueError("group fixtures need calendar dates")
            if not isinstance(fixture.venue, Venue) or fixture.venue not in (
                Venue.HOME,
                Venue.NEUTRAL,
            ):
                raise InvalidValueError("group fixtures need typed home or neutral venues")
            if not isinstance(fixture.fixture_id, FixtureId):
                raise InvalidValueError("group fixtures need typed fixture IDs")
        fixtures = {fixture.fixture_id: fixture for fixture in self.schedule}
        if len(fixtures) != len(self.schedule):
            raise InvalidValueError("duplicate group fixture in the calendar")
        seen = set()
        for result in self.results:
            fixture = result.fixture
            if fixture.fixture_id in seen:
                raise InvalidValueError("duplicate group result")
            seen.add(fixture.fixture_id)
            if fixtures.get(fixture.fixture_id) != fixture:
                raise InvalidValueError("group result does not match a scheduled fixture")
            if fixture.date > self.as_of:
                raise InvalidValueError("group results cannot be later than the cutoff")

    def matches(self, members: tuple[ClubSeasonId, ...]) -> tuple[GroupMatch, ...]:
        """Return all scheduled mini-table scores by the cutoff, rejecting missing ones."""
        required = {
            fixture.fixture_id
            for fixture in self.schedule
            if fixture.date <= self.as_of and fixture.home in members and fixture.away in members
        }
        results = tuple(result for result in self.results if result.fixture.fixture_id in required)
        if len(results) != len(required):
            raise InvalidValueError("missing required head-to-head result evidence")
        return results


@dataclass(frozen=True, slots=True)
class GroupRanking:
    """Stable presentation order plus the sets still tied after every configured criterion."""

    rows: tuple[LeagueRow, ...]
    unresolved_ties: tuple[tuple[ClubSeasonId, ...], ...]
    advance_per_group: int

    @property
    def qualifiers(self) -> tuple[ClubSeasonId, ...]:
        """Refuse to promote a club by its stable ID when a tie crosses qualification."""
        advancing = tuple(row.club_season_id for row in self.rows[: self.advance_per_group])
        for tied in self.unresolved_ties:
            if any(club in advancing for club in tied) and any(
                club not in advancing for club in tied
            ):
                raise InvalidValueError("qualification crosses an unresolved group tie")
        return advancing


@dataclass(frozen=True, slots=True)
class GroupTable:
    """Rank supplied accumulated rows; neither simulate nor infer third-party matches.

    Rows may come from the P2 external-results policy. H2H evidence must already contain
    simulated managed results and historical third-party results for the same cutoff.
    """

    competition_id: CompetitionId
    stage_id: str
    group_id: str
    participants: tuple[ClubSeasonId, ...]
    rows: tuple[LeagueRow, ...]
    rules: GroupRules
    evidence: GroupEvidence | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.competition_id, CompetitionId)
            or not isinstance(self.stage_id, str)
            or not self.stage_id
            or not isinstance(self.group_id, str)
            or not self.group_id
        ):
            raise InvalidValueError("a group table needs competition, stage and group IDs")
        if not isinstance(self.rules, GroupRules):
            raise InvalidValueError("a group table needs group rules")
        if (
            not isinstance(self.participants, tuple)
            or len(self.participants) != _GROUP_SIZE
            or not all(isinstance(club, ClubSeasonId) for club in self.participants)
            or len(set(self.participants)) != _GROUP_SIZE
        ):
            raise InvalidValueError("a group needs four distinct clubs")
        if not isinstance(self.rows, tuple) or not all(
            isinstance(row, LeagueRow) for row in self.rows
        ):
            raise InvalidValueError("group rows must be an immutable tuple")
        clubs = tuple(row.club_season_id for row in self.rows)
        if len(clubs) != _GROUP_SIZE or set(clubs) != set(self.participants):
            raise InvalidValueError("group rows must cover every club exactly once")
        if any(
            row.points
            != row.won * self.rules.points_per_win + row.drawn * self.rules.points_per_draw
            for row in self.rows
        ):
            raise InvalidValueError("group row points do not follow the configured rules")
        if self.evidence is not None:
            self._validate_evidence()

    def _validate_evidence(self) -> None:
        if not isinstance(self.evidence, GroupEvidence):
            raise InvalidValueError("group evidence must be known or None")
        for fixture in self.evidence.schedule:
            if (fixture.competition_id, fixture.stage, fixture.group) != (
                self.competition_id,
                self.stage_id,
                self.group_id,
            ) or fixture.leg is not None:
                raise InvalidValueError("evidence fixtures must belong to this group")
            if fixture.home not in self.participants or fixture.away not in self.participants:
                raise InvalidValueError("both evidence clubs must belong to this group")

    def rank(self) -> GroupRanking:
        """Points first, configured criteria next, stable IDs only for presentation."""
        rows = {row.club_season_id: row for row in self.rows}
        unresolved: list[tuple[ClubSeasonId, ...]] = []

        def resolve(members: tuple[ClubSeasonId, ...], index: int) -> tuple[ClubSeasonId, ...]:
            if len(members) <= 1:
                return members
            if index == len(self.rules.tiebreakers):
                stable = tuple(sorted(members, key=str))
                unresolved.append(stable)
                return stable
            criterion = self.rules.tiebreakers[index]
            if criterion not in _HEAD_TO_HEAD:
                partitions = _partition(members, lambda club: _overall_value(rows[club], criterion))
                return tuple(club for part in partitions for club in resolve(part, index + 1))
            end = index
            while (
                end < len(self.rules.tiebreakers) and self.rules.tiebreakers[end] in _HEAD_TO_HEAD
            ):
                end += 1
            values = self._mini_table(members)
            partitions = (members,)
            for head_criterion in self.rules.tiebreakers[index:end]:
                criterion_values = {club: values[club][head_criterion] for club in members}
                partitions = tuple(
                    part
                    for group in partitions
                    for part in _partition(group, criterion_values.__getitem__)
                )
            restart = self.rules.reapply_head_to_head and len(partitions) > 1
            return tuple(
                club for part in partitions for club in resolve(part, index if restart else end)
            )

        ordered = tuple(
            club
            for part in _partition(self.participants, lambda club: rows[club].points)
            for club in resolve(part, 0)
        )
        return GroupRanking(
            tuple(rows[club] for club in ordered), tuple(unresolved), self.rules.advance_per_group
        )

    def _mini_table(self, members: tuple[ClubSeasonId, ...]) -> dict[ClubSeasonId, dict[str, int]]:
        if self.evidence is None:
            raise InvalidValueError("head-to-head ranking requires explicit group match evidence")
        values = {club: dict.fromkeys(_HEAD_TO_HEAD, 0) for club in members}
        for match in self.evidence.matches(members):
            home, away = match.fixture.home, match.fixture.away
            visiting_goals = match.score.away if match.fixture.venue is Venue.HOME else 0
            for club, gf, ga, away_goals in (
                (home, match.score.home, match.score.away, 0),
                (away, match.score.away, match.score.home, visiting_goals),
            ):
                row = values[club]
                row["head_to_head_points"] += (
                    self.rules.points_per_win
                    if gf > ga
                    else self.rules.points_per_draw
                    if gf == ga
                    else 0
                )
                row["head_to_head_goal_difference"] += gf - ga
                row["head_to_head_goals_for"] += gf
                row["head_to_head_away_goals"] += away_goals
        return values


def _partition(
    members: tuple[ClubSeasonId, ...], value: Callable[[ClubSeasonId], int]
) -> tuple[tuple[ClubSeasonId, ...], ...]:
    ordered = sorted(members, key=value, reverse=True)
    return tuple(tuple(group) for _, group in groupby(ordered, key=value))


def _overall_value(row: LeagueRow, criterion: str) -> int:
    if criterion == "goal_difference":
        return row.goals_for - row.goals_against
    return row.goals_for if criterion == "goals_for" else row.won
