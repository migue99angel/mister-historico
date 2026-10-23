"""ADR-004 strength with immutable content normalisation and bounded design adjustments."""

import math
from dataclasses import dataclass, replace

from mister.shared_kernel.errors import InvalidValueError
from mister.simulation.domain.lineup import Lineup, select_lineup
from mister.simulation.domain.model import (
    AggregateIndices,
    Fitness,
    Morale,
    Position,
    Priority,
    SimTeam,
    Style,
    Tactic,
    TeamStrength,
)

_BETA = 0.40
# Design coefficients, not historical data or calibrated estimates. Both entries are gains:
# positive attack improves scoring; positive defence reduces vulnerability.
_STYLE_GAINS = {
    Style.BALANCED: (0.0, 0.0),
    Style.PRESSING: (0.04, -0.04),
    Style.COUNTER: (-0.04, 0.04),
    Style.POSSESSION: (0.02, -0.01),
}
_FIT_LIMIT = 0.03


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _line_means(lineup: Lineup) -> dict[Position, float]:
    return {
        position: sum(p.effective_rating for p in lineup.starters if p.position is position)
        / sum(p.position is position for p in lineup.starters)
        for position in Position
    }


def lineup_indices(lineup: Lineup) -> AggregateIndices:
    """Compute A and C from assigned line means, with the exact ADR-004 weights."""
    means = _line_means(lineup)
    return AggregateIndices(
        attack=0.50 * means[Position.FW] + 0.35 * means[Position.MF] + 0.15 * means[Position.DF],
        defense=0.20 * means[Position.GK] + 0.45 * means[Position.DF] + 0.35 * means[Position.MF],
    )


def morale_multiplier(morale: Morale) -> float:
    """ADR-004 team morale, separate from the individual player's effective rating."""
    return 1 + 0.06 * (morale.value - 50) / 50


def tactical_multipliers(tactic: Tactic, lineup: Lineup) -> tuple[float, float]:
    """Return attack and vulnerability multipliers; all fit coefficients are design choices.

    Pressing adds each starter's bounded (27-age)/10 contribution, averaged over all eleven.
    Unknown ages contribute zero individually: known ages are never extrapolated to others.
    Counter rewards a forward line stronger than the eleven's mean; possession rewards a
    stronger midfield. These relative-rating fits use a 30-point scale and never alter the
    base rating formula. Balanced has neutral fit. Each fit component is within +/-0.03.
    """
    attack_gain, defense_gain = _STYLE_GAINS[tactic.style]
    attack_fit = defense_fit = 0.0
    if tactic.style is Style.PRESSING:
        fit = (
            _FIT_LIMIT
            * sum(
                0.0 if entry.player.age is None else _clamp((27 - entry.player.age) / 10, -1, 1)
                for entry in lineup.starters
            )
            / len(lineup.starters)
        )
        attack_fit = defense_fit = fit
    elif tactic.style in (Style.COUNTER, Style.POSSESSION):
        line = Position.FW if tactic.style is Style.COUNTER else Position.MF
        overall = sum(entry.effective_rating for entry in lineup.starters) / len(lineup.starters)
        attack_fit = _FIT_LIMIT * _clamp((_line_means(lineup)[line] - overall) / 30, -1, 1)
        defense_fit = attack_fit if tactic.style is Style.POSSESSION else 0.0
    return (
        _clamp(1 + attack_gain + attack_fit, 0.92, 1.08),
        _clamp(1 - defense_gain - defense_fit, 0.92, 1.08),
    )


def _neutral_team(team: SimTeam, *, reference: bool = False) -> SimTeam:
    if team.squad is None:
        return team
    return replace(
        team,
        morale=Morale(50),
        squad=tuple(
            replace(
                player,
                fitness=Fitness(100),
                morale=Morale(50),
                injured=False if reference else player.injured,
            )
            for player in team.squad
        ),
    )


@dataclass(frozen=True, slots=True)
class StrengthReference:
    """Fixed mean exponentials from every competition participant as present in content.

    Construct once per competition/season, then reuse through transfers, injuries and blocks.
    Rebuilding from live squads would erase the effect of changing a team's players.
    """

    attack_mean: float
    defense_mean: float

    def __post_init__(self) -> None:
        for value in (self.attack_mean, self.defense_mean):
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                or value <= 0
            ):
                raise InvalidValueError("reference denominators must be positive finite numbers")

    @classmethod
    def from_indices(cls, indices: tuple[AggregateIndices, ...]) -> "StrengthReference":
        """Freeze the mean of exponentials (not the exponential of the mean indices)."""
        if not indices:
            raise InvalidValueError("a strength reference needs competition participants")
        return cls(
            sum(math.exp(_BETA * item.attack / 10) for item in indices) / len(indices),
            sum(math.exp(-_BETA * item.defense / 10) for item in indices) / len(indices),
        )

    @classmethod
    def from_teams(cls, teams: tuple[SimTeam, ...]) -> "StrengthReference":
        """Reference squads use their system and ratings, with no state, style or fit bonus."""
        return cls.from_indices(
            tuple(_team_indices(_neutral_team(team, reference=True)) for team in teams)
        )


def _team_indices(team: SimTeam, priority: Priority = Priority.HIGH) -> AggregateIndices:
    if team.aggregate is not None:
        return team.aggregate
    assert team.squad is not None and team.tactic is not None  # guaranteed by SimTeam
    return lineup_indices(select_lineup(team.squad, team.tactic, priority=priority))


def calculate_strength(
    team: SimTeam,
    reference: StrengthReference,
    *,
    priority: Priority = Priority.HIGH,
    neutral: bool = False,
) -> TeamStrength:
    """Normalize A/C, then apply tactic and morale once; aggregates stay fixed.

    `neutral=True` is the V1 rival policy: best eleven, full fitness, neutral player/team
    morale and no tactical multiplier. Injured players remain unavailable. Aggregates are
    already A/C in rating points and bypass all squad adjustments. Raw normalized factors
    are clamped to 0.4-2.5 before bounded tactic/morale; final lambda safety belongs to T2.1.
    """
    current = _neutral_team(team) if neutral else team
    indices = _team_indices(current, Priority.HIGH if neutral else priority)
    attack = _clamp(math.exp(_BETA * indices.attack / 10) / reference.attack_mean, 0.4, 2.5)
    defense = _clamp(math.exp(-_BETA * indices.defense / 10) / reference.defense_mean, 0.4, 2.5)
    if current.aggregate is not None or neutral:
        return TeamStrength(attack, defense)
    assert current.squad is not None and current.tactic is not None  # guaranteed by SimTeam
    lineup = select_lineup(current.squad, current.tactic, priority=priority)
    tactical_attack, tactical_defense = tactical_multipliers(current.tactic, lineup)
    morale = morale_multiplier(current.morale)
    return TeamStrength(attack * tactical_attack * morale, defense * tactical_defense / morale)
