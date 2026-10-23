"""Poisson rates from adjusted team strengths and competition parameters (ADR-004)."""

import math

from mister.shared_kernel.errors import InvalidValueError
from mister.simulation.domain.model import CompetitionParams, TeamStrength, Venue

_MIN_GOALS = 0.05
_MAX_GOALS = 6.0
_MIN_LOG_GOALS = math.log(_MIN_GOALS)
_MAX_LOG_GOALS = math.log(_MAX_GOALS)


class PoissonGoalModel:
    """Calculate lambda without reapplying tactic or morale already present in strengths."""

    def expected_goals(
        self,
        team: TeamStrength,
        opponent: TeamStrength,
        venue: Venue,
        params: CompetitionParams,
        *,
        extra_time: bool = False,
    ) -> float:
        if not isinstance(venue, Venue):
            raise InvalidValueError(f"unknown match venue {venue!r}")
        home_factor = math.log(params.home_advantage)
        venue_factor = home_factor if venue is Venue.HOME else -home_factor
        if venue is Venue.NEUTRAL:
            venue_factor = 0.0
        # Logarithms keep valid finite inputs safe from intermediate overflow/underflow.
        log_rate = math.fsum(
            (math.log(params.base_goals), math.log(team.attack), math.log(opponent.defense),
             venue_factor)
        )
        if log_rate <= _MIN_LOG_GOALS:
            rate = _MIN_GOALS
        elif log_rate >= _MAX_LOG_GOALS:
            rate = _MAX_GOALS
        else:
            rate = math.exp(log_rate)
        return rate / 3 if extra_time else rate
