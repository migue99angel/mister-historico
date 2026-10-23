"""Pure, deterministic selection with native-position coverage before rating and rotation."""

from dataclasses import dataclass

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayerId
from mister.simulation.domain.model import Position, Priority, SimPlayer, Tactic

_STARTERS = 11
_OUT_OF_POSITION_PENALTY = 5
_ROTATIONS = {Priority.HIGH: 0, Priority.NORMAL: 2, Priority.LOW: 4}


def effective_rating(player: SimPlayer) -> float:
    """ADR-004 step 1; fitness affects the rating only, never a second multiplier."""
    physical_penalty = 0.07 * max(0, 90 - player.fitness.value)
    morale_adjustment = 2 * (player.morale.value - 50) / 50
    return max(1.0, min(99.0, player.rating.value - physical_penalty + morale_adjustment))


@dataclass(frozen=True, slots=True)
class LineupPlayer:
    """A starter assigned to a line, including the bounded out-of-position penalty."""

    player: SimPlayer
    position: Position
    effective_rating: float


@dataclass(frozen=True, slots=True)
class Lineup:
    """Eleven assigned starters in GK/DF/MF/FW order and the actual rotation count."""

    starters: tuple[LineupPlayer, ...]
    rotated: int = 0


def _rank(player: SimPlayer) -> tuple[float, str]:
    return -effective_rating(player), player.player_id.value


def _slots(tactic: Tactic) -> dict[Position, int]:
    lines = tuple(int(value) for value in tactic.system.split("-"))
    return dict(zip(Position, (1, lines[0], sum(lines[1:-1]), lines[-1]), strict=True))


@dataclass(frozen=True, slots=True)
class _Choice:
    """Dynamic-programming candidate: coverage, then rating, then stable player IDs."""

    players: tuple[SimPlayer, ...] = ()
    native: int = 0
    rating: float = 0.0

    @property
    def order(self) -> tuple[int, float, tuple[str, ...]]:
        # min() chooses maximum coverage and rating, then lexicographically smaller IDs.
        return -self.native, -self.rating, tuple(sorted(p.player_id.value for p in self.players))


def _choices(
    players: tuple[SimPlayer, ...],
    slots: dict[Position, int],
    baseline: frozenset[PlayerId],
    rotations: int,
) -> dict[int, _Choice]:
    """Optimize four positional groups, retaining the best result per size/rotation count.

    Reserving native coverage globally avoids a greedy goalkeeper replacement taking the
    sole available defender. Each group needs only its best prefix of starters and reserves.
    Rotation never takes precedence over the native coverage of the strongest eleven.
    """
    states = {(0, 0): _Choice()}
    for position in Position:
        regulars = sorted(
            (p for p in players if p.position is position and p.player_id in baseline), key=_rank
        )
        reserves = sorted(
            (p for p in players if p.position is position and p.player_id not in baseline),
            key=_rank,
        )
        next_states: dict[tuple[int, int], _Choice] = {}
        for (size, rotated), previous in states.items():
            for kept in range(min(len(regulars), _STARTERS - size) + 1):
                for added in range(
                    min(len(reserves), rotations - rotated, _STARTERS - size - kept) + 1
                ):
                    selected = (*regulars[:kept], *reserves[:added])
                    candidate = _Choice(
                        (*previous.players, *selected),
                        previous.native + min(len(selected), slots[position]),
                        previous.rating + sum(effective_rating(p) for p in selected),
                    )
                    key = size + len(selected), rotated + added
                    current = next_states.get(key)
                    if current is None or candidate.order < current.order:
                        next_states[key] = candidate
        states = next_states
    return {rotated: choice for (size, rotated), choice in states.items() if size == _STARTERS}


def _assign(choice: _Choice, slots: dict[Position, int], rotated: int) -> Lineup:
    selected: dict[Position, list[SimPlayer]] = {}
    surplus: list[SimPlayer] = []
    for position in Position:
        ranked = sorted((p for p in choice.players if p.position is position), key=_rank)
        selected[position] = ranked[: slots[position]]
        surplus.extend(ranked[slots[position] :])
    replacements = iter(sorted(surplus, key=_rank))
    starters = []
    for position in Position:
        players = selected[position]
        players.extend(next(replacements) for _ in range(slots[position] - len(players)))
        for player in players:
            penalty = 0 if player.position is position else _OUT_OF_POSITION_PENALTY
            starters.append(
                LineupPlayer(player, position, max(1.0, effective_rating(player) - penalty))
            )
    return Lineup(tuple(starters), rotated)


def select_lineup(
    squad: tuple[SimPlayer, ...], tactic: Tactic, *, priority: Priority = Priority.HIGH
) -> Lineup:
    """Select the strongest eleven, then rotate up to 0/2/4 for high/normal/low priority.

    The strongest eleven maximizes native-position coverage, then total effective rating,
    with IDs resolving ties. Rotations preserve that coverage, maximize the same objective
    and use the largest feasible count up to the priority target. Missing positions are
    filled only after reserving every available native slot; their rating loses five points,
    floored at one. This function has no random source and never mutates the squad.
    """
    healthy = tuple(p for p in squad if not p.injured)
    if len(healthy) < _STARTERS:
        raise InvalidValueError("a lineup needs at least eleven healthy players")
    if len({p.player_id for p in healthy}) != len(healthy):
        raise InvalidValueError("a lineup needs distinct player IDs")
    slots = _slots(tactic)
    best = _choices(healthy, slots, frozenset(p.player_id for p in healthy), 0)[0]
    target = _ROTATIONS[priority]
    if target == 0:
        return _assign(best, slots, 0)
    candidates = _choices(healthy, slots, frozenset(p.player_id for p in best.players), target)
    feasible = max(count for count, choice in candidates.items() if choice.native == best.native)
    return _assign(candidates[feasible], slots, feasible)
