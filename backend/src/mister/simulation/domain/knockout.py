"""Aggregate-aware cup ties and evidenced historical bracket lineage."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import TYPE_CHECKING

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId
from mister.simulation.domain.model import FixtureSpec, MatchResult, Score, Venue

if TYPE_CHECKING:
    from mister.shared_kernel.randomness import RandomSource
    from mister.simulation.domain.model import MatchSetup
    from mister.simulation.domain.ports import MatchSimulator


_TWO_LEGS = 2
_TIE_SIZE = 2


@dataclass(frozen=True, slots=True)
class KnockoutRules:
    """Season-specific rules; extra-time away goals require an explicit design choice."""

    legs: int
    away_goals_rule: bool
    extra_time: bool
    penalties: bool
    away_goals_in_extra_time: bool | None = None

    def __post_init__(self) -> None:
        if type(self.legs) is not int or self.legs not in (1, 2):
            raise InvalidValueError("a knockout tie needs one or two legs")
        if any(
            type(value) is not bool
            for value in (self.away_goals_rule, self.extra_time, self.penalties)
        ):
            raise InvalidValueError("knockout switches must be booleans")
        if self.away_goals_rule and self.legs != _TWO_LEGS:
            raise InvalidValueError("away goals require two legs")
        if self.away_goals_rule and self.extra_time:
            if type(self.away_goals_in_extra_time) is not bool:
                raise InvalidValueError("extra-time away goals need an explicit boolean variant")
        elif self.away_goals_in_extra_time is not None:
            raise InvalidValueError("extra-time away-goals variant does not apply to these rules")


@dataclass(frozen=True, slots=True)
class KnockoutTie:
    """Scheduled legs in chronological order and an immutable prefix of played results.

    Aggregate scores are oriented like the first leg. A final result includes every period
    required by the rules; an unplayed leg never yields a winner. A tied tie with no deciding
    periods remains unresolved. Match winners and shootout goals never decide the aggregate.
    """

    rules: KnockoutRules
    fixtures: tuple[FixtureSpec, ...]
    results: tuple[MatchResult, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.rules, KnockoutRules):
            raise InvalidValueError("a tie needs knockout rules")
        if (
            not isinstance(self.fixtures, tuple)
            or not all(isinstance(fixture, FixtureSpec) for fixture in self.fixtures)
            or len(self.fixtures) != self.rules.legs
        ):
            raise InvalidValueError("the calendar must contain exactly the configured legs")
        if (
            not isinstance(self.results, tuple)
            or not all(isinstance(result, MatchResult) for result in self.results)
            or len(self.results) > len(self.fixtures)
        ):
            raise InvalidValueError("results must be an immutable prefix of scheduled legs")
        self._validate_calendar()
        self._validate_periods()

    def _validate_calendar(self) -> None:
        first = self.fixtures[0]
        if any(type(fixture.date) is not date or not isinstance(fixture.venue, Venue)
               for fixture in self.fixtures):
            raise InvalidValueError("knockout fixtures need calendar dates and typed venues")
        if not isinstance(first.stage, str) or not first.stage or first.group is not None:
            raise InvalidValueError("a knockout fixture needs a stage and cannot have a group")
        if self.rules.legs == 1:
            if first.leg not in (None, 1):
                raise InvalidValueError("a single fixture cannot be a second leg")
            return
        second = self.fixtures[1]
        if first.leg != 1 or second.leg != _TWO_LEGS:
            raise InvalidValueError("two-leg fixtures must be ordered as legs one and two")
        if first.date >= second.date or first.fixture_id == second.fixture_id:
            raise InvalidValueError("legs need distinct IDs and increasing dates")
        if (first.competition_id, first.stage, None) != (
            second.competition_id,
            second.stage,
            second.group,
        ):
            raise InvalidValueError("both legs must belong to the same competition and stage")
        if (first.home, first.away) != (second.away, second.home):
            raise InvalidValueError("the second leg must reverse the two clubs")
        if self.rules.away_goals_rule and any(f.venue is not Venue.HOME for f in self.fixtures):
            raise InvalidValueError("away goals require both fixtures at their home grounds")

    def _validate_periods(self) -> None:
        for index, result in enumerate(self.results):
            if index < self.rules.legs - 1 and (
                result.extra_time is not None or result.penalties is not None
            ):
                raise InvalidValueError("only the last leg can have deciding periods")
        if len(self.results) != self.rules.legs:
            return
        final = self.results[-1]
        regulation_winner = self._decision(self.results, include_extra=False)
        if regulation_winner is not None:
            if final.extra_time is not None or final.penalties is not None:
                raise InvalidValueError("regulation already decided the tie")
            return
        if (final.extra_time is not None) != self.rules.extra_time:
            raise InvalidValueError("extra time must follow the configured tie rules")
        after_extra = self._decision(self.results, include_extra=True)
        needs_penalties = after_extra is None and self.rules.penalties
        if (final.penalties is not None) != needs_penalties:
            raise InvalidValueError("penalties must follow an unresolved tie and its rules")

    @property
    def aggregate(self) -> Score:
        """All played goals, excluding penalties, from the first leg's home perspective."""
        return self._aggregate(self.results, include_extra=True)

    @staticmethod
    def _aggregate(results: tuple[MatchResult, ...], *, include_extra: bool) -> Score:
        home, away = 0, 0
        for index, result in enumerate(results):
            score = result.total if include_extra else result.regulation
            home += score.home if index == 0 else score.away
            away += score.away if index == 0 else score.home
        return Score(home, away)

    def _decision(
        self, results: tuple[MatchResult, ...], *, include_extra: bool
    ) -> ClubSeasonId | None:
        if len(results) != self.rules.legs:
            return None
        score = self._aggregate(results, include_extra=include_extra)
        if score.home != score.away:
            return self.fixtures[0].home if score.home > score.away else self.fixtures[0].away
        if self.rules.away_goals_rule:
            # The first home's away goals are scored in the second leg, and vice versa.
            first_away = results[0].regulation.away
            second_away = results[1].regulation.away
            if include_extra and self.rules.away_goals_in_extra_time:
                extra = results[1].extra_time
                second_away += extra.away if extra is not None else 0
            if first_away != second_away:
                return self.fixtures[0].home if second_away > first_away else self.fixtures[0].away
        return None

    @property
    def winner(self) -> ClubSeasonId | None:
        winner = self._decision(self.results, include_extra=True)
        if winner is not None or len(self.results) != self.rules.legs:
            return winner
        penalties = self.results[-1].penalties
        if penalties is None:
            return None
        fixture = self.fixtures[-1]
        return fixture.home if penalties.home > penalties.away else fixture.away

    @property
    def complete(self) -> bool:
        """All legs have been played and a winner is known."""
        return self.winner is not None

    def play_next(
        self, setup: MatchSetup, simulator: MatchSimulator, rng: RandomSource
    ) -> KnockoutTie:
        """Draw regulation exactly once; decide additional periods from the aggregate."""
        if (
            len(self.results) == self.rules.legs
            or setup.fixture != self.fixtures[len(self.results)]
        ):
            raise InvalidValueError("the setup must match the next unplayed fixture")
        result = simulator.simulate(setup, rng, decisive=False)
        if result.extra_time is not None or result.penalties is not None:
            raise InvalidValueError("the regulation simulator returned unexpected deciding periods")
        results = (*self.results, result)
        if len(results) == self.rules.legs and self._decision(results, include_extra=False) is None:
            if self.rules.extra_time:
                result = replace(result, extra_time=simulator.extra_time(setup, rng))
            results = (*self.results, result)
            if self._decision(results, include_extra=True) is None and self.rules.penalties:
                result = replace(result, penalties=simulator.penalty_shootout(setup, rng))
        return replace(self, results=(*self.results, result))


@dataclass(frozen=True, slots=True)
class HistoricalTie:
    """A real tie with its evidenced winner; pending means unknown, never a draw."""

    stage_id: str
    clubs: tuple[ClubSeasonId, ClubSeasonId]
    winner: ClubSeasonId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stage_id, str) or not self.stage_id:
            raise InvalidValueError("a historical tie needs a stage ID")
        if (
            not isinstance(self.clubs, tuple)
            or len(self.clubs) != _TIE_SIZE
            or not all(isinstance(club, ClubSeasonId) for club in self.clubs)
            or self.clubs[0] == self.clubs[1]
        ):
            raise InvalidValueError("a historical tie needs two distinct clubs")
        if self.winner is not None and self.winner not in self.clubs:
            raise InvalidValueError("the real winner must participate in the tie")


@dataclass(frozen=True, slots=True)
class HistoricalBracket:
    """An explicitly ordered knockout path; club overlap proves the next-stage lineage.

    No positional seeding is inferred. Resolving a next opponent also requires a unique,
    known winning tie for each next-stage club in the preceding stage. Formats with byes,
    draws, group qualification or missing feeder evidence need an explicit future contract.
    """

    stages: tuple[str, ...]
    ties: tuple[HistoricalTie, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.stages, tuple)
            or not self.stages
            or not all(isinstance(stage, str) and stage for stage in self.stages)
            or len(set(self.stages)) != len(self.stages)
        ):
            raise InvalidValueError(
                "the bracket needs distinct stages in explicit progression order"
            )
        if not isinstance(self.ties, tuple) or not all(
            isinstance(tie, HistoricalTie) for tie in self.ties
        ):
            raise InvalidValueError("historical ties must be an immutable tuple")
        slots: set[tuple[str, ClubSeasonId]] = set()
        for tie in self.ties:
            if tie.stage_id not in self.stages:
                raise InvalidValueError("a historical tie has an unknown stage")
            for club in tie.clubs:
                slot = (tie.stage_id, club)
                if slot in slots:
                    raise InvalidValueError("ambiguous historical ties for the same stage and club")
                slots.add(slot)

    def _winning_tie(self, stage: str, club: ClubSeasonId) -> HistoricalTie:
        candidates = tuple(tie for tie in self.ties if tie.stage_id == stage and club in tie.clubs)
        if len(candidates) != 1 or candidates[0].winner != club:
            raise InvalidValueError("the pertinent preceding tie needs a unique known real winner")
        return candidates[0]

    def next_opponent(
        self, completed_stage: str, historical_representative: ClubSeasonId
    ) -> ClubSeasonId:
        """Follow the club whose historical slot the simulated advancing club occupies."""
        if completed_stage not in self.stages or completed_stage == self.stages[-1]:
            raise InvalidValueError("the completed stage must have an explicit following stage")
        previous = self._winning_tie(completed_stage, historical_representative)
        next_stage = self.stages[self.stages.index(completed_stage) + 1]
        candidates = tuple(
            tie
            for tie in self.ties
            if tie.stage_id == next_stage and historical_representative in tie.clubs
        )
        if len(candidates) != 1:
            raise InvalidValueError("the historical lineage has no unique next tie")
        opponent = next(club for club in candidates[0].clubs if club != historical_representative)
        feeder = self._winning_tie(completed_stage, opponent)
        if feeder == previous:
            raise InvalidValueError("next-stage opponents must have distinct feeder ties")
        return opponent
