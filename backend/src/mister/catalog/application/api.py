"""Published API of the Catalog context: the read-only *published language* (PLAN §3.1).

Everything a playable season needs to be played, as immutable DTOs in pure Python: no Pydantic
and no import of the Catalog domain or infrastructure. Other contexts (Game, Evaluation) may
import this module, and only from an adapter of their own `infrastructure` (the ACL, PLAN §3.2
rule 4). Mapping the validated content tree to these DTOs is the job of the Catalog adapter
(T2.20); this module is only the contract.

Decisions:

- Slug identifiers that the shared kernel types (`PlayerId`, `CompetitionId`, ...) use those
  types. Stage, group and objective ids are local to a season file and stay plain `str` slugs.
- `goal_baseline` is always resolved: a content `from_league` reference is replaced by the
  referenced league's stats, so consumers never follow references.
- Ratings and ages are required: only release-validated content (no `verify: pending`) is
  published as playable.
- Effects are a closed union (`EffectDTO`), one frozen dataclass per type of the content DSL
  (`docs/content/content-format.md` §8). Consumers `match` on it and close the match with
  `assert_never`, so adding a type is a contract change that mypy reports everywhere.
- `PlayableSeasonDTO.club_seasons` holds every participant of any competition of the season
  (the own club-season included), sorted by id; `texts` holds only reviewed texts. The exact
  mapping is pinned by the Test FC oracle of the contract suite.
- Sources and `verify` flags stay in the content except for explicit head-to-head
  evidence: consumers need the provenance of its declared calendar coverage.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Literal, Protocol

from mister.catalog.domain.name_policy import NamePolicy
from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import (
    BlockId,
    ClubId,
    ClubSeasonId,
    CompetitionId,
    DilemmaId,
    FixtureId,
    OptionId,
    PlayableSeasonId,
    PlayerId,
)

# ----------------------------------------------------------------------------- vocabulary


class TacticStyle(StrEnum):
    PRESSING = "pressing"
    COUNTER = "counter"
    POSSESSION = "possession"
    BALANCED = "balanced"


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class Position(StrEnum):
    GK = "GK"
    DF = "DF"
    MF = "MF"
    FW = "FW"


class Subrole(StrEnum):
    CB = "CB"
    LB = "LB"
    RB = "RB"
    DM = "DM"
    CM = "CM"
    AM = "AM"
    WG = "WG"
    ST = "ST"


class Venue(StrEnum):
    HOME = "home"
    AWAY = "away"
    NEUTRAL = "neutral"


class CompetitionKind(StrEnum):
    LEAGUE = "league"
    CUP = "cup"
    SUPER_CUP = "super_cup"
    CONTINENTAL_CUP = "continental_cup"


class CompetitionTier(StrEnum):
    DOMESTIC_LEAGUE = "domestic_league"
    DOMESTIC_CUP = "domestic_cup"
    DOMESTIC_SUPER_CUP = "domestic_super_cup"
    CONTINENTAL_PRIMARY = "continental_primary"
    CONTINENTAL_SECONDARY = "continental_secondary"


class Round(StrEnum):
    """Rounds of a knockout competition, in playing order."""

    QUALIFYING = "qualifying"
    PLAYOFF = "playoff"
    GROUP_STAGE = "group_stage"
    ROUND_OF_128 = "round_of_128"
    ROUND_OF_64 = "round_of_64"
    ROUND_OF_32 = "round_of_32"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    FINAL = "final"


class Tiebreaker(StrEnum):
    HEAD_TO_HEAD_POINTS = "head_to_head_points"
    HEAD_TO_HEAD_GOAL_DIFFERENCE = "head_to_head_goal_difference"
    HEAD_TO_HEAD_GOALS_FOR = "head_to_head_goals_for"
    HEAD_TO_HEAD_AWAY_GOALS = "head_to_head_away_goals"
    GOAL_DIFFERENCE = "goal_difference"
    GOALS_FOR = "goals_for"
    WINS = "wins"
    CLUB_COEFFICIENT = "club_coefficient"


class ObjectiveKind(StrEnum):
    WIN = "win"
    FINISH_TOP = "finish_top"
    REACH_STAGE = "reach_stage"


class TextKind(StrEnum):
    PRESENTATION = "presentation"
    EVENT = "event"
    VERDICT = "verdict"


# ----------------------------------------------------------------------------- season shape


@dataclass(frozen=True, slots=True)
class TacticDTO:
    """Playing style plus system (`4-3-3`: outfield lines separated by hyphens)."""

    style: TacticStyle
    system: str


@dataclass(frozen=True, slots=True)
class BlockDTO:
    """A stretch of the season; `end` is the date of the standings cutoff."""

    id: BlockId
    label: str
    start: date
    end: date


@dataclass(frozen=True, slots=True)
class ManagerDTO:
    """The real manager of the season."""

    display_name: str
    alias_name: str


@dataclass(frozen=True, slots=True)
class GoalStatsDTO:
    """Goals of the home and the away sides over `matches` matches: the engine's baseline."""

    matches: int
    home_goals: int
    away_goals: int


@dataclass(frozen=True, slots=True)
class LeagueRulesDTO:
    """Format of a league: configured per competition and per season."""

    rounds: int
    points_per_win: int
    points_per_draw: int
    tiebreakers: tuple[Tiebreaker, ...]
    league_stats: GoalStatsDTO


@dataclass(frozen=True, slots=True)
class GroupDTO:
    id: str
    participants: tuple[ClubSeasonId, ...]


@dataclass(frozen=True, slots=True)
class GroupStageDTO:
    """Configuration of a group stage (only on a stage whose round is `GROUP_STAGE`)."""

    groups: tuple[GroupDTO, ...]
    points_per_win: int
    points_per_draw: int
    tiebreakers: tuple[Tiebreaker, ...]
    advance_per_group: int
    reapply_head_to_head: bool | None = None
    coefficients: tuple[tuple[ClubSeasonId, int], ...] = ()


@dataclass(frozen=True, slots=True)
class StageDTO:
    """A round of a knockout competition, or its group stage."""

    id: str
    name: str
    round: Round
    legs: int
    away_goals_rule: bool
    extra_time: bool
    penalties: bool
    group_stage: GroupStageDTO | None = None
    away_goals_in_extra_time: bool | None = None


@dataclass(frozen=True, slots=True)
class CompetitionDTO:
    """A competition of the season.

    A league has `league` rules and no stages; any other kind has stages and no league rules.
    `goal_baseline` is always present (for a league it equals `league.league_stats`).
    """

    id: CompetitionId
    name: str
    kind: CompetitionKind
    tier: CompetitionTier
    participants: tuple[ClubSeasonId, ...]
    goal_baseline: GoalStatsDTO
    league: LeagueRulesDTO | None = None
    stages: tuple[StageDTO, ...] = ()

    def __post_init__(self) -> None:
        is_league = self.kind is CompetitionKind.LEAGUE
        if is_league and (self.league is None or self.stages):
            raise InvalidValueError(f"league {self.id} needs league rules and no stages")
        if not is_league and (self.league is not None or not self.stages):
            raise InvalidValueError(f"competition {self.id} needs stages and no league rules")


@dataclass(frozen=True, slots=True)
class BoardObjectiveDTO:
    """What the board expects in a competition (editorial)."""

    id: str
    competition_id: CompetitionId
    kind: ObjectiveKind
    text: str
    target_position: int | None = None
    target_stage: str | None = None


@dataclass(frozen=True, slots=True)
class InjuryForcedEventDTO:
    """A real injury replayed in every run."""

    player_id: PlayerId
    date: date
    days: int


ForcedEventDTO = InjuryForcedEventDTO
"""Becomes a union as soon as a second kind of forced event exists."""


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeDTO:
    """What really happened in a competition (one per competition)."""

    competition_id: CompetitionId
    champion: bool
    final_position: int | None = None
    eliminated_in: str | None = None


# ----------------------------------------------------------------------------- squads


@dataclass(frozen=True, slots=True)
class PlayerDTO:
    player_id: PlayerId
    display_name: str
    alias_name: str
    position: Position
    age: int
    rating: int
    key: bool
    subrole: Subrole | None = None
    joined_on: date | None = None
    left_on: date | None = None


@dataclass(frozen=True, slots=True)
class AggregateStrengthDTO:
    """Strength of a rival without a squad (`defense` high means a better defence)."""

    attack: int
    defense: int


@dataclass(frozen=True, slots=True)
class RealLeagueDTO:
    """The league the club really played that season."""

    competition_label: str
    played: int
    goals_for: int
    goals_against: int


@dataclass(frozen=True, slots=True)
class ClubSeasonDTO:
    """A club in a season (ADR-015), as the own team or as a rival.

    Exactly one of `squad` and `aggregate`. Identity (name and colors) comes from the club.
    """

    id: ClubSeasonId
    club_id: ClubId
    name: str
    short_name: str
    primary_color: str
    secondary_color: str
    season: str
    default_tactic: TacticDTO
    squad: tuple[PlayerDTO, ...] | None
    aggregate: AggregateStrengthDTO | None
    real_league: RealLeagueDTO | None = None

    def __post_init__(self) -> None:
        if (self.squad is None) == (self.aggregate is None):
            raise InvalidValueError(f"{self.id} needs a squad or an aggregate, never both")


# ----------------------------------------------------------------------------- real history


@dataclass(frozen=True, slots=True)
class RealResultDTO:
    """A real result, from the own team's point of view."""

    goals_for: int
    goals_against: int
    extra_time: bool = False
    penalties_for: int | None = None
    penalties_against: int | None = None


@dataclass(frozen=True, slots=True)
class FixtureDTO:
    """An official match of the own team."""

    id: FixtureId
    date: date
    competition_id: CompetitionId
    opponent: ClubSeasonId
    venue: Venue
    round: int | None = None
    stage: str | None = None
    leg: int | None = None
    group: str | None = None
    key: bool = False
    result: RealResultDTO | None = None


@dataclass(frozen=True, slots=True)
class KnockoutSlotDTO:
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
class KnockoutCalendarDTO:
    """None slots means unknown; an empty sourced tuple declares applicable absence."""

    competition_id: CompetitionId
    slots: tuple[KnockoutSlotDTO, ...] | None
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]


@dataclass(frozen=True, slots=True)
class GroupEntryAssignmentDTO:
    """Historical representative of one explicitly sourced qualifying position."""

    source_stage_id: str
    group_id: str
    qualifying_position: int
    target_stage_id: str
    historical_representative: ClubSeasonId
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]


@dataclass(frozen=True, slots=True)
class GroupEntryAssignmentsDTO:
    """Complete declarations of historical qualifying slots for one competition."""

    competition_id: CompetitionId
    entries: tuple[GroupEntryAssignmentDTO, ...] | None
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]


@dataclass(frozen=True, slots=True)
class HeadToHeadFixtureDTO:
    """Sourced calendar entry; the home/away orientation is independent of the managed club."""

    fixture_id: FixtureId
    date: date
    home: ClubSeasonId
    away: ClubSeasonId
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]
    venue: Literal["home", "neutral"] | None = None


@dataclass(frozen=True, slots=True)
class HeadToHeadResultDTO:
    """Sourced regulation score (home, away); None remains explicitly pending."""

    fixture_id: FixtureId
    score: tuple[int, int] | None
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]


@dataclass(frozen=True, slots=True)
class HeadToHeadEvidenceDTO:
    """Declared complete calendar between covered clubs through an inclusive date.

    Sources are a narrow exception to editorial metadata staying outside published APIs:
    private table strategies require evidence of historical calendar completeness.
    """

    competition_id: CompetitionId
    complete_through: date
    covered_clubs: tuple[ClubSeasonId, ...]
    schedule: tuple[HeadToHeadFixtureDTO, ...]
    results: tuple[HeadToHeadResultDTO, ...]
    sources: tuple[str, ...]
    verify: Literal["ok", "pending"]
    stage_id: str | None = None
    group_id: str | None = None


@dataclass(frozen=True, slots=True)
class StandingRowDTO:
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
class StandingsCutoffDTO:
    """The real table of a league (or of a group) at the end of a block."""

    block_id: BlockId
    competition_id: CompetitionId
    date: date
    table: tuple[StandingRowDTO, ...]
    stage: str | None = None
    group: str | None = None


@dataclass(frozen=True, slots=True)
class RealTieDTO:
    """A real knockout tie, including the ones the own team did not play."""

    competition_id: CompetitionId
    stage: str
    clubs: tuple[ClubSeasonId, ClubSeasonId]
    winner: ClubSeasonId | None = None
    aggregate: str | None = None


# ----------------------------------------------------------------------------- effects DSL


@dataclass(frozen=True, slots=True)
class MoraleEffectDTO:
    """Morale of the whole squad (0-100 scale)."""

    delta: int


@dataclass(frozen=True, slots=True)
class PlayerMoraleEffectDTO:
    player_id: PlayerId
    delta: int


@dataclass(frozen=True, slots=True)
class SignPlayerEffectDTO:
    """Signs a player; with `from_club_season` he leaves that rival's squad."""

    player_id: PlayerId
    from_club_season: ClubSeasonId | None = None


@dataclass(frozen=True, slots=True)
class SellPlayerEffectDTO:
    """Sells a player; with `to_club_season` he joins that rival's squad."""

    player_id: PlayerId
    to_club_season: ClubSeasonId | None = None


@dataclass(frozen=True, slots=True)
class SetTacticEffectDTO:
    style: TacticStyle
    system: str


@dataclass(frozen=True, slots=True)
class CompetitionPriorityEffectDTO:
    competition_id: CompetitionId
    priority: Priority


@dataclass(frozen=True, slots=True)
class BoardConfidenceEffectDTO:
    """Confidence of the board (0-100 scale)."""

    delta: int


@dataclass(frozen=True, slots=True)
class YouthMinutesEffectDTO:
    player_id: PlayerId


@dataclass(frozen=True, slots=True)
class InjuryEffectDTO:
    """A forced injury from `date` for `days` days."""

    player_id: PlayerId
    date: date
    days: int


@dataclass(frozen=True, slots=True)
class FitnessEffectDTO:
    """Fitness of the whole squad, or of one player when `player_id` is set."""

    delta: int
    player_id: PlayerId | None = None


EffectDTO = (
    MoraleEffectDTO
    | PlayerMoraleEffectDTO
    | SignPlayerEffectDTO
    | SellPlayerEffectDTO
    | SetTacticEffectDTO
    | CompetitionPriorityEffectDTO
    | BoardConfidenceEffectDTO
    | YouthMinutesEffectDTO
    | InjuryEffectDTO
    | FitnessEffectDTO
)
"""The closed set of effects. Match on it exhaustively and finish with `assert_never`."""


# ----------------------------------------------------------------------------- dilemmas, texts


@dataclass(frozen=True, slots=True)
class DilemmaOptionDTO:
    id: OptionId
    label: str
    effects: tuple[EffectDTO, ...]


@dataclass(frozen=True, slots=True)
class DilemmaDTO:
    """A decision of a block. `historical_option` is what the real manager did."""

    id: DilemmaId
    block_id: BlockId
    title: str
    prompt: str
    options: tuple[DilemmaOptionDTO, ...]
    historical_option: OptionId

    def __post_init__(self) -> None:
        if self.historical_option not in {option.id for option in self.options}:
            raise InvalidValueError(
                f"historical option {self.historical_option} is not an option of {self.id}"
            )


@dataclass(frozen=True, slots=True)
class TextDTO:
    """A user-facing text (Spanish). Only reviewed texts are published."""

    id: str
    kind: TextKind
    body: str


# ----------------------------------------------------------------------------- the season


@dataclass(frozen=True, slots=True)
class PlayableSeasonSummaryDTO:
    """What the season picker lists."""

    id: PlayableSeasonId
    club_name: str
    short_name: str
    season: str
    historical_manager: str
    primary_color: str
    secondary_color: str


@dataclass(frozen=True, slots=True)
class PlayableSeasonDTO:
    """Everything the game needs of a playable season (ADR-015).

    `club_seasons` holds the own club-season and every rival (squad or aggregate);
    `market_players` the signable players that belong to no club of the game.
    """

    id: PlayableSeasonId
    club_season_id: ClubSeasonId
    season: str
    manager: ManagerDTO
    initial_tactic: TacticDTO
    blocks: tuple[BlockDTO, ...]
    competitions: tuple[CompetitionDTO, ...]
    forced_events: tuple[ForcedEventDTO, ...]
    board_objectives: tuple[BoardObjectiveDTO, ...]
    historical_outcomes: tuple[HistoricalOutcomeDTO, ...]
    club_seasons: tuple[ClubSeasonDTO, ...]
    market_players: tuple[PlayerDTO, ...]
    fixtures: tuple[FixtureDTO, ...]
    standings: tuple[StandingsCutoffDTO, ...]
    real_ties: tuple[RealTieDTO, ...]
    dilemmas: tuple[DilemmaDTO, ...]
    texts: tuple[TextDTO, ...]
    head_to_head: tuple[HeadToHeadEvidenceDTO, ...] | None = None
    knockout_calendar: tuple[KnockoutCalendarDTO, ...] | None = None
    group_entry_assignments: tuple[GroupEntryAssignmentsDTO, ...] | None = None

    def __post_init__(self) -> None:
        if all(club.id != self.club_season_id for club in self.club_seasons):
            raise InvalidValueError(f"own club season {self.club_season_id} is not in the season")

    @property
    def own_club_season(self) -> ClubSeasonDTO:
        return next(club for club in self.club_seasons if club.id == self.club_season_id)

    def summary(self) -> PlayableSeasonSummaryDTO:
        own = self.own_club_season
        return PlayableSeasonSummaryDTO(
            id=self.id,
            club_name=own.name,
            short_name=own.short_name,
            season=self.season,
            historical_manager=self.manager.display_name,
            primary_color=own.primary_color,
            secondary_color=own.secondary_color,
        )


# ----------------------------------------------------------------------------- the port


class PlayableSeasonNotFoundError(DomainError):
    """The requested playable season does not exist (API: `404 season_not_found`)."""

    code = "season_not_found"

    def __init__(self, season_id: PlayableSeasonId) -> None:
        super().__init__(f"playable season {season_id} not found")
        self.season_id = season_id


class SeasonContentProvider(Protocol):
    """Read-only access to the playable seasons (Catalog → Game, PLAN §3.1).

    Implemented by the Catalog infrastructure (in-memory fake, then the database adapter) and
    consumed by an ACL adapter of the consuming context.
    """

    def list_playable_seasons(self) -> Sequence[PlayableSeasonSummaryDTO]:
        """Summaries of every playable season, ordered by id."""
        ...

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        """The full season; raises `PlayableSeasonNotFoundError` if it does not exist."""
        ...


def present_person_name(display_name: str, alias_name: str, *, real_names: bool) -> str:
    """Apply the published presentation policy without exposing Catalog domain types."""
    return NamePolicy(real_names).display(display_name, alias_name)
