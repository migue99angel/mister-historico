"""`content/seasons/<slug>/texts.yaml`: narrative texts with a review status."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import ContentModel

TextId = Annotated[str, Field(pattern=r"^[a-z0-9]+([.-][a-z0-9]+)*$", max_length=80)]
TextKind = Literal["presentation", "event", "verdict"]
TextStatus = Literal["draft", "reviewed"]


class Text(ContentModel):
    """A user-facing text (Spanish). Only `reviewed` texts ship in release mode."""

    id: TextId
    kind: TextKind
    body: Annotated[str, Field(min_length=1)]
    status: TextStatus
    reviewed_by: Annotated[str, Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def _check_review(self) -> Self:
        if self.status == "reviewed" and not self.reviewed_by:
            raise ValueError("reviewed_by is required when status is reviewed")
        return self


class TextsFile(ContentModel):
    """All texts of the season."""

    schema_version: Literal[1]
    texts: Annotated[tuple[Text, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_unique_ids(self) -> Self:
        ids = [t.id for t in self.texts]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate text id")
        return self
