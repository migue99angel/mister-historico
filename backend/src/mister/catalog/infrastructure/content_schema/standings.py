"""`content/seasons/<slug>/standings.yaml`: real tables at cutoffs and real knockout ties (P2)."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import (
    ClubSeasonSlug,
    ContentModel,
    Slug,
    SourcedModel,
)
from mister.catalog.infrastructure.content_schema.competitions import (
    GroupEntryAssignments,
    KnockoutCalendar,
)
from mister.catalog.infrastructure.content_schema.evidence import HeadToHeadEvidence

Count = Annotated[int, Field(ge=0)]


class StandingRow(ContentModel):
    """One row of a real league table."""

    club_season: ClubSeasonSlug
    position: Annotated[int, Field(ge=1)]
    played: Count
    won: Count
    drawn: Count
    lost: Count
    goals_for: Count
    goals_against: Count
    points: Count

    @model_validator(mode="after")
    def _check_played(self) -> Self:
        if self.played != self.won + self.drawn + self.lost:
            raise ValueError(f"{self.club_season}: played must equal won + drawn + lost")
        return self


class StandingsCutoff(SourcedModel):
    """The real league table on the cutoff date of a block."""

    block: Slug
    competition: Slug
    stage: Slug | None = None
    group: Slug | None = None
    date: date
    table: Annotated[tuple[StandingRow, ...], Field(min_length=2)]

    @model_validator(mode="after")
    def _check_table(self) -> Self:
        if (self.stage is None) != (self.group is None):
            raise ValueError("stage and group go together (group tables) or both stay empty")
        if [r.position for r in self.table] != list(range(1, len(self.table) + 1)):
            raise ValueError("positions must be 1..n in table order")
        points = [r.points for r in self.table]
        if points != sorted(points, reverse=True):
            raise ValueError("table must be ordered by points, highest first")
        clubs = [r.club_season for r in self.table]
        if len(set(clubs)) != len(clubs):
            raise ValueError("a club appears twice in the table")
        return self


class RealTie(SourcedModel):
    """A real knockout tie, including those that do not involve the own team (P2)."""

    nullable_when_pending = ("winner",)

    competition: Slug
    stage: Slug
    clubs: Annotated[tuple[ClubSeasonSlug, ClubSeasonSlug], Field()]
    winner: ClubSeasonSlug | None
    aggregate: Annotated[str, Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def _check_winner(self) -> Self:
        if self.clubs[0] == self.clubs[1]:
            raise ValueError("a real tie needs distinct clubs")
        if self.winner is not None and self.winner not in self.clubs:
            raise ValueError("winner must be one of the clubs of the tie")
        return self


class StandingsFile(ContentModel):
    """Real tables at each block cutoff and the real bracket of the knockout competitions."""

    schema_version: Literal[1]
    cutoffs: tuple[StandingsCutoff, ...]
    ties: tuple[RealTie, ...] = ()
    head_to_head: tuple[HeadToHeadEvidence, ...] | None = None
    knockout_calendar: tuple[KnockoutCalendar, ...] | None = None
    group_entry_assignments: tuple[GroupEntryAssignments, ...] | None = None

    @model_validator(mode="after")
    def _check_unique_cutoffs(self) -> Self:
        keys = [(c.block, c.competition) for c in self.cutoffs]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate cutoff for a block and competition")
        return self
