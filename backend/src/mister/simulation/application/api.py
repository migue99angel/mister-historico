"""Published API of the simulation context (PLAN §3.2, rule 4).

The only module other contexts may import (from their own `infrastructure`, as an ACL).

Design: the DTOs are defined here, independent of `simulation.domain`, instead of re-exporting
its value objects. Vocabulary (style, system, position, venue...) travels as plain strings and
numbers, and only the shared-kernel IDs are reused, so T2.x can reshape the domain model
without breaking the callers. The use case validates these DTOs and maps them to domain
value objects, which raises `InvalidValueError` on bad input.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.shared_kernel.randomness import RandomSource

type PositionName = Literal["GK", "DF", "MF", "FW"]
type StyleName = Literal["pressing", "counter", "possession", "balanced"]
type PriorityName = Literal["low", "normal", "high"]
type VenueName = Literal["home", "neutral"]

# --------------------------------------------------------------------------- input


@dataclass(frozen=True, slots=True)
class TacticDTO:
    """Style and system (`4-3-3`), in the canonical content format."""

    style: StyleName
    system: str


@dataclass(frozen=True, slots=True)
class SquadPlayerInput:
    """A player with his state: rating 1-99, morale and fitness 0-100."""

    player_id: PlayerId
    position: PositionName
    rating: int
    morale: int = 50
    fitness: int = 100
    injured: bool = False


@dataclass(frozen=True, slots=True)
class SquadTeamInput:
    """A team simulated from its squad (the managed team and rivals with a squad)."""

    club_season_id: ClubSeasonId
    players: tuple[SquadPlayerInput, ...]
    tactic: TacticDTO
    morale: int = 50


@dataclass(frozen=True, slots=True)
class AggregateTeamInput:
    """A rival with fixed attack and defence indices, in rating points."""

    club_season_id: ClubSeasonId
    attack: float
    defense: float


type TeamInput = SquadTeamInput | AggregateTeamInput


@dataclass(frozen=True, slots=True)
class CompetitionParamsDTO:
    """Goals per team and match, and home-advantage factor `H`, from the content."""

    competition_id: CompetitionId
    base_goals: float
    home_advantage: float


@dataclass(frozen=True, slots=True)
class FixtureInput:
    """A scheduled match; `leg`, `stage` and `group` only apply to knockout and group matches."""

    fixture_id: FixtureId
    date: date
    competition_id: CompetitionId
    home: ClubSeasonId
    away: ClubSeasonId
    venue: VenueName = "home"
    key: bool = False
    leg: Literal[1, 2] | None = None
    stage: str | None = None
    group: str | None = None


@dataclass(frozen=True, slots=True)
class ForcedInjuryDTO:
    """An injury from the content (`forced_events`), applied on its date for `days` days."""

    player_id: PlayerId
    date: date
    days: int


@dataclass(frozen=True, slots=True)
class StandingRowDTO:
    """One row of a table."""

    club_season_id: ClubSeasonId
    position: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    points: int


@dataclass(frozen=True, slots=True)
class StandingsDTO:
    """A league table, or one group's table (`group`), as of a date."""

    competition_id: CompetitionId
    as_of: date
    rows: tuple[StandingRowDTO, ...]
    group: str | None = None


@dataclass(frozen=True, slots=True)
class SeasonSimInput:
    """What stays fixed during a season: the opponents (not the managed team), competition
    parameters, the whole calendar, forced injuries and the real tables at each cutoff."""

    teams: tuple[TeamInput, ...]
    competitions: tuple[CompetitionParamsDTO, ...]
    fixtures: tuple[FixtureInput, ...]
    forced_injuries: tuple[ForcedInjuryDTO, ...] = ()
    historical_standings: tuple[StandingsDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class BlockSimRequest:
    """Simulate the fixtures of `season` dated from `start` to `end` (both included).

    `managed_team` is its state at the start of the block. `competition_priorities` defaults to
    `normal` for any competition not listed. `prior_results` are the results of earlier blocks,
    needed to carry the standings forward.
    """

    season: SeasonSimInput
    block_id: BlockId
    start: date
    end: date
    managed_team: SquadTeamInput
    competition_priorities: Mapping[CompetitionId, PriorityName] = field(default_factory=dict)
    prior_results: tuple["MatchResultDTO", ...] = ()


# --------------------------------------------------------------------------- output


@dataclass(frozen=True, slots=True)
class MatchResultDTO:
    """Result of a played fixture. Extra time holds the goals of those 30 minutes only and
    `winner` is `None` for a drawn league match."""

    fixture_id: FixtureId
    competition_id: CompetitionId
    date: date
    home: ClubSeasonId
    away: ClubSeasonId
    regulation: tuple[int, int]
    extra_time: tuple[int, int] | None = None
    penalties: tuple[int, int] | None = None
    winner: Literal["home", "away"] | None = None
    key: bool = False


@dataclass(frozen=True, slots=True)
class InjuryDTO:
    """An injury suffered in the block (`forced` when it comes from the content)."""

    player_id: PlayerId
    date: date
    days: int
    forced: bool = False


@dataclass(frozen=True, slots=True)
class PlayerStateDTO:
    """Fitness and injury of a managed-team player at the end of the block."""

    player_id: PlayerId
    fitness: int
    injured_until: date | None = None


@dataclass(frozen=True, slots=True)
class EventDTO:
    """A notable fact of the block. New kinds are additive."""

    kind: Literal["advanced", "eliminated", "champion"]
    date: date
    club_season_id: ClubSeasonId
    competition_id: CompetitionId
    stage: str | None = None


@dataclass(frozen=True, slots=True)
class BlockSummaryDTO:
    """Outcome of a block: results, key matches (by fixture), tables, events and injuries."""

    block_id: BlockId
    results: tuple[MatchResultDTO, ...] = ()
    key_matches: tuple[FixtureId, ...] = ()
    standings: tuple[StandingsDTO, ...] = ()
    events: tuple[EventDTO, ...] = ()
    injuries: tuple[InjuryDTO, ...] = ()
    player_states: tuple[PlayerStateDTO, ...] = ()


# --------------------------------------------------------------------------- facade


class SimulationService:
    """Facade of the engine. Deterministic: the same request and `rng` give the same summary."""

    def simulate_block(self, request: BlockSimRequest, rng: RandomSource) -> BlockSummaryDTO:
        """Simulate one block in date order, drawing from streams derived from `rng`.

        Raises `InvalidValueError` for an invalid request. Not implemented until T2.6.
        """
        raise NotImplementedError("SimulationService.simulate_block is implemented in T2.6")
