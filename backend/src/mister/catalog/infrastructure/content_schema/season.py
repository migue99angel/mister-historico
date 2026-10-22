"""`content/seasons/<slug>/season.yaml`: blocks, competitions, objectives and real outcome."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import (
    ClubSeasonSlug,
    ContentModel,
    SeasonLabel,
    Slug,
    SourcedModel,
    season_is_consecutive,
)

MIN_BLOCKS = 5
MAX_BLOCKS = 6


class Block(ContentModel):
    """A stretch of the season. Blocks must not overlap; each ends on a standings cutoff."""

    id: Slug
    label: Annotated[str, Field(min_length=1, max_length=60)]
    start: date
    end: date

    @model_validator(mode="after")
    def _check_range(self) -> Self:
        if self.end < self.start:
            raise ValueError("end must not be before start")
        return self


class Manager(SourcedModel):
    """The real manager of the season."""

    display_name: Annotated[str, Field(min_length=1, max_length=80)]
    alias_name: Annotated[str, Field(min_length=1, max_length=80)]


class Tiebreaker(StrEnum):
    """Tiebreak criteria for league tables, applied in the listed order."""

    HEAD_TO_HEAD_POINTS = "head_to_head_points"
    HEAD_TO_HEAD_GOAL_DIFFERENCE = "head_to_head_goal_difference"
    HEAD_TO_HEAD_GOALS_FOR = "head_to_head_goals_for"
    HEAD_TO_HEAD_AWAY_GOALS = "head_to_head_away_goals"
    GOAL_DIFFERENCE = "goal_difference"
    GOALS_FOR = "goals_for"
    WINS = "wins"


class KnockoutStage(ContentModel):
    """A knockout round. Format and rules are set per competition and per season."""

    id: Slug
    name: Annotated[str, Field(min_length=1, max_length=60)]
    legs: Literal[1, 2]
    away_goals_rule: bool
    extra_time: bool
    penalties: bool

    @model_validator(mode="after")
    def _check_away_goals(self) -> Self:
        if self.away_goals_rule and self.legs != 2:
            raise ValueError("away_goals_rule only applies to two-legged stages")
        return self


class Group(ContentModel):
    """A group of a group stage."""

    id: Slug
    participants: Annotated[tuple[ClubSeasonSlug, ...], Field(min_length=2)]


class GroupStage(ContentModel):
    """Group stage of a continental competition."""

    groups: Annotated[tuple[Group, ...], Field(min_length=1)]
    legs: Literal[1, 2]
    points_per_win: Annotated[int, Field(ge=2, le=3)]
    tiebreakers: Annotated[tuple[Tiebreaker, ...], Field(min_length=1)]
    advance_per_group: Annotated[int, Field(ge=1)]


class _CompetitionBase(ContentModel):
    id: Slug
    name: Annotated[str, Field(min_length=1, max_length=60)]
    participants: Annotated[tuple[ClubSeasonSlug, ...], Field(min_length=2)]

    @model_validator(mode="after")
    def _check_participants(self) -> Self:
        if len(set(self.participants)) != len(self.participants):
            raise ValueError("duplicate participants")
        return self


class LeagueCompetition(_CompetitionBase):
    """A league: single or double round robin, with configurable points and tiebreakers."""

    kind: Literal["league"]
    rounds: Literal[1, 2]
    points_per_win: Annotated[int, Field(ge=2, le=3)]
    points_per_draw: Annotated[int, Field(ge=0, le=1)]
    tiebreakers: Annotated[tuple[Tiebreaker, ...], Field(min_length=1)]


class _KnockoutBase(_CompetitionBase):
    stages: Annotated[tuple[KnockoutStage, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_stages(self) -> Self:
        ids = [s.id for s in self.stages]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate stage id")
        return self


class CupCompetition(_KnockoutBase):
    """A domestic cup."""

    kind: Literal["cup"]


class SuperCupCompetition(_KnockoutBase):
    """A super cup."""

    kind: Literal["super_cup"]


class ContinentalCupCompetition(_KnockoutBase):
    """A continental cup, with an optional group stage before the knockout rounds."""

    kind: Literal["continental_cup"]
    group_stage: GroupStage | None = None

    @model_validator(mode="after")
    def _check_groups(self) -> Self:
        if self.group_stage is None:
            return self
        for group in self.group_stage.groups:
            unknown = set(group.participants) - set(self.participants)
            if unknown:
                raise ValueError(f"group {group.id} has non-participants: {sorted(unknown)}")
        return self


Competition = Annotated[
    LeagueCompetition | CupCompetition | SuperCupCompetition | ContinentalCupCompetition,
    Field(discriminator="kind"),
]


class BoardObjective(ContentModel):
    """What the board expects in a competition. Editorial, not a historical datum."""

    competition: Slug
    kind: Literal["win", "finish_top", "reach_stage"]
    target_position: Annotated[int, Field(ge=1)] | None = None
    target_stage: Slug | None = None
    text: Annotated[str, Field(min_length=1)]

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
    # Stage id where the club was eliminated (knockout competitions).
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
    blocks: tuple[Block, ...]
    competitions: Annotated[tuple[Competition, ...], Field(min_length=1)]
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
        return self

    def _check_blocks(self) -> None:
        if not MIN_BLOCKS <= len(self.blocks) <= MAX_BLOCKS:
            raise ValueError(f"a season has {MIN_BLOCKS} or {MAX_BLOCKS} blocks")
        ids = [b.id for b in self.blocks]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate block id")
        for previous, current in zip(self.blocks, self.blocks[1:], strict=False):
            if current.start <= previous.end:
                raise ValueError(
                    f"blocks overlap or are out of order: {previous.id} and {current.id}"
                )

    def _check_competitions(self) -> None:
        ids = [c.id for c in self.competitions]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate competition id")
        for competition in self.competitions:
            if self.club_season not in competition.participants:
                raise ValueError(f"participants of {competition.id} must include the own team")

    def _check_objectives(self) -> None:
        by_id = {c.id: c for c in self.competitions}
        for objective in self.board_objectives:
            competition = by_id.get(objective.competition)
            if competition is None:
                continue  # unknown references are reported by the integrity checks
            if objective.target_stage is not None and (
                isinstance(competition, LeagueCompetition)
                or objective.target_stage not in {s.id for s in competition.stages}
            ):
                raise ValueError(
                    f"target_stage {objective.target_stage!r} is not a stage of {competition.id}"
                )
