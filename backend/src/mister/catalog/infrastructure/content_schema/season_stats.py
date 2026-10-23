"""Inputs of the rating formula (ADR-006, `docs/content/rating-rubric.md` sections 2 and 3).

A player carries his `season_stats`; the club-season carries its `club_data` (match counts and
level). The rating itself is computed from them by `mister.catalog.domain.ratings`; it is
stored in the player and checked against the formula by the tree validation.
"""

from typing import Annotated, Literal, Self

from pydantic import Field, HttpUrl, model_validator

from mister.catalog.infrastructure.content_schema.base import (
    ContentModel,
    NonBlank,
    Rating,
    SourcedModel,
    Sources,
)

Count = Annotated[int, Field(ge=0)]
"""A count of minutes, matches, goals... (never negative)."""

MatchCount = Annotated[int, Field(ge=1)]
"""A number of matches the club played (at least one)."""

LevelTierValue = Literal["A", "B", "C", "D"]
"""Level of the club in the season (rubric section 3)."""

MAX_MINUTES_PER_APPEARANCE = 120
"""A full match with extra time."""

MAX_SCORING_PER_APPEARANCE = 4
"""Sanity ceiling for goals or assists per appearance; anything above is a copy error."""

AwardTierValue = Literal["W", "L"]
"""`W`: world-level individual award. `L`: official award of the club's league."""


class Award(ContentModel):
    """An individual award of the season, with the source that confirms it."""

    name: NonBlank
    tier: AwardTierValue
    source: HttpUrl


class SeasonStats(SourcedModel):
    """Public statistics of one player in one season (rubric section 2.1).

    `null` means "not found in the sources". The statistics the formula cannot do without may
    be `null` only with `verify: pending`; the optional ones (starts, clean sheets,
    all-competitions figures) may be `null` in a verified datum, and the formula has a
    documented fallback for each (rubric section 5). Position and age live in the player.

    `assists_all` is informational: the formula does not use it (rubric section 4.3), because
    no permitted source publishes reliable assists for 2003-2014.
    """

    nullable_when_pending = ("minutes_league", "appearances_league", "goals_all", "caps", "awards")

    minutes_league: Count | None
    starts_league: Count | None = None
    appearances_league: Count | None
    minutes_all: Count | None = None
    starts_all: Count | None = None
    appearances_all: Count | None = None
    goals_all: Count | None
    assists_all: Count | None = None
    clean_sheets_all: Count | None = None
    clean_sheets_league: Count | None = None
    caps: Count | None
    awards: tuple[Award, ...] | None
    available_matches_all: MatchCount | None = None

    @model_validator(mode="after")
    def _check_coherence(self) -> Self:
        for scope in ("league", "all"):
            starts = getattr(self, f"starts_{scope}")
            appearances = getattr(self, f"appearances_{scope}")
            if starts is not None and appearances is not None and starts > appearances:
                raise ValueError(f"starts_{scope} cannot exceed appearances_{scope}")
        for name in ("minutes", "starts", "appearances"):
            in_league = getattr(self, f"{name}_league")
            in_all = getattr(self, f"{name}_all")
            if in_league is not None and in_all is not None and in_league > in_all:
                raise ValueError(f"{name}_league cannot exceed {name}_all")
        for scope in ("league", "all"):
            minutes = getattr(self, f"minutes_{scope}")
            appearances = getattr(self, f"appearances_{scope}")
            if (
                minutes is not None
                and appearances is not None
                and minutes > MAX_MINUTES_PER_APPEARANCE * appearances
            ):
                raise ValueError(
                    f"minutes_{scope} cannot exceed {MAX_MINUTES_PER_APPEARANCE} per appearance"
                )
        self._check_counts_per_appearance()
        self._check_league_clean_sheets()
        return self

    def _check_league_clean_sheets(self) -> None:
        league = self.clean_sheets_league
        if league is None:
            return
        if self.appearances_league is not None and league > self.appearances_league:
            raise ValueError("clean_sheets_league cannot exceed appearances_league")
        if self.clean_sheets_all is not None and league > self.clean_sheets_all:
            raise ValueError("clean_sheets_league cannot exceed clean_sheets_all")

    def _check_counts_per_appearance(self) -> None:
        appearances = self.appearances_all
        if appearances is None:
            return
        for name in ("goals_all", "assists_all"):
            value = getattr(self, name)
            if value is not None and value > MAX_SCORING_PER_APPEARANCE * appearances:
                raise ValueError(
                    f"{name} cannot exceed {MAX_SCORING_PER_APPEARANCE} per appearance"
                )
        if self.clean_sheets_all is not None and self.clean_sheets_all > appearances:
            raise ValueError("clean_sheets_all cannot exceed appearances_all")


class RatingOverride(ContentModel):
    """A justified manual correction of the formula's rating (rubric section 7).

    Its distance from the formula is limited, which needs the formula and is therefore
    checked with the whole tree (`rating_checks`).
    """

    value: Rating
    rationale: NonBlank
    sources: Annotated[Sources, Field(min_length=1)]


class ClubData(SourcedModel):
    """What the formula needs to know of the club in the season (rubric sections 2.1 and 3).

    `level_tier_basis` states the criterion (final position, best European round) so a reviewer
    can check the tier. `club_name` names the real club of a market player, whose club is not
    one of the game; it is not used in a club squad.
    """

    nullable_when_pending = ("club_matches_all", "club_matches_league", "level_tier")

    club_matches_all: MatchCount | None
    club_matches_league: MatchCount | None
    level_tier: LevelTierValue | None
    level_tier_basis: NonBlank | None = None
    club_name: NonBlank | None = None

    @model_validator(mode="after")
    def _check_club_data(self) -> Self:
        all_matches, league_matches = self.club_matches_all, self.club_matches_league
        if all_matches is not None and league_matches is not None and league_matches > all_matches:
            raise ValueError("club_matches_league cannot exceed club_matches_all")
        if self.verify == "ok" and self.level_tier_basis is None:
            raise ValueError("level_tier_basis is required for a verified level_tier")
        return self
