"""The ratings use case: compute, check and explain the ratings of a club-season."""

import pytest

from mister.catalog.application.ports import (
    ClubSeasonRatings,
    ClubSeasonRatingsUnavailableError,
    PlayerNotInSquadError,
    PlayerRatingSource,
)
from mister.catalog.application.ratings_tool import RatingsTool
from mister.catalog.domain.ratings import AwardTier, ClubContext, LevelTier, PlayerStats, Position
from mister.catalog.infrastructure.in_memory.rating_sheets import InMemoryRatingSheetStore

CLUB = "fake-fc-2000-01"


def stats(position: Position = Position.MF, **overrides: object) -> PlayerStats:
    base: dict[str, object] = {
        "position": position,
        "age": 27,
        "minutes_league": 1000,
        "starts_league": 10,
        "appearances_league": 12,
        "minutes_all": 1200,
        "starts_all": 12,
        "appearances_all": 14,
        "goals_all": 2,
        "clean_sheets_all": None,
        "caps": 0,
        "awards": (),
        "available_matches_all": None,
    }
    base.update(overrides)
    return PlayerStats(**base)  # type: ignore[arg-type]


def source(
    player_id: str,
    player_stats: PlayerStats,
    stored: int | None,
    override: int | None = None,
    *,
    partial_season: bool = False,
) -> PlayerRatingSource:
    return PlayerRatingSource(
        player_id,
        f"Name {player_id}",
        player_stats,
        CLUB_CONTEXT,
        stored,
        override,
        partial_season=partial_season,
    )


CLUB_CONTEXT = ClubContext(club_matches_all=20, club_matches_league=16, level_tier=LevelTier.C)


def tool(*players: PlayerRatingSource) -> tuple[RatingsTool, InMemoryRatingSheetStore]:
    store = InMemoryRatingSheetStore([ClubSeasonRatings(CLUB, players)])
    return RatingsTool(store), store


def test_check_reports_no_discrepancy_when_ratings_match_the_formula() -> None:
    probe, _ = tool(source("a", stats(), 0))
    expected = probe.explain(CLUB, "a").expected
    ready, store = tool(source("a", stats(), expected))

    report = ready.check(CLUB)

    assert report.discrepancies == ()
    assert store.saved == {}


def test_check_reports_a_discrepancy_without_writing_anything() -> None:
    ready, store = tool(source("a", stats(), 99), source("b", stats(), None))

    report = ready.check(CLUB)

    assert [line.player_id for line in report.discrepancies] == ["a", "b"]
    assert not report.written
    assert store.saved == {}


def test_compute_saves_the_formula_ratings_and_marks_the_report_as_written() -> None:
    ready, store = tool(source("a", stats(), 1), source("b", stats(Position.FW, goals_all=9), 1))

    report = ready.compute(CLUB)

    assert report.written
    assert store.saved[CLUB] == {
        "a": report.lines[0].expected,
        "b": report.lines[1].expected,
    }
    assert report.lines[1].expected is not None
    assert report.lines[0].expected is not None
    assert report.lines[1].expected > report.lines[0].expected


def test_compute_does_not_write_when_everything_is_up_to_date() -> None:
    probe, _ = tool(source("a", stats(), 0))
    expected = probe.explain(CLUB, "a").expected
    ready, store = tool(source("a", stats(), expected))

    report = ready.compute(CLUB)

    assert not report.written
    assert store.saved == {}


def test_an_override_value_is_the_expected_rating() -> None:
    probe, _ = tool(source("a", stats(), 0))
    formula = probe.explain(CLUB, "a").expected
    assert formula is not None
    ready, store = tool(source("a", stats(), formula, override=formula + 4))

    report = ready.compute(CLUB)

    assert report.lines[0].expected == formula + 4
    assert report.lines[0].overridden
    assert store.saved[CLUB] == {"a": formula + 4}


def test_a_player_whose_rating_cannot_be_computed_gets_a_null_rating() -> None:
    ready, store = tool(source("a", stats(goals_all=None), 70))

    report = ready.compute(CLUB)

    assert report.lines[0].expected is None
    assert report.lines[0].result.missing == ("goals_all",)
    assert store.saved[CLUB] == {"a": None}


def test_an_override_that_is_too_far_from_the_formula_is_a_problem_of_the_line() -> None:
    probe, _ = tool(source("a", stats(), 0))
    formula = probe.explain(CLUB, "a").expected
    assert formula is not None
    ready, _ = tool(source("a", stats(), formula + 20, override=formula + 20))

    report = ready.check(CLUB)

    assert report.lines[0].problem is not None
    assert "more than 12" in report.lines[0].problem
    assert report.lines[0] in report.discrepancies


def test_an_override_over_a_missing_statistic_is_a_problem_of_the_line() -> None:
    ready, _ = tool(source("a", stats(goals_all=None), 70, override=70))

    report = ready.check(CLUB)

    assert report.lines[0].problem is not None
    assert "missing" in report.lines[0].problem


def test_the_report_carries_anti_inflation_alerts() -> None:
    maxed = stats(
        Position.FW,
        minutes_all=1800,
        starts_all=20,
        goals_all=40,
        caps=10,
        awards=(AwardTier.W,),
        age=20,
    )
    ready, _ = tool(source("kid", maxed, 1))

    report = ready.check(CLUB)

    assert any("kid" in alert for alert in report.alerts)


def test_explain_returns_the_breakdown_of_one_player() -> None:
    ready, _ = tool(source("a", stats(), None))

    line = ready.explain(CLUB, "a")

    assert line.result.components is not None
    assert line.result.rating == line.expected
    assert line.display_name == "Name a"


def test_explain_of_an_unknown_player_fails() -> None:
    ready, _ = tool(source("a", stats(), None))

    with pytest.raises(PlayerNotInSquadError) as raised:
        ready.explain(CLUB, "nobody")

    assert raised.value.code == "player_not_in_squad"


def test_an_unknown_club_season_fails() -> None:
    ready, _ = tool()

    with pytest.raises(ClubSeasonRatingsUnavailableError) as raised:
        ready.check("other-fc-2000-01")

    assert raised.value.code == "club_season_ratings_unavailable"


def test_a_partial_season_without_available_matches_is_warned_about() -> None:
    ready, _ = tool(source("late", stats(), 1, partial_season=True))

    report = ready.check(CLUB)

    assert any("late" in alert and "available_matches_all" in alert for alert in report.alerts)


def test_a_partial_season_with_available_matches_raises_no_warning() -> None:
    ready, _ = tool(source("late", stats(available_matches_all=10), 1, partial_season=True))

    assert ready.check(CLUB).alerts == ()
