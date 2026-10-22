"""Immutable value objects of the simulation engine (ADR-004).

Pure data and validation, no simulation logic: strength, lambda and sampling live in the
strategies that implement `domain/ports.py` (T2.1, T2.2). Every invariant violation raises
`InvalidValueError`. Vocabulary follows the glossary and the content format.
"""

import math
import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import ClassVar

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId, PlayerId


class Style(StrEnum):
    """Tactical style (content-format: `pressing | counter | possession | balanced`)."""

    PRESSING = "pressing"
    COUNTER = "counter"
    POSSESSION = "possession"
    BALANCED = "balanced"


class Priority(StrEnum):
    """Competition priority: how many starters rotate (0, 2 or 4 in ADR-004)."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class Position(StrEnum):
    """Line of a player; it alone decides the slot he fills (never his subrole)."""

    GK = "GK"
    DF = "DF"
    MF = "MF"
    FW = "FW"


class Venue(StrEnum):
    """Ground from a team's point of view; a fixture is `home` (home team's ground) or `neutral`."""

    HOME = "home"
    AWAY = "away"
    NEUTRAL = "neutral"


class Side(StrEnum):
    """Which team of a fixture."""

    HOME = "home"
    AWAY = "away"


def _require_finite(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise InvalidValueError(f"{name} must be a finite number, got {value!r}")


def _require_positive(name: str, *values: float) -> None:
    for value in values:
        _require_finite(name, value)
        if value <= 0:
            raise InvalidValueError(f"{name} must be > 0, got {value!r}")


@dataclass(frozen=True, slots=True)
class _BoundedInt:
    """Integer in `[LOW, HIGH]`."""

    value: int
    LOW: ClassVar[int]
    HIGH: ClassVar[int]

    def __post_init__(self) -> None:
        if (
            isinstance(self.value, bool)
            or not isinstance(self.value, int)
            or not self.LOW <= self.value <= self.HIGH
        ):
            raise InvalidValueError(
                f"{type(self).__name__} must be an integer in {self.LOW}-{self.HIGH}, "
                f"got {self.value!r}"
            )


@dataclass(frozen=True, slots=True)
class Rating(_BoundedInt):
    """Player rating, 1-99 (rating rubric)."""

    LOW: ClassVar[int] = 1
    HIGH: ClassVar[int] = 99


@dataclass(frozen=True, slots=True)
class Morale(_BoundedInt):
    """Morale, 0-100; 50 is neutral. Used for players and for the team."""

    LOW: ClassVar[int] = 0
    HIGH: ClassVar[int] = 100


@dataclass(frozen=True, slots=True)
class Fitness(_BoundedInt):
    """Physical condition, 0-100; above 90 it has no effect (ADR-004 step 1)."""

    LOW: ClassVar[int] = 0
    HIGH: ClassVar[int] = 100


@dataclass(frozen=True, slots=True)
class TeamStrength:
    """Normalised strength factors of a team in one competition (ADR-004 step 4).

    `attack` multiplies the team's own goals (above 1 is a better attack than the competition
    average). `defense` is a vulnerability factor applied to the rival's goals, so below 1 is
    a better defence. The average team of the competition has both at 1. Tactic and morale
    adjustments are already folded in by the strength calculation (T2.2).
    """

    attack: float
    defense: float

    def __post_init__(self) -> None:
        _require_positive("TeamStrength factors", self.attack, self.defense)


@dataclass(frozen=True, slots=True)
class AggregateIndices:
    """Fixed attack `A` and defence `C` indices of an aggregate rival, in rating points."""

    attack: float
    defense: float

    def __post_init__(self) -> None:
        for value in (self.attack, self.defense):
            _require_finite("AggregateIndices", value)
            if not Rating.LOW <= value <= Rating.HIGH:
                raise InvalidValueError(f"index must be in rating points 1-99, got {value!r}")


@dataclass(frozen=True, slots=True)
class CompetitionParams:
    """Historical goal parameters of a competition: goals per team per match and home factor `H`."""

    base_goals: float
    home_advantage: float

    def __post_init__(self) -> None:
        _require_positive("CompetitionParams", self.base_goals, self.home_advantage)


_SYSTEM = re.compile(r"[1-9](-[1-9]){2,4}")
_SYSTEM_OUTFIELD_PLAYERS = 10
_SYSTEM_MAX_LINE = 6


@dataclass(frozen=True, slots=True)
class Tactic:
    """Style plus system (`4-3-3`): 3-5 lines of 1-6 players adding up to exactly 10."""

    style: Style
    system: str

    def __post_init__(self) -> None:
        if not isinstance(self.style, Style):
            raise InvalidValueError(f"unknown tactical style {self.style!r}")
        if not isinstance(self.system, str) or _SYSTEM.fullmatch(self.system) is None:
            raise InvalidValueError(f"system must look like '4-3-3', got {self.system!r}")
        lines = [int(n) for n in self.system.split("-")]
        if max(lines) > _SYSTEM_MAX_LINE or sum(lines) != _SYSTEM_OUTFIELD_PLAYERS:
            raise InvalidValueError(
                f"system lines must be 1-6 and add up to 10, got {self.system!r}"
            )


@dataclass(frozen=True, slots=True)
class Score:
    """Goals of both teams in one period of a match (or in a shootout)."""

    home: int
    away: int

    def __post_init__(self) -> None:
        for goals in (self.home, self.away):
            if isinstance(goals, bool) or not isinstance(goals, int) or goals < 0:
                raise InvalidValueError(f"goals must be an integer >= 0, got {goals!r}")


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Result of a match: 90 minutes, then optional extra time (goals of those 30 minutes only)
    and optional shootout. `winner` is `None` for a draw (league)."""

    regulation: Score
    extra_time: Score | None = None
    penalties: Score | None = None

    def __post_init__(self) -> None:
        if self.extra_time is not None and self.regulation.home != self.regulation.away:
            raise InvalidValueError("extra time needs a drawn regulation score")
        if self.penalties is not None:
            if self.total.home != self.total.away:
                raise InvalidValueError("a shootout needs a level score after extra time")
            if self.penalties.home == self.penalties.away:
                raise InvalidValueError("a shootout cannot end level")

    @property
    def total(self) -> Score:
        """Goals after regulation and extra time, shootout excluded."""
        extra = self.extra_time or Score(0, 0)
        return Score(self.regulation.home + extra.home, self.regulation.away + extra.away)

    @property
    def winner(self) -> Side | None:
        """The side that won, deciding by goals first and the shootout if level."""
        decisive = self.penalties or self.total
        if decisive.home == decisive.away:
            return None
        return Side.HOME if decisive.home > decisive.away else Side.AWAY


@dataclass(frozen=True, slots=True)
class FixtureSpec:
    """A match to simulate. `venue` is `home` or `neutral`; `leg`, `stage` (slug) and `group`
    apply to knockout and group matches only. `key` marks a highlighted match."""

    fixture_id: FixtureId
    date: date
    competition_id: CompetitionId
    home: ClubSeasonId
    away: ClubSeasonId
    venue: Venue = Venue.HOME
    key: bool = False
    leg: int | None = None
    stage: str | None = None
    group: str | None = None

    def __post_init__(self) -> None:
        if self.home == self.away:
            raise InvalidValueError("a team cannot play itself")
        if self.venue is Venue.AWAY:
            raise InvalidValueError("a fixture is at the home team's ground or neutral")
        if self.leg not in (None, 1, 2):
            raise InvalidValueError(f"leg must be 1 or 2, got {self.leg!r}")
        if self.stage is None and (self.leg is not None or self.group is not None):
            raise InvalidValueError("leg and group need a stage")


@dataclass(frozen=True, slots=True)
class SimPlayer:
    """A player as the engine sees him. `injured` players are never starters."""

    player_id: PlayerId
    position: Position
    rating: Rating
    morale: Morale = Morale(50)
    fitness: Fitness = Fitness(100)
    injured: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.position, Position) or not isinstance(self.rating, Rating):
            raise InvalidValueError("position and rating must be a Position and a Rating")


_STARTERS = 11


@dataclass(frozen=True, slots=True)
class SimTeam:
    """A team: either a squad with a tactic (the managed team and rivals with a squad) or
    an aggregate with fixed `A` and `C` indices (ADR-004 section 2), never both."""

    club_season_id: ClubSeasonId
    squad: tuple[SimPlayer, ...] | None = None
    tactic: Tactic | None = None
    aggregate: AggregateIndices | None = None
    morale: Morale = Morale(50)

    def __post_init__(self) -> None:
        if (self.squad is None) == (self.aggregate is None):
            raise InvalidValueError("a team is either a squad or an aggregate, never both")
        if (self.tactic is None) != (self.squad is None):
            raise InvalidValueError("a squad team needs a tactic and an aggregate cannot have one")
        if self.squad is not None and (
            len(self.squad) < _STARTERS or len({p.player_id for p in self.squad}) != len(self.squad)
        ):
            raise InvalidValueError("a squad needs at least 11 distinct players")


@dataclass(frozen=True, slots=True)
class MatchSetup:
    """Everything a `MatchSimulator` needs about one match: the fixture, both strengths and
    the competition's goal parameters."""

    fixture: FixtureSpec
    home: TeamStrength
    away: TeamStrength
    params: CompetitionParams
