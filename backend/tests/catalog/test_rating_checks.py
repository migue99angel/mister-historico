"""Tree validation of ratings: the stored rating must be the formula's (or the override's)."""

import shutil
from pathlib import Path
from typing import Any

import pytest
from tests.catalog.test_content_tree import FIXTURE_ROOT, OWN, SQUAD, assert_issue, edit, issues_of

from mister.catalog.domain.ratings import compute_rating
from mister.catalog.infrastructure.content_schema import load_content_tree
from mister.catalog.infrastructure.content_schema.ratings_bridge import (
    club_context,
    player_stats,
)

PLAYER = 3  # a defender of Test FC: its formula rating leaves room above and below
RIVAL = "club-seasons/mock-city-2000-01/squad.yaml"
MARKET = "club-seasons/_market-2000-01/squad.yaml"
SOURCE_A = "https://example.org/test-content/overrides/a"
SOURCE_B = "https://example.org/test-content/overrides/b"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(FIXTURE_ROOT, target)
    return target


def formula(root: Path, index: int = PLAYER, club_season: str = OWN) -> int:
    squad = load_content_tree(root, release=False).squads[club_season]
    result = compute_rating(player_stats(squad.players[index]), club_context(squad))
    assert result.rating is not None
    return result.rating


def with_override(
    value: int, sources: tuple[str, ...] = (SOURCE_A,), *, rating: int | None = None
) -> Any:
    def mutate(data: dict[str, Any]) -> None:
        data["players"][PLAYER]["rating_override"] = {
            "value": value,
            "rationale": "Fictional long injury, documented in the sources.",
            "sources": list(sources),
        }
        data["players"][PLAYER]["rating"] = value if rating is None else rating

    return mutate


def test_the_synthetic_ratings_all_match_the_formula(root: Path) -> None:
    load_content_tree(root, release=True)


def test_a_rating_that_differs_from_the_formula_names_file_player_and_expected_value(
    root: Path,
) -> None:
    expected = formula(root)
    edit(root, SQUAD, lambda d: d["players"][PLAYER].update(rating=expected + 1))

    issues = issues_of(root)

    assert_issue(issues, SQUAD, f"players.{PLAYER}.rating", f"expected {expected}")
    assert_issue(issues, SQUAD, f"players.{PLAYER}.rating", "tfc-04")


def test_a_rival_squad_is_checked_too(root: Path) -> None:
    expected = formula(root, 0, "mock-city-2000-01")
    edit(root, RIVAL, lambda d: d["players"][0].update(rating=expected - 1))

    assert_issue(issues_of(root), RIVAL, "players.0.rating", f"expected {expected}")


def test_a_market_squad_rating_is_not_computed(root: Path) -> None:
    edit(root, MARKET, lambda d: d["players"][0].update(rating=99))

    load_content_tree(root, release=False)


def test_a_change_of_club_level_changes_every_expected_rating(root: Path) -> None:
    def demote(data: dict[str, Any]) -> None:
        data["club_data"]["level_tier"] = "D" if data["club_data"]["level_tier"] != "D" else "A"

    edit(root, SQUAD, demote)

    issues = issues_of(root)

    assert len([i for i in issues if i.path == SQUAD and i.field.endswith(".rating")]) > 10


def test_a_pending_player_without_enough_statistics_has_a_null_rating(root: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        player = data["players"][PLAYER]
        player["season_stats"].update(minutes_league=None, minutes_all=None, verify="pending")
        player.update(rating=None, verify="pending")

    edit(root, SQUAD, mutate)

    load_content_tree(root, release=False)
    assert_issue(issues_of(root, release=True), SQUAD, f"players.{PLAYER}.verify", "pending")


def test_a_rating_with_statistics_that_do_not_allow_one_is_reported(root: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["players"][PLAYER]["season_stats"].update(goals_all=None, verify="pending")

    edit(root, SQUAD, mutate)

    assert_issue(
        issues_of(root), SQUAD, f"players.{PLAYER}.rating", "expected null (missing: goals_all)"
    )


def test_a_calculable_player_with_a_null_rating_is_reported(root: Path) -> None:
    expected = formula(root)
    edit(root, SQUAD, lambda d: d["players"][PLAYER].update(rating=None, verify="pending"))

    assert_issue(issues_of(root), SQUAD, f"players.{PLAYER}.rating", f"expected {expected}")


# ------------------------------------------------------------------------------- overrides
def test_the_stored_rating_of_an_overridden_player_is_the_override_value(root: Path) -> None:
    edit(root, SQUAD, with_override(formula(root) + 6))

    load_content_tree(root, release=True)


def test_an_overridden_player_with_the_formula_rating_is_reported(root: Path) -> None:
    value = formula(root) + 3
    edit(root, SQUAD, with_override(value, rating=value - 1))

    assert_issue(issues_of(root), SQUAD, f"players.{PLAYER}.rating", f"expected {value}")


def test_an_override_seven_points_away_needs_two_distinct_sources(root: Path) -> None:
    edit(root, SQUAD, with_override(formula(root) + 7))

    assert_issue(
        issues_of(root), SQUAD, f"players.{PLAYER}.rating_override", "two distinct sources"
    )


def test_two_equal_sources_do_not_count_as_two_distinct_sources(root: Path) -> None:
    edit(root, SQUAD, with_override(formula(root) - 7, (SOURCE_A, SOURCE_A)))

    assert_issue(
        issues_of(root), SQUAD, f"players.{PLAYER}.rating_override", "two distinct sources"
    )


def test_an_override_twelve_points_away_with_two_sources_is_accepted(root: Path) -> None:
    edit(root, SQUAD, with_override(formula(root) + 12, (SOURCE_A, SOURCE_B)))

    load_content_tree(root, release=False)


def test_an_override_more_than_twelve_points_away_is_rejected(root: Path) -> None:
    edit(root, SQUAD, with_override(formula(root) + 13, (SOURCE_A, SOURCE_B)))

    assert_issue(issues_of(root), SQUAD, f"players.{PLAYER}.rating_override", "more than 12")


def test_an_override_below_the_formula_is_measured_the_same_way(root: Path) -> None:
    edit(root, SQUAD, with_override(formula(root) - 13, (SOURCE_A, SOURCE_B)))

    assert_issue(issues_of(root), SQUAD, f"players.{PLAYER}.rating_override", "more than 12")


def test_an_override_cannot_fix_missing_statistics(root: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["players"][PLAYER]["season_stats"].update(goals_all=None, verify="pending")
        with_override(70)(data)

    edit(root, SQUAD, mutate)

    assert_issue(
        issues_of(root),
        SQUAD,
        f"players.{PLAYER}.rating_override",
        "statistics are missing: goals_all",
    )


def test_a_rating_rationale_next_to_an_override_is_accepted(root: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        with_override(formula(root) + 2)(data)
        data["players"][PLAYER]["rating_rationale"] = "Reviewed against the sources."

    edit(root, SQUAD, mutate)

    load_content_tree(root, release=False)
