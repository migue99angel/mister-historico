"""`content/clubs/<club>.yaml`: the stable identity of a club across seasons."""

from typing import Annotated, Literal

from pydantic import Field

from mister.catalog.infrastructure.content_schema.base import ContentModel, Slug

HexColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class ClubColors(ContentModel):
    """Primary and secondary colors, used to draw a generic crest (never a real one)."""

    primary: HexColor
    secondary: HexColor


class ClubFile(ContentModel):
    """A club. The file name must be `<club_id>.yaml`."""

    schema_version: Literal[1]
    club_id: Slug
    name: Annotated[str, Field(min_length=1, max_length=60)]
    short_name: Annotated[str, Field(min_length=2, max_length=8)]
    colors: ClubColors
