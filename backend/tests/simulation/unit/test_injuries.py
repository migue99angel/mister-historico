"""Seeded injury rules and dated absences for synthetic Test FC 2000-01."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.simulation.unit.test_lineup import TACTIC, squad

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import FixtureId, PlayerId
from mister.shared_kernel.randomness import Key, StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.domain.injuries import (
    Injury,
    apply_injuries,
    injured_until,
    injury_risk,
    simulate_injury,
)
from mister.simulation.domain.lineup import select_lineup
from mister.simulation.domain.model import Fitness

DAY = date(2000, 1, 1)
PLAYER = PlayerId("test-player")
FIXTURE = FixtureId("test-fc-match")


class FixedDraws(StdlibRandomSource):
    """Controlled leaf values with a record of the exact derivation and draw count."""

    def __init__(self, accident: float = 0.0, duration: float = 0.0) -> None:
        super().__init__(Seed(0))
        self.values = iter((accident, duration))
        self.keys: list[tuple[Key, ...]] = []
        self.draws = 0

    def stream(self, *keys: Key) -> "FixedDraws":
        self.keys.append(keys)
        return self

    def random(self) -> float:
        self.draws += 1
        return next(self.values)


def test_risk_uses_pre_match_fitness_and_minutes() -> None:
    assert injury_risk(Fitness(100), 90) == pytest.approx(0.02)
    assert injury_risk(Fitness(50), 90) == pytest.approx(0.04)
    assert injury_risk(Fitness(0), 120) == pytest.approx(0.08)


@given(st.integers(0, 100), st.integers(0, 100), st.integers(0, 120))
def test_risk_is_bounded_and_grows_as_fitness_drops(a: int, b: int, minutes: int) -> None:
    assert 0 <= injury_risk(Fitness(a), minutes) <= 1
    assert injury_risk(Fitness(min(a, b)), minutes) >= injury_risk(Fitness(max(a, b)), minutes)


@given(st.integers(0, 120), st.integers(0, 120), st.integers(0, 100))
def test_risk_grows_with_minutes(a: int, b: int, fitness: int) -> None:
    assert injury_risk(Fitness(fitness), min(a, b)) <= injury_risk(Fitness(fitness), max(a, b))


def test_non_participant_has_no_risk_no_injury_and_consumes_no_randomness() -> None:
    rng = FixedDraws()
    assert injury_risk(Fitness(0), 0) == 0
    assert simulate_injury(rng, FIXTURE, PLAYER, DAY, Fitness(0), 0) is None
    assert rng.keys == []
    assert rng.draws == 0


@pytest.mark.parametrize("accident,injured", [(0.0, True), (0.019999, True), (0.02, False), (0.99, False)])
def test_each_participant_uses_one_normative_leaf_and_two_draws(
    accident: float, injured: bool
) -> None:
    rng = FixedDraws(accident, 0.5)
    result = simulate_injury(rng, FIXTURE, PLAYER, DAY, Fitness(100), 90)
    assert (result is not None) is injured
    assert rng.keys == [("match", str(FIXTURE), "injury", str(PLAYER))]
    assert rng.draws == 2


@pytest.mark.parametrize("draw,days", [(0.0, 7), (0.599999, 7), (0.6, 14), (0.899999, 14), (0.9, 28), (0.999999, 28)])
def test_duration_distribution_has_provisional_seven_fourteen_and_twenty_eight_day_bands(
    draw: float, days: int
) -> None:
    result = simulate_injury(FixedDraws(0.0, draw), FIXTURE, PLAYER, DAY, Fitness(100), 90)
    assert result == Injury(PLAYER, DAY, days)


def test_same_seed_reproduces_injuries_and_durations_without_shifting_other_players() -> None:
    players = [PlayerId(f"test-player-{i}") for i in range(128)]
    rng = StdlibRandomSource(Seed(42))

    def outcomes(ids: list[PlayerId]) -> dict[PlayerId, Injury | None]:
        return {p: simulate_injury(rng, FIXTURE, p, DAY, Fitness(0), 120) for p in ids}

    forward = outcomes(players)
    assert any(injury is not None for injury in forward.values())
    assert outcomes(list(reversed(players))) == forward
    assert outcomes(players[::2]) == {p: forward[p] for p in players[::2]}
    fresh = StdlibRandomSource(Seed(42))
    assert simulate_injury(fresh, FIXTURE, players[0], DAY, Fitness(0), 120) == forward[players[0]]


def test_another_fixture_does_not_consume_the_first_fixtures_randomness() -> None:
    rng = StdlibRandomSource(Seed(42))
    before = simulate_injury(rng, FIXTURE, PLAYER, DAY, Fitness(0), 120)
    simulate_injury(rng, FixtureId("test-other-match"), PLAYER, DAY, Fitness(0), 120)
    assert simulate_injury(rng, FIXTURE, PLAYER, DAY, Fitness(0), 120) == before
    recorded = FixedDraws()
    simulate_injury(recorded, FixtureId("test-other-match"), PLAYER, DAY, Fitness(0), 120)
    assert recorded.keys == [("match", "test-other-match", "injury", "test-player")]


@pytest.mark.parametrize("offset,expected", [(-1, None), (0, 7), (6, 7), (7, None), (8, None)])
def test_absence_is_start_inclusive_and_return_date_exclusive(offset: int, expected: int | None) -> None:
    injuries = (Injury(PLAYER, DAY, 7, forced=True),)
    assert injured_until(PLAYER, injuries, DAY + timedelta(days=offset)) == (
        None if expected is None else DAY + timedelta(days=expected)
    )


def test_overlaps_take_latest_active_end_without_applying_future_events_early() -> None:
    injuries = (Injury(PLAYER, DAY, 7), Injury(PLAYER, DAY + timedelta(days=3), 14, True))
    assert injured_until(PLAYER, injuries, DAY + timedelta(days=2)) == DAY + timedelta(days=7)
    assert injured_until(PLAYER, injuries, DAY + timedelta(days=3)) == DAY + timedelta(days=17)
    assert injured_until(PLAYER, tuple(reversed(injuries)), DAY + timedelta(days=7)) == DAY + timedelta(days=17)


def test_disjoint_historical_absences_keep_the_healthy_gap() -> None:
    injuries = (Injury(PLAYER, DAY, 2, True), Injury(PLAYER, DAY + timedelta(days=5), 2, True))
    assert injured_until(PLAYER, injuries, DAY + timedelta(days=2)) is None
    assert injured_until(PLAYER, injuries, DAY + timedelta(days=4)) is None
    assert injured_until(PLAYER, injuries, DAY + timedelta(days=5)) == DAY + timedelta(days=7)
    assert injured_until(PlayerId("test-other-player"), injuries, DAY) is None


@given(st.integers(0, 2**64 - 1))
def test_forced_absences_apply_before_lineup_with_any_seed(seed: int) -> None:
    players = squad()
    target = select_lineup(players, TACTIC).starters[0].player.player_id
    forced = Injury(target, DAY, 7, True)
    # Different seeds may affect accidental injuries, never the forced interval.
    simulate_injury(StdlibRandomSource(Seed(seed)), FIXTURE, target, DAY, Fitness(100), 90)
    updated = apply_injuries(players, (forced,), DAY)
    assert target not in {p.player.player_id for p in select_lineup(updated, TACTIC).starters}
    assert players == squad()
    assert forced.forced


def test_projection_clears_expired_injuries_and_never_preapplies_future_absences() -> None:
    players = squad()
    target = players[0].player_id
    injury = Injury(target, DAY, 7, True)
    active = apply_injuries(players, (injury,), DAY)
    assert active[0].injured
    assert not apply_injuries(active, (injury,), DAY + timedelta(days=7))[0].injured
    assert not apply_injuries(players, (injury,), DAY - timedelta(days=1))[0].injured
    assert active[1:] == players[1:]


def test_projection_rejects_an_injured_flag_without_an_explicit_started_interval() -> None:
    players = squad()
    flagged = (replace(players[0], injured=True), *players[1:])
    with pytest.raises(InvalidValueError):
        apply_injuries(flagged, (), DAY)
    with pytest.raises(InvalidValueError):
        apply_injuries(flagged, (Injury(players[0].player_id, DAY + timedelta(days=1), 7),), DAY)


def test_projection_rejects_missing_players_and_duplicate_squad_ids() -> None:
    with pytest.raises(InvalidValueError):
        apply_injuries(squad(), (Injury(PLAYER, DAY, 7, True),), DAY)
    with pytest.raises(InvalidValueError):
        apply_injuries((squad()[0], squad()[0]), (), DAY)


def test_injuries_are_immutable_and_expose_first_available_day() -> None:
    injury = Injury(PLAYER, DAY, 7)
    assert injury.available_on == DAY + timedelta(days=7)
    with pytest.raises(FrozenInstanceError):
        injury.days = 9  # type: ignore[misc]


@pytest.mark.parametrize("days", [0, -1, True, 1.5, "7", None, 10**400])
def test_injury_rejects_invalid_or_unrepresentable_durations(days: Any) -> None:
    with pytest.raises(InvalidValueError):
        Injury(PLAYER, DAY, days)


def test_last_representable_return_day_is_valid_but_overflow_is_rejected() -> None:
    assert Injury(PLAYER, date.max - timedelta(days=1), 1).available_on == date.max
    with pytest.raises(InvalidValueError):
        Injury(PLAYER, date.max, 1)
    with pytest.raises(InvalidValueError):
        simulate_injury(FixedDraws(), FIXTURE, PLAYER, date.max, Fitness(100), 90)


@pytest.mark.parametrize("bad", [None, "2000-01-01", datetime(2000, 1, 1)])
def test_injury_operations_require_calendar_dates(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        Injury(PLAYER, bad, 7)
    with pytest.raises(InvalidValueError):
        injured_until(PLAYER, (), bad)
    with pytest.raises(InvalidValueError):
        apply_injuries(squad(), (), bad)
    with pytest.raises(InvalidValueError):
        simulate_injury(FixedDraws(), FIXTURE, PLAYER, bad, Fitness(100), 90)


@pytest.mark.parametrize("bad", [None, "test-player", True])
def test_injury_operations_require_typed_player_ids(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        Injury(bad, DAY, 7)
    with pytest.raises(InvalidValueError):
        injured_until(bad, (), DAY)
    with pytest.raises(InvalidValueError):
        simulate_injury(FixedDraws(), FIXTURE, bad, DAY, Fitness(100), 90)


@pytest.mark.parametrize("bad", [None, "test-match", True])
def test_simulation_requires_a_typed_fixture_id(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        simulate_injury(FixedDraws(), bad, PLAYER, DAY, Fitness(100), 90)


@pytest.mark.parametrize("bad", [-1, 121, True, 1.5, None])
def test_injury_rules_reject_invalid_minutes(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        injury_risk(Fitness(100), bad)
    with pytest.raises(InvalidValueError):
        simulate_injury(FixedDraws(), FIXTURE, PLAYER, DAY, Fitness(100), bad)


@pytest.mark.parametrize("bad", [None, 100, True])
def test_risk_requires_a_fitness_value_object(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        injury_risk(bad, 90)


@pytest.mark.parametrize("bad", [None, 1, "true"])
def test_forced_flag_requires_a_boolean(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        Injury(PLAYER, DAY, 7, bad)
