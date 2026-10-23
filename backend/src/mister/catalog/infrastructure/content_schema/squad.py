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
    `rationale` and `sources`. A player of a market squad has no club in the game, so he carries
    the `club_data` of his own real club; in a club squad the squad's `club_data` applies.
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
    season_stats: SeasonStats
    club_data: ClubData | None = None
    rating_override: RatingOverride | None = None
    joined_on: date | None = None
    left_on: date | None = None

    @model_validator(mode="after")
    def _check_player(self) -> Self:
        if self.position is not None:
            allowed = _SUBROLES_BY_POSITION[self.position]
            if self.subrole is not None and self.subrole not in allowed:
                raise ValueError(
                    f"subrole {self.subrole} is not valid for position {self.position}"
                )
            if self.season_stats.clean_sheets_all is not None and self.position is not Position.GK:
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
    club_data: ClubData | None
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
            self._check_club_data_of(index, entry)
            for value in (entry.joined_on, entry.left_on):
                if value is not None and not first <= value <= last:
                    raise ValueError(
                        f"{entry.player_id}: {value} is outside the season window {first}..{last}"
                    )
        return self

    def _check_club_data_of(self, index: int, entry: PlayerEntry) -> None:
        """Where the player's club data lives, and the statistics against it (rubric 2.1)."""
        where = f"players.{index}"
        if not self.is_market:
            if entry.club_data is not None:
                raise ValueError(f"{where}.club_data is only for a market player")
            club = self.club_data
        else:
            club = entry.club_data
            if club is None:
                raise ValueError(f"{where}.club_data is required for a market player")
            if club.club_name is None:
                raise ValueError(f"{where}.club_data.club_name is required for a market player")
        if club is not None:
            _check_stats_against_club(where, entry.season_stats, club)


def _check_stats_against_club(where: str, stats: SeasonStats, club: ClubData) -> None:
    """A player cannot have played more matches than his club did (or than he was registered)."""
    all_matches = club.club_matches_all
    available = stats.available_matches_all
    if available is not None and all_matches is not None and available > all_matches:
        raise ValueError(
            f"{where}.season_stats: available_matches_all cannot exceed club_matches_all"
        )
    playable = available if available is not None else all_matches
    appearances = stats.appearances_all
    if appearances is not None and playable is not None and appearances > playable:
        raise ValueError(
            f"{where}.season_stats: appearances_all cannot exceed the matches the player could play"
            f" ({playable})"
        )
    league = club.club_matches_league
    if (
        stats.appearances_league is not None
        and league is not None
        and stats.appearances_league > league
    ):
        raise ValueError(
            f"{where}.season_stats: appearances_league cannot exceed club_matches_league"
        )


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
