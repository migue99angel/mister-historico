"""Published API of the simulation context (PLAN §3.2, rule 4).

The only module other contexts may import, and only from their own `infrastructure` (as an
ACL). It is the contract of one block of the season: the content-derived, fixed data goes once
in `SeasonSimInput` and the run state goes per block in `BlockSimRequest`.

Fixed during a run: the reference squads of every participant, which also fix the ADR-004
section 2 normalisation (computed over the participants as they are in the content, so signing
a star raises your attack over a fixed reference). Variable: the managed team and the rivals
changed by signings and sales (`team_overrides`, from the `SquadRegistry`, ADR-015).

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

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.shared_kernel.randomness import RandomSource
from mister.simulation.application import simulate_block

# Vocabulary: exactly the values of the content schema, OpenAPI and the domain enums
# (`tests/simulation/unit/test_vocabulary.py` compares them).
type PositionName = Literal["GK", "DF", "MF", "FW"]
type StyleName = Literal["pressing", "counter", "possession", "balanced"]
type PriorityName = Literal["low", "normal", "high"]
type VenueName = Literal["home", "neutral"]  # of a fixture: the home team's ground or neutral
type TeamVenueName = Literal["home", "away", "neutral"]  # from the managed team's point of view
type UserResultName = Literal["win", "draw", "loss"]
type CompetitionKindName = Literal["league", "cup", "super_cup", "continental_cup"]
type CompetitionTierName = Literal[
    "domestic_league",
    "domestic_cup",
    "domestic_super_cup",
    "continental_primary",
    "continental_secondary",
]
type RoundName = Literal[
    "qualifying",
    "playoff",
    "group_stage",
    "round_of_128",
    "round_of_64",
    "round_of_32",
    "round_of_16",
    "quarter_final",
    "semi_final",
    "final",
]
type TiebreakerName = Literal[
    "head_to_head_points",
    "head_to_head_goal_difference",
    "head_to_head_goals_for",
    "head_to_head_away_goals",
    "goal_difference",
    "goals_for",
    "wins",
]

# --------------------------------------------------------------------------- teams


@dataclass(frozen=True, slots=True)
class TacticDTO:
    """Style and system (`4-3-3`), in the canonical content format."""

    style: StyleName
    system: str


@dataclass(frozen=True, slots=True)
class SquadPlayerInput:
    """A player with his state: rating 1-99, morale and fitness 0-100.

    `injured_until` is the first day he is available again (`None` if healthy); `youth_minutes`
    marks a player the manager must give minutes to (effect of a dilemma).
    """

    player_id: PlayerId
    position: PositionName
    rating: int
    age: int | None = None
    morale: int = 50
    fitness: int = 100
    injured_until: date | None = None
    youth_minutes: bool = False


@dataclass(frozen=True, slots=True)
class SquadTeamInput:
    """A team simulated from its squad: the managed team and rivals with a squad."""

    club_season_id: ClubSeasonId
    players: tuple[SquadPlayerInput, ...]
    tactic: TacticDTO


@dataclass(frozen=True, slots=True)
class AggregateTeamInput:
    """A rival with fixed attack and defence indices, in rating points."""

    club_season_id: ClubSeasonId
    attack: float
    defense: float


type TeamInput = SquadTeamInput | AggregateTeamInput

# --------------------------------------------------------------------------- competitions


@dataclass(frozen=True, slots=True)
class GroupInput:
    """A group of a group stage."""

    group_id: str
    participants: tuple[ClubSeasonId, ...]


@dataclass(frozen=True, slots=True)
class StageInput:
    """A round of a knockout competition or its group stage, with that season's rules."""

    stage_id: str
    round: RoundName
    legs: Literal[1, 2]
    away_goals_rule: bool
    extra_time: bool
    penalties: bool
    groups: tuple[GroupInput, ...] = ()
    points_per_win: int | None = None
    points_per_draw: int | None = None
    tiebreakers: tuple[TiebreakerName, ...] = ()
    advance_per_group: int | None = None
    away_goals_in_extra_time: bool | None = None
    reapply_head_to_head: bool | None = None


@dataclass(frozen=True, slots=True)
class RealTieInput:
    """A real knockout tie, also those without the managed team: if you go further than in
    reality, your rival is the real winner of the tie. `winner` is `None` while pending."""

    stage_id: str
    clubs: tuple[ClubSeasonId, ClubSeasonId]
    winner: ClubSeasonId | None = None


@dataclass(frozen=True, slots=True)
class CompetitionInput:
    """A competition of the season with its rules and its goal parameters (ADR-004 section 4).

    A league sets `rounds`, `points_per_win`, `points_per_draw` and `tiebreakers`; the other
    kinds set `stages` (and `real_ties`). `participants` are the ones in the content.
    """

    competition_id: CompetitionId
    kind: CompetitionKindName
    tier: CompetitionTierName
    participants: tuple[ClubSeasonId, ...]
    base_goals: float
    home_advantage: float
    rounds: Literal[1, 2] | None = None
    points_per_win: int | None = None
    points_per_draw: int | None = None
    tiebreakers: tuple[TiebreakerName, ...] = ()
    stages: tuple[StageInput, ...] = ()
    real_ties: tuple[RealTieInput, ...] = ()


# --------------------------------------------------------------------------- fixtures


@dataclass(frozen=True, slots=True)
class RealResultInput:
    """The real result of a match, from the managed team's point of view, as the content
    stores it: goals include extra time when `extra_time` is true (the content does not split
    them) and the shootout is apart. Needed for P2 (`HistoricalExternalResults`)."""

    goals_for: int
    goals_against: int
    extra_time: bool = False
    penalties_for: int | None = None
    penalties_against: int | None = None


@dataclass(frozen=True, slots=True)
class FixtureInput:
    """A scheduled match of the managed team. `round` is the matchday of a league or group
    match; `leg`, `stage_id` and `group_id` only apply to knockout and group matches."""

    fixture_id: FixtureId
    date: date
    competition_id: CompetitionId
    home: ClubSeasonId
    away: ClubSeasonId
    venue: VenueName = "home"
    key: bool = False
    round: int | None = None
    leg: Literal[1, 2] | None = None
    stage_id: str | None = None
    group_id: str | None = None
    real_result: RealResultInput | None = None


@dataclass(frozen=True, slots=True)
class ForcedInjuryDTO:
    """An injury applied on its date for `days` days: from the content (`forced_events`) or
    from a dilemma effect."""

    player_id: PlayerId
    date: date
    days: int


@dataclass(frozen=True, slots=True)
class KnockoutSlotInput:
    """Historical bracket slot; swapping occupants never changes its ID, date or venue."""

    fixture_id: FixtureId
    stage_id: str
    date: date | None
    home: ClubSeasonId
    away: ClubSeasonId
    venue: Literal["home", "neutral"] | None
    leg: Literal[1, 2] | None
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]


@dataclass(frozen=True, slots=True)
class KnockoutCalendarInput:
    """None slots means unknown; an empty sourced tuple declares applicable absence."""

    competition_id: CompetitionId
    slots: tuple[KnockoutSlotInput, ...] | None
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]


@dataclass(frozen=True, slots=True)
class GroupEntryAssignmentInput:
    """Historical representative of one explicitly sourced qualifying position."""

    source_stage_id: str
    group_id: str
    qualifying_position: int
    target_stage_id: str
    historical_representative: ClubSeasonId
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]


@dataclass(frozen=True, slots=True)
class GroupEntryAssignmentsInput:
    """Complete declarations of historical qualifying slots for one competition."""

    competition_id: CompetitionId
    entries: tuple[GroupEntryAssignmentInput, ...] | None
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]


@dataclass(frozen=True, slots=True)
class HeadToHeadFixtureInput:
    """Sourced calendar entry; the home/away orientation is independent of the managed club."""

    fixture_id: FixtureId
    date: date
    home: ClubSeasonId
    away: ClubSeasonId
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]
    venue: Literal["home", "neutral"] | None = None


@dataclass(frozen=True, slots=True)
class HeadToHeadResultInput:
    """Sourced regulation score (home, away); None remains explicitly pending."""

    fixture_id: FixtureId
    score: tuple[int, int] | None
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]


@dataclass(frozen=True, slots=True)
class HeadToHeadEvidenceInput:
    """Declared complete calendar between covered clubs through an inclusive date.

    Sources are a narrow exception to editorial metadata staying outside published APIs:
    private table strategies require evidence of historical calendar completeness.
    """

    competition_id: CompetitionId
    complete_through: date
    covered_clubs: tuple[ClubSeasonId, ...]
    schedule: tuple[HeadToHeadFixtureInput, ...]
    results: tuple[HeadToHeadResultInput, ...]
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]
    stage_id: str | None = None
    group_id: str | None = None


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
    """A league table, or a group's table (`stage_id` and `group_id`), as of a date."""

    competition_id: CompetitionId
    as_of: date
    rows: tuple[StandingRowDTO, ...]
    stage_id: str | None = None
    group_id: str | None = None
    unresolved_ties: tuple[tuple[ClubSeasonId, ...], ...] | None = None

    def __post_init__(self) -> None:
        if self.unresolved_ties is None:
            return
        if not isinstance(self.unresolved_ties, tuple):
            raise InvalidValueError("unresolved ties must be an immutable tuple or None")
        order = [row.club_season_id for row in self.rows]
        if len(set(order)) != len(order):
            raise InvalidValueError("unresolved standings need distinct row participants")
        used: set[ClubSeasonId] = set()
        for group in self.unresolved_ties:
            _require_clubs(group, minimum=2)
            if used.intersection(group) or not set(group) <= set(order):
                raise InvalidValueError("unresolved groups must be disjoint row participants")
            indices = sorted(order.index(club) for club in group)
            if indices != list(range(indices[0], indices[-1] + 1)):
                raise InvalidValueError(
                    "unresolved groups must occupy contiguous presentation rows"
                )
            used.update(group)


# --------------------------------------------------------------------------- request


@dataclass(frozen=True, slots=True)
class SeasonSimInput:
    """What the content fixes for the whole season.

    `teams` are the reference squads (or aggregates) of **every** participant, the managed
    team included, as the content has them: they fix the strength normalisation. `fixtures`
    are the managed team's whole calendar; `forced_injuries` come from the content.
    """

    managed_club_season_id: ClubSeasonId
    teams: tuple[TeamInput, ...]
    competitions: tuple[CompetitionInput, ...]
    fixtures: tuple[FixtureInput, ...]
    forced_injuries: tuple[ForcedInjuryDTO, ...] = ()
    historical_standings: tuple[StandingsDTO, ...] = ()
    head_to_head: tuple[HeadToHeadEvidenceInput, ...] | None = None
    knockout_calendar: tuple[KnockoutCalendarInput, ...] | None = None
    group_entry_assignments: tuple[GroupEntryAssignmentsInput, ...] | None = None


@dataclass(frozen=True, slots=True)
class BlockSimRequest:
    """Simulate the fixtures of `season` dated from `start` to `end` (both included).

    `managed_team` is its state at the start of the block and `team_morale` its morale (mu in
    ADR-004, apart from each player's morale). `team_overrides` are the effective squads of
    the rivals changed by signings and sales; any other rival plays with its reference squad.
    `competition_priorities` defaults to `normal`. `forced_injuries_from_effects` are injuries
    caused by dilemma effects, dated, on top of the season's. `prior_results` are the results
    of earlier blocks, to carry the standings forward.
    `state_as_of=None` means the incoming state is already situated at `start`. A continuation
    supplies its previous close explicitly; T2.6 recovers from that date and rejects a date
    after `start`. It must never infer this cursor from `prior_results`.
    """

    season: SeasonSimInput
    block_id: BlockId
    start: date
    end: date
    managed_team: SquadTeamInput
    team_morale: int = 50
    team_overrides: tuple[SquadTeamInput, ...] = ()
    competition_priorities: Mapping[CompetitionId, PriorityName] = field(default_factory=dict)
    forced_injuries_from_effects: tuple[ForcedInjuryDTO, ...] = ()
    prior_results: tuple["MatchResultDTO", ...] = ()
    state_as_of: date | None = None


# --------------------------------------------------------------------------- output


@dataclass(frozen=True, slots=True)
class MatchResultDTO:
    """Result of a played fixture; enough to build the OpenAPI `MatchReport`.

    `regulation` is the 90 minutes. `extra_time` holds the goals of those 30 minutes only and
    `penalties` the shootout. `venue`, `opponent` and `user_result` are from the managed
    team's point of view (`user_result` counts extra time and penalties). `winner` is the match
    winner by side, `None` for a drawn league match.
    """

    fixture_id: FixtureId
    competition_id: CompetitionId
    date: date
    home: ClubSeasonId
    away: ClubSeasonId
    regulation: tuple[int, int]
    venue: TeamVenueName
    opponent: ClubSeasonId
    user_result: UserResultName
    extra_time: tuple[int, int] | None = None
    penalties: tuple[int, int] | None = None
    winner: Literal["home", "away"] | None = None
    key: bool = False
    round: int | None = None
    stage_id: str | None = None
    group_id: str | None = None
    leg: Literal[1, 2] | None = None


@dataclass(frozen=True, slots=True)
class InjuryDTO:
    """An injury suffered in the block (`forced` when it comes from content or an effect)."""

    player_id: PlayerId
    date: date
    days: int
    forced: bool = False


@dataclass(frozen=True, slots=True)
class PlayerStateDTO:
    """State of a managed-team player at the close of the block: fitness, injury and the
    minutes he played in the block (a star without minutes loses morale, T3.3)."""

    player_id: PlayerId
    fitness: int
    injured_until: date | None = None
    minutes_played: int = 0


@dataclass(frozen=True, slots=True)
class EventDTO:
    """A notable fact of the block: the managed team advances, is eliminated or wins a
    competition. New kinds are additive."""

    kind: Literal["advanced", "eliminated", "champion"]
    date: date
    club_season_id: ClubSeasonId
    competition_id: CompetitionId
    stage_id: str | None = None


_TIE_CLUB_COUNT = 2
_MAX_TIE_FIXTURES = 2


def _require_clubs(clubs: tuple[ClubSeasonId, ...], *, minimum: int) -> None:
    if (
        not isinstance(clubs, tuple)
        or len(clubs) < minimum
        or not all(isinstance(club, ClubSeasonId) for club in clubs)
        or len(set(clubs)) != len(clubs)
    ):
        raise InvalidValueError("clubs must be a tuple of distinct typed club IDs")


@dataclass(frozen=True, slots=True)
class UnresolvedKnockoutTieDTO:
    """Exhausted tie without a winner, emitted only from complete domain state by T2.6.

    This value validates identity, not exhaustion: rules and previous-block results live
    in the use case. A match winner is never interpreted here as a tie winner.
    """

    competition_id: CompetitionId
    stage_id: str
    clubs: tuple[ClubSeasonId, ...]
    fixture_ids: tuple[FixtureId, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.competition_id, CompetitionId):
            raise InvalidValueError("an unresolved tie needs a typed competition ID")
        if not isinstance(self.stage_id, str) or not self.stage_id.strip():
            raise InvalidValueError("an unresolved tie needs a stage ID")
        _require_clubs(self.clubs, minimum=2)
        if len(self.clubs) != _TIE_CLUB_COUNT:
            raise InvalidValueError("an unresolved knockout tie needs exactly two clubs")
        if (
            not isinstance(self.fixture_ids, tuple)
            or not 1 <= len(self.fixture_ids) <= _MAX_TIE_FIXTURES
            or not all(isinstance(value, FixtureId) for value in self.fixture_ids)
            or len(set(self.fixture_ids)) != len(self.fixture_ids)
        ):
            raise InvalidValueError("an unresolved tie needs one or two distinct typed fixture IDs")


@dataclass(frozen=True, slots=True)
class BlockSummaryDTO:
    """Outcome of a block: results, key matches (by fixture), tables, events, injuries and
    the managed team's player states at the close."""

    block_id: BlockId
    results: tuple[MatchResultDTO, ...] = ()
    key_matches: tuple[FixtureId, ...] = ()
    standings: tuple[StandingsDTO, ...] = ()
    events: tuple[EventDTO, ...] = ()
    injuries: tuple[InjuryDTO, ...] = ()
    player_states: tuple[PlayerStateDTO, ...] = ()
    unresolved_knockout_ties: tuple[UnresolvedKnockoutTieDTO, ...] | None = None

    def __post_init__(self) -> None:
        if self.unresolved_knockout_ties is None:
            return
        if not isinstance(self.unresolved_knockout_ties, tuple):
            raise InvalidValueError("unresolved knockout ties must be an immutable tuple or None")
        used: set[FixtureId] = set()
        occupied: set[tuple[CompetitionId, str, ClubSeasonId]] = set()
        for tie in self.unresolved_knockout_ties:
            if not isinstance(tie, UnresolvedKnockoutTieDTO):
                raise InvalidValueError("unresolved knockout entries must be typed values")
            keys = {(tie.competition_id, tie.stage_id, club) for club in tie.clubs}
            if used.intersection(tie.fixture_ids) or occupied.intersection(keys):
                raise InvalidValueError(
                    "unresolved ties cannot repeat fixtures or stage participants"
                )
            used.update(tie.fixture_ids)
            occupied.update(keys)
            for result in self.results:
                if result.fixture_id in tie.fixture_ids and (
                    result.competition_id != tie.competition_id
                    or result.stage_id != tie.stage_id
                    or {result.home, result.away} != set(tie.clubs)
                ):
                    raise InvalidValueError("a played result contradicts unresolved tie identity")


# --------------------------------------------------------------------------- facade


class SimulationService:
    """Facade of the engine. Deterministic: the same request and `rng` give the same summary."""

    def simulate_block(self, request: BlockSimRequest, rng: RandomSource) -> BlockSummaryDTO:
        """Simulate one block in date order, drawing from streams derived from `rng`.

        Delegates to `application/simulate_block.py`, which T2.6 implements; raises
        `InvalidValueError` for an invalid request and `NotImplementedError` until then.
        """
        return simulate_block.simulate_block(request, rng)
