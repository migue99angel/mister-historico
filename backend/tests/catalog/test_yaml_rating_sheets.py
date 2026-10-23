"""The YAML adapter of the ratings: reading squads and rewriting only the ratings."""

import shutil
from pathlib import Path

import pytest
import yaml

from mister.catalog.application.ports import ClubSeasonRatingsUnavailableError
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore

FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "content"
SQUAD = "club-seasons/test-fc-2000-01/squad.yaml"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(FIXTURE_ROOT, target)
    return target


def lines(root: Path) -> list[str]:
    return (root / SQUAD).read_text(encoding="utf-8").splitlines()


def test_an_invalid_squad_reports_its_schema_issues(root: Path) -> None:
    path = root / SQUAD
    path.write_text(path.read_text(encoding="utf-8").replace("key: false", "key: 3", 1))

    with pytest.raises(ClubSeasonRatingsUnavailableError, match=r"players\.0\.key"):
        YamlRatingSheetStore(root).load("test-fc-2000-01")


def test_an_aggregate_has_no_players_to_rate(root: Path) -> None:
    with pytest.raises(ClubSeasonRatingsUnavailableError, match="squad"):
        YamlRatingSheetStore(root).load("overseas-fc-2000-01")


def test_saving_changes_only_the_rating_lines_and_keeps_comments_and_order(root: Path) -> None:
    path = root / SQUAD
    path.write_text("# Fictional squad kept by hand\n" + path.read_text(encoding="utf-8"))
    before = lines(root)
    stored = {
        p.player_id: p.stored_rating
        for p in YamlRatingSheetStore(root).load("test-fc-2000-01").players
    }

    YamlRatingSheetStore(root).save("test-fc-2000-01", {"tfc-01": (stored["tfc-01"] or 0) + 1})

    after = lines(root)
    changed = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
    assert len(before) == len(after)
    assert after[0] == "# Fictional squad kept by hand"
    assert len(changed) == 1
    assert changed[0][0].strip().startswith("rating:")


def test_saving_the_same_ratings_leaves_the_file_byte_identical(root: Path) -> None:
    store = YamlRatingSheetStore(root)
    original = (root / SQUAD).read_bytes()
    stored = {p.player_id: p.stored_rating for p in store.load("test-fc-2000-01").players}

    store.save("test-fc-2000-01", stored)

    assert (root / SQUAD).read_bytes() == original


def test_a_null_rating_marks_the_player_as_pending(root: Path) -> None:
    store = YamlRatingSheetStore(root)

    store.save("test-fc-2000-01", {"tfc-05": None})

    data = yaml.safe_load((root / SQUAD).read_text(encoding="utf-8"))
    player = next(p for p in data["players"] if p["player_id"] == "tfc-05")
    assert player["rating"] is None
    assert player["verify"] == "pending"


def changed_lines(before: str, after: str) -> list[tuple[str, str]]:
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    assert len(old) == len(new)
    return [(a, b) for a, b in zip(old, new, strict=True) if a != b]


def test_a_long_line_and_trailing_spaces_elsewhere_are_left_untouched(root: Path) -> None:
    path = root / SQUAD
    text = path.read_text(encoding="utf-8")
    long_line = "    # " + "a very long fictional comment " * 8 + "  \n"
    text = text.replace("players:\n", "players:\n" + long_line, 1)
    path.write_text(text, encoding="utf-8")
    store = YamlRatingSheetStore(root)
    current = {p.player_id: p.stored_rating for p in store.load("test-fc-2000-01").players}

    store.save("test-fc-2000-01", {"tfc-01": (current["tfc-01"] or 0) + 1})

    changes = changed_lines(text, path.read_text(encoding="utf-8"))
    assert len(changes) == 1
    assert changes[0][0].strip().startswith("rating:")


def test_an_indented_list_keeps_its_indentation(root: Path) -> None:
    path = root / SQUAD
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, indent=4, width=60),
        encoding="utf-8",
    )
    before = path.read_text(encoding="utf-8")
    store = YamlRatingSheetStore(root)
    current = {p.player_id: p.stored_rating for p in store.load("test-fc-2000-01").players}

    store.save("test-fc-2000-01", {"tfc-02": 50, "tfc-03": (current["tfc-03"] or 0) + 1})

    changes = changed_lines(before, path.read_text(encoding="utf-8"))
    assert len(changes) == 2
    assert all(old.strip().startswith("rating:") for old, _ in changes)


def test_a_trailing_comment_on_the_rating_line_survives(root: Path) -> None:
    path = root / SQUAD
    text = path.read_text(encoding="utf-8")
    first = next(line for line in text.splitlines() if line.startswith("  rating:"))
    path.write_text(text.replace(first, first + "  # checked", 1), encoding="utf-8")
    store = YamlRatingSheetStore(root)

    store.save("test-fc-2000-01", {"tfc-01": 51})

    assert "  rating: 51  # checked" in path.read_text(encoding="utf-8")


def test_an_unfixable_rating_line_is_reported_instead_of_guessing(root: Path) -> None:
    path = root / SQUAD
    text = path.read_text(encoding="utf-8")
    first = next(line for line in text.splitlines() if line.startswith("  rating:"))
    path.write_text(text.replace(first, "  rating: &r 70", 1), encoding="utf-8")

    with pytest.raises(ClubSeasonRatingsUnavailableError, match="rating"):
        YamlRatingSheetStore(root).save("test-fc-2000-01", {"tfc-01": 51})


def test_a_market_squad_can_be_loaded_and_saved(root: Path) -> None:
    store = YamlRatingSheetStore(root)

    store.save("_market-2000-01", {"mkt-01": 55})

    loaded = {p.player_id: p.stored_rating for p in store.load("_market-2000-01").players}
    assert loaded["mkt-01"] == 55
