"""Sourced regulation-time evidence, separate from the managed team's fixture calendar."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import ClubSeasonSlug, Slug, SourcedModel
from mister.catalog.infrastructure.content_schema.fixtures import Goals


class HeadToHeadFixture(SourcedModel):
    """One dated home/away match in a declared complete calendar."""

    nullable_when_pending = ("venue",)

    fixture_id: Slug
    date: date
    home: ClubSeasonSlug
    away: ClubSeasonSlug
    venue: Literal["home", "neutral"] | None = None

    @model_validator(mode="after")
    def _check_sides(self) -> Self:
        if self.home == self.away:
            raise ValueError("a fixture needs distinct home and away clubs")
        return self


class HeadToHeadResult(SourcedModel):
    """A regulation-time score, home first, identified by its calendar fixture."""

    nullable_when_pending = ("score",)

    fixture_id: Slug
    score: tuple[Goals, Goals] | None


class HeadToHeadEvidence(SourcedModel):
    """Editorial declaration of all matches between covered clubs through an inclusive date."""

    competition: Slug
    complete_through: date
    covered_clubs: Annotated[tuple[ClubSeasonSlug, ...], Field(min_length=2)]
    schedule: tuple[HeadToHeadFixture, ...]
    results: tuple[HeadToHeadResult, ...]
    stage: Slug | None = None
    group: Slug | None = None

    @model_validator(mode="after")
    def _check_calendar(self) -> Self:
        if (self.stage is None) != (self.group is None):
            raise ValueError("stage and group must both be present or both absent")
        if len(set(self.covered_clubs)) != len(self.covered_clubs):
            raise ValueError("covered_clubs must be distinct")
        fixtures = {f.fixture_id for f in self.schedule}
        results = {r.fixture_id for r in self.results}
        if len(fixtures) != len(self.schedule) or len(results) != len(self.results):
            raise ValueError("duplicate fixture id in schedule or results")
        if fixtures != results:
            raise ValueError("schedule and results must identify exactly the same fixtures")
        occupied: set[tuple[date, str]] = set()
        for fixture in self.schedule:
            if fixture.date > self.complete_through:
                raise ValueError("schedule dates must not exceed complete_through")
            if fixture.home not in self.covered_clubs or fixture.away not in self.covered_clubs:
                raise ValueError("schedule participants must belong to covered_clubs")
            for club in (fixture.home, fixture.away):
                key = (fixture.date, club)
                if key in occupied:
                    raise ValueError("a covered club cannot play twice on the same date")
                occupied.add(key)
        return self
