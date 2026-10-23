"""The calibration anchors (T1.7b): real player-seasons whose band the author knows.

They live in `content/anchors/` as market squads (one per season), so the same schema and the
same `mister content ratings compute` CLI apply. These tests read only that folder.
"""

import re
from pathlib import Path

import pytest
import yaml

from mister.catalog.application.ratings_tool import RatingsTool
from mister.catalog.domain.ratings import (
    AwardTier,
    ClubContext,
    LevelTier,
    PlayerStats,
    Position,
    compute_rating,
)
from mister.catalog.infrastructure.content_schema.rating_sheets import YamlRatingSheetStore

pytestmark = pytest.mark.content

ANCHORS_ROOT = Path(__file__).resolve().parents[4] / "content" / "anchors"
EXPECTED_ANCHORS = 24
KNOWN_KEY_GAPS = {
    "thierry-henry": 5,
    "diego-forlan": 1,
    "alvaro-negredo": -4,
    "gorka-iraizoz": -2,
    "juan-arango": 2,
    "aritz-aduriz": -6,
}
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


def _declared() -> list[dict[str, object]]:
    bands = ANCHORS_ROOT / "bands.yaml"
    return list(yaml.safe_load(bands.read_text(encoding="utf-8"))["anchors"])


def test_the_key_flag_of_bands_matches_the_squad_files() -> None:
    in_squads = {}
    for path in _squad_files():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for player in data["players"]:
            in_squads[(path.parent.name, player["player_id"])] = player["key"]

    declared = {(a["club_season"], a["player_id"]): a["key"] for a in _declared()}

    assert declared == in_squads


def test_only_key_anchors_carry_a_rating_override() -> None:
    for path in _squad_files():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for player in data["players"]:
            if player.get("rating_override") is not None:
                assert player["key"], player["player_id"]


def test_every_override_is_within_the_limits_of_the_rubric() -> None:
    tool = RatingsTool(YamlRatingSheetStore(ANCHORS_ROOT))
    for club_season in _squad_ids():
        assert not tool.check(club_season).problems


@pytest.mark.parametrize(
    ("club_season", "player_id"),
    [("_market-2004-05", "diego-forlan"), ("_market-2010-11", "alvaro-negredo")],
)
def test_press_scoring_trophies_do_not_count_as_official_league_awards(
    club_season: str, player_id: str
) -> None:
    """Pichichi and Zarra are MARCA trophies, outside the official league tier of rubric 2.1."""
    tool = RatingsTool(YamlRatingSheetStore(ANCHORS_ROOT))

    result = tool.explain(club_season, player_id).result

    assert result.components is not None
    assert result.components.awards == 0


def _gap(rating: int, band: str) -> int:
    low, high = (int(part) for part in band.split("-"))
    return min(0, rating - low) or max(0, rating - high)


def test_the_formula_alone_meets_the_calibration_criterion_for_non_key_anchors() -> None:
    """Rubric section 9: at most 1 in 5 outside the band and none more than 5 points away."""
    tool = RatingsTool(YamlRatingSheetStore(ANCHORS_ROOT))
    gaps = []
    for anchor in _declared():
        if anchor["key"]:
            continue
        line = tool.explain(str(anchor["club_season"]), str(anchor["player_id"]))
        assert line.result.rating is not None
        gaps.append(_gap(line.result.rating, str(anchor["band"])))

    assert gaps
    assert sum(gap != 0 for gap in gaps) <= len(gaps) / 5
    assert max(abs(gap) for gap in gaps) <= 5


def test_the_documented_league_clean_sheet_example_matches_the_formula() -> None:
    """Check the published synthetic example, including the fallback to league data."""
    rubric = ANCHORS_ROOT.parents[1] / "docs" / "content" / "rating-rubric.md"
    section = rubric.read_text(encoding="utf-8").split("### 10.4 ")[1].split("### 10.5 ")[0]
    documented = re.search(r"la media sería \*\*(\d+)\*\*", section)
    assert documented is not None
    goalkeeper = PlayerStats(
        position=Position.GK,
        age=27,
        minutes_league=3420,
        starts_league=38,
        appearances_league=38,
        minutes_all=4900,
        starts_all=54,
        appearances_all=54,
        goals_all=0,
        clean_sheets_all=None,
        clean_sheets_league=20,
        caps=3,
        awards=(AwardTier.L,),
    )
    club = ClubContext(club_matches_all=55, club_matches_league=38, level_tier=LevelTier.A)

    assert int(documented.group(1)) == compute_rating(goalkeeper, club).rating


def test_provisional_calibration_has_exactly_the_documented_unresolved_key_gaps() -> None:
    """The accepted limitations must not hide any new or changed historical discrepancy."""
    tool = RatingsTool(YamlRatingSheetStore(ANCHORS_ROOT))
    failures = {}
    for anchor in _declared():
        if not anchor["key"]:
            continue
        line = tool.explain(str(anchor["club_season"]), str(anchor["player_id"]))
        assert line.expected is not None
        gap = _gap(line.expected, str(anchor["band"]))
        if gap:
            failures[str(anchor["player_id"])] = gap

    assert failures == KNOWN_KEY_GAPS


@pytest.mark.calibration
@pytest.mark.parametrize(
    "anchor",
    [
        pytest.param(
            anchor,
            id=str(anchor["player_id"]),
            marks=(
                pytest.mark.xfail(
                    strict=True,
                    raises=AssertionError,
                    reason=(
                        f"Accepted provisional gap {KNOWN_KEY_GAPS[str(anchor['player_id'])]:+d}; "
                        "docs/calibration/anchors.md#pendientes-históricos"
                    ),
                )
                if anchor["player_id"] in KNOWN_KEY_GAPS
                else ()
            ),
        )
        for anchor in _declared()
        if anchor["key"]
    ],
)
def test_reviewed_key_anchor_meets_its_declared_band(anchor: dict[str, object]) -> None:
    """Expose each historical failure as strict xfail, never as a successful calibration."""
    tool = RatingsTool(YamlRatingSheetStore(ANCHORS_ROOT))
    line = tool.explain(str(anchor["club_season"]), str(anchor["player_id"]))
    assert line.expected is not None

    assert _gap(line.expected, str(anchor["band"])) == 0
