"""Club-season content: `squad.yaml` (full squad) and `aggregate.yaml` (strength only)."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from mister.catalog.infrastructure.content_schema.base import (
    ClubSeasonSlug,
    NonBlank,
    PlayerId,
    Rating,
    SeasonLabel,
    Slug,
    SourcedModel,
    enum_from_text,
    season_is_consecutive,
    season_window,
)
from mister.catalog.infrastructure.content_schema.effects import Tactic
from mister.catalog.infrastructure.content_schema.season_stats import (
    ClubData,
    RatingOverride,
    SeasonStats,
)

MARKET_PREFIX = "_market-"
MIN_AGE = 15
MAX_AGE = 50
DEFAULT_TACTIC = Tactic(style="balanced", system="4-4-2")


class Position(StrEnum):
    """Broad position of a player. It decides the engine line, never `subrole`."""

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
    """A player in a club-season squad. `sources` back his membership of the squad.

    `position`, `age` and `rating` may be `null` only while the player is `verify: pending`.
    The rating is computed from `season_stats` and the club's `club_data` (ADR-006) and checked
    against the formula by the tree validation. `rating_override` replaces it, with a
    `rationale` and `sources`; `rating_rationale` only makes sense next to an override.
    Statistics are required in a club squad and absent in a market squad (it has no club).
    """

    nullable_when_pending = ("position", "age", "rating")

    player_id: PlayerId
    display_name: NonBlank
    alias_name: NonBlank
    position: Annotated[Position, enum_from_text(Position)] | None
    subrole: Annotated[Subrole, enum_from_text(Subrole)] | None = None
    age: Annotated[int, Field(ge=MIN_AGE, le=MAX_AGE)] | None
    rating: Rating | None
    key: bool
    season_stats: SeasonStats | None = None
    rating_override: RatingOverride | None = None
    rating_rationale: NonBlank | None = None
    joined_on: date | None = None
    left_on: date | None = None

    @model_validator(mode="after")
    def _check_player(self) -> Self:
        if self.rating_rationale and self.rating_override is None:
            raise ValueError("rating_rationale is only for a rating_override")
        if self.position is not None:
            allowed = _SUBROLES_BY_POSITION[self.position]
            if self.subrole is not None and self.subrole not in allowed:
                raise ValueError(
                    f"subrole {self.subrole} is not valid for position {self.position}"
                )
            stats = self.season_stats
            if (
                stats is not None
                and stats.clean_sheets_all is not None
                and self.position is not Position.GK
            ):
                raise ValueError("clean_sheets_all is only for goalkeepers")
        if self.joined_on and self.left_on and self.left_on < self.joined_on:
            raise ValueError("left_on must not be before joined_on")
        return self


class RealLeague(SourcedModel):
    """The league the club really played that season, with its real goals (P6).

    `competition_label` is free text (e.g. the name of the real league). It is compared with
    the standings only when it equals the name of a league of the playable season.
    """

    nullable_when_pending = ("played", "goals_for", "goals_against")

    competition_label: NonBlank
    played: Annotated[int, Field(ge=0)] | None
    goals_for: Annotated[int, Field(ge=0)] | None
    goals_against: Annotated[int, Field(ge=0)] | None


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
    """A full squad. Its `sources` and `verify` cover the squad as a whole."""

    real_league: RealLeague | None
    club_data: ClubData | None = None
    default_tactic: Tactic = DEFAULT_TACTIC
    players: Annotated[tuple[PlayerEntry, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _check_squad(self) -> Self:
        if not self.is_market and self.real_league is None:
            raise ValueError("real_league is required for a club squad")
        if self.is_market and self.club_data is not None:
            raise ValueError("a market squad has no club_data")
        if not self.is_market and self.club_data is None:
            raise ValueError("club_data is required for a club squad")
        ids = [p.player_id for p in self.players]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate player_id: {', '.join(duplicates)}")
        first, last = season_window(self.season)
        for index, entry in enumerate(self.players):
            if self.is_market and entry.season_stats is not None:
                raise ValueError(f"players.{index}.season_stats: a market squad has no club")
            if not self.is_market and entry.season_stats is None:
                raise ValueError(f"players.{index}.season_stats is required in a club squad")
            for value in (entry.joined_on, entry.left_on):
                if value is not None and not first <= value <= last:
                    raise ValueError(
                        f"{entry.player_id}: {value} is outside the season window {first}..{last}"
                    )
        return self


class AggregateFile(_ClubSeasonFile):
    """A rival without a squad (outside the top flight): only an aggregate strength.

    `attack` and `defense` are indices in rubric rating points (1-99), the "A" and the "C" of
    ADR-004. A higher `defense` means a *better* defence (it concedes fewer goals).
    """

    nullable_when_pending = ("attack", "defense")

    attack: Rating | None
    defense: Rating | None
    rating_rationale: NonBlank | None = None

    @model_validator(mode="after")
    def _check_aggregate(self) -> Self:
        if self.is_market:
            raise ValueError("a market cannot be an aggregate")
        if self.verify == "ok" and not self.rating_rationale:
            raise ValueError("rating_rationale is required for a verified aggregate")
        return self
