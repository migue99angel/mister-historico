"""Explicit sourced historical slots and qualifying positions, without bracket inference."""

import datetime as dt
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import ClubSeasonSlug, Slug, SourcedModel


class HistoricalBooleanRule(SourcedModel):
    """An explicitly verified historical switch; None remains unknown."""

    nullable_when_pending = ("value",)
    value: bool | None


class KnockoutSlot(SourcedModel):
    """Calendar identity of a historical slot; its future occupants are separate game state."""

    nullable_when_pending = ("date", "venue")
    fixture_id: Slug
    stage_id: Slug
    date: dt.date | None
    home: ClubSeasonSlug
    away: ClubSeasonSlug
    venue: Literal["home", "neutral"] | None
    leg: Literal[1, 2] | None = None

    @model_validator(mode="after")
    def _check_sides(self) -> Self:
        if self.home == self.away:
            raise ValueError("knockout slots require distinct clubs")
        return self


class KnockoutCalendar(SourcedModel):
    """A complete explicit calendar for one competition; a null collection is pending."""

    nullable_when_pending = ("slots",)
    competition: Slug
    slots: tuple[KnockoutSlot, ...] | None

    @model_validator(mode="after")
    def _check_ids(self) -> Self:
        ids = [slot.fixture_id for slot in self.slots or ()]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate knockout fixture id")
        return self


class GroupEntryAssignment(SourcedModel):
    """Historical representative of an explicit group position in a target stage."""

    source_stage_id: Slug
    group_id: Slug
    qualifying_position: Annotated[int, Field(ge=1)]
    target_stage_id: Slug
    historical_representative: ClubSeasonSlug


class GroupEntryAssignments(SourcedModel):
    """All explicitly sourced qualifying positions of one competition."""

    nullable_when_pending = ("entries",)
    competition: Slug
    entries: tuple[GroupEntryAssignment, ...] | None

    @model_validator(mode="after")
    def _check_positions(self) -> Self:
        positions = [
            (e.source_stage_id, e.group_id, e.qualifying_position) for e in self.entries or ()
        ]
        representatives = [
            (e.target_stage_id, e.historical_representative) for e in self.entries or ()
        ]
        if len(set(positions)) != len(positions) or len(set(representatives)) != len(
            representatives
        ):
            raise ValueError("duplicate qualifying position or target representative")
        return self
