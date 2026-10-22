"""`content/seasons/<slug>/dilemmas.yaml`: the decisions offered to the player."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import (
    ContentModel,
    NonBlank,
    Slug,
    SourcedModel,
)
from mister.catalog.infrastructure.content_schema.effects import Effect

MIN_OPTIONS = 2
MAX_OPTIONS = 4


class Option(ContentModel):
    """One possible answer to a dilemma, with its effects."""

    id: Slug
    label: NonBlank
    effects: tuple[Effect, ...] = ()


class HistoricalOption(SourcedModel):
    """Which option the real manager took, with the sources that prove it."""

    option: Slug


class Dilemma(ContentModel):
    """A dilemma of a block. Exactly one option is the historical one."""

    id: Slug
    block: Slug
    title: NonBlank
    prompt: NonBlank
    options: Annotated[tuple[Option, ...], Field(min_length=MIN_OPTIONS, max_length=MAX_OPTIONS)]
    historical_option: HistoricalOption

    @model_validator(mode="after")
    def _check_options(self) -> Self:
        ids = [o.id for o in self.options]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate option id")
        if self.historical_option.option not in ids:
            raise ValueError("historical_option must be one of the options")
        return self


class DilemmasFile(ContentModel):
    """All dilemmas of the season."""

    schema_version: Literal[1]
    dilemmas: Annotated[tuple[Dilemma, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_unique_ids(self) -> Self:
        ids = [d.id for d in self.dilemmas]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate dilemma id")
        return self
