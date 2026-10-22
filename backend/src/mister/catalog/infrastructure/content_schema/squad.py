"""Club-season content: `squad.yaml` (full squad) and `aggregate.yaml` (strength only)."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import (
    ClubSeasonSlug,
    PlayerId,
    Rating,
    SeasonLabel,
    Slug,
    SourcedModel,
    season_is_consecutive,
    season_window,
)

MIN_CLUB_SQUAD = 18
MAX_CLUB_SQUAD = 40
MARKET_PREFIX = "_market-"


class Position(StrEnum):
    """Broad position of a player."""

    GK = "GK"
    DF = "DF"
    MF = "MF"
    FW = "FW"


class Subrole(StrEnum):
    """Optional finer role; it must be coherent with the position."""

    CB = "CB"
    LB = "LB"
    RB = "RB"
    DM = "DM"
    CM = "CM"
    AM = "AM"
    WG = "WG"
    ST = "ST"


_SUBROLES_BY_POSITION: dict[Position, frozenset[Subrole]] = {
    Position.GK: frozenset(),
    Position.DF: frozenset({Subrole.CB, Subrole.LB, Subrole.RB}),
    Position.MF: frozenset({Subrole.DM, Subrole.CM, Subrole.AM, Subrole.WG}),
    Position.FW: frozenset({Subrole.WG, Subrole.ST}),
}


class PlayerEntry(SourcedModel):
    """A player in a club-season squad. `sources` back his membership of the squad."""

    nullable_when_pending = ("age",)

    player_id: PlayerId
    display_name: Annotated[str, Field(min_length=1, max_length=80)]
    alias_name: Annotated[str, Field(min_length=1, max_length=80)]
    position: Position
    subrole: Subrole | None = None
    age: Annotated[int, Field(ge=14, le=50)] | None
    rating: Rating
    key: bool
    rating_rationale: Annotated[str, Field(min_length=1)] | None = None
    joined_on: date | None = None
    left_on: date | None = None

    @model_validator(mode="after")
    def _check_player(self) -> Self:
        if self.key and not self.rating_rationale:
            raise ValueError("rating_rationale is required for key players")
        if self.subrole is not None and self.subrole not in _SUBROLES_BY_POSITION[self.position]:
            raise ValueError(f"subrole {self.subrole} is not valid for position {self.position}")
        if self.joined_on and self.left_on and self.left_on < self.joined_on:
            raise ValueError("left_on must not be before joined_on")
        return self


class _ClubSeasonFile(SourcedModel):
    """Fields common to squad and aggregate files."""

    schema_version: Literal[1]
    club_season: ClubSeasonSlug
    club: Slug | None
    season: SeasonLabel

    @property
    def is_market(self) -> bool:
        return self.club_season.startswith(MARKET_PREFIX)

    @model_validator(mode="after")
    def _check_identity(self) -> Self:
        if not season_is_consecutive(self.season):
            raise ValueError(f"season {self.season} must span two consecutive years")
        if self.is_market:
            if self.club is not None:
                raise ValueError("a market squad has no club")
            expected = f"{MARKET_PREFIX}{self.season}"
        else:
            if self.club is None:
                raise ValueError("club is required")
            expected = f"{self.club}-{self.season}"
        if self.club_season != expected:
            raise ValueError(f"club_season must be {expected!r}")
        return self


class SquadFile(_ClubSeasonFile):
    """A full squad. Its `sources` and `verify` cover the real league goals."""

    real_goals_for: Annotated[int, Field(ge=0)] | None
    real_goals_against: Annotated[int, Field(ge=0)] | None
    players: Annotated[tuple[PlayerEntry, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_squad(self) -> Self:
        if not self.is_market:
            self._check_league_goals()
            if not MIN_CLUB_SQUAD <= len(self.players) <= MAX_CLUB_SQUAD:
                raise ValueError(
                    f"a club squad needs between {MIN_CLUB_SQUAD} and {MAX_CLUB_SQUAD} players"
                )
            if not any(p.position is Position.GK for p in self.players):
                raise ValueError("a club squad needs at least one goalkeeper")
        ids = [p.player_id for p in self.players]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate player_id: {', '.join(duplicates)}")
        self._check_dates_in_window()
        return self

    def _check_league_goals(self) -> None:
        if self.verify != "ok":
            return
        for name in ("real_goals_for", "real_goals_against"):
            if getattr(self, name) is None:
                raise ValueError(f"{name} is null: use verify: pending")

    def _check_dates_in_window(self) -> None:
        first, last = season_window(self.season)
        for entry in self.players:
            for value in (entry.joined_on, entry.left_on):
                if value is not None and not first <= value <= last:
                    raise ValueError(
                        f"{entry.player_id}: {value} is outside the season window {first}..{last}"
                    )


class AggregateFile(_ClubSeasonFile):
    """A rival without a squad (outside the top flight): only an aggregate strength."""

    attack: Rating
    defense: Rating
    rating_rationale: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def _no_market(self) -> Self:
        if self.is_market:
            raise ValueError("a market cannot be an aggregate")
        return self
