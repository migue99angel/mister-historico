"""Provisional fitness rules for synthetic Test FC 2000-01."""

from datetime import date
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mister.shared_kernel.errors import InvalidValueError
from mister.simulation.domain.fitness import match_fitness, recover_between, recover_fitness
from mister.simulation.domain.model import Fitness, Priority


def test_recovery_adds_four_points_per_day_and_caps_at_full_fitness() -> None:
    assert recover_fitness(Fitness(50), 3) == Fitness(62)
    assert recover_fitness(Fitness(99), 1) == Fitness(100)


@pytest.mark.parametrize("priority,expected", [(Priority.LOW, 90), (Priority.NORMAL, 89), (Priority.HIGH, 88)])
def test_priority_scales_match_effort(priority: Priority, expected: int) -> None:
    assert match_fitness(Fitness(100), 90, priority) == Fitness(expected)


def test_extra_time_and_partial_minutes_use_ceiling_and_floor_at_zero() -> None:
    assert match_fitness(Fitness(100), 120, Priority.HIGH) == Fitness(84)
    assert match_fitness(Fitness(100), 1, Priority.HIGH) == Fitness(99)
    assert match_fitness(Fitness(3), 90, Priority.HIGH) == Fitness(0)


@given(st.integers(0, 100), st.integers(0, 120), st.sampled_from(list(Priority)))
def test_match_fitness_stays_bounded_and_zero_minutes_cost_nothing(
    initial: int, minutes: int, priority: Priority
) -> None:
    assert 0 <= match_fitness(Fitness(initial), minutes, priority).value <= initial
    assert match_fitness(Fitness(initial), 0, priority) == Fitness(initial)


def test_congestion_reduces_pre_match_fitness_through_shorter_recovery() -> None:
    exhausted = match_fitness(Fitness(80), 90, Priority.HIGH)
    assert recover_fitness(exhausted, 2).value < recover_fitness(exhausted, 7).value


@given(st.integers(0, 100), st.integers(0, 100), st.integers(0, 100))
def test_recovery_composes_without_counting_a_block_boundary_twice(
    initial: int, first: int, second: int
) -> None:
    assert recover_fitness(recover_fitness(Fitness(initial), first), second) == recover_fitness(
        Fitness(initial), first + second
    )


def test_calendar_recovery_uses_elapsed_days_and_allows_same_day() -> None:
    start, middle, end = date(2000, 1, 1), date(2000, 1, 3), date(2000, 1, 5)
    assert recover_between(Fitness(30), start, start) == Fitness(30)
    assert recover_between(recover_between(Fitness(30), start, middle), middle, end) == recover_between(
        Fitness(30), start, end
    )


def test_huge_recovery_saturates_without_float_or_timedelta_overflow() -> None:
    assert recover_fitness(Fitness(0), 10**400) == Fitness(100)
    assert recover_between(Fitness(0), date.min, date.max) == Fitness(100)


@pytest.mark.parametrize("bad", [-1, True, 1.5, "2", None])
def test_recovery_rejects_invalid_day_counts(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        recover_fitness(Fitness(50), bad)


@pytest.mark.parametrize("bad", [-1, 121, 10**400, True, 1.5, "90", None])
def test_match_rejects_invalid_minutes(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        match_fitness(Fitness(50), bad, Priority.NORMAL)


@pytest.mark.parametrize("bad", ["high", None, True])
def test_match_rejects_unknown_priorities(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        match_fitness(Fitness(50), 90, bad)


def test_calendar_recovery_rejects_reversed_or_invalid_dates() -> None:
    with pytest.raises(InvalidValueError):
        recover_between(Fitness(50), date(2000, 1, 2), date(2000, 1, 1))
    with pytest.raises(InvalidValueError):
        recover_between(Fitness(50), None, date(2000, 1, 1))  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [None, 50, True])
def test_fitness_helpers_reject_values_without_the_fitness_value_object(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        recover_fitness(bad, 1)
    with pytest.raises(InvalidValueError):
        match_fitness(bad, 90, Priority.NORMAL)
