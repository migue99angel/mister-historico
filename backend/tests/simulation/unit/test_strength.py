"""ADR-004 strength against a fixed Test FC reference, with no historical data."""

import math
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId
from mister.simulation.domain.lineup import select_lineup
from mister.simulation.domain.model import (
    AggregateIndices,
    Fitness,
    Morale,
    Position,
    Rating,
    SimTeam,
    Style,
    Tactic,
)
from mister.simulation.domain.strength import (
    StrengthReference,
    calculate_strength,
    lineup_indices,
    morale_multiplier,
    tactical_multipliers,
)
from tests.simulation.unit.test_lineup import TACTIC, squad


def team() -> SimTeam:
    return SimTeam(ClubSeasonId("test-fc-2000-01"), squad=squad(), tactic=TACTIC)


def reference() -> StrengthReference:
    return StrengthReference.from_indices((AggregateIndices(70, 70),))


def test_line_weights_are_exactly_the_adr_attack_and_defense_weights() -> None:
    ratings = {Position.GK: 80, Position.DF: 76, Position.MF: 78, Position.FW: 82}
    players = tuple(replace(player, rating=Rating(ratings[player.position])) for player in squad())
    indices = lineup_indices(select_lineup(players, TACTIC))
    assert indices.attack == pytest.approx(79.7)
    assert indices.defense == pytest.approx(77.5)


def test_a_better_forward_increases_attack_without_changing_defense() -> None:
    original = team()
    assert original.squad is not None
    improved = replace(
        original,
        squad=tuple(
            replace(player, rating=Rating(90)) if player.position is Position.FW else player
            for player in original.squad
        ),
    )
    before = calculate_strength(original, reference())
    after = calculate_strength(improved, reference())
    assert after.attack > before.attack
    assert after.defense == before.defense


def test_removing_a_rivals_best_forward_reduces_attack_against_the_fixed_reference() -> None:
    original = team()
    assert original.squad is not None
    weakened = replace(
        original,
        squad=tuple(
            player for player in original.squad if player.player_id != original.squad[9].player_id
        ),
    )
    fixed = StrengthReference.from_teams((original,))
    assert (
        calculate_strength(weakened, fixed, neutral=True).attack
        < calculate_strength(original, fixed, neutral=True).attack
    )
    assert fixed == StrengthReference.from_teams((original,))


def test_reference_is_the_mean_of_exponentials_rather_than_the_exponential_of_the_mean() -> None:
    fixed = StrengthReference.from_indices((AggregateIndices(60, 80), AggregateIndices(80, 60)))
    assert fixed.attack_mean == pytest.approx((math.exp(2.4) + math.exp(3.2)) / 2)
    assert fixed.defense_mean == pytest.approx((math.exp(-3.2) + math.exp(-2.4)) / 2)


def test_content_pool_normalizes_to_one_for_both_factors() -> None:
    indices = tuple(AggregateIndices(value, value) for value in (60, 70, 80))
    fixed = StrengthReference.from_indices(indices)
    teams = tuple(
        SimTeam(ClubSeasonId(f"test-rival-{i}"), aggregate=value) for i, value in enumerate(indices)
    )
    strengths = tuple(calculate_strength(value, fixed) for value in teams)
    assert sum(value.attack for value in strengths) / len(strengths) == pytest.approx(1)
    assert sum(value.defense for value in strengths) / len(strengths) == pytest.approx(1)


def test_an_aggregate_uses_fixed_indices_and_ignores_morale() -> None:
    rival = SimTeam(ClubSeasonId("test-rival-2000-01"), aggregate=AggregateIndices(75, 65))
    result = calculate_strength(rival, reference())
    assert result.attack == pytest.approx(math.exp(0.2))
    assert result.defense == pytest.approx(math.exp(0.2))
    assert result == calculate_strength(replace(rival, morale=Morale(0)), reference())


def test_low_team_morale_reduces_attack_and_increases_vulnerability_with_exact_bounds() -> None:
    low = calculate_strength(replace(team(), morale=Morale(0)), reference())
    high = calculate_strength(replace(team(), morale=Morale(100)), reference())
    assert high.attack / low.attack == pytest.approx(1.06 / 0.94)
    assert low.defense / high.defense == pytest.approx(1.06 / 0.94)


@given(st.integers(min_value=0, max_value=100))
def test_team_morale_multiplier_stays_in_adr_bounds(value: int) -> None:
    assert 0.94 <= morale_multiplier(Morale(value)) <= 1.06


def test_neutral_rivals_ignore_state_and_tactical_adjustments() -> None:
    original = team()
    assert original.squad is not None
    altered = replace(
        original,
        squad=tuple(
            replace(player, fitness=Fitness(0), morale=Morale(0), age=70)
            for player in original.squad
        ),
        morale=Morale(0),
        tactic=Tactic(Style.PRESSING, "4-4-2"),
    )
    assert calculate_strength(altered, reference(), neutral=True) == calculate_strength(
        original, reference(), neutral=True
    )


def test_reference_squads_use_content_ratings_and_no_adjustments() -> None:
    original = team()
    assert original.squad is not None
    altered = replace(
        original,
        squad=tuple(
            replace(player, fitness=Fitness(0), morale=Morale(0), injured=True)
            for player in original.squad
        ),
        morale=Morale(0),
        tactic=Tactic(Style.PRESSING, "4-4-2"),
    )
    assert StrengthReference.from_teams((original,)) == StrengthReference.from_teams((altered,))


@pytest.mark.parametrize("style", list(Style))
def test_styles_have_no_free_double_bonus_and_respect_component_bounds(style: Style) -> None:
    attack, defense = tactical_multipliers(Tactic(style, "4-4-2"), select_lineup(squad(), TACTIC))
    assert 0.95 <= attack <= 1.05
    assert 0.95 <= defense <= 1.05
    assert -0.02 - 1e-12 <= (attack - 1) + (1 - defense) <= 0.02 + 1e-12


@given(
    st.sampled_from(list(Style)),
    st.integers(min_value=0, max_value=150),
    st.integers(min_value=1, max_value=99),
)
def test_total_tactical_adjustments_stay_in_adr_bounds(style: Style, age: int, rating: int) -> None:
    players = tuple(
        replace(
            player,
            age=age,
            rating=Rating(rating) if player.position is Position.MF else player.rating,
        )
        for player in squad()
    )
    attack, defense = tactical_multipliers(Tactic(style, "4-4-2"), select_lineup(players, TACTIC))
    assert 0.92 <= attack <= 1.08
    assert 0.92 <= defense <= 1.08


def test_pressing_fits_young_players_better_than_veterans() -> None:
    tactic = Tactic(Style.PRESSING, "4-4-2")
    young = select_lineup(tuple(replace(player, age=17) for player in squad()), tactic)
    old = select_lineup(tuple(replace(player, age=37) for player in squad()), tactic)
    young_attack, young_defense = tactical_multipliers(tactic, young)
    old_attack, old_defense = tactical_multipliers(tactic, old)
    assert young_attack > old_attack
    assert young_defense < old_defense


def test_unknown_age_contributes_zero_without_imputing_known_ages() -> None:
    tactic = Tactic(Style.PRESSING, "4-4-2")
    unknown = tactical_multipliers(tactic, select_lineup(squad(), tactic))
    players = tuple(
        replace(player, age=17) if i == 0 else player for i, player in enumerate(squad())
    )
    partial = tactical_multipliers(tactic, select_lineup(players, tactic))
    assert partial[0] - unknown[0] == pytest.approx(0.03 / 11)
    assert unknown == pytest.approx((1.04, 1.04))


def test_normalization_safety_clamps_both_extremes() -> None:
    for own, other, expected in [
        (AggregateIndices(99, 1), AggregateIndices(1, 99), 2.5),
        (AggregateIndices(1, 99), AggregateIndices(99, 1), 0.4),
    ]:
        result = calculate_strength(
            SimTeam(ClubSeasonId("test-rival"), aggregate=own),
            StrengthReference.from_indices((other,)),
        )
        assert (result.attack, result.defense) == (expected, expected)


def test_reference_rejects_an_empty_pool() -> None:
    with pytest.raises(InvalidValueError, match="reference"):
        StrengthReference.from_indices(())


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True])
def test_reference_rejects_invalid_denominators(value: float) -> None:
    with pytest.raises(InvalidValueError):
        StrengthReference(value, 1)
    with pytest.raises(InvalidValueError):
        StrengthReference(1, value)
