"""Value objects of the simulation domain: ranges, formats and result rules."""

from dataclasses import FrozenInstanceError
from datetime import date
from typing import Any

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.simulation.domain.model import (
    AggregateIndices,
    CompetitionParams,
    Fitness,
    FixtureSpec,
    MatchResult,
    Morale,
    Position,
    Rating,
    Score,
    Side,
    SimPlayer,
    SimTeam,
    Style,
    Tactic,
    TeamStrength,
    Venue,
)


@pytest.mark.parametrize("cls", [Rating, Morale, Fitness])
def test_bounded_values_are_immutable_and_compare_by_value(cls: Any) -> None:
    value = cls(50)

    assert value == cls(50)
    with pytest.raises(FrozenInstanceError):
        value.value = 51


@pytest.mark.parametrize("value", [0, 100, -1, 1.5, True, "50"])
def test_rating_rejects_values_outside_1_to_99(value: Any) -> None:
    with pytest.raises(InvalidValueError):
        Rating(value)


@pytest.mark.parametrize("value", [1, 99])
def test_rating_accepts_its_bounds(value: int) -> None:
    assert Rating(value).value == value


@pytest.mark.parametrize("cls", [Morale, Fitness])
@pytest.mark.parametrize("value", [-1, 101, 50.0, False])
def test_morale_and_fitness_reject_values_outside_0_to_100(cls: Any, value: Any) -> None:
    with pytest.raises(InvalidValueError):
        cls(value)


@pytest.mark.parametrize("cls", [Morale, Fitness])
@pytest.mark.parametrize("value", [0, 100])
def test_morale_and_fitness_accept_their_bounds(cls: Any, value: int) -> None:
    assert cls(value).value == value


@pytest.mark.parametrize(
    ("attack", "defense"),
    [(0.0, 1.0), (1.0, -0.5), (float("nan"), 1.0), (1.0, float("inf")), (1, 1.0)],
)
def test_team_strength_rejects_non_positive_or_non_finite_factors(
    attack: Any, defense: Any
) -> None:
    with pytest.raises(InvalidValueError):
        TeamStrength(attack, defense)


def test_team_strength_keeps_its_factors() -> None:
    strength = TeamStrength(1.2, 0.8)

    assert (strength.attack, strength.defense) == (1.2, 0.8)


@pytest.mark.parametrize("system", ["4-3-3", "4-2-3-1", "4-1-2-1-2", "3-4-3", "6-2-2"])
def test_tactic_accepts_canonical_systems(system: str) -> None:
    assert Tactic(Style.PRESSING, system).system == system


@pytest.mark.parametrize(
    "system",
    ["4-4", "0-5-5", "7-2-1", "1-1-1-1-1-1", "4-4-1", "4-3-3-", "a-b-c", "4-4-2 ", ""],
)
def test_tactic_rejects_invalid_systems(system: str) -> None:
    with pytest.raises(InvalidValueError):
        Tactic(Style.BALANCED, system)


def test_tactic_rejects_a_style_outside_the_vocabulary() -> None:
    with pytest.raises(InvalidValueError):
        Tactic("tiki-taka", "4-4-2")  # type: ignore[arg-type]


def test_style_vocabulary_is_canonical() -> None:
    assert {style.value for style in Style} == {"pressing", "counter", "possession", "balanced"}


@pytest.mark.parametrize("goals", [(-1, 0), (0, -1)])
def test_score_rejects_negative_goals(goals: tuple[int, int]) -> None:
    with pytest.raises(InvalidValueError):
        Score(*goals)


def test_score_rejects_non_integer_goals() -> None:
    with pytest.raises(InvalidValueError):
        Score(1.5, 0)  # type: ignore[arg-type]


def test_regulation_win_decides_the_winner() -> None:
    assert MatchResult(Score(2, 1)).winner is Side.HOME
    assert MatchResult(Score(0, 3)).winner is Side.AWAY


def test_a_regulation_draw_without_tiebreakers_has_no_winner() -> None:
    assert MatchResult(Score(1, 1)).winner is None


def test_extra_time_goals_decide_a_regulation_draw() -> None:
    result = MatchResult(Score(1, 1), extra_time=Score(0, 1))

    assert result.winner is Side.AWAY
    assert result.total == Score(1, 2)


def test_penalties_decide_when_extra_time_stays_level() -> None:
    result = MatchResult(Score(1, 1), extra_time=Score(0, 0), penalties=Score(4, 3))

    assert result.winner is Side.HOME


def test_penalties_may_follow_a_regulation_draw_directly() -> None:
    assert MatchResult(Score(0, 0), penalties=Score(3, 5)).winner is Side.AWAY


def test_extra_time_requires_a_regulation_draw() -> None:
    with pytest.raises(InvalidValueError):
        MatchResult(Score(2, 1), extra_time=Score(0, 0))


def test_penalties_require_a_level_score_after_extra_time() -> None:
    with pytest.raises(InvalidValueError):
        MatchResult(Score(1, 1), extra_time=Score(1, 0), penalties=Score(4, 3))
    with pytest.raises(InvalidValueError):
        MatchResult(Score(2, 1), penalties=Score(4, 3))


def test_a_shootout_cannot_end_level() -> None:
    with pytest.raises(InvalidValueError):
        MatchResult(Score(1, 1), penalties=Score(3, 3))


_HOME = ClubSeasonId("test-fc-2000-01")
_AWAY = ClubSeasonId("demo-athletic-2000-01")


def _fixture(**overrides: Any) -> FixtureSpec:
    fields: dict[str, Any] = {
        "fixture_id": FixtureId("fx-1"),
        "date": date(2000, 9, 3),
        "competition_id": CompetitionId("liga-test"),
        "home": _HOME,
        "away": _AWAY,
    }
    return FixtureSpec(**{**fields, **overrides})


def test_fixture_defaults_to_a_home_ground_league_match() -> None:
    fixture = _fixture()

    assert fixture.venue is Venue.HOME
    assert fixture.key is False
    assert (fixture.leg, fixture.stage, fixture.group) == (None, None, None)


def test_fixture_accepts_a_neutral_knockout_leg() -> None:
    fixture = _fixture(venue=Venue.NEUTRAL, key=True, stage="final", leg=1)

    assert fixture.venue is Venue.NEUTRAL
    assert fixture.leg == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"away": _HOME},
        {"venue": Venue.AWAY},
        {"leg": 3, "stage": "semifinal"},
        {"leg": 1},
        {"group": "A"},
    ],
    ids=["same-team", "away-venue", "bad-leg", "leg-without-stage", "group-without-stage"],
)
def test_fixture_rejects_inconsistent_fields(overrides: dict[str, Any]) -> None:
    with pytest.raises(InvalidValueError):
        _fixture(**overrides)


def _player(index: int, **overrides: Any) -> SimPlayer:
    fields: dict[str, Any] = {
        "player_id": PlayerId(f"player-{index}"),
        "position": Position.MF,
        "rating": Rating(70),
    }
    return SimPlayer(**{**fields, **overrides})


def _squad(size: int = 11) -> tuple[SimPlayer, ...]:
    return tuple(_player(i) for i in range(size))


def test_sim_player_defaults_to_neutral_morale_full_fitness_and_healthy() -> None:
    player = _player(1)

    assert player.morale == Morale(50)
    assert player.fitness == Fitness(100)
    assert player.injured is False


def test_sim_player_rejects_wrong_value_object_types() -> None:
    with pytest.raises(InvalidValueError):
        _player(1, rating=70)
    with pytest.raises(InvalidValueError):
        _player(1, position="GK")


def test_squad_team_has_a_roster_and_a_tactic() -> None:
    team = SimTeam(_HOME, squad=_squad(), tactic=Tactic(Style.BALANCED, "4-4-2"))

    assert team.aggregate is None
    assert team.morale == Morale(50)


def test_aggregate_team_has_fixed_indices_and_no_roster() -> None:
    team = SimTeam(_AWAY, aggregate=AggregateIndices(attack=68.5, defense=71.0))

    assert team.squad is None
    assert team.tactic is None


def test_team_cannot_be_a_squad_and_an_aggregate_at_once() -> None:
    with pytest.raises(InvalidValueError):
        SimTeam(
            _HOME,
            squad=_squad(),
            tactic=Tactic(Style.BALANCED, "4-4-2"),
            aggregate=AggregateIndices(70.0, 70.0),
        )


def test_team_needs_either_a_squad_or_an_aggregate() -> None:
    with pytest.raises(InvalidValueError):
        SimTeam(_HOME)


def test_squad_team_requires_a_tactic_and_an_aggregate_forbids_one() -> None:
    with pytest.raises(InvalidValueError):
        SimTeam(_HOME, squad=_squad())
    with pytest.raises(InvalidValueError):
        SimTeam(_HOME, aggregate=AggregateIndices(70.0, 70.0), tactic=Tactic(Style.COUNTER, "4-4-2"))


def test_squad_needs_eleven_distinct_players() -> None:
    tactic = Tactic(Style.BALANCED, "4-4-2")
    with pytest.raises(InvalidValueError):
        SimTeam(_HOME, squad=_squad(10), tactic=tactic)
    with pytest.raises(InvalidValueError):
        SimTeam(_HOME, squad=(*_squad(10), _player(0)), tactic=tactic)


@pytest.mark.parametrize(("attack", "defense"), [(0.0, 50.0), (50.0, 100.0), (float("nan"), 50.0)])
def test_aggregate_indices_must_be_rating_points(attack: float, defense: float) -> None:
    with pytest.raises(InvalidValueError):
        AggregateIndices(attack, defense)


@pytest.mark.parametrize(("base", "advantage"), [(0.0, 1.1), (1.3, 0.0), (1.3, float("inf"))])
def test_competition_params_must_be_positive_and_finite(base: float, advantage: float) -> None:
    with pytest.raises(InvalidValueError):
        CompetitionParams(base, advantage)
