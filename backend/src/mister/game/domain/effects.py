"""Pure interpreter for the private game effects DSL."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import assert_never

from mister.game.domain.state import (
    CompetitionPriority,
    ForcedInjury,
    PlayerState,
    Priority,
    RunState,
    Tactic,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, PlayerId


def _bounded_int(name: str, value: object, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise InvalidValueError(f"{name} must be an integer from {minimum} to {maximum}")


def _date(value: object, name: str) -> None:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise InvalidValueError(f"{name} must be a date")


def _player_id(value: object) -> None:
    if not isinstance(value, PlayerId):
        raise InvalidValueError("player_id must be a PlayerId")


@dataclass(frozen=True, slots=True)
class MoraleEffect:
    delta: int

    def __post_init__(self) -> None:
        _bounded_int("morale delta", self.delta, -20, 20)


@dataclass(frozen=True, slots=True)
class PlayerMoraleEffect:
    player_id: PlayerId
    delta: int

    def __post_init__(self) -> None:
        _player_id(self.player_id)
        _bounded_int("player morale delta", self.delta, -30, 30)


@dataclass(frozen=True, slots=True)
class SignPlayerEffect:
    player_id: PlayerId
    from_club_season: ClubSeasonId | None
    effective_on: date

    def __post_init__(self) -> None:
        _player_id(self.player_id)
        if self.from_club_season is not None and not isinstance(
            self.from_club_season, ClubSeasonId
        ):
            raise InvalidValueError("from_club_season must be a ClubSeasonId or None")
        _date(self.effective_on, "effective_on")


@dataclass(frozen=True, slots=True)
class SellPlayerEffect:
    player_id: PlayerId
    to_club_season: ClubSeasonId | None
    effective_on: date

    def __post_init__(self) -> None:
        _player_id(self.player_id)
        if self.to_club_season is not None and not isinstance(
            self.to_club_season, ClubSeasonId
        ):
            raise InvalidValueError("to_club_season must be a ClubSeasonId or None")
        _date(self.effective_on, "effective_on")


@dataclass(frozen=True, slots=True)
class SetTacticEffect:
    tactic: Tactic

    def __post_init__(self) -> None:
        if not isinstance(self.tactic, Tactic):
            raise InvalidValueError("tactic must be a Tactic")


@dataclass(frozen=True, slots=True)
class CompetitionPriorityEffect:
    competition_id: CompetitionId
    priority: Priority

    def __post_init__(self) -> None:
        if not isinstance(self.competition_id, CompetitionId) or not isinstance(
            self.priority, Priority
        ):
            raise InvalidValueError("competition priority requires a competition ID and Priority")


@dataclass(frozen=True, slots=True)
class BoardConfidenceEffect:
    delta: int

    def __post_init__(self) -> None:
        _bounded_int("board confidence delta", self.delta, -25, 25)


@dataclass(frozen=True, slots=True)
class YouthMinutesEffect:
    player_id: PlayerId

    def __post_init__(self) -> None:
        _player_id(self.player_id)


@dataclass(frozen=True, slots=True)
class InjuryEffect:
    player_id: PlayerId
    date: date
    days: int

    def __post_init__(self) -> None:
        _player_id(self.player_id)
        _date(self.date, "date")
        _bounded_int("injury days", self.days, 1, 365)


@dataclass(frozen=True, slots=True)
class FitnessEffect:
    delta: int
    player_id: PlayerId | None = None

    def __post_init__(self) -> None:
        _bounded_int("fitness delta", self.delta, -30, 30)
        if self.player_id is not None:
            _player_id(self.player_id)


Effect = (
    MoraleEffect
    | PlayerMoraleEffect
    | SignPlayerEffect
    | SellPlayerEffect
    | SetTacticEffect
    | CompetitionPriorityEffect
    | BoardConfidenceEffect
    | YouthMinutesEffect
    | InjuryEffect
    | FitnessEffect
)


def _clamp(value: int, delta: int) -> int:
    return min(100, max(0, value + delta))


def _as_of(state: RunState, on: date | None) -> date:
    if on is not None:
        _date(on, "on")
        return on
    if state.state_as_of is None:
        raise InvalidValueError("state_as_of is required to resolve current squad membership")
    return state.state_as_of


def _require_own_player(state: RunState, player_id: PlayerId, on: date) -> PlayerState:
    if state.squad_registry.owner_on(player_id, on) != state.managed_club_season_id:
        raise InvalidValueError(
            "Effect player must belong to the managed club on its effective date"
        )
    for player in state.players:
        if player.player_id == player_id:
            return player
    raise InvalidValueError("Effect references an unknown player")


def _replace_player(state: RunState, changed: PlayerState) -> RunState:
    return replace(
        state,
        players=tuple(changed if p.player_id == changed.player_id else p for p in state.players),
    )


def apply(  # noqa: PLR0911, PLR0912 - exhaustive union dispatch
    effect: Effect, state: RunState, *, on: date | None = None
) -> RunState:
    """Apply one effect using its effective membership date without advancing the run cursor.

    ``on`` resolves current squad membership and takes precedence over ``state_as_of``.
    Transfers always validate their origin at their own ``effective_on`` date.
    """
    if isinstance(effect, MoraleEffect):
        return replace(state, team_morale=_clamp(state.team_morale, effect.delta))
    if isinstance(effect, PlayerMoraleEffect):
        player = _require_own_player(state, effect.player_id, _as_of(state, on))
        return _replace_player(state, replace(player, morale=_clamp(player.morale, effect.delta)))
    if isinstance(effect, SignPlayerEffect):
        owner = state.squad_registry.owner_on(effect.player_id, effect.effective_on)
        if owner != effect.from_club_season:
            raise InvalidValueError("Sign effect origin does not own the player on effective date")
        registry = state.squad_registry.transfer(
            effect.player_id, effect.from_club_season, state.managed_club_season_id,
            effect.effective_on,
        )
        return replace(state, squad_registry=registry)
    if isinstance(effect, SellPlayerEffect):
        _require_own_player(state, effect.player_id, effect.effective_on)
        registry = state.squad_registry.transfer(
            effect.player_id, state.managed_club_season_id, effect.to_club_season,
            effect.effective_on,
        )
        return replace(state, squad_registry=registry)
    if isinstance(effect, SetTacticEffect):
        return replace(state, tactic=effect.tactic)
    if isinstance(effect, CompetitionPriorityEffect):
        priority = CompetitionPriority(effect.competition_id, effect.priority)
        existing = next(
            (i for i, item in enumerate(state.competition_priorities)
             if item.competition_id == effect.competition_id),
            None,
        )
        priorities = list(state.competition_priorities)
        if existing is None:
            priorities.append(priority)
        else:
            priorities[existing] = priority
        return replace(state, competition_priorities=tuple(priorities))
    if isinstance(effect, BoardConfidenceEffect):
        return replace(state, board_confidence=_clamp(state.board_confidence, effect.delta))
    if isinstance(effect, YouthMinutesEffect):
        player = _require_own_player(state, effect.player_id, _as_of(state, on))
        return _replace_player(state, replace(player, youth_minutes=True))
    if isinstance(effect, InjuryEffect):
        _require_own_player(state, effect.player_id, _as_of(state, on))
        injury = ForcedInjury(effect.player_id, effect.date, effect.days)
        return replace(state, forced_injuries=(*state.forced_injuries, injury))
    if isinstance(effect, FitnessEffect):
        membership_date = _as_of(state, on)
        if effect.player_id is not None:
            player = _require_own_player(state, effect.player_id, membership_date)
            updated = replace(player, fitness=_clamp(player.fitness, effect.delta))
            return _replace_player(state, updated)
        own_ids = set(
            state.squad_registry.squad_on(state.managed_club_season_id, membership_date)
        )
        players = tuple(
            replace(player, fitness=_clamp(player.fitness, effect.delta))
            if player.player_id in own_ids else player
            for player in state.players
        )
        return replace(state, players=players)
    assert_never(effect)
