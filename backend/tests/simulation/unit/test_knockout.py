"""Synthetic Test FC cup rules; no historical regulations are assumed."""

from collections import deque
from dataclasses import dataclass, field, replace
from datetime import date

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.shared_kernel.randomness import RandomSource, StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.domain.knockout import (
    HistoricalBracket,
    HistoricalTie,
    KnockoutRules,
    KnockoutTie,
)
from mister.simulation.domain.model import (
    CompetitionParams,
    FixtureSpec,
    MatchResult,
    MatchSetup,
    Score,
    TeamStrength,
    Venue,
)

TEST = ClubSeasonId("test-fc-2000-01")
DEMO = ClubSeasonId("demo-athletic-2000-01")
SAMPLE = ClubSeasonId("sample-united-2000-01")
DUMMY = ClubSeasonId("dummy-rovers-2000-01")


def _fixtures(*, single: bool = False, competition: str = "test-cup") -> tuple[FixtureSpec, ...]:
    first = FixtureSpec(
        FixtureId("test-first"),
        date(2001, 2, 1),
        CompetitionId(competition),
        TEST,
        DEMO,
        venue=Venue.NEUTRAL if single else Venue.HOME,
        stage="final" if single else "quarter",
        leg=None if single else 1,
    )
    return (
        (first,)
        if single
        else (
            first,
            replace(
                first,
                fixture_id=FixtureId("test-second"),
                date=date(2001, 2, 8),
                home=DEMO,
                away=TEST,
                leg=2,
            ),
        )
    )


def _setup(fixture: FixtureSpec) -> MatchSetup:
    return MatchSetup(
        fixture, TeamStrength(1.2, 0.8), TeamStrength(0.9, 1.1), CompetitionParams(1.4, 1.2)
    )


@dataclass
class _Simulator:
    regulation: deque[MatchResult]
    extra: Score = field(default_factory=lambda: Score(0, 0))
    penalties: Score = field(default_factory=lambda: Score(4, 5))
    calls: list[tuple[str, MatchSetup, RandomSource, bool]] = field(default_factory=list)

    def simulate(
        self, setup: MatchSetup, rng: RandomSource, *, decisive: bool = False
    ) -> MatchResult:
        self.calls.append(("regulation", setup, rng, decisive))
        return self.regulation.popleft()

    def extra_time(self, setup: MatchSetup, rng: RandomSource) -> Score:
        self.calls.append(("extra_time", setup, rng, False))
        return self.extra

    def penalty_shootout(self, setup: MatchSetup, rng: RandomSource) -> Score:
        self.calls.append(("penalties", setup, rng, False))
        return self.penalties


@pytest.mark.parametrize(
    "competition", ["test-cup", "test-champions", "test-uefa", "test-supercup"]
)
def test_away_goals_qualify_the_second_leg_visitor(competition: str) -> None:
    tie = KnockoutTie(
        KnockoutRules(2, True, False, True),
        _fixtures(competition=competition),
        (MatchResult(Score(1, 0)), MatchResult(Score(2, 1))),
    )
    assert tie.winner == TEST
    assert tie.aggregate == Score(2, 2)


def test_a_single_first_leg_has_no_tie_winner() -> None:
    tie = KnockoutTie(KnockoutRules(2, False, True, True), _fixtures(), (MatchResult(Score(8, 0)),))
    assert tie.winner is None
    assert not tie.complete


def test_aggregate_level_triggers_extra_time_even_when_second_leg_is_not_drawn() -> None:
    fixtures = _fixtures()
    tie = KnockoutTie(KnockoutRules(2, False, True, True), fixtures, (MatchResult(Score(1, 0)),))
    simulator = _Simulator(deque([MatchResult(Score(1, 0))]))
    rng = StdlibRandomSource(Seed(42))
    setup = _setup(fixtures[1])
    played = tie.play_next(setup, simulator, rng)
    assert simulator.calls == [
        ("regulation", setup, rng, False),
        ("extra_time", setup, rng, False),
        ("penalties", setup, rng, False),
    ]
    assert played.winner == TEST
    assert played.aggregate == Score(1, 1)
    assert played.results[-1] == MatchResult(Score(1, 0), Score(0, 0), Score(4, 5))
    assert played.complete


def test_a_drawn_second_leg_needs_no_extra_time_when_aggregate_decides() -> None:
    fixtures = _fixtures()
    tie = KnockoutTie(KnockoutRules(2, False, True, True), fixtures, (MatchResult(Score(2, 0)),))
    simulator = _Simulator(deque([MatchResult(Score(1, 1))]))
    rng = StdlibRandomSource(Seed(42))
    setup = _setup(fixtures[1])
    assert tie.play_next(setup, simulator, rng).winner == TEST
    assert simulator.calls == [("regulation", setup, rng, False)]


@pytest.mark.parametrize(("count_extra", "expected", "calls"), [(True, TEST, 2), (False, DEMO, 3)])
def test_extra_time_away_goals_variant_is_explicit(
    count_extra: bool, expected: ClubSeasonId, calls: int
) -> None:
    fixtures = _fixtures()
    tie = KnockoutTie(
        KnockoutRules(2, True, True, True, away_goals_in_extra_time=count_extra),
        fixtures,
        (MatchResult(Score(0, 0)),),
    )
    simulator = _Simulator(deque([MatchResult(Score(0, 0))]), Score(1, 1), Score(5, 4))
    played = tie.play_next(_setup(fixtures[1]), simulator, StdlibRandomSource(Seed(7)))
    assert played.winner == expected
    assert played.aggregate == Score(1, 1)
    assert len(simulator.calls) == calls


def test_away_goals_with_extra_time_requires_an_explicit_variant() -> None:
    with pytest.raises(InvalidValueError, match="explicit"):
        KnockoutRules(2, True, True, True)


@pytest.mark.parametrize(
    ("extra", "penalties", "expected"),
    [(Score(1, 0), None, TEST), (Score(0, 0), Score(4, 5), DEMO)],
)
def test_single_neutral_final_uses_configured_periods(
    extra: Score, penalties: Score | None, expected: ClubSeasonId
) -> None:
    tie = KnockoutTie(
        KnockoutRules(1, False, True, True),
        _fixtures(single=True),
        (MatchResult(Score(1, 1), extra, penalties),),
    )
    assert tie.winner == expected


def test_no_extra_time_rule_goes_directly_to_penalties() -> None:
    fixtures = _fixtures(single=True)
    simulator = _Simulator(deque([MatchResult(Score(0, 0))]))
    rng = StdlibRandomSource(Seed(42))
    setup = _setup(fixtures[0])
    played = KnockoutTie(KnockoutRules(1, False, False, True), fixtures).play_next(
        setup, simulator, rng
    )
    assert played.winner == DEMO
    assert simulator.calls == [("regulation", setup, rng, False), ("penalties", setup, rng, False)]


@pytest.mark.parametrize(
    "results",
    [
        (MatchResult(Score(1, 0), Score(0, 0)),),
        (MatchResult(Score(0, 0), penalties=Score(4, 5)),),
        (MatchResult(Score(0, 0), Score(1, 0), Score(4, 5)),),
    ],
)
def test_impossible_final_periods_are_rejected(results: tuple[MatchResult, ...]) -> None:
    with pytest.raises(InvalidValueError):
        KnockoutTie(KnockoutRules(1, False, True, True), _fixtures(single=True), results)


def test_first_leg_cannot_contain_extra_time() -> None:
    with pytest.raises(InvalidValueError):
        KnockoutTie(
            KnockoutRules(2, False, True, True),
            _fixtures(),
            (MatchResult(Score(0, 0), Score(0, 0)),),
        )


def test_unresolved_tie_without_deciding_periods_has_no_winner() -> None:
    tie = KnockoutTie(
        KnockoutRules(1, False, False, False), _fixtures(single=True), (MatchResult(Score(0, 0)),)
    )
    assert tie.winner is None
    assert not tie.complete


def _bracket(*, winner: ClubSeasonId | None = SAMPLE) -> HistoricalBracket:
    return HistoricalBracket(
        ("quarter", "semi"),
        (
            HistoricalTie("quarter", (TEST, DEMO), DEMO),
            HistoricalTie("quarter", (SAMPLE, DUMMY), winner),
            HistoricalTie("semi", (DEMO, SAMPLE), DEMO),
        ),
    )


def test_advancing_beyond_history_uses_the_other_real_quarter_final_winner() -> None:
    assert _bracket().next_opponent("quarter", DEMO) == SAMPLE


def test_pending_previous_winner_cannot_supply_a_future_opponent() -> None:
    with pytest.raises(InvalidValueError, match="winner"):
        _bracket(winner=None).next_opponent("quarter", DEMO)


def test_historical_lineage_must_be_a_known_previous_winner() -> None:
    with pytest.raises(InvalidValueError, match="winner"):
        _bracket().next_opponent("quarter", TEST)


def test_ambiguous_next_tie_is_rejected() -> None:
    bracket = _bracket()
    with pytest.raises(InvalidValueError, match="ambiguous"):
        HistoricalBracket(
            bracket.stages, (*bracket.ties, HistoricalTie("semi", (DEMO, DUMMY), DUMMY))
        )
