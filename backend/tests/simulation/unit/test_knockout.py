"""Synthetic Test FC cup rules; no historical regulations are assumed."""

from collections import deque
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any

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


@pytest.mark.parametrize("changes", [{"stage": ""}, {"date": "2001-02-01"}, {"venue": "home"}])
def test_knockout_fixture_metadata_is_validated(changes: dict[str, Any]) -> None:
    fixture = replace(_fixtures(single=True)[0], **changes)
    with pytest.raises(InvalidValueError):
        KnockoutTie(KnockoutRules(1, False, False, False), (fixture,))


@pytest.mark.parametrize(
    "changes",
    [
        {"legs": 3},
        {"legs": True},
        {"extra_time": 1},
        {"away_goals_rule": 1},
        {"penalties": 0},
        {"away_goals_rule": True},
        {"away_goals_in_extra_time": False},
    ],
)
def test_knockout_rules_reject_incoherent_configuration(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidValueError):
        replace(KnockoutRules(1, False, False, False), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"rules": None},
        {"fixtures": []},
        {"fixtures": (None,)},
        {"results": []},
        {"results": (None,)},
        {"results": (MatchResult(Score(0, 0)),) * 3},
    ],
)
def test_tie_requires_immutable_typed_inputs(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidValueError):
        replace(KnockoutTie(KnockoutRules(2, False, False, False), _fixtures()), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"leg": 1},
        {"date": date(2001, 2, 1)},
        {"fixture_id": FixtureId("test-first")},
        {"competition_id": CompetitionId("other-cup")},
        {"stage": "semi"},
        {"group": "a"},
        {"home": SAMPLE},
        {"venue": Venue.NEUTRAL},
    ],
)
def test_return_leg_must_match_the_same_tie(changes: dict[str, Any]) -> None:
    first, second = _fixtures()
    with pytest.raises(InvalidValueError):
        KnockoutTie(KnockoutRules(2, True, False, False), (first, replace(second, **changes)))


@pytest.mark.parametrize("changes", [{"leg": 2}, {"stage": None}, {"group": "a"}])
def test_single_match_must_be_a_valid_knockout_fixture(changes: dict[str, Any]) -> None:
    first = replace(_fixtures(single=True)[0], **changes)
    with pytest.raises(InvalidValueError):
        KnockoutTie(KnockoutRules(1, False, False, False), (first,))


def test_first_leg_is_simulated_without_deciding_periods() -> None:
    fixtures = _fixtures()
    setup = _setup(fixtures[0])
    rng = StdlibRandomSource(Seed(9))
    simulator = _Simulator(deque([MatchResult(Score(1, 0))]))
    tie = KnockoutTie(KnockoutRules(2, False, True, True), fixtures).play_next(
        setup, simulator, rng
    )
    assert tie.results == (MatchResult(Score(1, 0)),)
    assert tie.winner is None
    assert simulator.calls == [("regulation", setup, rng, False)]


def test_extra_time_can_decide_the_aggregate_without_a_shootout() -> None:
    fixtures = _fixtures()
    simulator = _Simulator(deque([MatchResult(Score(1, 0))]), Score(1, 0))
    tie = KnockoutTie(KnockoutRules(2, False, True, True), fixtures, (MatchResult(Score(1, 0)),))
    played = tie.play_next(_setup(fixtures[1]), simulator, StdlibRandomSource(Seed(9)))
    assert played.winner == DEMO
    assert len(simulator.calls) == 2


def test_wrong_setup_is_rejected_before_sampling() -> None:
    simulator = _Simulator(deque())
    tie = KnockoutTie(KnockoutRules(2, False, False, False), _fixtures())
    with pytest.raises(InvalidValueError, match="next"):
        tie.play_next(_setup(_fixtures()[1]), simulator, StdlibRandomSource(Seed(9)))
    assert not simulator.calls


def test_completed_tie_cannot_be_simulated_again() -> None:
    fixtures = _fixtures(single=True)
    tie = KnockoutTie(KnockoutRules(1, False, False, False), fixtures, (MatchResult(Score(1, 0)),))
    with pytest.raises(InvalidValueError, match="next"):
        tie.play_next(_setup(fixtures[0]), _Simulator(deque()), StdlibRandomSource(Seed(9)))


def test_regulation_simulator_cannot_prematurely_decide_the_match() -> None:
    fixtures = _fixtures(single=True)
    simulator = _Simulator(deque([MatchResult(Score(0, 0), Score(1, 0))]))
    with pytest.raises(InvalidValueError, match="unexpected"):
        KnockoutTie(KnockoutRules(1, False, True, True), fixtures).play_next(
            _setup(fixtures[0]), simulator, StdlibRandomSource(Seed(9))
        )


@pytest.mark.parametrize(
    ("scores", "winner"),
    [
        ((Score(0, 1), Score(0, 0)), DEMO),
        ((Score(0, 1), Score(2, 0)), DEMO),
        ((Score(2, 1), Score(1, 0)), DEMO),
        ((Score(2, 0), Score(0, 0)), TEST),
    ],
)
def test_both_aggregate_and_away_goal_orientations(
    scores: tuple[Score, Score], winner: ClubSeasonId
) -> None:
    tie = KnockoutTie(
        KnockoutRules(2, True, False, False), _fixtures(), tuple(MatchResult(s) for s in scores)
    )
    assert tie.winner == winner


@pytest.mark.parametrize(
    "changes",
    [
        {"stage_id": ""},
        {"clubs": ()},
        {"clubs": (TEST, TEST)},
        {"clubs": (TEST, "demo")},
        {"winner": SAMPLE},
    ],
)
def test_historical_tie_requires_an_evidenced_participating_winner(
    changes: dict[str, Any],
) -> None:
    with pytest.raises(InvalidValueError):
        replace(HistoricalTie("quarter", (TEST, DEMO), DEMO), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"stages": ()},
        {"stages": ("quarter", "quarter")},
        {"stages": ("",)},
        {"ties": []},
        {"ties": (HistoricalTie("unknown", (TEST, DEMO)),)},
    ],
)
def test_bracket_requires_an_explicit_unambiguous_stage_sequence(
    changes: dict[str, Any],
) -> None:
    with pytest.raises(InvalidValueError):
        replace(_bracket(), **changes)


@pytest.mark.parametrize("stage", ["semi", "unknown"])
def test_bracket_cannot_invent_a_following_stage(stage: str) -> None:
    with pytest.raises(InvalidValueError):
        _bracket().next_opponent(stage, DEMO)


def test_bracket_cannot_invent_a_next_pairing_from_previous_winners() -> None:
    bracket = _bracket()
    with pytest.raises(InvalidValueError, match="next tie"):
        replace(bracket, ties=bracket.ties[:2]).next_opponent("quarter", DEMO)


def test_bracket_cannot_invent_the_opponents_previous_winning_tie() -> None:
    bracket = _bracket()
    with pytest.raises(InvalidValueError, match="winner"):
        replace(bracket, ties=(bracket.ties[0], bracket.ties[2])).next_opponent("quarter", DEMO)
