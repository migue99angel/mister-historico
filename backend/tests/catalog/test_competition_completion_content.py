"""Sourced competition slots and qualifying positions of synthetic Test FC."""

import shutil
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from tests.catalog.test_content_tree import FIXTURE_ROOT, OWN, SEASON, assert_issue, edit, issues_of

from mister.catalog.infrastructure.content_schema import load_content_tree
from mister.catalog.infrastructure.content_schema.competitions import KnockoutCalendar

SOURCE = "https://example.org/test-content/competition-completion"
STANDINGS = f"{SEASON}/standings.yaml"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(FIXTURE_ROOT, target)
    return target


def test_unknown_pending_and_known_empty_slots_remain_distinct() -> None:
    pending = KnockoutCalendar.model_validate(
        {"competition": "copa-test", "slots": None, "sources": [], "verify": "pending"}
    )
    empty = KnockoutCalendar.model_validate(
        {"competition": "copa-test", "slots": [], "sources": [SOURCE], "verify": "ok"}
    )
    assert pending.slots is None
    assert empty.slots == ()
    with pytest.raises(ValidationError):
        KnockoutCalendar.model_validate(
            {"competition": "copa-test", "slots": None, "sources": [SOURCE], "verify": "ok"}
        )


def test_synthetic_calendar_and_entries_preserve_existing_history(root: Path) -> None:
    actual = load_content_tree(root, release=True).seasons[OWN]
    assert actual.standings.knockout_calendar is not None
    assert [len(c.slots or ()) for c in actual.standings.knockout_calendar] == [5, 1, 1]
    assert actual.standings.group_entry_assignments is not None
    entries = actual.standings.group_entry_assignments[0].entries
    assert entries is not None
    assert [(e.qualifying_position, e.historical_representative) for e in entries] == [
        (1, OWN),
        (2, "overseas-fc-2000-01"),
    ]
    assert [len(e.schedule) for e in actual.standings.head_to_head or ()] == [30, 12]


@pytest.mark.parametrize("field", ["knockout_calendar", "group_entry_assignments"])
def test_unknown_completion_is_development_only_when_paths_require_it(
    root: Path, field: str
) -> None:
    edit(root, STANDINGS, lambda d: d.update({field: None}))
    load_content_tree(root, release=False)
    assert_issue(issues_of(root, release=True), STANDINGS, field, "required")


def test_reapplication_rule_must_be_explicit_and_verified_for_direct_group_criteria(
    root: Path,
) -> None:
    edit(
        root,
        f"{SEASON}/season.yaml",
        lambda d: d["competitions"][3]["stages"][0].update(reapply_head_to_head=None),
    )
    load_content_tree(root, release=False)
    assert_issue(
        issues_of(root, release=True), f"{SEASON}/season.yaml", "reapply_head_to_head", "explicit"
    )


@pytest.mark.parametrize("value", [False, True])
def test_both_sourced_reapplication_policies_can_ship(root: Path, value: bool) -> None:
    edit(
        root,
        f"{SEASON}/season.yaml",
        lambda d: d["competitions"][3]["stages"][0].update(
            reapply_head_to_head={"value": value, "sources": [SOURCE], "verify": "ok"}
        ),
    )
    load_content_tree(root, release=True)


@pytest.mark.parametrize("field", ["date", "venue"])
def test_missing_slot_date_or_venue_stays_null_and_pending(root: Path, field: str) -> None:
    edit(
        root,
        STANDINGS,
        lambda d: d["knockout_calendar"][0]["slots"][0].update({field: None, "verify": "pending"}),
    )
    load_content_tree(root, release=False)
    assert_issue(issues_of(root, release=True), STANDINGS, "verify", "pending")


@pytest.mark.parametrize(
    "change",
    [
        {"home": OWN, "away": OWN},
        {"stage_id": "missing"},
        {"home": "ghost-2000-01"},
        {"date": date(2002, 1, 1)},
        {"venue": "neutral"},
        {"leg": 2},
    ],
)
def test_invalid_or_conflicting_historical_slot_is_rejected(
    root: Path, change: dict[str, Any]
) -> None:
    edit(root, STANDINGS, lambda d: d["knockout_calendar"][0]["slots"][0].update(change))
    assert_issue(issues_of(root), STANDINGS, "knockout_calendar")


def test_two_legs_require_inverted_sides_and_increasing_dates(root: Path) -> None:
    def invalid(data: dict[str, Any]) -> None:
        slots = data["knockout_calendar"][0]["slots"]
        pair = [
            s for s in slots if s["stage_id"] == "semifinal" and OWN not in (s["home"], s["away"])
        ]
        pair[1].update(home=pair[0]["home"], away=pair[0]["away"], date=pair[0]["date"])

    edit(root, STANDINGS, invalid)
    assert_issue(issues_of(root), STANDINGS, "knockout_calendar", "legs")


def test_verified_calendar_cannot_omit_an_external_historical_leg(root: Path) -> None:
    def omit(data: dict[str, Any]) -> None:
        slots = data["knockout_calendar"][0]["slots"]
        index = next(
            i
            for i, s in enumerate(slots)
            if s["stage_id"] == "semifinal" and OWN not in (s["home"], s["away"])
        )
        slots.pop(index)

    edit(root, STANDINGS, omit)
    assert_issue(issues_of(root), STANDINGS, "knockout_calendar", "legs")


def test_duplicate_slot_ids_are_rejected_globally(root: Path) -> None:
    edit(
        root,
        STANDINGS,
        lambda d: d["knockout_calendar"][1]["slots"][0].update(
            fixture_id=d["knockout_calendar"][0]["slots"][0]["fixture_id"]
        ),
    )
    assert_issue(issues_of(root), STANDINGS, "knockout_calendar", "fixture")


def test_knockout_ids_cannot_reuse_a_head_to_head_identity(root: Path) -> None:
    edit(
        root,
        STANDINGS,
        lambda d: d["knockout_calendar"][0]["slots"][0].update(
            fixture_id=d["head_to_head"][0]["schedule"][0]["fixture_id"]
        ),
    )
    assert_issue(issues_of(root), STANDINGS, "knockout_calendar", "fixture")


@pytest.mark.parametrize(
    "change",
    [
        {"qualifying_position": 3},
        {"qualifying_position": True},
        {"group_id": "unknown"},
        {"source_stage_id": "final"},
        {"target_stage_id": "groups"},
        {"historical_representative": "abroad-athletic-2000-01"},
    ],
)
def test_entry_must_match_a_qualified_final_group_position_and_unique_target(
    root: Path, change: dict[str, Any]
) -> None:
    edit(root, STANDINGS, lambda d: d["group_entry_assignments"][0]["entries"][0].update(change))
    assert_issue(issues_of(root), STANDINGS, "group_entry_assignments")


def test_duplicate_qualifying_position_is_rejected(root: Path) -> None:
    edit(
        root,
        STANDINGS,
        lambda d: d["group_entry_assignments"][0]["entries"].append(
            deepcopy(d["group_entry_assignments"][0]["entries"][0])
        ),
    )
    assert_issue(issues_of(root), STANDINGS, "group_entry_assignments", "duplicate")


def test_release_needs_every_qualifying_position_not_only_the_managed_club(root: Path) -> None:
    edit(root, STANDINGS, lambda d: d["group_entry_assignments"][0]["entries"].pop())
    load_content_tree(root, release=False)
    assert_issue(issues_of(root, release=True), STANDINGS, "group_entry_assignments", "position")


def test_unknown_third_party_venue_is_never_replaced_by_home(root: Path) -> None:
    def unknown(data: dict[str, Any]) -> None:
        target = next(
            f for f in data["head_to_head"][1]["schedule"] if OWN not in (f["home"], f["away"])
        )
        target.update(venue=None, verify="pending")

    edit(root, STANDINGS, unknown)
    actual = load_content_tree(root, release=False).seasons[OWN].standings.head_to_head
    assert actual is not None
    assert any(f.venue is None for f in actual[1].schedule)
    assert_issue(issues_of(root, release=True), STANDINGS, "verify", "pending")


def test_known_direct_venue_cannot_contradict_a_managed_fixture(root: Path) -> None:
    edit(root, STANDINGS, lambda d: d["head_to_head"][0]["schedule"][0].update(venue="neutral"))
    assert_issue(issues_of(root), STANDINGS, "head_to_head", "venue")


@pytest.mark.parametrize("managed_home", [True, False])
def test_neutral_managed_group_fixture_uses_explicit_calendar_orientation(
    root: Path, managed_home: bool
) -> None:
    def neutral_fixtures(data: dict[str, Any]) -> None:
        next(f for f in data["fixtures"] if f["id"] == "tfc-cont-g2")["venue"] = "neutral"

    def neutral_evidence(data: dict[str, Any]) -> None:
        history = data["head_to_head"][1]
        slot = next(f for f in history["schedule"] if f["fixture_id"] == "tfc-cont-g2")
        slot.update(
            venue="neutral",
            home=OWN if managed_home else "abroad-athletic-2000-01",
            away="abroad-athletic-2000-01" if managed_home else OWN,
        )
        next(r for r in history["results"] if r["fixture_id"] == "tfc-cont-g2")["score"] = (
            [1, 2] if managed_home else [2, 1]
        )

    edit(root, f"{SEASON}/fixtures.yaml", neutral_fixtures)
    edit(root, STANDINGS, neutral_evidence)
    load_content_tree(root, release=True)


def test_complete_historical_slots_remain_available_beyond_real_elimination(root: Path) -> None:
    def earlier_elimination(data: dict[str, Any]) -> None:
        data["fixtures"] = [f for f in data["fixtures"] if f["id"] != "tfc-copa-final"]
        for fixture in data["fixtures"]:
            if fixture["id"] in ("tfc-copa-sf-1", "tfc-copa-sf-2"):
                fixture["result"].update(goals_for=0, goals_against=1)

    def history(data: dict[str, Any]) -> None:
        semi = next(
            t
            for t in data["ties"]
            if t["competition"] == "copa-test" and t["stage"] == "semifinal" and OWN in t["clubs"]
        )
        semi.update(winner="placeholder-town-2000-01", aggregate="0-2")
        final = next(
            t for t in data["ties"] if t["competition"] == "copa-test" and t["stage"] == "final"
        )
        final.update(
            clubs=["placeholder-town-2000-01", "sample-united-2000-01"],
            winner="sample-united-2000-01",
            aggregate="0-1",
        )
        slot = next(s for s in data["knockout_calendar"][0]["slots"] if s["stage_id"] == "final")
        slot.update(
            fixture_id="external-test-final", home="placeholder-town-2000-01", sources=[SOURCE]
        )

    def outcome(data: dict[str, Any]) -> None:
        next(o for o in data["historical_outcome"] if o["competition"] == "copa-test").update(
            champion=False, eliminated_in="semifinal"
        )

    edit(root, f"{SEASON}/fixtures.yaml", earlier_elimination)
    edit(root, STANDINGS, history)
    edit(root, f"{SEASON}/season.yaml", outcome)
    content = load_content_tree(root, release=True).seasons[OWN]
    assert content.standings.knockout_calendar is not None
    final = next(
        s for s in content.standings.knockout_calendar[0].slots or () if s.stage_id == "final"
    )
    assert OWN not in (final.home, final.away)
    assert final.date == date(2001, 5, 26)


def test_destination_must_follow_every_feeding_predecessor_tie(root: Path) -> None:
    def late_origins(data: dict[str, Any]) -> None:
        external = [
            s
            for s in data["knockout_calendar"][0]["slots"]
            if s["stage_id"] == "semifinal" and OWN not in (s["home"], s["away"])
        ]
        for slot in external:
            slot["date"] = date(2001, 5, 26 + slot["leg"])

    edit(root, STANDINGS, late_origins)
    assert_issue(issues_of(root, release=True), STANDINGS, "knockout_calendar", "predecessor")


def test_group_entry_target_cannot_add_unqualified_historical_contenders(root: Path) -> None:
    def extra_final(data: dict[str, Any]) -> None:
        clubs = ["abroad-athletic-2000-01", "faraway-city-2000-01"]
        data["ties"].append(
            {
                "competition": "copa-continental-test",
                "stage": "final",
                "clubs": clubs,
                "winner": clubs[0],
                "sources": [SOURCE],
                "verify": "ok",
            }
        )
        slot = deepcopy(data["knockout_calendar"][2]["slots"][0])
        slot.update(fixture_id="unqualified-final", home=clubs[0], away=clubs[1], sources=[SOURCE])
        data["knockout_calendar"][2]["slots"].append(slot)

    edit(root, STANDINGS, extra_final)
    assert_issue(issues_of(root, release=True), STANDINGS, "group_entry_assignments", "exactly")


def test_group_target_may_precede_cutoff_when_calendar_proves_group_finished(root: Path) -> None:
    def early(data: dict[str, Any]) -> None:
        next(f for f in data["fixtures"] if f["id"] == "tfc-cont-final")["date"] = date(2001, 1, 30)

    edit(root, f"{SEASON}/fixtures.yaml", early)
    edit(
        root,
        STANDINGS,
        lambda d: d["knockout_calendar"][2]["slots"][0].update(date=date(2001, 1, 30)),
    )
    load_content_tree(root, release=True)


def test_group_target_cannot_precede_the_last_accredited_group_match(root: Path) -> None:
    day = date(2000, 12, 18)
    edit(
        root,
        f"{SEASON}/fixtures.yaml",
        lambda d: next(f for f in d["fixtures"] if f["id"] == "tfc-cont-final").update(date=day),
    )
    edit(root, STANDINGS, lambda d: d["knockout_calendar"][2]["slots"][0].update(date=day))

    def postpone_external(data: dict[str, Any]) -> None:
        external = max(
            (f for f in data["head_to_head"][1]["schedule"] if OWN not in (f["home"], f["away"])),
            key=lambda f: f["date"],
        )
        external["date"] = date(2000, 12, 20)

    edit(root, STANDINGS, postpone_external)
    assert_issue(issues_of(root, release=True), STANDINGS, "group_entry_assignments", "group match")


def general_criteria(data: dict[str, Any]) -> None:
    for competition in data["competitions"]:
        if competition["kind"] == "league":
            competition["tiebreakers"] = ["goal_difference"]
        for stage in competition.get("stages", []):
            if stage["round"] == "group_stage":
                stage["tiebreakers"] = ["goal_difference"]


def test_an_earlier_final_table_can_accredit_group_completion_without_a_calendar(
    root: Path,
) -> None:
    edit(root, f"{SEASON}/season.yaml", general_criteria)
    edit(root, STANDINGS, lambda d: d.update(head_to_head=None))
    load_content_tree(root, release=True)


def test_a_later_table_without_complete_calendar_cannot_accredit_earlier_group_completion(
    root: Path,
) -> None:
    edit(root, f"{SEASON}/season.yaml", general_criteria)
    edit(root, STANDINGS, lambda d: d.update(head_to_head=None))
    day = date(2001, 1, 30)
    edit(
        root,
        f"{SEASON}/fixtures.yaml",
        lambda d: next(f for f in d["fixtures"] if f["id"] == "tfc-cont-final").update(date=day),
    )
    edit(root, STANDINGS, lambda d: d["knockout_calendar"][2]["slots"][0].update(date=day))
    assert_issue(
        issues_of(root, release=True),
        STANDINGS,
        "group_entry_assignments",
        "insufficient calendar evidence",
    )


def test_independent_branches_may_overlap_rounds_when_each_feeder_finishes_first(
    root: Path,
) -> None:
    additions = [
        "demo-athletic-2000-01",
        "dummy-rovers-2000-01",
        "fixture-wanderers-2000-01",
        "overseas-fc-2000-01",
    ]
    pairs = [
        (OWN, additions[0], OWN, date(2000, 8, 25)),
        ("placeholder-town-2000-01", additions[1], "placeholder-town-2000-01", date(2000, 10, 1)),
        ("sample-united-2000-01", additions[2], "sample-united-2000-01", date(2000, 12, 10)),
        ("mock-city-2000-01", additions[3], "mock-city-2000-01", date(2000, 12, 15)),
    ]

    def format_change(data: dict[str, Any]) -> None:
        cup = data["competitions"][1]
        cup["participants"].extend(additions)
        cup["stages"].insert(
            0,
            {
                "id": "quarterfinal",
                "name": "Test quarterfinal",
                "round": "quarter_final",
                "legs": 1,
                "away_goals_rule": False,
                "extra_time": False,
                "penalties": False,
            },
        )

    def calendar(data: dict[str, Any]) -> None:
        for index, (home, away, winner, day) in enumerate(pairs):
            data["ties"].append(
                {
                    "competition": "copa-test",
                    "stage": "quarterfinal",
                    "clubs": [home, away],
                    "winner": winner,
                    "sources": [SOURCE],
                    "verify": "ok",
                }
            )
            data["knockout_calendar"][0]["slots"].append(
                {
                    "fixture_id": f"test-quarter-{index}",
                    "stage_id": "quarterfinal",
                    "home": home,
                    "away": away,
                    "date": day,
                    "venue": "home",
                    "leg": None,
                    "sources": [SOURCE],
                    "verify": "ok",
                }
            )
        external = next(
            s
            for s in data["knockout_calendar"][0]["slots"]
            if s["fixture_id"] == "copa-test-external-sf-1"
        )
        external["date"] = date(2000, 12, 20)

    def managed(data: dict[str, Any]) -> None:
        data["fixtures"].append(
            {
                "id": "test-quarter-0",
                "competition": "copa-test",
                "stage": "quarterfinal",
                "date": date(2000, 8, 25),
                "opponent": additions[0],
                "venue": "home",
                "result": {"goals_for": 2, "goals_against": 0},
                "sources": [SOURCE],
                "verify": "ok",
            }
        )

    edit(root, f"{SEASON}/season.yaml", format_change)
    edit(root, STANDINGS, calendar)
    edit(root, f"{SEASON}/fixtures.yaml", managed)
    load_content_tree(root, release=True)


def test_group_assignments_cannot_skip_an_unaccredited_first_knockout_stage(root: Path) -> None:
    def add_stage(data: dict[str, Any]) -> None:
        stages = data["competitions"][3]["stages"]
        stages.insert(1, {"id": "semifinal", "name": "Synthetic semifinal", "round": "semi_final", "legs": 1, "away_goals_rule": False, "extra_time": False, "penalties": False})
    def add_history(data: dict[str, Any]) -> None:
        pairs = [(OWN, "abroad-athletic-2000-01"), ("overseas-fc-2000-01", "faraway-city-2000-01")]
        for index, (home, away) in enumerate(pairs):
            data["ties"].append({"competition": "copa-continental-test", "stage": "semifinal", "clubs": [home, away], "winner": home, "sources": [SOURCE], "verify": "ok"})
            data["knockout_calendar"][2]["slots"].append({"fixture_id": f"continental-semi-{index}", "stage_id": "semifinal", "date": date(2001, 2, 15), "home": home, "away": away, "venue": "home", "leg": None, "sources": [SOURCE], "verify": "ok"})
    def add_managed(data: dict[str, Any]) -> None:
        data["fixtures"].append({"id": "continental-semi-0", "date": date(2001, 2, 15), "competition": "copa-continental-test", "stage": "semifinal", "opponent": "abroad-athletic-2000-01", "venue": "home", "result": {"goals_for": 1, "goals_against": 0}, "sources": [SOURCE], "verify": "ok"})
    edit(root, f"{SEASON}/season.yaml", add_stage)
    edit(root, STANDINGS, add_history)
    edit(root, f"{SEASON}/fixtures.yaml", add_managed)
    assert_issue(issues_of(root, release=True), STANDINGS, "group_entry_assignments", "exactly")
