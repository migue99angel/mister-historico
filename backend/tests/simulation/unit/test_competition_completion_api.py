"""Explicit competition completion contracts for synthetic Test FC scenarios."""

from dataclasses import fields
from datetime import date
from typing import Any

import pytest

from mister.catalog.application import api as catalog
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.application import api

CLUBS = tuple(
    ClubSeasonId(name + "-2000-01")
    for name in ("test-fc", "sample-united", "mock-city", "demo-athletic")
)
COMP = CompetitionId("liga-test")
DAY = date(2000, 9, 30)


def table(unresolved: Any = None) -> api.StandingsDTO:
    rows = tuple(api.StandingRowDTO(c, i + 1, 0, 0, 0, 0, 0, 0, 0) for i, c in enumerate(CLUBS))
    return api.StandingsDTO(COMP, DAY, rows, unresolved_ties=unresolved)


def test_unresolved_information_distinguishes_unknown_from_evaluated_empty() -> None:
    assert table().unresolved_ties is None
    assert table(()).unresolved_ties == ()
    assert table(((CLUBS[0], CLUBS[1]),)).rows[0].position == 1


@pytest.mark.parametrize(
    "bad",
    [
        [],
        ((),),
        ((CLUBS[0],),),
        ((CLUBS[0], CLUBS[0]),),
        ((CLUBS[0], CLUBS[2]),),
        ((CLUBS[0], CLUBS[1]), (CLUBS[1], CLUBS[2])),
        ((CLUBS[0], ClubSeasonId("missing-2000-01")),),
        (("test-fc-2000-01", CLUBS[1]),),
    ],
)
def test_unresolved_groups_are_immutable_disjoint_distinct_contiguous_and_present(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        table(bad)


def test_multiple_separate_unresolved_groups_preserve_presentation_order() -> None:
    assert table((CLUBS[:2], CLUBS[2:])).unresolved_ties == (CLUBS[:2], CLUBS[2:])


def test_legacy_construction_leaves_new_contract_inputs_unknown() -> None:
    assert (
        api.StageInput("groups", "group_stage", 2, False, False, False).reapply_head_to_head is None
    )
    assert catalog.GroupStageDTO((), 3, 1, (), 2).reapply_head_to_head is None
    season = api.SeasonSimInput(CLUBS[0], (), (), ())
    assert season.knockout_calendar is None
    assert season.group_entry_assignments is None
    assert api.BlockSummaryDTO(BlockId("b1")).unresolved_knockout_ties is None
    assert fields(catalog.PlayableSeasonDTO)[-1].name == "group_entry_assignments"


def test_both_contexts_own_equivalent_independent_sourced_completion_types() -> None:
    for name in (
        "KnockoutSlot",
        "KnockoutCalendar",
        "GroupEntryAssignment",
        "GroupEntryAssignments",
    ):
        left, right = getattr(catalog, name + "DTO"), getattr(api, name + "Input")
        assert left is not right
        assert [f.name for f in fields(left)] == [f.name for f in fields(right)]


def test_known_empty_and_pending_calendars_preserve_sources_without_fabricating_slots() -> None:
    unknown = api.KnockoutCalendarInput(COMP, None, (), "pending")
    known = api.KnockoutCalendarInput(
        COMP, (), ("https://example.org/test-content/calendar",), "ok"
    )
    assert unknown.slots is None
    assert known.slots == ()


def test_unresolved_knockout_value_has_typed_distinct_clubs_and_unique_match_ids() -> None:
    actual = api.UnresolvedKnockoutTieDTO(COMP, "final", CLUBS[:2], (FixtureId("test-final"),))
    assert actual.clubs == CLUBS[:2]
    assert not hasattr(actual, "sources")


@pytest.mark.parametrize(
    ("clubs", "ids"),
    [
        (CLUBS[:1], (FixtureId("test-final"),)),
        ((CLUBS[0], CLUBS[0]), (FixtureId("test-final"),)),
        (CLUBS[:2], ()),
        (CLUBS[:2], (FixtureId("same"), FixtureId("same"))),
        (CLUBS[:2], ("untyped",)),
    ],
)
def test_invalid_unresolved_knockout_identity_is_rejected(clubs: Any, ids: Any) -> None:
    with pytest.raises(InvalidValueError):
        api.UnresolvedKnockoutTieDTO(COMP, "final", clubs, ids)
