"""The rating formula of the rubric (`docs/content/rating-rubric.md`, section 4).

The worked examples of section 10 of the rubric are the oracle: each one must give exactly the
documented rating. Every name and figure here is fictional, like in the rubric.
"""

from dataclasses import replace
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mister.catalog.domain.ratings import (
    AwardTier,
    BasisKind,
    ClubContext,
    LevelTier,
    PlayerStats,
    Position,
    compute_rating,
    distinct_source_count,
    override_issue,
    override_problem,
    round_raw,
)


def stats(position: Position | None = Position.MF, /, **overrides: object) -> PlayerStats:
    """A fully known player with league and all-competitions data; tests override what matters."""
    base: dict[str, object] = {
        "position": position,
        "age": 27,
        "minutes_league": 2000,
        "starts_league": 20,
        "appearances_league": 25,
        "minutes_all": 2500,
        "starts_all": 28,
        "appearances_all": 32,
        "goals_all": 5,
        "assists_all": 4,
        "clean_sheets_all": None,
        "caps": 0,
        "awards": (),
        "available_matches_all": None,
    }
    base.update(overrides)
    return PlayerStats(**base)  # type: ignore[arg-type]


ATLANTIC = ClubContext(club_matches_all=55, club_matches_league=38, level_tier=LevelTier.A)
NORTH = ClubContext(club_matches_all=42, club_matches_league=38, level_tier=LevelTier.C)


# ------------------------------------------------------------------ rubric section 10 examples
def test_rubric_example_forward_with_awards_and_caps_rates_95() -> None:
    forward = stats(
        Position.FW,
        minutes_league=3140,
        appearances_league=36,
        minutes_all=4350,
        starts_all=50,
        appearances_all=53,
        goals_all=38,
        assists_all=9,
        caps=7,
        awards=(AwardTier.L, AwardTier.L),
    )

    result = compute_rating(forward, ATLANTIC)

    assert result.rating == 95
    assert result.basis is BasisKind.ALL
    assert result.raw is not None
    assert float(result.raw) == pytest.approx(95.21, abs=0.01)
    assert result.components is not None
    assert float(result.components.importance) == pytest.approx(0.888, abs=0.001)
    assert float(result.components.production) == pytest.approx(0.966, abs=0.001)
    assert float(result.components.selection) == pytest.approx(0.875)
    assert float(result.components.awards) == pytest.approx(0.70)
    assert result.components.level == 6


def test_rubric_example_midfielder_rates_80() -> None:
    midfielder = stats(
        Position.MF, minutes_all=3900, starts_all=44, goals_all=6, assists_all=12, caps=5
    )

    assert compute_rating(midfielder, ATLANTIC).rating == 80


def test_rubric_example_defender_in_a_mid_table_club_rates_67() -> None:
    defender = stats(
        Position.DF, minutes_all=2900, starts_all=33, goals_all=2, assists_all=1, caps=0
    )

    assert compute_rating(defender, NORTH).rating == 67


def _goalkeeper(clean_sheets: int | None) -> PlayerStats:
    return stats(
        Position.GK,
        minutes_all=4900,
        starts_all=54,
        goals_all=0,
        assists_all=0,
        clean_sheets_all=clean_sheets,
        caps=3,
        awards=(AwardTier.L,),
    )


def test_rubric_example_goalkeeper_with_clean_sheets_rates_90() -> None:
    result = compute_rating(_goalkeeper(24), ATLANTIC)

    assert result.rating == 90
    assert result.raw is not None
    assert float(result.raw) == pytest.approx(89.51, abs=0.05)  # the rubric rounds each term


def test_rubric_example_goalkeeper_without_clean_sheets_counts_zero_and_rates_78() -> None:
    result = compute_rating(_goalkeeper(None), ATLANTIC)

    assert result.rating == 78
    assert result.components is not None
    assert result.components.production == 0
    assert "clean_sheets: null" in result.notes


def test_rubric_example_rotation_substitute_without_assists_counts_zero_and_rates_49() -> None:
    substitute = stats(
        Position.MF, minutes_all=520, starts_all=4, goals_all=1, assists_all=None, caps=0
    )

    result = compute_rating(substitute, NORTH)

    assert result.rating == 49
    assert "assists: null" in result.notes


def test_rubric_example_injured_defender_rates_63_before_any_override() -> None:
    injured = stats(
        Position.DF, minutes_all=1800, starts_all=20, goals_all=1, assists_all=1, caps=2
    )

    assert compute_rating(injured, ATLANTIC).rating == 63


# ------------------------------------------------------------------------- formula details
def test_a_missing_start_count_counts_as_zero_starts() -> None:
    result = compute_rating(stats(starts_all=None, minutes_all=2475), ATLANTIC)

    assert result.components is not None
    assert result.components.importance == Fraction(7, 10) * Fraction(2475, 90 * 55)


def test_available_matches_replace_the_club_matches_for_a_mid_season_arrival() -> None:
    arrival = stats(minutes_all=1800, starts_all=20, available_matches_all=22)

    full_season = compute_rating(replace(arrival, available_matches_all=None), ATLANTIC)
    part_season = compute_rating(arrival, ATLANTIC)

    assert full_season.rating is not None
    assert part_season.rating is not None
    assert part_season.rating > full_season.rating


def test_available_matches_make_the_club_match_count_unnecessary() -> None:
    arrival = stats(available_matches_all=22)

    result = compute_rating(arrival, replace(ATLANTIC, club_matches_all=None))

    assert result.rating is not None


def test_clean_sheets_of_an_outfield_player_are_ignored() -> None:
    plain = compute_rating(stats(Position.DF, clean_sheets_all=None), ATLANTIC)
    with_sheets = compute_rating(stats(Position.DF, clean_sheets_all=30), ATLANTIC)

    assert plain == with_sheets


def test_each_club_tier_is_three_points_apart() -> None:
    raws = [compute_rating(stats(), replace(ATLANTIC, level_tier=tier)).raw for tier in LevelTier]

    assert all(raw is not None for raw in raws)
    a, b, c, d = raws
    assert a is not None
    assert b is not None
    assert c is not None
    assert d is not None
    assert [a - b, b - c, c - d] == [3, 3, 3]


def test_a_world_award_weighs_more_than_a_league_award() -> None:
    world = compute_rating(stats(awards=(AwardTier.W,)), NORTH).components
    league = compute_rating(stats(awards=(AwardTier.L,)), NORTH).components

    assert world is not None
    assert league is not None
    assert world.awards == Fraction(60, 100)
    assert league.awards == Fraction(35, 100)


def test_awards_saturate_at_one() -> None:
    components = compute_rating(stats(awards=(AwardTier.W, AwardTier.W)), NORTH).components

    assert components is not None
    assert components.awards == 1


def test_age_does_not_change_the_rating() -> None:
    young = compute_rating(stats(age=17), ATLANTIC)
    old = compute_rating(stats(age=38), ATLANTIC)

    assert young == old


# ------------------------------------------------------------------------------ rounding
def test_a_raw_rating_of_exactly_half_rounds_up() -> None:
    # avail 35, one goal and no assists in a mid-table club: 46 + 14 * (1/35 / 0.8) = 46.5
    half = stats(
        Position.FW,
        minutes_all=0,
        starts_all=0,
        goals_all=1,
        assists_all=0,
        available_matches_all=35,
    )

    result = compute_rating(half, NORTH)

    assert result.raw == Fraction(93, 2)
    assert result.rating == 47


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (Fraction(465, 10), 47),
        (Fraction(4649999996, 10**8), 47),  # 46.49999996 is 46.500000 at 6 decimals
        (Fraction(46499999, 10**6), 46),  # 46.499999 stays below the half
        (Fraction(0), 1),
        (Fraction(1004, 10), 99),
    ],
)
def test_round_raw_rounds_to_six_decimals_then_half_up_and_clamps(
    raw: Fraction, expected: int
) -> None:
    assert round_raw(raw) == expected


def test_the_rating_is_clamped_to_99() -> None:
    maxed = stats(
        Position.FW,
        minutes_all=99999,
        starts_all=99,
        goals_all=99,
        assists_all=99,
        caps=99,
        awards=(AwardTier.W, AwardTier.W),
    )

    result = compute_rating(maxed, ATLANTIC)

    assert result.raw == 101
    assert result.rating == 99


def test_the_lowest_reachable_rating_is_in_range() -> None:
    nothing = stats(Position.DF, minutes_all=0, starts_all=0, goals_all=0, assists_all=0, caps=0)

    result = compute_rating(nothing, replace(ATLANTIC, level_tier=LevelTier.D))

    assert result.rating == 43


# --------------------------------------------------------------------------- missing data
@pytest.mark.parametrize("missing", ["position", "age", "goals_all", "caps", "awards"])
def test_a_missing_required_statistic_gives_no_rating(missing: str) -> None:
    result = compute_rating(stats(**{missing: None}), ATLANTIC)

    assert result.rating is None
    assert result.raw is None
    assert result.components is None
    assert result.basis is None
    assert result.missing == (missing,)


def test_no_minutes_at_all_gives_no_rating() -> None:
    result = compute_rating(stats(minutes_all=None, minutes_league=None), ATLANTIC)

    assert result.rating is None
    assert result.missing == ("minutes",)


def test_a_club_without_level_tier_gives_no_rating() -> None:
    result = compute_rating(stats(), replace(ATLANTIC, level_tier=None))

    assert result.rating is None
    assert result.missing == ("level_tier",)


def test_a_club_without_match_count_gives_no_rating() -> None:
    result = compute_rating(stats(), replace(ATLANTIC, club_matches_all=None))

    assert result.rating is None
    assert result.missing == ("club_matches_all",)


def test_every_missing_item_is_reported_together() -> None:
    result = compute_rating(stats(goals_all=None, caps=None), replace(ATLANTIC, level_tier=None))

    assert result.missing == ("goals_all", "caps", "level_tier")


def test_league_figures_stand_in_when_the_all_competitions_minutes_are_missing() -> None:
    league_only = stats(
        Position.FW,
        minutes_league=3000,
        starts_league=30,
        appearances_league=34,
        minutes_all=None,
        starts_all=None,
        appearances_all=None,
        goals_all=12,
        assists_all=None,
    )

    result = compute_rating(league_only, NORTH)

    # importance on 38 league matches, production on the 42 matches of the club
    assert result.basis is BasisKind.LEAGUE
    assert "basis: league" in result.notes
    assert result.raw is not None
    expected = 46 + 22 * (0.7 * 3000 / 3420 + 0.3 * 30 / 38) + 14 * (12 / 42) / 0.8
    assert float(result.raw) == pytest.approx(expected, abs=1e-4)
    assert result.rating == 70


def test_league_start_count_is_used_on_the_league_basis_and_may_be_missing() -> None:
    with_starts = compute_rating(
        stats(minutes_all=None, appearances_all=None, starts_league=38), NORTH
    )
    without_starts = compute_rating(
        stats(minutes_all=None, appearances_all=None, starts_league=None), NORTH
    )

    assert with_starts.components is not None
    assert without_starts.components is not None
    assert without_starts.components.importance == Fraction(7, 10) * Fraction(2000, 90 * 38)
    assert with_starts.components.importance > without_starts.components.importance


def test_the_league_basis_respects_the_available_matches_of_a_mid_season_arrival() -> None:
    arrival = stats(
        minutes_all=None, appearances_all=None, minutes_league=900, available_matches_all=10
    )

    result = compute_rating(arrival, NORTH)

    assert result.basis is BasisKind.LEAGUE
    assert result.components is not None
    # 900 minutes in the 10 matches he could play, not in the 38 of the league
    assert result.components.importance == 1
    full = compute_rating(replace(arrival, available_matches_all=None), NORTH)
    assert full.components is not None
    assert full.components.importance < 1


def test_the_league_basis_still_needs_the_matches_of_the_club_for_production() -> None:
    result = compute_rating(stats(minutes_all=None), replace(NORTH, club_matches_all=None))

    assert result.rating is None
    assert result.missing == ("club_matches_all",)


def test_missing_appearances_all_falls_back_to_the_league() -> None:
    result = compute_rating(stats(appearances_all=None), NORTH)

    assert result.basis is BasisKind.LEAGUE


def test_the_league_fallback_needs_the_league_appearances() -> None:
    result = compute_rating(stats(minutes_all=None, appearances_league=None), NORTH)

    assert result.rating is None
    assert result.missing == ("minutes",)


def test_the_league_fallback_needs_the_league_match_count() -> None:
    result = compute_rating(stats(minutes_all=None), replace(NORTH, club_matches_league=None))

    assert result.rating is None
    assert result.missing == ("club_matches_league",)


def test_all_minutes_without_all_appearances_or_league_data_gives_no_rating() -> None:
    result = compute_rating(
        stats(appearances_all=None, minutes_league=None, appearances_league=None), NORTH
    )

    assert result.rating is None
    assert result.missing == ("minutes",)


# ----------------------------------------------------------------------- invalid inputs
@pytest.mark.parametrize(
    "bad",
    [
        {"minutes_all": -1},
        {"goals_all": -1},
        {"caps": -1},
        {"available_matches_all": 0},
    ],
)
def test_impossible_statistics_are_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="invalid"):
        compute_rating(stats(**bad), ATLANTIC)


def test_a_club_with_zero_matches_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid"):
        compute_rating(stats(), replace(ATLANTIC, club_matches_all=0))


# ---------------------------------------------------------------------------- properties
POSITIONS = st.sampled_from(list(Position))
TIERS = st.sampled_from(list(LevelTier))
AWARDS = st.lists(st.sampled_from(list(AwardTier)), max_size=4).map(tuple)


@st.composite
def players(draw: st.DrawFn) -> tuple[PlayerStats, ClubContext]:
    position = draw(POSITIONS)
    matches = draw(st.integers(min_value=10, max_value=70))
    player = stats(
        position,
        minutes_all=draw(st.integers(min_value=0, max_value=90 * matches)),
        starts_all=draw(st.integers(min_value=0, max_value=matches)),
        goals_all=draw(st.integers(min_value=0, max_value=60)),
        assists_all=draw(st.integers(min_value=0, max_value=40)),
        clean_sheets_all=draw(st.integers(min_value=0, max_value=matches))
        if position is Position.GK
        else None,
        caps=draw(st.integers(min_value=0, max_value=20)),
        awards=draw(AWARDS),
    )
    club = ClubContext(club_matches_all=matches, club_matches_league=38, level_tier=draw(TIERS))
    return player, club


def _rating(player: PlayerStats, club: ClubContext) -> int:
    rating = compute_rating(player, club).rating
    assert rating is not None
    return rating


@given(players(), st.integers(min_value=0, max_value=4000))
def test_more_minutes_never_lower_the_rating(
    case: tuple[PlayerStats, ClubContext], extra: int
) -> None:
    player, club = case
    assert player.minutes_all is not None

    better = replace(player, minutes_all=player.minutes_all + extra)

    assert _rating(better, club) >= _rating(player, club)


@given(players(), st.integers(min_value=0, max_value=40))
def test_more_starts_never_lower_the_rating(
    case: tuple[PlayerStats, ClubContext], extra: int
) -> None:
    player, club = case
    assert player.starts_all is not None

    better = replace(player, starts_all=player.starts_all + extra)

    assert _rating(better, club) >= _rating(player, club)


@given(players(), st.integers(min_value=0, max_value=40))
def test_more_goals_never_lower_the_rating(
    case: tuple[PlayerStats, ClubContext], extra: int
) -> None:
    player, club = case
    assert player.goals_all is not None

    better = replace(player, goals_all=player.goals_all + extra)

    assert _rating(better, club) >= _rating(player, club)


@given(players(), st.integers(min_value=0, max_value=40))
def test_more_assists_never_lower_the_rating(
    case: tuple[PlayerStats, ClubContext], extra: int
) -> None:
    player, club = case
    assert player.assists_all is not None

    better = replace(player, assists_all=player.assists_all + extra)

    assert _rating(better, club) >= _rating(player, club)


@given(players(), st.integers(min_value=0, max_value=40))
def test_more_clean_sheets_never_lower_a_goalkeeper_rating(
    case: tuple[PlayerStats, ClubContext], extra: int
) -> None:
    player, club = case
    goalkeeper = replace(player, position=Position.GK, clean_sheets_all=3)

    better = replace(goalkeeper, clean_sheets_all=3 + extra)

    assert _rating(better, club) >= _rating(goalkeeper, club)


@given(players(), st.integers(min_value=0, max_value=20))
def test_more_caps_never_lower_the_rating(
    case: tuple[PlayerStats, ClubContext], extra: int
) -> None:
    player, club = case
    assert player.caps is not None

    better = replace(player, caps=player.caps + extra)

    assert _rating(better, club) >= _rating(player, club)


@given(players(), st.lists(st.sampled_from(list(AwardTier)), max_size=3))
def test_more_awards_never_lower_the_rating(
    case: tuple[PlayerStats, ClubContext], extra: list[AwardTier]
) -> None:
    player, club = case
    assert player.awards is not None

    better = replace(player, awards=(*player.awards, *extra))

    assert _rating(better, club) >= _rating(player, club)


@given(players(), TIERS, TIERS)
def test_a_higher_club_tier_never_lowers_the_rating(
    case: tuple[PlayerStats, ClubContext], first: LevelTier, second: LevelTier
) -> None:
    player, club = case
    low, high = sorted((first, second), key=lambda tier: "DCBA".index(tier.value))

    higher = _rating(player, replace(club, level_tier=high))
    lower = _rating(player, replace(club, level_tier=low))

    assert higher >= lower


@given(players(), st.integers(min_value=0, max_value=30))
def test_more_matches_to_play_never_raise_the_rating(
    case: tuple[PlayerStats, ClubContext], extra: int
) -> None:
    player, club = case
    assert club.club_matches_all is not None

    longer = replace(club, club_matches_all=club.club_matches_all + extra)

    assert _rating(player, longer) <= _rating(player, club)


@given(players(), st.integers(min_value=0, max_value=40))
def test_finding_the_assists_never_lowers_the_rating(
    case: tuple[PlayerStats, ClubContext], found: int
) -> None:
    player, club = case

    unknown = replace(player, assists_all=None)

    assert _rating(replace(player, assists_all=found), club) >= _rating(unknown, club)


@given(players(), st.integers(min_value=0, max_value=40))
def test_finding_the_clean_sheets_never_lowers_a_goalkeeper_rating(
    case: tuple[PlayerStats, ClubContext], found: int
) -> None:
    player, club = case
    unknown = replace(player, position=Position.GK, clean_sheets_all=None)

    assert _rating(replace(unknown, clean_sheets_all=found), club) >= _rating(unknown, club)


@given(players(), st.integers(min_value=0, max_value=70), st.booleans())
def test_finding_the_starts_never_lowers_the_rating(
    case: tuple[PlayerStats, ClubContext], found: int, league_basis: bool
) -> None:
    player, club = case
    if league_basis:
        player = replace(player, minutes_all=None, appearances_all=None)
        unknown = replace(player, starts_league=None)
        known = replace(player, starts_league=found)
    else:
        unknown = replace(player, starts_all=None)
        known = replace(player, starts_all=found)

    assert _rating(known, club) >= _rating(unknown, club)


@given(players())
def test_the_rating_is_always_between_1_and_99(case: tuple[PlayerStats, ClubContext]) -> None:
    player, club = case

    assert 1 <= _rating(player, club) <= 99


@given(players())
def test_the_formula_is_deterministic(case: tuple[PlayerStats, ClubContext]) -> None:
    player, club = case

    assert compute_rating(player, club) == compute_rating(player, club)


# ------------------------------------------------------------------------------ overrides
@pytest.mark.parametrize(
    ("formula", "value", "sources"),
    [(70, 70, 1), (70, 76, 1), (70, 64, 1), (70, 77, 2), (70, 58, 2), (70, 82, 3)],
)
def test_an_override_within_the_documented_limits_has_no_problem(
    formula: int, value: int, sources: int
) -> None:
    assert override_problem(formula, value, sources) is None


def test_an_override_seven_to_twelve_points_away_needs_two_distinct_sources() -> None:
    problem = override_problem(70, 77, 1)

    assert problem is not None
    assert "two distinct sources" in problem


def test_an_override_more_than_twelve_points_away_is_never_allowed() -> None:
    problem = override_problem(70, 83, 5)

    assert problem is not None
    assert "more than 12" in problem


def test_a_missing_assist_count_is_the_same_as_zero_assists() -> None:
    assert (
        compute_rating(stats(assists_all=None), NORTH).rating
        == compute_rating(stats(assists_all=0), NORTH).rating
    )


def test_override_issue_explains_a_missing_statistic() -> None:
    result = compute_rating(stats(goals_all=None), NORTH)

    issue = override_issue(result, 70, 2)

    assert issue is not None
    assert "statistics are missing: goals_all" in issue


def test_override_issue_applies_the_limits_to_the_formula_rating() -> None:
    result = compute_rating(stats(), NORTH)
    assert result.rating is not None

    assert override_issue(result, result.rating + 5, 1) is None
    far = override_issue(result, result.rating + 13, 3)
    assert far is not None
    assert "more than 12" in far


def test_distinct_sources_ignore_trailing_slash_scheme_case_and_host_case() -> None:
    urls = [
        "https://example.org/a",
        "https://example.org/a/",
        "HTTPS://EXAMPLE.ORG/a",
        "http://example.org/a",
    ]

    assert distinct_source_count(urls) == 1


def test_distinct_sources_keep_different_paths_apart() -> None:
    assert distinct_source_count(["https://example.org/a", "https://example.org/b"]) == 2
