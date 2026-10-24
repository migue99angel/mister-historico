"""Pure provisional injury sampling and calendar availability, independent of IO."""

from dataclasses import dataclass, replace
from datetime import date, timedelta

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import FixtureId, PlayerId
from mister.shared_kernel.randomness import RandomSource
from mister.simulation.domain.fitness import _require_date, _require_fitness, _require_minutes
from mister.simulation.domain.model import Fitness, SimPlayer

_BASE_RISK = 0.02
_REGULATION_MINUTES = 90
_FATIGUE_SCALE = 50
_SHORT_DURATION = 7
_MEDIUM_DURATION = 14
_LONG_DURATION = 28
_SHORT_CUMULATIVE = 0.6
_MEDIUM_CUMULATIVE = 0.9


def _require_player_id(player_id: PlayerId) -> None:
    if not isinstance(player_id, PlayerId):
        raise InvalidValueError("player_id must be a PlayerId")


@dataclass(frozen=True, slots=True)
class Injury:
    """Unavailability on `[date, available_on)`; `available_on` is the first healthy day."""

    player_id: PlayerId
    date: date
    days: int
    forced: bool = False

    def __post_init__(self) -> None:
        _require_player_id(self.player_id)
        _require_date(self.date)
        if isinstance(self.days, bool) or not isinstance(self.days, int) or self.days <= 0:
            raise InvalidValueError("injury days must be a positive integer")
        if self.days > (date.max - self.date).days:
            raise InvalidValueError("injury return date is outside the calendar range")
        if not isinstance(self.forced, bool):
            raise InvalidValueError("forced must be a boolean")

    @property
    def available_on(self) -> date:
        """First day the player can be selected again, validated at construction."""
        return self.date + timedelta(days=self.days)


def injury_risk(fitness: Fitness, minutes: int) -> float:
    """Provisional chance based on pre-match fitness and one match's actual minutes."""
    _require_fitness(fitness)
    _require_minutes(minutes)
    return min(
        1.0,
        _BASE_RISK * minutes / _REGULATION_MINUTES * (1 + (Fitness.HIGH - fitness.value) / _FATIGUE_SCALE),
    )


def simulate_injury(
    rng: RandomSource,
    fixture_id: FixtureId,
    player_id: PlayerId,
    on_date: date,
    fitness: Fitness,
    minutes: int,
) -> Injury | None:
    """Use exactly one ADR-005 leaf and two draws per participant, none for zero minutes.

    The first draw decides the accident; the second always decides a candidate duration,
    even when no injury occurs. `fitness` is the recovered, pre-match value, before wear.
    """
    if not isinstance(fixture_id, FixtureId):
        raise InvalidValueError("fixture_id must be a FixtureId")
    _require_player_id(player_id)
    _require_date(on_date)
    risk = injury_risk(fitness, minutes)
    if minutes == 0:
        return None
    leaf = rng.stream("match", str(fixture_id), "injury", str(player_id))
    accident, duration = leaf.random(), leaf.random()
    if accident >= risk:
        return None
    if duration < _SHORT_CUMULATIVE:
        days = _SHORT_DURATION
    elif duration < _MEDIUM_CUMULATIVE:
        days = _MEDIUM_DURATION
    else:
        days = _LONG_DURATION
    return Injury(player_id, on_date, days)


def injured_until(player_id: PlayerId, injuries: tuple[Injury, ...], on_date: date) -> date | None:
    """Latest end of currently active absences; future and disjoint events never bridge gaps."""
    _require_player_id(player_id)
    _require_date(on_date)
    return max(
        (
            injury.available_on
            for injury in injuries
            if injury.player_id == player_id and injury.date <= on_date < injury.available_on
        ),
        default=None,
    )


def apply_injuries(
    squad: tuple[SimPlayer, ...], injuries: tuple[Injury, ...], on_date: date
) -> tuple[SimPlayer, ...]:
    """Project a complete applicable injury timeline to lineup flags without mutating input.

    Call before lineup selection. The caller filters events to the applicable squad and
    retains initial injury intervals, including started intervals that have since expired.
    A true input flag without any started interval is ambiguous and rejected rather than
    silently healed. An expired interval permits recovery; only active intervals set flags.
    """
    _require_date(on_date)
    ids = {p.player_id for p in squad}
    if len(ids) != len(squad):
        raise InvalidValueError("injury projection requires distinct squad player IDs")
    if any(injury.player_id not in ids for injury in injuries):
        raise InvalidValueError("injury refers to a player outside the applicable squad")
    started = {injury.player_id for injury in injuries if injury.date <= on_date}
    if any(player.injured and player.player_id not in started for player in squad):
        raise InvalidValueError("an injured player requires an explicit started injury interval")
    return tuple(
        replace(player, injured=injured_until(player.player_id, injuries, on_date) is not None)
        for player in squad
    )
