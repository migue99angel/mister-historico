"""The calibration anchors (T1.7b): real player-seasons whose band the author knows.

They live in `content/anchors/` as market squads (one per season), so the same schema and the
same `mister content ratings compute` CLI apply. These tests read only that folder.
"""

from pathlib import Path

import pytest
import yaml

from mister.catalog.application.ratings_tool import RatingsTool
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore

pytestmark = pytest.mark.content

ANCHORS_ROOT = Path(__file__).resolve().parents[4] / "content" / "anchors"
EXPECTED_ANCHORS = 24
PLAYABLE_CLUB_SEASONS = {
    ("Valencia CF", "2003-04"),
    ("Sevilla FC", "2005-06"),
    ("FC Barcelona", "2008-09"),
    ("Real Madrid CF", "2012-13"),
    ("Atlético de Madrid", "2013-14"),
}


def _squad_files() -> list[Path]:
    return sorted((ANCHORS_ROOT / "club-seasons").glob("*/squad.yaml"))


def _squad_ids() -> list[str]:
    return [path.parent.name for path in _squad_files()]


def test_every_anchor_squad_validates_against_the_content_schema() -> None:
    assert _squad_ids(), "no anchor squads found"
    store = YamlRatingSheetStore(ANCHORS_ROOT)
    for club_season in _squad_ids():
        store.load(club_season)  # raises if the squad does not validate


def test_there_are_twenty_four_anchors() -> None:
    store = YamlRatingSheetStore(ANCHORS_ROOT)
    total = sum(len(store.load(club_season).players) for club_season in _squad_ids())
    assert total == EXPECTED_ANCHORS


def test_no_anchor_comes_from_the_five_playable_seasons() -> None:
    found = set()
    for path in _squad_files():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for player in data["players"]:
            found.add((player["club_data"]["club_name"], data["season"]))
    assert not found & PLAYABLE_CLUB_SEASONS


def test_every_anchor_declares_its_band() -> None:
    bands = ANCHORS_ROOT / "bands.yaml"
    declared = yaml.safe_load(bands.read_text(encoding="utf-8"))["anchors"]
    stored = {
        (path.parent.name, player["player_id"])
        for path in _squad_files()
        for player in yaml.safe_load(path.read_text(encoding="utf-8"))["players"]
    }
    assert {(a["club_season"], a["player_id"]) for a in declared} == stored


def test_stored_ratings_equal_the_formula_for_every_anchor() -> None:
    tool = RatingsTool(YamlRatingSheetStore(ANCHORS_ROOT))
    for club_season in _squad_ids():
        report = tool.check(club_season)
        assert not report.discrepancies, [line.player_id for line in report.discrepancies]
