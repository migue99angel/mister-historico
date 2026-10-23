"""`mister content ratings compute`: writes the formula's ratings, or checks them (CI)."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from mister.entrypoints.cli.app import app

FIXTURE_ROOT = Path(__file__).parent.parent.parent / "fixtures" / "content"
CLUB_SEASON = "test-fc-2000-01"
REPO_CONTENT = Path(__file__).parents[4] / "content"
SQUAD = Path("club-seasons") / CLUB_SEASON / "squad.yaml"
runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(FIXTURE_ROOT, target)
    return target


def edit(root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = root / SQUAD
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8"
    )


def run(root: Path, *arguments: str) -> Any:
    return runner.invoke(
        app, ["content", "ratings", "compute", CLUB_SEASON, "--root", str(root), *arguments]
    )


def ratings(root: Path) -> dict[str, int | None]:
    data = yaml.safe_load((root / SQUAD).read_text(encoding="utf-8"))
    return {p["player_id"]: p["rating"] for p in data["players"]}


def test_the_synthetic_content_passes_the_check(root: Path) -> None:
    result = run(root, "--check")

    assert result.exit_code == 0, result.output
    assert "up to date" in result.output


def test_check_fails_with_a_message_per_discrepancy_and_writes_nothing(root: Path) -> None:
    edit(root, lambda d: d["players"][4].update(rating=d["players"][4]["rating"] + 1))
    before = (root / SQUAD).read_bytes()

    result = run(root, "--check")

    assert result.exit_code == 1
    assert "tfc-05" in result.output
    assert (root / SQUAD).read_bytes() == before


def test_compute_writes_the_formula_ratings_and_the_check_then_passes(root: Path) -> None:
    good = ratings(root)
    edit(root, lambda d: d["players"][4].update(rating=3))
    edit(root, lambda d: d["players"][5].update(rating=None, verify="pending"))

    result = run(root)

    assert result.exit_code == 0, result.output
    assert "tfc-05" in result.output
    assert ratings(root)["tfc-05"] == good["tfc-05"]
    assert ratings(root)["tfc-06"] == good["tfc-06"]
    assert run(root, "--check").exit_code == 0


def test_compute_keeps_comments_and_the_order_of_the_file(root: Path) -> None:
    good = ratings(root)
    edit(root, lambda d: d["players"][4].update(rating=3))
    path = root / SQUAD
    path.write_text("# Reviewed by hand\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    before = path.read_text(encoding="utf-8").splitlines()

    result = run(root)

    after = path.read_text(encoding="utf-8").splitlines()
    assert result.exit_code == 0, result.output
    assert after[0] == "# Reviewed by hand"
    assert [a for a, b in zip(before, after, strict=True) if a != b] == ["  rating: 3"]
    assert ratings(root)["tfc-05"] == good["tfc-05"]


def test_compute_of_an_overridden_player_keeps_the_override_value(root: Path) -> None:
    before = ratings(root)

    run(root)

    assert ratings(root) == before


def test_an_override_too_far_from_the_formula_fails_even_without_check(root: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["players"][2]["rating_override"]["value"] = 99
        data["players"][2]["rating"] = 99

    edit(root, mutate)

    result = run(root)

    assert result.exit_code == 1
    assert "tfc-03" in result.output
    assert "more than 12" in result.output


def test_explain_prints_the_breakdown_of_the_player_and_writes_nothing(root: Path) -> None:
    edit(root, lambda d: d["players"][4].update(rating=3))
    before = (root / SQUAD).read_bytes()

    result = run(root, "--explain", "tfc-05")

    assert result.exit_code == 0, result.output
    for part in ("tfc-05", "importance", "production", "selection", "awards", "level", "raw"):
        assert part in result.output
    assert (root / SQUAD).read_bytes() == before


def test_explain_shows_what_is_missing_when_nothing_can_be_computed(root: Path) -> None:
    edit(
        root,
        lambda d: d["players"][4]["season_stats"].update(goals_all=None, verify="pending"),
    )

    result = run(root, "--explain", "tfc-05")

    assert result.exit_code == 0, result.output
    assert "missing: goals_all" in result.output


def test_explain_of_an_unknown_player_fails_with_a_clear_message(root: Path) -> None:
    result = run(root, "--explain", "nobody")

    assert result.exit_code == 2
    assert "nobody" in result.output


def test_an_unknown_club_season_fails_with_a_clear_message(root: Path) -> None:
    result = runner.invoke(
        app, ["content", "ratings", "compute", "nowhere-fc-2000-01", "--root", str(root)]
    )

    assert result.exit_code == 2
    assert "nowhere-fc-2000-01" in result.output


def test_alerts_are_printed_as_warnings_and_do_not_fail_the_run(root: Path) -> None:
    def inflate(data: dict[str, Any]) -> None:
        for player in data["players"]:
            player["season_stats"].update(minutes_all=1260, starts_all=14, appearances_all=14)
            player["season_stats"].update(
                minutes_league=900, starts_league=10, appearances_league=10
            )
            player["season_stats"]["goals_all"] = 12
            player["season_stats"]["caps"] = 8
            player.pop("rating_override", None)
            player["season_stats"].pop("available_matches_all", None)
        data["club_data"]["level_tier"] = "A"

    edit(root, inflate)

    result = run(root)

    assert result.exit_code == 0, result.output
    assert "warning" in result.output.lower()


def test_the_root_defaults_to_the_content_directory(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(root.parent)

    result = runner.invoke(app, ["content", "ratings", "compute", CLUB_SEASON, "--check"])

    assert result.exit_code == 0, result.output


def test_the_help_lists_the_content_command() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "content" in result.output


def test_notes_of_the_fallbacks_are_printed_per_player(root: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["players"][0]["season_stats"].pop("clean_sheets_all", None)
        data["players"][5]["season_stats"].update(minutes_all=None, appearances_all=None)

    edit(root, mutate)

    result = run(root)

    assert result.exit_code == 0, result.output
    assert "note: tfc-01: clean_sheets: null" in result.output
    assert "note: tfc-06: basis: league" in result.output


def test_the_default_root_falls_back_to_the_content_of_the_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["content", "ratings", "compute", CLUB_SEASON, "--check"])

    assert result.exit_code == 2
    assert str(REPO_CONTENT) in result.output.replace("\n", "")


def test_a_partial_season_without_available_matches_is_a_warning(root: Path) -> None:
    edit(root, lambda d: d["players"][21]["season_stats"].pop("available_matches_all"))
    edit(root, lambda d: d["players"][21].update(rating=1))

    result = run(root)

    assert "warning: tfc-22" in result.output
    assert result.exit_code == 0
