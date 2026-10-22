"""The rating formula: a player's 1-99 rating computed from the statistics of one season.

This is a pure implementation of section 4 of `docs/content/rating-rubric.md` (ADR-006); the
rubric is the normative specification and this module follows it step by step. Nothing here
reads files, dates or randomness: the same statistics always give the same rating.

Arithmetic uses `fractions.Fraction`, so there is no floating-point noise. The rubric asks for
"exact decimals, or `bruta` rounded to 6 decimals, then half up": `round_raw` does the latter
on exact values.

Missing data (rubric section 5) never produces an invented value: when a required statistic is
`None`, the result has `rating=None` and lists what is missing.
"""

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from math import floor

from mister.shared_kernel.errors import InvalidValueError

MIN_RATING = 1
MAX_RATING = 99
MAX_OVERRIDE_GAP_WITH_RATIONALE = 6
MAX_OVERRIDE_GAP = 12
MIN_SOURCES_FOR_LARGE_GAP = 2

_FLOOR = Fraction(46)
_W_IMPORTANCE = Fraction(22)
_W_PRODUCTION = Fraction(14)
_W_SELECTION = Fraction(6)
_W_AWARDS = Fraction(7)

_MINUTES_WEIGHT = Fraction("0.70")
_STARTS_WEIGHT = Fraction("0.30")
_ASSIST_WEIGHT = Fraction("0.5")
_NO_ASSISTS_DISCOUNT = Fraction("0.80")
_GK_CLEAN_SHEET_CAP = Fraction("0.55")
_GK_NEUTRAL_PRODUCTION = Fraction("0.35")
_CAPS_SATURATION = 8
_WORLD_AWARD = Fraction("0.60")
_LEAGUE_AWARD = Fraction("0.35")
_FULL_MATCH_MINUTES = 90
_DECIMALS = 10**6
_HALF = Fraction(1, 2)
_ONE = Fraction(1)


class Position(StrEnum):
    """The position the player spent most minutes in. The formula only uses this one."""

    GK = "GK"
    DF = "DF"
    MF = "MF"
    FW = "FW"


class LevelTier(StrEnum):
    """Level of the club in the season (rubric section 3)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class AwardTier(StrEnum):
    """`W`: world-level individual award; `L`: official award of the club's league."""

    W = "W"
    L = "L"


class BasisKind(StrEnum):
    """Which statistics fed the importance: all official competitions, or the league only."""

    ALL = "all"
    LEAGUE = "league"


_GOALS_PER_MATCH_CAP: dict[Position, Fraction] = {
    Position.FW: Fraction("0.80"),
    Position.MF: Fraction("0.45"),
    Position.DF: Fraction("0.20"),
}
_LEVEL_POINTS: dict[LevelTier, int] = {
    LevelTier.A: 6,
    LevelTier.B: 3,
    LevelTier.C: 0,
    LevelTier.D: -3,
}


@dataclass(frozen=True, slots=True)
class PlayerStats:
    """The statistics of one player in one season (rubric section 2.1).

    `None` means "not found in the sources". `awards` lists the tier of every award.
    """

    position: Position | None
    age: int | None
    minutes_league: int | None
    starts_league: int | None
    appearances_league: int | None
    minutes_all: int | None
    starts_all: int | None
    appearances_all: int | None
    goals_all: int | None
    assists_all: int | None
    clean_sheets_all: int | None
    caps: int | None
    awards: tuple[AwardTier, ...] | None
    available_matches_all: int | None = None


@dataclass(frozen=True, slots=True)
class ClubContext:
    """The club-season data the formula needs (rubric section 2.1)."""

    club_matches_all: int | None
    club_matches_league: int | None
    level_tier: LevelTier | None


@dataclass(frozen=True, slots=True)
class RatingComponents:
    """The pieces of the formula: I, P, N and V in `[0, 1]`, and T in rating points."""

    importance: Fraction
    production: Fraction
    selection: Fraction
    awards: Fraction
    level: int


@dataclass(frozen=True, slots=True)
class RatingResult:
    """Outcome of the formula.

    `rating` is `None` when a required statistic is missing (`missing` names them, using the
    field names of the rubric). `raw` is the value before rounding. `notes` records the
    documented fallbacks that were used (`assists: null`, `basis: league`...).
    """

    rating: int | None
    raw: Fraction | None
    components: RatingComponents | None
    basis: BasisKind | None
    missing: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Basis:
    kind: BasisKind
    minutes: int
    starts: int | None
    available: int


def round_raw(raw: Fraction) -> int:
    """Round to 6 decimals, then to an integer with "half up", and clamp to `[1, 99]`."""
    six_decimals = Fraction(floor(raw * _DECIMALS + _HALF), _DECIMALS)
    return max(MIN_RATING, min(MAX_RATING, floor(six_decimals + _HALF)))


def compute_rating(stats: PlayerStats, club: ClubContext) -> RatingResult:
    """Compute the rating of a player in a club-season (rubric section 4.1).

    Raises:
        InvalidValueError: if a count is negative, or a match count is not positive.
    """
    _check_valid(stats, club)
    missing = [
        name
        for name, value in (
            ("position", stats.position),
            ("age", stats.age),
            ("goals_all", stats.goals_all),
            ("caps", stats.caps),
            ("awards", stats.awards),
        )
        if value is None
    ]
    basis, missing_basis = _select_basis(stats, club)
    if missing_basis is not None:
        missing.append(missing_basis)
    if club.level_tier is None:
        missing.append("level_tier")
    position, goals, caps, awards, tier = (
        stats.position,
        stats.goals_all,
        stats.caps,
        stats.awards,
        club.level_tier,
    )
    if (
        missing
        or basis is None
        or position is None
        or goals is None
        or caps is None
        or awards is None
        or tier is None
    ):
        return RatingResult(None, None, None, None, tuple(missing), ())

    notes = [f"basis: {basis.kind}"] if basis.kind is BasisKind.LEAGUE else []
    production, production_notes = _production(
        position, goals, stats.assists_all, stats.clean_sheets_all, basis.available
    )
    components = RatingComponents(
        importance=_importance(basis),
        production=production,
        selection=min(_ONE, Fraction(caps, _CAPS_SATURATION)),
        awards=_awards(awards),
        level=_LEVEL_POINTS[tier],
    )
    raw = (
        _FLOOR
        + _W_IMPORTANCE * components.importance
        + _W_PRODUCTION * components.production
        + _W_SELECTION * components.selection
        + _W_AWARDS * components.awards
        + components.level
    )
    return RatingResult(
        rating=round_raw(raw),
        raw=raw,
        components=components,
        basis=basis.kind,
        missing=(),
        notes=(*notes, *production_notes),
    )


def _check_valid(stats: PlayerStats, club: ClubContext) -> None:
    counts = {
        "minutes_league": stats.minutes_league,
        "starts_league": stats.starts_league,
        "appearances_league": stats.appearances_league,
        "minutes_all": stats.minutes_all,
        "starts_all": stats.starts_all,
        "appearances_all": stats.appearances_all,
        "goals_all": stats.goals_all,
        "assists_all": stats.assists_all,
        "clean_sheets_all": stats.clean_sheets_all,
        "caps": stats.caps,
    }
    for name, value in counts.items():
        if value is not None and value < 0:
            raise InvalidValueError(f"invalid {name}: {value} is negative")
    match_counts = {
        "available_matches_all": stats.available_matches_all,
        "club_matches_all": club.club_matches_all,
        "club_matches_league": club.club_matches_league,
    }
    for name, value in match_counts.items():
        if value is not None and value <= 0:
            raise InvalidValueError(f"invalid {name}: {value} is not positive")


def _select_basis(stats: PlayerStats, club: ClubContext) -> tuple[_Basis | None, str | None]:
    """Choose all-competitions data, or the league as a fallback (rubric section 5).

    Returns the basis, or the name of what is missing.
    """
    if stats.minutes_all is not None and stats.appearances_all is not None:
        available = stats.available_matches_all
        if available is None:
            available = club.club_matches_all
        if available is None:
            return None, "club_matches_all"
        return _Basis(BasisKind.ALL, stats.minutes_all, stats.starts_all, available), None
    if stats.minutes_league is not None and stats.appearances_league is not None:
        if club.club_matches_league is None:
            return None, "club_matches_league"
        return (
            _Basis(
                BasisKind.LEAGUE,
                stats.minutes_league,
                stats.starts_league,
                club.club_matches_league,
            ),
            None,
        )
    return None, "minutes"


def _importance(basis: _Basis) -> Fraction:
    share_minutes = min(_ONE, Fraction(basis.minutes, _FULL_MATCH_MINUTES * basis.available))
    if basis.starts is None:
        return share_minutes
    share_starts = min(_ONE, Fraction(basis.starts, basis.available))
    return _MINUTES_WEIGHT * share_minutes + _STARTS_WEIGHT * share_starts


def _production(
    position: Position,
    goals: int,
    assists: int | None,
    clean_sheets: int | None,
    available: int,
) -> tuple[Fraction, tuple[str, ...]]:
    if position is Position.GK:
        if clean_sheets is None:
            return _GK_NEUTRAL_PRODUCTION, ("clean_sheets: null",)
        return min(_ONE, Fraction(clean_sheets, available) / _GK_CLEAN_SHEET_CAP), ()
    cap = _GOALS_PER_MATCH_CAP[position]
    if assists is None:
        rate = Fraction(goals, available)
        return min(_ONE, rate / (_NO_ASSISTS_DISCOUNT * cap)), ("assists: null",)
    return min(_ONE, (goals + _ASSIST_WEIGHT * assists) / available / cap), ()


def _awards(awards: tuple[AwardTier, ...]) -> Fraction:
    world = awards.count(AwardTier.W)
    league = awards.count(AwardTier.L)
    return min(_ONE, _WORLD_AWARD * world + _LEAGUE_AWARD * league)


def override_problem(formula_rating: int, value: int, distinct_sources: int) -> str | None:
    """Why a `rating_override` breaks the limits of rubric section 7.4, or `None` if it is fine.

    Up to 6 points away from the formula the rationale is enough; from 7 to 12 two distinct
    sources are also needed; more than 12 is never allowed.
    """
    gap = abs(value - formula_rating)
    if gap > MAX_OVERRIDE_GAP:
        return (
            f"differs {gap} points from the formula ({formula_rating}): more than 12 is forbidden"
        )
    if gap > MAX_OVERRIDE_GAP_WITH_RATIONALE and distinct_sources < MIN_SOURCES_FOR_LARGE_GAP:
        return (
            f"differs {gap} points from the formula ({formula_rating}): "
            "from 7 to 12 points it needs at least two distinct sources"
        )
    return None
