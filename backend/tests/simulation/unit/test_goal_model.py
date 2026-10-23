"""Expected goals use already adjusted strengths and the competition's own parameters."""

import math
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mister.shared_kernel.errors import InvalidValueError
from mister.simulation.domain.goal_model import PoissonGoalModel
from mister.simulation.domain.model import CompetitionParams, TeamStrength, Venue
from mister.simulation.domain.ports import GoalModel  # noqa: TC001

_FACTOR = st.floats(min_value=0.4, max_value=2.5)
_BASE = st.floats(min_value=0.5, max_value=2.0)


@pytest.mark.parametrize(
    ("venue", "factor"), [(Venue.HOME, 1.15), (Venue.AWAY, 1 / 1.15), (Venue.NEUTRAL, 1.0)]
)
def test_expected_goals_multiply_adjusted_attack_opponent_vulnerability_and_venue(
    venue: Venue, factor: float
) -> None:
    model: GoalModel = PoissonGoalModel()

    actual = model.expected_goals(
        TeamStrength(1.2, 0.8), TeamStrength(1.4, 1.1), venue, CompetitionParams(1.3, 1.15)
    )

    assert actual == pytest.approx(1.3 * 1.2 * 1.1 * factor)


@given(attack=_FACTOR, increase=st.floats(min_value=0.001, max_value=0.5), defense=_FACTOR)
def test_increasing_own_attack_cannot_reduce_expected_goals(
    attack: float, increase: float, defense: float
) -> None:
    model = PoissonGoalModel()
    params = CompetitionParams(1.3, 1.15)
    opponent = TeamStrength(1.0, defense)

    assert model.expected_goals(
        TeamStrength(attack + increase, 1.0), opponent, Venue.HOME, params
    ) >= model.expected_goals(TeamStrength(attack, 1.0), opponent, Venue.HOME, params)


@given(defense=_FACTOR, improvement=st.floats(min_value=0.001, max_value=0.3), attack=_FACTOR)
def test_stronger_opponent_defense_means_lower_vulnerability_and_cannot_raise_goals(
    defense: float, improvement: float, attack: float
) -> None:
    model = PoissonGoalModel()
    params = CompetitionParams(1.3, 1.15)
    team = TeamStrength(attack, 1.0)

    assert model.expected_goals(
        team, TeamStrength(1.0, defense - improvement), Venue.HOME, params
    ) <= model.expected_goals(team, TeamStrength(1.0, defense), Venue.HOME, params)


@given(base=_BASE, advantage=st.floats(min_value=1.001, max_value=2.0))
def test_home_advantage_above_one_increases_goals_and_away_decreases_them(
    base: float, advantage: float
) -> None:
    model = PoissonGoalModel()
    team = TeamStrength(1.0, 1.0)
    params = CompetitionParams(base, advantage)

    assert model.expected_goals(team, team, Venue.AWAY, params) < base
    assert model.expected_goals(team, team, Venue.HOME, params) > base


@given(attack=_FACTOR, defense=_FACTOR, advantage=st.floats(min_value=0.01, max_value=100))
def test_neutral_ground_ignores_the_home_advantage(
    attack: float, defense: float, advantage: float
) -> None:
    model = PoissonGoalModel()
    team, opponent = TeamStrength(attack, 1.0), TeamStrength(1.0, defense)

    assert model.expected_goals(
        team, opponent, Venue.NEUTRAL, CompetitionParams(1.3, advantage)
    ) == model.expected_goals(team, opponent, Venue.NEUTRAL, CompetitionParams(1.3, 1.0))


@given(
    attack=st.floats(min_value=5e-324, max_value=1e308),
    defense=st.floats(min_value=5e-324, max_value=1e308),
    base=st.floats(min_value=5e-324, max_value=1e308),
    advantage=st.floats(min_value=5e-324, max_value=1e308),
    venue=st.sampled_from(list(Venue)),
)
def test_all_valid_positive_parameters_produce_finite_clamped_goals(
    attack: float, defense: float, base: float, advantage: float, venue: Venue
) -> None:
    result = PoissonGoalModel().expected_goals(
        TeamStrength(attack, 1.0),
        TeamStrength(1.0, defense),
        venue,
        CompetitionParams(base, advantage),
    )

    assert math.isfinite(result)
    assert 0.05 <= result <= 6.0


@pytest.mark.parametrize(("base", "expected"), [(1e-300, 0.05), (1.8, 1.8), (1e300, 6.0)])
def test_extra_time_is_one_third_of_the_clamped_regulation_lambda(
    base: float, expected: float
) -> None:
    team = TeamStrength(1.0, 1.0)

    assert PoissonGoalModel().expected_goals(
        team, team, Venue.HOME, CompetitionParams(base, 1.0), extra_time=True
    ) == pytest.approx(expected / 3)


@pytest.mark.parametrize("venue", ["home", "stadium", None, True])
def test_expected_goals_rejects_a_venue_outside_the_domain_vocabulary(venue: Any) -> None:
    team = TeamStrength(1.0, 1.0)

    with pytest.raises(InvalidValueError):
        PoissonGoalModel().expected_goals(team, team, venue, CompetitionParams(1.3, 1.15))


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf"), True])
def test_invalid_strength_and_competition_parameters_are_rejected_at_the_value_boundary(
    value: Any,
) -> None:
    with pytest.raises(InvalidValueError):
        TeamStrength(value, 1.0)
    with pytest.raises(InvalidValueError):
        TeamStrength(1.0, value)
    with pytest.raises(InvalidValueError):
        CompetitionParams(value, 1.0)
    with pytest.raises(InvalidValueError):
        CompetitionParams(1.3, value)


@pytest.mark.parametrize(
    ("attack", "defense", "base", "advantage", "venue"),
    [
        (1e-300, 1e300, 1e-300, 1e300, Venue.HOME),
        (1e300, 1e-300, 1e300, 1e300, Venue.AWAY),
    ],
)
def test_intermediate_overflow_or_underflow_does_not_change_a_finite_product(
    attack: float, defense: float, base: float, advantage: float, venue: Venue
) -> None:
    assert PoissonGoalModel().expected_goals(
        TeamStrength(attack, 1.0),
        TeamStrength(1.0, defense),
        venue,
        CompetitionParams(base, advantage),
    ) == pytest.approx(1.0)
