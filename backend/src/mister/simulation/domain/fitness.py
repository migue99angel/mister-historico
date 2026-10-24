"""Pure provisional fitness rules; design parameters pending gameplay calibration."""

from datetime import date
from math import ceil

from mister.shared_kernel.errors import InvalidValueError
from mister.simulation.domain.model import Fitness, Priority

_RECOVERY_PER_DAY = 4
_MATCH_WEAR = 12
_REGULATION_MINUTES = 90
_MAX_MINUTES = 120
_EFFORT = {Priority.LOW: 0.8, Priority.NORMAL: 0.9, Priority.HIGH: 1.0}


def _require_fitness(fitness: Fitness) -> None:
    if not isinstance(fitness, Fitness):
        raise InvalidValueError("fitness must be a Fitness value object")


def _require_minutes(minutes: int) -> None:
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 0 <= minutes <= _MAX_MINUTES:
        raise InvalidValueError("match minutes must be an integer in 0-120")


def _require_date(value: date) -> None:
    # A datetime is not a calendar date: silently accepting times breaks day arithmetic.
    if type(value) is not date:
        raise InvalidValueError("a calendar date is required")


def recover_fitness(fitness: Fitness, days: int) -> Fitness:
    """Recover four points per elapsed day; large non-negative integers saturate safely."""
    _require_fitness(fitness)
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        raise InvalidValueError("recovery days must be a non-negative integer")
    return Fitness(min(Fitness.HIGH, fitness.value + _RECOVERY_PER_DAY * days))


def recover_between(fitness: Fitness, start: date, end: date) -> Fitness:
    """Recover over `end - start`, without including either block boundary twice."""
    _require_date(start)
    _require_date(end)
    return recover_fitness(fitness, (end - start).days)


def match_fitness(fitness: Fitness, minutes: int, priority: Priority) -> Fitness:
    """Apply one match's wear to pre-match fitness; recovery is a separate operation."""
    _require_fitness(fitness)
    _require_minutes(minutes)
    if not isinstance(priority, Priority):
        raise InvalidValueError("priority must be a Priority")
    wear = ceil(_MATCH_WEAR * minutes / _REGULATION_MINUTES * _EFFORT[priority])
    return Fitness(max(Fitness.LOW, fitness.value - wear))
