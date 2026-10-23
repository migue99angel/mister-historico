"""Fixture streams isolate periods, teams and shootouts, with reproducible football scores."""

import math
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import date
from statistics import mean
from typing import Self

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.domain.goal_model import PoissonGoalModel
from mister.simulation.domain.match_simulator import PoissonMatchSimulator
from mister.simulation.domain.model import (
    CompetitionParams,
    FixtureSpec,
    MatchResult,
    MatchSetup,
    Score,
    Side,
    TeamStrength,
    Venue,
)
from mister.simulation.domain.ports import MatchSimulator  # noqa: TC001

type _Path = tuple[str | int, ...]


@dataclass
class _Draws:
    goals: dict[_Path, int] = field(default_factory=dict)
    uniforms: deque[float] = field(default_factory=deque)
    constant: float | None = None
    streams: list[_Path] = field(default_factory=list)
    rates: list[tuple[_Path, float]] = field(default_factory=list)
    consumed: int = 0


class _ScriptedRandomSource(StdlibRandomSource):
    """A seeded-source compatible fake that records every logical leaf and sample."""

    def __init__(self, draws: _Draws, path: _Path = ()) -> None:
        self.draws = draws
        self.path = path

    def stream(self, *keys: str | int) -> Self:
        path = (*self.path, *keys)
        self.draws.streams.append(path)
        return type(self)(self.draws, path)

    def poisson(self, lam: float) -> int:
        self.draws.rates.append((self.path, lam))
        return self.draws.goals[self.path]

    def random(self) -> float:
        self.draws.consumed += 1
        if self.draws.uniforms:
            return self.draws.uniforms.popleft()
        if self.draws.constant is not None:
            return self.draws.constant
        raise AssertionError("unexpected random draw")


@dataclass
class _RecordingGoalModel:
    calls: list[tuple[TeamStrength, TeamStrength, Venue, CompetitionParams, bool]] = field(
        default_factory=list
    )

    def expected_goals(
        self,
        team: TeamStrength,
        opponent: TeamStrength,
        venue: Venue,
        params: CompetitionParams,
        *,
        extra_time: bool = False,
    ) -> float:
        self.calls.append((team, opponent, venue, params, extra_time))
        return 0.6 if extra_time else 1.8


def _setup(*, fixture_id: str = "test-match", venue: Venue = Venue.HOME) -> MatchSetup:
    return MatchSetup(
        FixtureSpec(
            FixtureId(fixture_id),
            date(2000, 9, 3),
            CompetitionId("liga-test"),
            ClubSeasonId("test-fc-2000-01"),
            ClubSeasonId("demo-athletic-2000-01"),
            venue,
        ),
        TeamStrength(1.2, 0.8),
        TeamStrength(0.9, 1.1),
        CompetitionParams(1.3, 1.15),
    )


def _period_draws(regulation: Score, extra_time: Score | None = None) -> _Draws:
    extra_time = extra_time or Score(0, 0)
    return _Draws(
        goals={
            ("match", "test-match", "goals", "home"): regulation.home,
            ("match", "test-match", "goals", "away"): regulation.away,
            ("match", "test-match", "extra_time", "home"): extra_time.home,
            ("match", "test-match", "extra_time", "away"): extra_time.away,
        }
    )


@pytest.mark.parametrize("venue", [Venue.HOME, Venue.NEUTRAL])
def test_regulation_uses_exact_leaf_streams_and_both_teams_point_of_view(venue: Venue) -> None:
    setup, draws, model = _setup(venue=venue), _period_draws(Score(2, 1)), _RecordingGoalModel()
    simulator: MatchSimulator = PoissonMatchSimulator(model)

    assert simulator.simulate(setup, _ScriptedRandomSource(draws)) == MatchResult(Score(2, 1))
    assert draws.streams == [
        ("match", "test-match", "goals", "home"),
        ("match", "test-match", "goals", "away"),
    ]
    away_venue = Venue.NEUTRAL if venue is Venue.NEUTRAL else Venue.AWAY
    assert model.calls == [
        (setup.home, setup.away, venue, setup.params, False),
        (setup.away, setup.home, away_venue, setup.params, False),
    ]
    assert [rate for _, rate in draws.rates] == [1.8, 1.8]


@pytest.mark.parametrize("venue", [Venue.HOME, Venue.NEUTRAL])
def test_extra_time_has_distinct_leaf_streams_and_asks_for_thirty_minute_rates(
    venue: Venue,
) -> None:
    setup, draws, model = (
        _setup(venue=venue),
        _period_draws(Score(1, 0), Score(0, 2)),
        _RecordingGoalModel(),
    )

    assert PoissonMatchSimulator(model).extra_time(setup, _ScriptedRandomSource(draws)) == Score(
        0, 2
    )
    assert draws.streams == [
        ("match", "test-match", "extra_time", "home"),
        ("match", "test-match", "extra_time", "away"),
    ]
    away_venue = Venue.NEUTRAL if venue is Venue.NEUTRAL else Venue.AWAY
    assert model.calls == [
        (setup.home, setup.away, venue, setup.params, True),
        (setup.away, setup.home, away_venue, setup.params, True),
    ]
    assert [rate for _, rate in draws.rates] == [0.6, 0.6]


def test_a_league_draw_ends_after_regulation() -> None:
    draws = _period_draws(Score(1, 1))

    assert PoissonMatchSimulator().simulate(_setup(), _ScriptedRandomSource(draws)) == MatchResult(
        Score(1, 1)
    )
    assert len(draws.streams) == 2


def test_a_decisive_regulation_win_does_not_use_tiebreakers() -> None:
    draws = _period_draws(Score(2, 1))

    assert PoissonMatchSimulator().simulate(
        _setup(), _ScriptedRandomSource(draws), decisive=True
    ) == MatchResult(Score(2, 1))
    assert len(draws.streams) == 2


def test_a_decisive_draw_uses_extra_time_before_penalties() -> None:
    draws = _period_draws(Score(1, 1), Score(0, 1))

    assert PoissonMatchSimulator().simulate(
        _setup(), _ScriptedRandomSource(draws), decisive=True
    ) == MatchResult(Score(1, 1), extra_time=Score(0, 1))
    assert len(draws.streams) == 4


def test_a_decisive_draw_still_level_after_extra_time_uses_penalties() -> None:
    draws = _period_draws(Score(1, 1), Score(0, 0))
    draws.uniforms.extend([0.0, 0.99] * 3)

    assert PoissonMatchSimulator().simulate(
        _setup(), _ScriptedRandomSource(draws), decisive=True
    ) == MatchResult(Score(1, 1), extra_time=Score(0, 0), penalties=Score(3, 0))
    assert draws.streams[-1] == ("match", "test-match", "penalties")


@given(seed=st.integers(min_value=0, max_value=2**64 - 1))
def test_same_seed_and_fixture_replay_exactly_even_after_other_root_draws(seed: int) -> None:
    setup, simulator, rng = _setup(), PoissonMatchSimulator(), StdlibRandomSource(Seed(seed))
    result = simulator.simulate(setup, rng, decisive=True)
    rng.random()
    simulator.simulate(_setup(fixture_id="other-match"), rng, decisive=True)

    assert simulator.simulate(setup, rng, decisive=True) == result
    assert simulator.simulate(setup, StdlibRandomSource(Seed(seed)), decisive=True) == result


def test_changing_home_attack_cannot_move_away_or_another_fixture_stream() -> None:
    setup, simulator, rng = _setup(), PoissonMatchSimulator(), StdlibRandomSource(Seed(46))
    before = simulator.simulate(setup, rng)
    other = simulator.simulate(_setup(fixture_id="other-match"), rng)
    stronger_home = replace(setup, home=TeamStrength(2.5, setup.home.defense))
    after = simulator.simulate(stronger_home, rng)

    assert after.regulation.home >= before.regulation.home
    assert after.regulation.away == before.regulation.away
    assert simulator.simulate(_setup(fixture_id="other-match"), rng) == other


def test_extra_time_and_penalties_do_not_advance_regulation_or_the_root() -> None:
    setup, simulator, rng = _setup(), PoissonMatchSimulator(), StdlibRandomSource(Seed(68))
    expected = simulator.simulate(setup, rng)
    simulator.extra_time(setup, rng)
    simulator.penalty_shootout(setup, rng)

    assert simulator.simulate(setup, rng) == expected
    assert rng.random() == StdlibRandomSource(Seed(68)).random()


def test_one_hundred_thousand_matches_have_the_expected_goal_means() -> None:
    setup, simulator, model, rng = (
        _setup(),
        PoissonMatchSimulator(),
        PoissonGoalModel(),
        StdlibRandomSource(Seed(20261023)),
    )
    sample_size = 100_000
    home_goals, away_goals = 0, 0
    for index in range(sample_size):
        fixture = replace(setup.fixture, fixture_id=FixtureId(f"sample-{index}"))
        result = simulator.simulate(replace(setup, fixture=fixture), rng)
        home_goals += result.regulation.home
        away_goals += result.regulation.away
    for goals, team, opponent, venue in [
        (home_goals, setup.home, setup.away, Venue.HOME),
        (away_goals, setup.away, setup.home, Venue.AWAY),
    ]:
        rate = model.expected_goals(team, opponent, venue, setup.params)
        # A Poisson sample mean has SE sqrt(lambda/N). Six SE avoids a fragile seed threshold.
        assert abs(goals / sample_size - rate) < 6 * math.sqrt(rate / sample_size)


@pytest.mark.parametrize(
    ("uniforms", "expected", "consumed"),
    [
        ([0.0, 0.99] * 3, Score(3, 0), 6),
        ([0.99, 0.0] * 3, Score(0, 3), 6),
        ([0.99, 0.0] * 2 + [0.99, 0.99, 0.99], Score(0, 2), 7),
        ([0.0, 0.0] * 4 + [0.99, 0.0], Score(4, 5), 10),
    ],
)
def test_shootouts_alternate_and_stop_as_soon_as_the_score_is_irreversible(
    uniforms: list[float], expected: Score, consumed: int
) -> None:
    draws = _Draws(uniforms=deque(uniforms))

    assert (
        PoissonMatchSimulator().penalty_shootout(_setup(), _ScriptedRandomSource(draws)) == expected
    )
    assert draws.consumed == consumed
    assert draws.streams == [("match", "test-match", "penalties")]


@pytest.mark.parametrize("constant", [0.0, 0.5, math.nextafter(1.0, 0.0)])
def test_sudden_death_terminates_for_constant_uniforms_without_an_arbitrary_cap(
    constant: float,
) -> None:
    draws = _Draws(constant=constant)
    equal = replace(_setup(), home=TeamStrength(1.0, 1.0), away=TeamStrength(1.0, 1.0))

    score = PoissonMatchSimulator().penalty_shootout(equal, _ScriptedRandomSource(draws))

    assert abs(score.home - score.away) == 1
    assert draws.consumed == 12


@pytest.mark.parametrize(
    ("sudden_draws", "expected"),
    [
        ([0.0, 0.0], Score(6, 5)),
        ([0.5, 0.99], Score(6, 7)),
    ],
)
def test_sudden_death_counts_joint_goals_before_a_conditionally_drawn_winner(
    sudden_draws: list[float],
    expected: Score,
) -> None:
    draws = _Draws(uniforms=deque([0.0] * 10 + sudden_draws))
    equal = replace(_setup(), home=TeamStrength(1.0, 1.0), away=TeamStrength(1.0, 1.0))

    assert PoissonMatchSimulator().penalty_shootout(equal, _ScriptedRandomSource(draws)) == expected


def test_shootouts_have_no_additional_home_advantage() -> None:
    setup, simulator = _setup(), PoissonMatchSimulator()
    neutral = replace(setup, fixture=replace(setup.fixture, venue=Venue.NEUTRAL))
    huge_advantage = replace(setup, params=CompetitionParams(1.3, 100.0))

    for seed in range(100):
        rng = StdlibRandomSource(Seed(seed))
        assert simulator.penalty_shootout(setup, rng) == simulator.penalty_shootout(neutral, rng)
        assert simulator.penalty_shootout(setup, rng) == simulator.penalty_shootout(
            huge_advantage, rng
        )


def test_penalty_conversion_uses_both_adjusted_attack_and_opposing_vulnerability() -> None:
    setup = replace(_setup(), home=TeamStrength(2.0, 0.5), away=TeamStrength(0.5, 2.0))
    draws = _Draws(uniforms=deque([0.76, 0.74] * 3))

    assert PoissonMatchSimulator().penalty_shootout(setup, _ScriptedRandomSource(draws)) == Score(
        3, 0
    )


def test_equal_teams_have_symmetric_shootout_win_rates_and_strength_adds_a_bounded_bias() -> None:
    simulator, rng = PoissonMatchSimulator(), StdlibRandomSource(Seed(6021))
    wins_equal: list[int] = []
    wins_stronger: list[int] = []
    wins_weaker: list[int] = []
    sample_size = 10_000
    for index in range(sample_size):
        setup = _setup(fixture_id=f"shootout-{index}")
        equal = replace(setup, home=TeamStrength(1.0, 1.0), away=TeamStrength(1.0, 1.0))
        stronger = replace(setup, home=TeamStrength(2.5, 0.4), away=TeamStrength(0.4, 2.5))
        weaker = replace(stronger, home=stronger.away, away=stronger.home)
        for match, wins in [(equal, wins_equal), (stronger, wins_stronger), (weaker, wins_weaker)]:
            score = simulator.penalty_shootout(match, rng)
            assert score.home != score.away
            wins.append(int(score.home > score.away))
    # Six binomial SE at p=.5 is .03 for 10,000 samples; deterministic seed throughout.
    assert abs(mean(wins_equal) - 0.5) < 0.03
    assert 0.5 < mean(wins_stronger) < 0.75
    assert 0.25 < mean(wins_weaker) < 0.5
    assert abs(mean(wins_stronger) + mean(wins_weaker) - 1) < 0.03


@given(seed=st.integers(min_value=0, max_value=2**64 - 1))
def test_decisive_matches_always_produce_a_winner(seed: int) -> None:
    result = PoissonMatchSimulator().simulate(
        _setup(), StdlibRandomSource(Seed(seed)), decisive=True
    )

    assert result.winner in (Side.HOME, Side.AWAY)
