"""Deterministic match periods and strength-adjusted shootouts (ADR-004/005)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from mister.simulation.domain.goal_model import PoissonGoalModel
from mister.simulation.domain.model import MatchResult, Score, Venue

if TYPE_CHECKING:
    from mister.shared_kernel.randomness import RandomSource
    from mister.simulation.domain.model import MatchSetup
    from mister.simulation.domain.ports import GoalModel

_SHOOTOUT_KICKS = 5
_PENALTY_BASE_PROBABILITY = 0.75
_PENALTY_MAX_ADJUSTMENT = 0.05


class PoissonMatchSimulator:
    """Sample each side and period from its own leaf of the root random source."""

    def __init__(self, goal_model: GoalModel | None = None) -> None:
        self._goal_model = PoissonGoalModel() if goal_model is None else goal_model

    def simulate(
        self, setup: MatchSetup, rng: RandomSource, *, decisive: bool = False
    ) -> MatchResult:
        regulation = self._period(setup, rng, extra_time=False)
        if not decisive or regulation.home != regulation.away:
            return MatchResult(regulation)
        extra_time = self.extra_time(setup, rng)
        penalties = (
            self.penalty_shootout(setup, rng) if extra_time.home == extra_time.away else None
        )
        return MatchResult(regulation, extra_time, penalties)

    def extra_time(self, setup: MatchSetup, rng: RandomSource) -> Score:
        return self._period(setup, rng, extra_time=True)

    def _period(self, setup: MatchSetup, rng: RandomSource, *, extra_time: bool) -> Score:
        period = "extra_time" if extra_time else "goals"
        fixture_id = str(setup.fixture.fixture_id)
        home_venue = setup.fixture.venue
        away_venue = Venue.NEUTRAL if home_venue is Venue.NEUTRAL else Venue.AWAY
        home_rate = self._goal_model.expected_goals(
            setup.home, setup.away, home_venue, setup.params, extra_time=extra_time
        )
        away_rate = self._goal_model.expected_goals(
            setup.away, setup.home, away_venue, setup.params, extra_time=extra_time
        )
        return Score(
            rng.stream("match", fixture_id, period, "home").poisson(home_rate),
            rng.stream("match", fixture_id, period, "away").poisson(away_rate),
        )

    def penalty_shootout(self, setup: MatchSetup, rng: RandomSource) -> Score:
        stream = rng.stream("match", str(setup.fixture.fixture_id), "penalties")
        # Provisional game-design parameters: no historical conversion rate or home bonus.
        balance = 0.5 * math.fsum(
            (
                math.log(setup.home.attack),
                math.log(setup.away.defense),
                -math.log(setup.away.attack),
                -math.log(setup.home.defense),
            )
        )
        delta = _PENALTY_MAX_ADJUSTMENT * math.tanh(balance)
        home_probability = _PENALTY_BASE_PROBABILITY + delta
        away_probability = _PENALTY_BASE_PROBABILITY - delta
        home, away = 0, 0
        for kick in range(_SHOOTOUT_KICKS):
            remaining = _SHOOTOUT_KICKS - kick - 1
            home += stream.random() < home_probability
            if home > away + remaining + 1 or away > home + remaining:
                return Score(home, away)
            away += stream.random() < away_probability
            if home > away + remaining or away > home + remaining:
                return Score(home, away)
        # Marginalise pairs of misses. Each effective round either scores for both or
        # decides the winner, so joint goals before the outcome follow a geometric law.
        joint_goal = home_probability * away_probability
        home_wins = home_probability * (1 - away_probability)
        away_wins = (1 - home_probability) * away_probability
        decisive_probability = home_wins + away_wins
        joint_given_effective = joint_goal / (joint_goal + decisive_probability)
        joint_rounds = math.floor(math.log1p(-stream.random()) / math.log(joint_given_effective))
        home += joint_rounds
        away += joint_rounds
        if stream.random() < home_wins / decisive_probability:
            return Score(home + 1, away)
        return Score(home, away + 1)
