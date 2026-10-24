"""`content/seasons/<slug>/season.yaml`: blocks, competitions, objectives and real outcome."""

from datetime import date, timedelta
from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import (
    ClubSeasonSlug,
    ContentModel,
    NonBlank,
    PlayerId,
    SeasonLabel,
    Slug,
    SourcedModel,
    enum_from_text,
    season_is_consecutive,
)
from mister.catalog.infrastructure.content_schema.effects import MAX_INJURY_DAYS, Tactic

TWO_LEGS = 2
MIN_BLOCKS = 5
MAX_BLOCKS = 6

Round = Literal[
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
_ROUND_ORDER: dict[str, int] = {name: rank for rank, name in enumerate(Round.__args__)}  # type: ignore[attr-defined]


class Block(ContentModel):
    """A stretch of the season. Blocks must not overlap; each ends on a standings cutoff."""

    id: Slug
    label: NonBlank
    start: date
    end: date

    @model_validator(mode="after")
    def _check_range(self) -> Self:
        if self.end < self.start:
            raise ValueError("end must not be before start")
        return self


class Manager(SourcedModel):
    """The real manager of the season."""

    display_name: NonBlank
    alias_name: NonBlank


class Tiebreaker(StrEnum):
    """Tiebreak criteria for league tables, applied in the listed order."""

    HEAD_TO_HEAD_POINTS = "head_to_head_points"
    HEAD_TO_HEAD_GOAL_DIFFERENCE = "head_to_head_goal_difference"
    HEAD_TO_HEAD_GOALS_FOR = "head_to_head_goals_for"
    HEAD_TO_HEAD_AWAY_GOALS = "head_to_head_away_goals"
    GOAL_DIFFERENCE = "goal_difference"
    GOALS_FOR = "goals_for"
    WINS = "wins"


Tiebreakers = Annotated[
    tuple[Annotated[Tiebreaker, enum_from_text(Tiebreaker)], ...], Field(min_length=1)
]


class GoalStats(SourcedModel):
    """Goals scored by the home and the away sides over a number of matches.

    It gives the engine its goal baseline and home advantage.
    """

    nullable_when_pending = ("matches", "home_goals", "away_goals")

    matches: Annotated[int, Field(ge=1)] | None
    home_goals: Annotated[int, Field(ge=1)] | None
    away_goals: Annotated[int, Field(ge=1)] | None


class GoalBaselineFromLeague(ContentModel):
    """Reuse the goal statistics of a league of the same season."""

    from_league: Slug


GoalBaseline = GoalBaselineFromLeague | GoalStats


class Group(ContentModel):
    """A group of a group stage."""

    id: Slug
    participants: Annotated[tuple[ClubSeasonSlug, ...], Field(min_length=2)]


class AwayGoalsExtraTime(SourcedModel):
    """Historical extra-time variant; unknown never means disabled."""

    nullable_when_pending = ("value",)
    value: bool | None


class Stage(ContentModel):
    """A round of a knockout competition, or its group stage (`round: group_stage`).

    Format and rules are set per competition and per season. The group fields are required
    for a group stage and forbidden otherwise.
    """

    id: Slug
    name: NonBlank
    round: Round
    legs: Literal[1, 2]
    away_goals_rule: bool
    extra_time: bool
    penalties: bool
    groups: Annotated[tuple[Group, ...], Field(min_length=1)] | None = None
    points_per_win: Annotated[int, Field(ge=2, le=3)] | None = None
    points_per_draw: Annotated[int, Field(ge=0, le=1)] | None = None
    tiebreakers: Tiebreakers | None = None
    advance_per_group: Annotated[int, Field(ge=1)] | None = None
    away_goals_in_extra_time: AwayGoalsExtraTime | None = None

    @property
    def is_group_stage(self) -> bool:
        return self.round == "group_stage"

    @model_validator(mode="after")
    def _check_stage(self) -> Self:
        if self.away_goals_rule and self.legs != TWO_LEGS:
            raise ValueError("away_goals_rule only applies to two-legged stages")
        variant = self.away_goals_in_extra_time
        if (
            variant is not None
            and variant.value is True
            and not (
                self.legs == TWO_LEGS
                and self.away_goals_rule
                and self.extra_time
                and not self.is_group_stage
            )
        ):
            raise ValueError(
                "away_goals_in_extra_time true requires a two-legged knockout "
                "with away goals and extra time"
            )
        group_fields = {
            "groups": self.groups,
            "points_per_win": self.points_per_win,
            "points_per_draw": self.points_per_draw,
            "tiebreakers": self.tiebreakers,
            "advance_per_group": self.advance_per_group,
        }
        if self.is_group_stage:
            missing = [name for name, value in group_fields.items() if value is None]
            if missing:
                raise ValueError(f"a group_stage needs {', '.join(missing)}")
            smallest = min(len(g.participants) for g in self.groups or ())
            if (self.advance_per_group or 0) >= smallest:
                raise ValueError(
                    f"advance_per_group must be smaller than the group size ({smallest})"
                )
        elif any(value is not None for value in group_fields.values()):
            raise ValueError("group fields (groups, points...) only apply to a group_stage")
        return self


KnockoutStage = Stage


class _CompetitionBase(ContentModel):
    id: Slug
    name: NonBlank
    participants: Annotated[tuple[ClubSeasonSlug, ...], Field(min_length=2)]

    @model_validator(mode="after")
    def _check_participants(self) -> Self:
        if len(set(self.participants)) != len(self.participants):
            raise ValueError("duplicate participants")
        return self


class LeagueCompetition(_CompetitionBase):
    """A league: single or double round robin, with configurable points and tiebreakers."""

    kind: Literal["league"]
    tier: Literal["domestic_league"]
    rounds: Literal[1, 2]
    points_per_win: Annotated[int, Field(ge=2, le=3)]
    points_per_draw: Annotated[int, Field(ge=0, le=1)]
    tiebreakers: Tiebreakers
    league_stats: GoalStats

    @property
    def total_matches(self) -> int:
        n = len(self.participants)
        return n * (n - 1) // 2 * self.rounds

    @model_validator(mode="after")
    def _check_stats(self) -> Self:
        matches = self.league_stats.matches
        if matches is not None and matches != self.total_matches:
            raise ValueError(
                f"league_stats.matches is {matches} but the format has {self.total_matches}"
            )
        return self


class _KnockoutBase(_CompetitionBase):
    goal_baseline: GoalBaseline
    stages: Annotated[tuple[Stage, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_stages(self) -> Self:
        ids = [s.id for s in self.stages]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate stage id")
        for earlier, later in pairwise(self.stages):
            rank_a, rank_b = _ROUND_ORDER[earlier.round], _ROUND_ORDER[later.round]
            repeated_qualifying = earlier.round == later.round == "qualifying"
            if rank_a > rank_b or (rank_a == rank_b and not repeated_qualifying):
                raise ValueError(
                    "stages must be listed in the order of their rounds "
                    "(only qualifying may repeat)"
                )
        for stage in self.stages:
            for group in stage.groups or ():
                unknown = set(group.participants) - set(self.participants)
                if unknown:
                    raise ValueError(f"group {group.id} has non-participants: {sorted(unknown)}")
        return self


class CupCompetition(_KnockoutBase):
    """A domestic cup."""

    kind: Literal["cup"]
    tier: Literal["domestic_cup"]


class SuperCupCompetition(_KnockoutBase):
    """A domestic super cup."""

    kind: Literal["super_cup"]
    tier: Literal["domestic_super_cup"]


class ContinentalCupCompetition(_KnockoutBase):
    """A continental cup, with a group stage and/or knockout rounds."""

    kind: Literal["continental_cup"]
    tier: Literal["continental_primary", "continental_secondary"]


Competition = Annotated[
    LeagueCompetition | CupCompetition | SuperCupCompetition | ContinentalCupCompetition,
    Field(discriminator="kind"),
]


class InjuryEvent(SourcedModel):
    """A real injury that really happened and is replayed in every run."""

    type: Literal["injury"]
    player_id: PlayerId
    date: date
    days: Annotated[int, Field(ge=1, le=MAX_INJURY_DAYS)]


# A union discriminated by `type` as soon as a second kind of forced event exists.
ForcedEvent = InjuryEvent


class BoardObjective(ContentModel):
    """What the board expects in a competition. Editorial, not a historical datum."""

    id: Slug
    competition: Slug
    kind: Literal["win", "finish_top", "reach_stage"]
    target_position: Annotated[int, Field(ge=1)] | None = None
    target_stage: Slug | None = None
    text: NonBlank

    @model_validator(mode="after")
    def _check_target(self) -> Self:
        if self.kind == "finish_top" and self.target_position is None:
            raise ValueError("target_position is required for finish_top")
        if self.kind == "reach_stage" and self.target_stage is None:
            raise ValueError("target_stage is required for reach_stage")
        return self


class CompetitionOutcome(SourcedModel):
    """What really happened in a competition."""

    competition: Slug
    champion: bool
    # Final league position. A league outcome needs it unless pending (checked by the loader).
    final_position: Annotated[int, Field(ge=1)] | None
    # Id of the stage where the club was eliminated; may be the group stage.
    eliminated_in: Slug | None

    @model_validator(mode="after")
    def _check_outcome(self) -> Self:
        if self.champion and self.eliminated_in is not None:
            raise ValueError("a champion cannot be eliminated: champion and eliminated_in clash")
        return self


class SeasonFile(ContentModel):
    """The playable season: everything that references club-seasons but is not a squad."""

    schema_version: Literal[1]
    slug: Slug
    club_season: ClubSeasonSlug
    season: SeasonLabel
    manager: Manager
    initial_tactic: Tactic
    blocks: tuple[Block, ...]
    competitions: Annotated[tuple[Competition, ...], Field(min_length=1)]
    forced_events: tuple[ForcedEvent, ...] = ()
    board_objectives: Annotated[tuple[BoardObjective, ...], Field(min_length=1)]
    historical_outcome: Annotated[tuple[CompetitionOutcome, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_season(self) -> Self:
        if not season_is_consecutive(self.season):
            raise ValueError(f"season {self.season} must span two consecutive years")
        if not self.club_season.endswith(self.season):
            raise ValueError("club_season must belong to the same season")
        self._check_blocks()
        self._check_competitions()
        self._check_objectives()
        self._check_forced_events()
        return self

    def _check_blocks(self) -> None:
        if not MIN_BLOCKS <= len(self.blocks) <= MAX_BLOCKS:
            raise ValueError(f"a season has {MIN_BLOCKS} or {MAX_BLOCKS} blocks")
        ids = [b.id for b in self.blocks]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate block id")
        for previous, current in pairwise(self.blocks):
            if current.start <= previous.end:
                raise ValueError(
                    f"blocks overlap or are out of order: {previous.id} and {current.id}"
                )

    def _check_competitions(self) -> None:
        ids = [c.id for c in self.competitions]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate competition id")
        leagues = {c.id for c in self.competitions if isinstance(c, LeagueCompetition)}
        for competition in self.competitions:
            if self.club_season not in competition.participants:
                raise ValueError(f"participants of {competition.id} must include the own team")
            baseline = getattr(competition, "goal_baseline", None)
            if isinstance(baseline, GoalBaselineFromLeague) and baseline.from_league not in leagues:
                raise ValueError(
                    f"from_league {baseline.from_league!r} is not a league of the season"
                )

    def _check_objectives(self) -> None:
        ids = [o.id for o in self.board_objectives]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate objective id")
        by_id = {c.id: c for c in self.competitions}
        for objective in self.board_objectives:
            competition = by_id.get(objective.competition)
            if competition is None:
                continue  # unknown references are reported by the integrity checks
            if isinstance(competition, LeagueCompetition):
                limit = len(competition.participants)
                if objective.target_position is not None and objective.target_position > limit:
                    raise ValueError(
                        f"target_position {objective.target_position} exceeds the {limit} teams"
                    )
            elif objective.kind == "finish_top":
                raise ValueError("finish_top only applies to a league")
            if objective.target_stage is not None and (
                isinstance(competition, LeagueCompetition)
                or objective.target_stage not in {s.id for s in competition.stages}
            ):
                raise ValueError(
                    f"target_stage {objective.target_stage!r} is not a stage of {competition.id}"
                )

    def _check_forced_events(self) -> None:
        first, last = self.blocks[0].start, self.blocks[-1].end
        for event in self.forced_events:
            ends = event.date + timedelta(days=event.days)  # first day after the injury
            if not (event.date <= last and ends > first):
                raise ValueError(
                    f"forced event of {event.player_id} ({event.date}, {event.days} days) does "
                    f"not overlap the season blocks {first}..{last}"
                )
