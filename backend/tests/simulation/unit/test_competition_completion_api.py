"""Explicit competition completion contracts for synthetic Test FC scenarios."""

from dataclasses import fields, replace
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


def second_leg() -> api.MatchResultDTO:
    return api.MatchResultDTO(
        FixtureId("second-leg"),
        COMP,
        DAY,
        CLUBS[1],
        CLUBS[0],
        (1, 2),
        "away",
        CLUBS[1],
        "win",
        winner="away",
        stage_id="semifinal",
        leg=2,
    )


def test_exhausted_tie_can_span_blocks_and_have_an_individual_second_leg_winner() -> None:
    tie = api.UnresolvedKnockoutTieDTO(
        COMP, "semifinal", CLUBS[:2], (FixtureId("first-leg"), FixtureId("second-leg"))
    )
    summary = api.BlockSummaryDTO(
        BlockId("b2"), results=(second_leg(),), unresolved_knockout_ties=(tie,)
    )
    assert summary.unresolved_knockout_ties == (tie,)
    assert summary.results[0].winner == "away"
    assert (
        api.BlockSummaryDTO(BlockId("b2"), unresolved_knockout_ties=()).unresolved_knockout_ties
        == ()
    )


@pytest.mark.parametrize("bad", [[], ("untyped",)])
def test_unresolved_knockout_collection_requires_immutable_typed_values(bad: Any) -> None:
    with pytest.raises(InvalidValueError):
        api.BlockSummaryDTO(BlockId("b2"), unresolved_knockout_ties=bad)


@pytest.mark.parametrize(
    "change",
    [{"competition_id": CompetitionId("other")}, {"stage_id": "final"}, {"home": CLUBS[2]}],
)
def test_present_results_must_match_unresolved_knockout_identity(change: dict[str, Any]) -> None:
    tie = api.UnresolvedKnockoutTieDTO(
        COMP, "semifinal", CLUBS[:2], (FixtureId("first-leg"), FixtureId("second-leg"))
    )
    with pytest.raises(InvalidValueError):
        api.BlockSummaryDTO(
            BlockId("b2"),
            results=(replace(second_leg(), **change),),
            unresolved_knockout_ties=(tie,),
        )


def test_unresolved_knockout_collection_cannot_repeat_fixtures_or_stage_participants() -> None:
    first = api.UnresolvedKnockoutTieDTO(COMP, "semifinal", CLUBS[:2], (FixtureId("first"),))
    second = api.UnresolvedKnockoutTieDTO(
        COMP, "semifinal", (CLUBS[0], CLUBS[2]), (FixtureId("second"),)
    )
    for pair in ((first, first), (first, second)):
        with pytest.raises(InvalidValueError):
            api.BlockSummaryDTO(BlockId("b2"), unresolved_knockout_ties=pair)


@pytest.mark.parametrize(("competition", "stage"), [("untyped", "final"), (COMP, ""), (COMP, True)])
def test_unresolved_knockout_scope_requires_a_typed_competition_and_nonblank_stage(
    competition: Any, stage: Any
) -> None:
    with pytest.raises(InvalidValueError):
        api.UnresolvedKnockoutTieDTO(competition, stage, CLUBS[:2], (FixtureId("final"),))


def test_swapped_positions_contract_oracle_transforms_both_final_occupants() -> None:
    # Synthetic oracle for the future connector, not block simulation.
    historical = api.KnockoutSlotInput(
        FixtureId("test-final"),
        "final",
        DAY,
        CLUBS[0],
        CLUBS[1],
        "neutral",
        None,
        ("https://example.org/test-content/calendar",),
        "ok",
    )
    occupants = {CLUBS[0]: CLUBS[1], CLUBS[1]: CLUBS[0]}
    effective = replace(
        historical, home=occupants[historical.home], away=occupants[historical.away]
    )
    assert (effective.home, effective.away) == (CLUBS[1], CLUBS[0])
    assert effective.home != effective.away
    assert (effective.fixture_id, effective.date, effective.venue) == (
        historical.fixture_id,
        DAY,
        "neutral",
    )


def test_mixed_semifinal_oracle_updates_both_surviving_slot_occupants() -> None:
    # Historical semis Test-Mock and Sample-Demo were won by Test and Sample.
    # Positions swapped Test/Sample: Sample advances externally via Test's
    # historical slot, while Demo beats managed Test via Sample's slot.
    historical = api.KnockoutSlotInput(
        FixtureId("test-final"),
        "final",
        DAY,
        CLUBS[0],
        CLUBS[1],
        "neutral",
        None,
        ("https://example.org/test-content/calendar",),
        "ok",
    )
    surviving = {CLUBS[0]: CLUBS[1], CLUBS[1]: CLUBS[3]}
    effective = replace(
        historical, home=surviving[historical.home], away=surviving[historical.away]
    )
    assert (effective.home, effective.away) == (CLUBS[1], CLUBS[3])
    assert len(set(surviving.values())) == len(surviving)
    assert CLUBS[0] not in surviving.values()
    assert effective.fixture_id == historical.fixture_id


def test_block_request_appends_optional_state_date_without_inferring_it_from_results() -> None:
    season = api.SeasonSimInput(CLUBS[0], (), (), ())
    team = api.SquadTeamInput(CLUBS[0], (), api.TacticDTO("balanced", "4-4-2"))
    request = api.BlockSimRequest(
        season, BlockId("b2"), DAY, DAY, team, prior_results=(second_leg(),)
    )
    field_names = [field.name for field in fields(api.BlockSimRequest)]
    assert field_names[:10] == [
        "season",
        "block_id",
        "start",
        "end",
        "managed_team",
        "team_morale",
        "team_overrides",
        "competition_priorities",
        "forced_injuries_from_effects",
        "prior_results",
    ]
    assert field_names[-3:] == ["state_as_of", "squad_memberships", "player_pool"]
    assert request.state_as_of is None
    assert request.squad_memberships is None
    assert request.player_pool is None


def test_continuation_request_preserves_the_explicit_previous_state_date() -> None:
    season = api.SeasonSimInput(CLUBS[0], (), (), ())
    team = api.SquadTeamInput(CLUBS[0], (), api.TacticDTO("balanced", "4-4-2"))
    previous_close = date(2000, 9, 29)
    request = api.BlockSimRequest(season, BlockId("b2"), DAY, DAY, team, state_as_of=previous_close)
    assert request.state_as_of == previous_close
