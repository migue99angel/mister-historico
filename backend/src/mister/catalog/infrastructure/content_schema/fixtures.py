"""`content/seasons/<slug>/fixtures.yaml`: the real matches of the own team."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import (
    ClubSeasonSlug,
    ContentModel,
    Slug,
    SourcedModel,
)

Venue = Literal["home", "away", "neutral"]
Goals = Annotated[int, Field(ge=0, le=30)]


class RealResult(ContentModel):
    """Real score from the own team's point of view (after extra time, before penalties)."""

    goals_for: Goals
    goals_against: Goals
    extra_time: bool = False
    penalties_for: Goals | None = None
    penalties_against: Goals | None = None

    @model_validator(mode="after")
    def _check_penalties(self) -> Self:
        if (self.penalties_for is None) != (self.penalties_against is None):
            raise ValueError("penalties_for and penalties_against go together")
        if self.penalties_for is not None:
            if self.goals_for != self.goals_against:
                raise ValueError("penalties are only taken when the score is level")
            if self.penalties_for == self.penalties_against:
                raise ValueError("penalties cannot end level")
        return self


class Fixture(SourcedModel):
    """A real match. League matches carry `round`; knockout matches carry `stage` (and `leg`)."""

    nullable_when_pending = ("result",)

    id: Slug
    date: date
    competition: Slug
    round: Annotated[int, Field(ge=1)] | None = None
    stage: Slug | None = None
    leg: Literal[1, 2] | None = None
    group: Slug | None = None
    key: bool = False
    opponent: ClubSeasonSlug
    venue: Venue
    result: RealResult | None

    @model_validator(mode="after")
    def _check_kind(self) -> Self:
        if self.round is None and self.stage is None:
            raise ValueError("a fixture needs a round (league), a stage (knockout) or both (group)")
        if self.round is not None and self.stage is not None and self.group is None:
            raise ValueError("a fixture with a round and a stage needs a group (group stage)")
        if self.group is not None and self.stage is None:
            raise ValueError("a group fixture needs its stage")
        if self.leg is not None and self.stage is None:
            raise ValueError("leg only applies to knockout fixtures")
        return self


class FixturesFile(ContentModel):
    """All real matches of the own team in the season."""

    schema_version: Literal[1]
    fixtures: Annotated[tuple[Fixture, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_unique_ids(self) -> Self:
        ids = [f.id for f in self.fixtures]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate fixture id")
        dates = [f.date for f in self.fixtures]
        repeated = sorted({d for d in dates if dates.count(d) > 1})
        if repeated:
            raise ValueError(f"two fixtures on the same date: {', '.join(map(str, repeated))}")
        return self
