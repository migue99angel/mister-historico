"""The strategy ports can be implemented by plain classes (structural typing, checked by mypy)."""

from datetime import date

from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.shared_kernel.randomness import RandomSource, StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.domain.model import (
    CompetitionParams,
    FixtureSpec,
    MatchResult,
    MatchSetup,
    Score,
    TeamStrength,
    Venue,
)

# Runtime import on purpose: it makes coverage measure `ports.py`.
from mister.simulation.domain.ports import GoalModel, MatchSimulator  # noqa: TC001


class _ConstantGoalModel:
    def expected_goals(
        self,
        team: TeamStrength,
        opponent: TeamStrength,
        venue: Venue,
        params: CompetitionParams,
        *,
        extra_time: bool = False,
    ) -> float:
        return params.base_goals / (3 if extra_time else 1)


class _ScriptedSimulator:
    def simulate(
        self, setup: MatchSetup, rng: RandomSource, *, decisive: bool = False
    ) -> MatchResult:
        return MatchResult(Score(1, 0))

    def extra_time(self, setup: MatchSetup, rng: RandomSource) -> Score:
        return Score(0, 0)

    def penalty_shootout(self, setup: MatchSetup, rng: RandomSource) -> Score:
        return Score(4, 3)


def _setup() -> MatchSetup:
    fixture = FixtureSpec(
        FixtureId("fx-1"),
        date(2000, 9, 3),
        CompetitionId("liga-test"),
        ClubSeasonId("test-fc-2000-01"),
        ClubSeasonId("demo-athletic-2000-01"),
    )
    return MatchSetup(
        fixture, TeamStrength(1.0, 1.0), TeamStrength(1.0, 1.0), CompetitionParams(1.3, 1.15)
    )


def test_a_goal_model_can_be_a_plain_class() -> None:
    setup = _setup()
    model: GoalModel = _ConstantGoalModel()

    assert model.expected_goals(setup.home, setup.away, Venue.HOME, setup.params) == 1.3
    assert (
        model.expected_goals(setup.home, setup.away, Venue.HOME, setup.params, extra_time=True)
        < 1.3
    )


def test_a_match_simulator_can_be_a_plain_class() -> None:
    setup = _setup()
    rng = StdlibRandomSource(Seed(1))
    simulator: MatchSimulator = _ScriptedSimulator()

    assert simulator.simulate(setup, rng).regulation == Score(1, 0)
    assert simulator.extra_time(setup, rng) == Score(0, 0)
    assert simulator.penalty_shootout(setup, rng) == Score(4, 3)
