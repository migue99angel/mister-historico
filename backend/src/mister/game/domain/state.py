"""Immutable initial state carried by a game run."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from mister.game.domain.squad_registry import SquadRegistry
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import CompetitionId, PlayerId, PlayableSeasonId


class Position(StrEnum):
    """Player's broad playing position."""

    GK = "GK"
    DF = "DF"
    MF = "MF"
    FW = "FW"


class TacticStyle(StrEnum):
    """Team's overall tactical approach."""

    PRESSING = "pressing"
    COUNTER = "counter"
    POSSESSION = "possession"
    BALANCED = "balanced"


class Priority(StrEnum):
    """Relative importance assigned to a competition."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Tactic:
    """Tactical style and formation line counts."""

    style: TacticStyle
    system: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.style, TacticStyle):
            raise InvalidValueError("style must be a TacticStyle")
        if not isinstance(self.system, tuple) or not 3 <= len(self.system) <= 5:
            raise InvalidValueError("system must contain three to five lines")
        if any(type(line) is not int or not 1 <= line <= 6 for line in self.system) or sum(self.system) != 10:
            raise InvalidValueError("system lines must be integers from one to six and sum to ten")


@dataclass(frozen=True, slots=True)
class PlayerState:
    """Run-local player condition and performance state."""

    player_id: PlayerId
    position: Position
    rating: int
    age: int | None
    morale: int
    fitness: int
    injured_until: date | None = None
    youth_minutes: bool = False
    minutes_played: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, PlayerId) or not isinstance(self.position, Position):
            raise InvalidValueError("PlayerState requires a player ID and Position")
        _bounded_int("rating", self.rating, 1, 99)
        if self.age is not None:
            _bounded_int("age", self.age, 0, None)
        _bounded_int("morale", self.morale, 0, 100)
        _bounded_int("fitness", self.fitness, 0, 100)
        _bounded_int("minutes_played", self.minutes_played, 0, None)
        if self.injured_until is not None and not _is_date(self.injured_until):
            raise InvalidValueError("injured_until must be a date or None")
        if type(self.youth_minutes) is not bool:
            raise InvalidValueError("youth_minutes must be a bool")


@dataclass(frozen=True, slots=True)
class CompetitionPriority:
    """A competition's caller-supplied priority."""

    competition_id: CompetitionId
    priority: Priority

    def __post_init__(self) -> None:
        if not isinstance(self.competition_id, CompetitionId) or not isinstance(self.priority, Priority):
            raise InvalidValueError("CompetitionPriority requires a competition ID and Priority")


@dataclass(frozen=True, slots=True)
class ForcedInjury:
    """A deterministic externally selected injury for a player and date."""

    player_id: PlayerId
    injured_on: date
    days: int

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, PlayerId) or not _is_date(self.injured_on):
            raise InvalidValueError("ForcedInjury requires a player ID and date")
        _bounded_int("days", self.days, 1, None)


@dataclass(frozen=True, slots=True)
class RunState:
    """Private immutable snapshot of the state at a point in a run."""

    managed_club_season_id: PlayableSeasonId
    squad_registry: SquadRegistry
    players: tuple[PlayerState, ...]
    tactic: Tactic
    competition_priorities: tuple[CompetitionPriority, ...]
    team_morale: int
    board_confidence: int
    state_as_of: date | None
    forced_injuries: tuple[ForcedInjury, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.managed_club_season_id, PlayableSeasonId):
            raise InvalidValueError("managed_club_season_id must be a PlayableSeasonId")
        if not isinstance(self.squad_registry, SquadRegistry) or not isinstance(self.tactic, Tactic):
            raise InvalidValueError("RunState requires a SquadRegistry and Tactic")
        if not isinstance(self.players, tuple) or any(not isinstance(item, PlayerState) for item in self.players):
            raise InvalidValueError("players must be a tuple of PlayerState values")
        if len({item.player_id for item in self.players}) != len(self.players):
            raise InvalidValueError("RunState player IDs must be unique")
        if self.squad_registry.player_ids - {item.player_id for item in self.players}:
            raise InvalidValueError("Squad registry references an unknown player")
        if not isinstance(self.competition_priorities, tuple) or any(
            not isinstance(item, CompetitionPriority) for item in self.competition_priorities
        ):
            raise InvalidValueError("competition_priorities must be a tuple of CompetitionPriority values")
        competition_ids = [item.competition_id for item in self.competition_priorities]
        if len(set(competition_ids)) != len(competition_ids):
            raise InvalidValueError("Competition priorities must have unique competition IDs")
        if not isinstance(self.forced_injuries, tuple) or any(
            not isinstance(item, ForcedInjury) for item in self.forced_injuries
        ):
            raise InvalidValueError("forced_injuries must be a tuple of ForcedInjury values")
        known_players = {item.player_id for item in self.players}
        if any(item.player_id not in known_players for item in self.forced_injuries):
            raise InvalidValueError("Forced injury references an unknown player")
        _bounded_int("team_morale", self.team_morale, 0, 100)
        _bounded_int("board_confidence", self.board_confidence, 0, 100)
        if self.state_as_of is not None and not _is_date(self.state_as_of):
            raise InvalidValueError("state_as_of must be a date or None")


def _bounded_int(name: str, value: object, minimum: int, maximum: int | None) -> None:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        if maximum is None:
            raise InvalidValueError(f"{name} must be an integer greater than or equal to {minimum}")
        raise InvalidValueError(f"{name} must be an integer from {minimum} to {maximum}")


def _is_date(value: object) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)
