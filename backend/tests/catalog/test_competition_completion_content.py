"""Sourced competition slots and qualifying positions of synthetic Test FC."""

import shutil
from copy import deepcopy
from datetime import date, timedelta
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
