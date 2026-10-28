"""Pure block morale updates for the managed club's effective squad."""

from dataclasses import dataclass, replace
from datetime import date, datetime

from mister.game.domain.board import BlockResults
from mister.game.domain.state import RunState
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayerId

_MAX_MORALE = 100
_MAX_RATING = 99


@dataclass(frozen=True, slots=True)
class PlayerMinutes:
    """Explicit minutes and caller-decided eligibility for one known player."""

    player_id: PlayerId
    minutes: int
    star: bool
    eligible: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, PlayerId):
            raise InvalidValueError("player minutes requires a PlayerId")
        if type(self.minutes) is not int or self.minutes < 0:
            raise InvalidValueError("block minutes must be a non-negative integer")
        if type(self.star) is not bool or type(self.eligible) is not bool:
            raise InvalidValueError("star and eligible must be booleans")


@dataclass(frozen=True, slots=True)
class MoraleRules:
    """Required balancing parameters for team and player morale."""

    win_delta: int
    draw_delta: int
    loss_delta: int
    star_rating_threshold: int
    minimum_minutes: int
    unused_star_delta: int

    def __post_init__(self) -> None:
        if any(
            type(value) is not int
            for value in (
                self.win_delta,
                self.draw_delta,
                self.loss_delta,
                self.star_rating_threshold,
                self.minimum_minutes,
                self.unused_star_delta,
            )
        ):
            raise InvalidValueError("morale rule values must be integers")
        if not 1 <= self.star_rating_threshold <= _MAX_RATING or self.minimum_minutes < 0:
            raise InvalidValueError("star threshold must be 1..99 and minimum minutes non-negative")

    def apply(
        self, state: RunState, results: BlockResults, minutes: tuple[PlayerMinutes, ...], on: date
    ) -> RunState:
        """Return a state with morale deltas; unrelated player and run fields are preserved."""
        if not isinstance(state, RunState) or not isinstance(results, BlockResults):
            raise InvalidValueError("morale requires RunState and BlockResults")
        if not isinstance(minutes, tuple) or any(
            not isinstance(item, PlayerMinutes) for item in minutes
        ):
            raise InvalidValueError("minutes must be a tuple of PlayerMinutes values")
        if len({item.player_id for item in minutes}) != len(minutes):
            raise InvalidValueError("player minutes IDs must be unique")
        if not isinstance(on, date) or isinstance(on, datetime):
            raise InvalidValueError("on must be a date")
        result_delta = (
            results.wins * self.win_delta
            + results.draws * self.draw_delta
            + results.losses * self.loss_delta
        )
        observed = {item.player_id: item for item in minutes}
        updated_players = []
        for player in state.players:
            if state.squad_registry.owner_on(player.player_id, on) != state.managed_club_season_id:
                updated_players.append(player)
                continue
            entry = observed.get(player.player_id)
            delta = result_delta
            if (
                entry is not None
                and entry.eligible
                and entry.star
                and player.rating >= self.star_rating_threshold
                and entry.minutes < self.minimum_minutes
            ):
                delta += self.unused_star_delta
            updated_players.append(
                replace(player, morale=max(0, min(_MAX_MORALE, player.morale + delta)))
            )
        return replace(
            state,
            team_morale=max(0, min(_MAX_MORALE, state.team_morale + result_delta)),
            players=tuple(updated_players),
        )
