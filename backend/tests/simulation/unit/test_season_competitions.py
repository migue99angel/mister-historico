"""Cup lineage and complete group-position permutations on fictional sourced evidence."""

from dataclasses import replace
from datetime import date

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.application.api import (
    AggregateTeamInput, BlockSimRequest, CompetitionInput, FixtureInput,
    GroupEntryAssignmentInput, GroupEntryAssignmentsInput, GroupInput,
    HeadToHeadEvidenceInput, HeadToHeadFixtureInput, HeadToHeadResultInput,
    KnockoutCalendarInput, KnockoutSlotInput, RealResultInput, RealTieInput,
    StageInput, StandingRowDTO, StandingsDTO,
)
from mister.simulation.domain.model import MatchResult, MatchSetup, Score
from tests.simulation.unit.test_simulate_block import (
    END, ME, RIVAL, START, FixedMatches, continuation, play, request,
)

CUP = CompetitionId("copa-test")
OTHER = ClubSeasonId("demo-athletic-2000-01")
FOURTH = ClubSeasonId("mock-city-2000-01")
SOURCES = ("https://example.org/test-fc/competition",)
FINAL_DAY = date(2000, 9, 7)


def cup_request(*, legs: int = 2, deciding: bool = True) -> BlockSimRequest:
    value = request()
    stages = (
        StageInput("semi", "semi_final", legs, False, deciding, deciding),
        StageInput("final", "final", 1, False, deciding, deciding),
    )
    own = [FixtureInput(FixtureId("semi-1"), START, CUP, ME, RIVAL,
                        stage_id="semi", leg=1, real_result=RealResultInput(1, 0))]
    if legs == 2:
        own.append(FixtureInput(FixtureId("semi-2"), END, CUP, RIVAL, ME,
            stage_id="semi", leg=2, real_result=RealResultInput(0, 0)))
    own.append(FixtureInput(FixtureId("final"), FINAL_DAY, CUP, ME, OTHER,
        stage_id="final", venue="neutral", real_result=RealResultInput(1, 0)))
    slots = tuple(KnockoutSlotInput(f.fixture_id, f.stage_id or "", f.date, f.home, f.away,
        f.venue, f.leg, SOURCES, "ok") for f in own)
    external = tuple(KnockoutSlotInput(FixtureId(f"external-{leg}"), "semi",
        START if leg == 1 else END, OTHER if leg == 1 else FOURTH,
        FOURTH if leg == 1 else OTHER, "home", leg, SOURCES, "ok")
        for leg in range(1, legs + 1))
    competition = CompetitionInput(CUP, "cup", "domestic_cup", (ME, RIVAL, OTHER, FOURTH),
        1.2, 1.15, stages=stages, real_ties=(
            RealTieInput("semi", (ME, RIVAL), ME),
            RealTieInput("semi", (OTHER, FOURTH), OTHER),
            RealTieInput("final", (ME, OTHER), ME),
        ))
    season = replace(value.season, competitions=(competition,), fixtures=tuple(own),
        teams=(*value.season.teams, AggregateTeamInput(OTHER, 60, 60),
               AggregateTeamInput(FOURTH, 65, 65)), historical_standings=(),
        knockout_calendar=(KnockoutCalendarInput(CUP, (*slots, *external), SOURCES, "ok"),))
    return replace(value, season=season, end=FINAL_DAY)


class OwnWins(FixedMatches):
    def simulate(self, setup: MatchSetup, rng: object, *, decisive: bool = False) -> MatchResult:
        self.setups.append(setup)
        return MatchResult(Score(1, 0) if setup.fixture.home == ME else Score(0, 1))


class OwnLoses(OwnWins):
    def simulate(self, setup: MatchSetup, rng: object, *, decisive: bool = False) -> MatchResult:
        self.setups.append(setup)
        return MatchResult(Score(0, 1) if setup.fixture.home == ME else Score(1, 0))


def test_cup_progression_uses_stable_slots_and_marks_knockout_matches_key() -> None:
    summary = play(cup_request(), OwnWins())
    assert tuple(r.fixture_id for r in summary.results) == (
        FixtureId("semi-1"), FixtureId("semi-2"), FixtureId("final"))
    assert summary.results[-1].opponent == OTHER
    assert summary.results[-1].venue == "neutral"
    assert summary.key_matches == tuple(r.fixture_id for r in summary.results)
    assert tuple(e.kind for e in summary.events) == ("advanced", "champion")


def test_cup_second_leg_reconstructs_prior_prefix_without_repeating_events() -> None:
    value = cup_request()
    first = play(replace(value, end=START), OwnWins())
    second = play(continuation(value, first), OwnWins())
    whole = play(value, OwnWins())
    assert (*first.results, *second.results) == whole.results
    assert (*first.events, *second.events) == whole.events
    assert second.unresolved_knockout_ties == ()


def test_elimination_removes_later_managed_calendar_matches() -> None:
    summary = play(cup_request(), OwnLoses())
    assert tuple(r.fixture_id for r in summary.results) == (FixtureId("semi-1"), FixtureId("semi-2"))
    assert tuple(e.kind for e in summary.events) == ("eliminated",)


def test_exhausted_tie_without_deciding_rules_is_reported_without_champion() -> None:
    summary = play(cup_request(legs=1, deciding=False), FixedMatches(Score(0, 0)))
    assert len(summary.unresolved_knockout_ties or ()) == 1
    assert summary.unresolved_knockout_ties[0].fixture_ids == (FixtureId("semi-1"),)  # type: ignore[index]
    assert summary.events == ()
    assert len(summary.results) == 1


def test_extra_time_uses_120_real_minutes_and_recovered_pre_match_fitness() -> None:
    value = cup_request(legs=1)
    summary = play(replace(value, end=START), FixedMatches(Score(0, 0)))
    assert summary.results[0].extra_time == (0, 0)
    assert summary.results[0].penalties == (4, 3)
    assert sum(p.minutes_played for p in summary.player_states) == 11 * 120


def test_progression_beyond_historical_elimination_uses_calendar_slots() -> None:
    value = cup_request(legs=1)
    competition = replace(value.season.competitions[0], real_ties=(
        RealTieInput("semi", (ME, RIVAL), RIVAL),
        RealTieInput("semi", (OTHER, FOURTH), OTHER),
        RealTieInput("final", (RIVAL, OTHER), OTHER),
    ))
    assert value.season.knockout_calendar is not None
    calendar = value.season.knockout_calendar[0]
    assert calendar.slots is not None
    slots = tuple(replace(slot, home=RIVAL) if slot.stage_id == "final" else slot
                  for slot in calendar.slots)
    season = replace(value.season, competitions=(competition,),
        fixtures=(value.season.fixtures[0],),
        knockout_calendar=(replace(calendar, slots=slots),))
    summary = play(replace(value, season=season), OwnWins())
    assert summary.results[-1].fixture_id == FixtureId("final")
    assert summary.results[-1].home == ME
    assert summary.results[-1].opponent == OTHER


def group_request() -> BlockSimRequest:
    value = request()
    group = StageInput("groups", "group_stage", 1, False, False, False,
        groups=(GroupInput("a", (ME, RIVAL, OTHER, FOURTH)),),
        points_per_win=3, points_per_draw=1, tiebreakers=("goal_difference",),
        advance_per_group=2)
    final = StageInput("final", "final", 1, False, True, True)
    competition = CompetitionInput(CUP, "continental_cup", "continental_primary",
        (ME, RIVAL, OTHER, FOURTH), 1.2, 1.15, stages=(group, final),
        real_ties=(RealTieInput("final", (ME, RIVAL), ME),))
    pairs = ((ME, RIVAL, 1), (ME, OTHER, 2), (ME, FOURTH, 3),
             (RIVAL, OTHER, 1), (RIVAL, FOURTH, 2), (OTHER, FOURTH, 3))
    schedule = tuple(HeadToHeadFixtureInput(FixtureId(f"group-{i}"), date(2000, 9, day),
        home, away, SOURCES, "ok", "home") for i, (home, away, day) in enumerate(pairs))
    results = tuple(HeadToHeadResultInput(f.fixture_id, (1, 0), SOURCES, "ok") for f in schedule)
    own = tuple(FixtureInput(f.fixture_id, f.date, CUP, f.home, f.away,
        stage_id="groups", group_id="a", round=i+1, real_result=RealResultInput(1, 0))
        for i, f in enumerate(schedule[:3]))
    final_fixture = FixtureInput(FixtureId("group-final"), FINAL_DAY, CUP, ME, RIVAL,
        stage_id="final", venue="neutral", real_result=RealResultInput(1, 0))
    rows = tuple(StandingRowDTO(club, i+1, 3, 3-i, 0, i, 3-i, i, (3-i)*3)
                 for i, club in enumerate((ME, RIVAL, OTHER, FOURTH)))
    table = StandingsDTO(CUP, END, rows, "groups", "a")
    entries = tuple(GroupEntryAssignmentInput("groups", "a", i+1, "final", club,
        SOURCES, "ok") for i, club in enumerate((ME, RIVAL)))
    season = replace(value.season, teams=(*value.season.teams,
        AggregateTeamInput(OTHER, 65, 65), AggregateTeamInput(FOURTH, 60, 60)),
        competitions=(competition,), fixtures=(*own, final_fixture), historical_standings=(table,),
        head_to_head=(HeadToHeadEvidenceInput(CUP, END, (ME, RIVAL, OTHER, FOURTH),
            schedule, results, SOURCES, "ok", "groups", "a"),),
        knockout_calendar=(KnockoutCalendarInput(CUP, (KnockoutSlotInput(
            final_fixture.fixture_id, "final", FINAL_DAY, ME, RIVAL, "neutral", None,
            SOURCES, "ok"),), SOURCES, "ok"),),
        group_entry_assignments=(GroupEntryAssignmentsInput(CUP, entries, SOURCES, "ok"),))
    return replace(value, season=season, end=FINAL_DAY)


class SwapGroupPositions(OwnWins):
    def simulate(self, setup: MatchSetup, rng: object, *, decisive: bool = False) -> MatchResult:
        if setup.fixture.fixture_id == FixtureId("group-0"):
            self.setups.append(setup)
            return MatchResult(Score(0, 1))
        return super().simulate(setup, rng, decisive=decisive)


def test_swapping_group_positions_permutates_both_final_occupants() -> None:
    summary = play(group_request(), SwapGroupPositions())
    final = summary.results[-1]
    assert (final.home, final.away) == (RIVAL, ME)
    assert final.fixture_id == FixtureId("group-final")
    assert final.venue == "neutral"
    assert summary.standings[0].rows[0].club_season_id == RIVAL
    assert summary.standings[0].rows[1].club_season_id == ME
    assert tuple(e.kind for e in summary.events) == ("advanced", "champion")


def test_group_permutation_is_reconstructed_from_prior_blocks() -> None:
    value = group_request()
    first = play(replace(value, end=END), SwapGroupPositions())
    second_value = continuation(value, first)
    second_value = replace(second_value, start=date(2000, 9, 4), state_as_of=END)
    second = play(second_value, SwapGroupPositions())
    whole = play(value, SwapGroupPositions())
    assert (*first.results, *second.results) == whole.results
    assert (*first.events, *second.events) == whole.events


def test_unknown_knockout_calendar_is_rejected_when_a_path_needs_it() -> None:
    value = cup_request()
    season = replace(value.season, knockout_calendar=None,
                     fixtures=value.season.fixtures[:2])
    with pytest.raises(InvalidValueError, match=r"calendar|slot"):
        play(replace(value, season=season), OwnWins())


def test_inconsistent_prior_effective_occupants_are_rejected() -> None:
    value = group_request()
    whole = play(value, SwapGroupPositions())
    changed = replace(whole.results[-1], home=ME, away=RIVAL)
    with pytest.raises(InvalidValueError):
        play(replace(value, start=date(2000, 9, 8), end=date(2000, 9, 8),
                     prior_results=(*whole.results[:-1], changed)), SwapGroupPositions())
