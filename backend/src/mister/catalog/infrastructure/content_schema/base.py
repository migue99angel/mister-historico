"""Building blocks shared by every content model: strict base, identifiers and sources."""

from typing import Annotated, ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
CLUB_SEASON_PATTERN = r"^_?[a-z0-9]+(-[a-z0-9]+)*-\d{4}-\d{2}$"
SEASON_PATTERN = r"^\d{4}-\d{2}$"

Slug = Annotated[str, StringConstraints(pattern=SLUG_PATTERN, max_length=64)]
"""Lowercase kebab-case identifier (clubs, competitions, blocks, dilemmas...)."""

PlayerId = Annotated[str, StringConstraints(pattern=SLUG_PATTERN, max_length=64)]
"""Stable player identifier; the same person keeps the same id across seasons."""

ClubSeasonSlug = Annotated[str, StringConstraints(pattern=CLUB_SEASON_PATTERN, max_length=80)]
"""`<club>-<yyyy>-<yy>`, e.g. `test-fc-2000-01`. A leading underscore marks a market squad."""

SeasonLabel = Annotated[str, StringConstraints(pattern=SEASON_PATTERN)]
"""Season as `yyyy-yy`, e.g. `2000-01`."""

Verify = Literal["ok", "pending"]
"""`ok`: the datum was checked against its sources. `pending`: missing or unconfirmed."""

Rating = Annotated[int, Field(ge=1, le=99)]
"""Player or team rating on the project rubric (1-99)."""

Sources = Annotated[tuple[HttpUrl, ...], Field(description="URLs backing the datum.")]


class ContentModel(BaseModel):
    """Immutable model that rejects unknown fields: typos must fail loudly."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class SourcedModel(ContentModel):
    """A historical datum: it cites its sources and states whether it was verified.

    Golden rule: never invent. A datum that cannot be found is left as `null` with
    `verify: pending`; release validation then fails, which is the intended behaviour.
    """

    # Fields that may be `null` only while the datum is pending.
    nullable_when_pending: ClassVar[tuple[str, ...]] = ()

    sources: Sources
    verify: Verify

    @model_validator(mode="after")
    def _check_sources_and_pending(self) -> Self:
        if self.verify == "ok" and not self.sources:
            raise ValueError("a verified datum (verify: ok) needs at least one source")
        if self.verify == "ok":
            empty = [name for name in self.nullable_when_pending if getattr(self, name) is None]
            if empty:
                raise ValueError(f"{', '.join(empty)} is null: use verify: pending")
        return self
