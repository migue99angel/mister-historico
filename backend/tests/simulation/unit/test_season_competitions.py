"""Cup lineage and complete group-position permutations on fictional sourced evidence."""

from dataclasses import replace
from datetime import date
from typing import Literal, cast

import pytest
from tests.simulation.unit.test_simulate_block import (
    END,
    ME,
    RIVAL,
    START,
    FixedMatches,
    continuation,
    play,
    request,
)

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.application.api import (
    AggregateTeamInput,
    BlockSimRequest,
    CompetitionInput,
    FixtureInput,
    GroupEntryAssignmentInput,
    GroupEntryAssignmentsInput,
    GroupInput,
    HeadToHeadEvidenceInput,
    HeadToHeadFixtureInput,
    HeadToHeadResultInput,
    KnockoutCalendarInput,
    KnockoutSlotInput,
    RealResultInput,
    RealTieInput,
    StageInput,
    StandingRowDTO,
    StandingsDTO,
)
from mister.simulation.application.simulate_block import _stages
from mister.simulation.domain.model import MatchResult, MatchSetup, Score

CUP = CompetitionId("copa-test")
OTHER = ClubSeasonId("demo-athletic-2000-01")
FOURTH = ClubSeasonId("mock-city-2000-01")
SOURCES = ("https://example.org/test-fc/competition",)
FINAL_DAY = date(2000, 9, 7)


def cup_request(*, legs: Literal[1, 2] = 2, deciding: bool = True) -> BlockSimRequest:
    value = request()
    stages = (
        StageInput("semi", "semi_final", legs, False, deciding, deciding),
        StageInput("final", "final", 1, False, deciding, deciding),
    )
    own = [
        FixtureInput(
            FixtureId("semi-1"),
            START,
            CUP,
            ME,
            RIVAL,
            stage_id="semi",
            leg=1,
            real_result=RealResultInput(1, 0),
        )
    ]
    if legs == 2:
        own.append(
            FixtureInput(
                FixtureId("semi-2"),
                END,
                CUP,
                RIVAL,
                ME,
                stage_id="semi",
                leg=2,
                real_result=RealResultInput(0, 0),
            )
        )
    own.append(
        FixtureInput(
            FixtureId("final"),
            FINAL_DAY,
            CUP,
            ME,
            OTHER,
            stage_id="final",
            venue="neutral",
            real_result=RealResultInput(1, 0),
        )
    )
    slots = tuple(
        KnockoutSlotInput(
            f.fixture_id, f.stage_id or "", f.date, f.home, f.away, f.venue, f.leg, SOURCES, "ok"
        )
        for f in own
    )
    external = tuple(
        KnockoutSlotInput(
            FixtureId(f"external-{leg}"),
            "semi",
            START if leg == 1 else END,
            OTHER if leg == 1 else FOURTH,
            FOURTH if leg == 1 else OTHER,
            "home",
            cast("Literal[1, 2]", leg),
            SOURCES,
            "ok",
        )
        for leg in range(1, legs + 1)
    )
    competition = CompetitionInput(
        CUP,
        "cup",
        "domestic_cup",
        (ME, RIVAL, OTHER, FOURTH),
        1.2,
        1.15,
        stages=stages,
        real_ties=(
            RealTieInput("semi", (ME, RIVAL), ME),
            RealTieInput("semi", (OTHER, FOURTH), OTHER),
            RealTieInput("final", (ME, OTHER), ME),
        ),
    )
    season = replace(
        value.season,
        competitions=(competition,),
        fixtures=tuple(own),
        teams=(
            *value.season.teams,
            AggregateTeamInput(OTHER, 60, 60),
            AggregateTeamInput(FOURTH, 65, 65),
        ),
        historical_standings=(),
        knockout_calendar=(KnockoutCalendarInput(CUP, (*slots, *external), SOURCES, "ok"),),
    )
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
        FixtureId("semi-1"),
        FixtureId("semi-2"),
        FixtureId("final"),
    )
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
    assert tuple(r.fixture_id for r in summary.results) == (
        FixtureId("semi-1"),
        FixtureId("semi-2"),
    )
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
    competition = replace(
        value.season.competitions[0],
        real_ties=(
            RealTieInput("semi", (ME, RIVAL), RIVAL),
            RealTieInput("semi", (OTHER, FOURTH), OTHER),
            RealTieInput("final", (RIVAL, OTHER), OTHER),
        ),
    )
    assert value.season.knockout_calendar is not None
    calendar = value.season.knockout_calendar[0]
    assert calendar.slots is not None
    slots = tuple(
        replace(slot, home=RIVAL) if slot.stage_id == "final" else slot for slot in calendar.slots
    )
    season = replace(
        value.season,
        competitions=(competition,),
        fixtures=(value.season.fixtures[0],),
        knockout_calendar=(replace(calendar, slots=slots),),
    )
    summary = play(replace(value, season=season), OwnWins())
    assert summary.results[-1].fixture_id == FixtureId("final")
    assert summary.results[-1].home == ME
    assert summary.results[-1].opponent == OTHER


def group_request() -> BlockSimRequest:
    value = request()
    group = StageInput(
        "groups",
        "group_stage",
        1,
        False,
        False,
        False,
        groups=(GroupInput("a", (ME, RIVAL, OTHER, FOURTH)),),
        points_per_win=3,
        points_per_draw=1,
        tiebreakers=("goal_difference",),
        advance_per_group=2,
    )
    final = StageInput("final", "final", 1, False, True, True)
    competition = CompetitionInput(
        CUP,
        "continental_cup",
        "continental_primary",
        (ME, RIVAL, OTHER, FOURTH),
        1.2,
        1.15,
        stages=(group, final),
        real_ties=(RealTieInput("final", (ME, RIVAL), ME),),
    )
    pairs = (
        (ME, RIVAL, 1),
        (ME, OTHER, 2),
        (ME, FOURTH, 3),
        (RIVAL, OTHER, 1),
        (RIVAL, FOURTH, 2),
        (OTHER, FOURTH, 3),
    )
    schedule = tuple(
        HeadToHeadFixtureInput(
            FixtureId(f"group-{i}"), date(2000, 9, day), home, away, SOURCES, "ok", "home"
        )
        for i, (home, away, day) in enumerate(pairs)
    )
    results = tuple(HeadToHeadResultInput(f.fixture_id, (1, 0), SOURCES, "ok") for f in schedule)
    own = tuple(
        FixtureInput(
            f.fixture_id,
            f.date,
            CUP,
            f.home,
            f.away,
            stage_id="groups",
            group_id="a",
            round=i + 1,
            real_result=RealResultInput(1, 0),
        )
        for i, f in enumerate(schedule[:3])
    )
    final_fixture = FixtureInput(
        FixtureId("group-final"),
        FINAL_DAY,
        CUP,
        ME,
        RIVAL,
        stage_id="final",
        venue="neutral",
        real_result=RealResultInput(1, 0),
    )
    rows = tuple(
        StandingRowDTO(club, i + 1, 3, 3 - i, 0, i, 3 - i, i, (3 - i) * 3)
        for i, club in enumerate((ME, RIVAL, OTHER, FOURTH))
    )
    table = StandingsDTO(CUP, END, rows, "groups", "a")
    entries = tuple(
        GroupEntryAssignmentInput("groups", "a", i + 1, "final", club, SOURCES, "ok")
        for i, club in enumerate((ME, RIVAL))
    )
    season = replace(
        value.season,
        teams=(
            *value.season.teams,
            AggregateTeamInput(OTHER, 65, 65),
            AggregateTeamInput(FOURTH, 60, 60),
        ),
        competitions=(competition,),
        fixtures=(*own, final_fixture),
        historical_standings=(table,),
        head_to_head=(
            HeadToHeadEvidenceInput(
                CUP,
                END,
                (ME, RIVAL, OTHER, FOURTH),
                schedule,
                results,
                SOURCES,
                "ok",
                "groups",
                "a",
            ),
        ),
        knockout_calendar=(
            KnockoutCalendarInput(
                CUP,
                (
                    KnockoutSlotInput(
                        final_fixture.fixture_id,
                        "final",
                        FINAL_DAY,
                        ME,
                        RIVAL,
                        "neutral",
                        None,
                        SOURCES,
                        "ok",
                    ),
                ),
                SOURCES,
                "ok",
            ),
        ),
        group_entry_assignments=(GroupEntryAssignmentsInput(CUP, entries, SOURCES, "ok"),),
    )
    return replace(value, season=season, end=FINAL_DAY)


def test_group_input_passes_exact_coefficients_to_domain_rules() -> None:
    competition = group_request().season.competitions[0]
    coefficients = ((ME, 101001), (RIVAL, 101004), (OTHER, 101003), (FOURTH, 101002))
    group = replace(
        competition.stages[0],
        tiebreakers=("club_coefficient",),
        coefficients=coefficients,
    )
    stages = _stages(replace(competition, stages=(group, *competition.stages[1:])))
    assert stages[0].group_rules is not None
    assert stages[0].group_rules.coefficients == coefficients


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
    season = replace(value.season, knockout_calendar=None, fixtures=value.season.fixtures[:2])
    with pytest.raises(InvalidValueError, match=r"calendar|slot"):
        play(replace(value, season=season), OwnWins())


def test_inconsistent_prior_effective_occupants_are_rejected() -> None:
    value = group_request()
    whole = play(value, SwapGroupPositions())
    changed = replace(whole.results[-1], home=ME, away=RIVAL)
    with pytest.raises(InvalidValueError):
        play(
            replace(
                value,
                start=date(2000, 9, 8),
                end=date(2000, 9, 8),
                prior_results=(*whole.results[:-1], changed),
            ),
            SwapGroupPositions(),
        )


def test_closed_group_keeps_direct_evidence_after_the_last_calendar_date() -> None:
    value = group_request()
    competition = value.season.competitions[0]
    group = replace(
        competition.stages[0],
        tiebreakers=("head_to_head_points", "goal_difference"),
        reapply_head_to_head=False,
    )
    competition = replace(competition, stages=(group, competition.stages[1]))
    summary = play(
        replace(value, season=replace(value.season, competitions=(competition,))),
        SwapGroupPositions(),
    )
    assert summary.results[-1].home == RIVAL
    assert summary.results[-1].away == ME


def test_complete_group_calendar_closes_before_a_later_snapshot_cutoff() -> None:
    value = group_request()
    table = replace(value.season.historical_standings[0], as_of=date(2000, 9, 9))
    value = replace(value, season=replace(value.season, historical_standings=(table,)))
    summary = play(value, SwapGroupPositions())
    assert summary.events[0].date == END
    assert summary.results[-1].fixture_id == FixtureId("group-final")


def test_a_simulated_residual_group_tie_assigns_repeatable_qualifying_positions() -> None:
    value = group_request()
    competition = value.season.competitions[0]
    group = replace(competition.stages[0], tiebreakers=())
    competition = replace(competition, stages=(group, competition.stages[1]))

    # A direct draw makes Test and Sample level at the two qualifying positions.
    class SeedTie(OwnWins):
        def simulate(
            self, setup: MatchSetup, rng: object, *, decisive: bool = False
        ) -> MatchResult:
            if setup.fixture.fixture_id == FixtureId("group-0"):
                return MatchResult(Score(0, 0))
            return super().simulate(setup, rng, decisive=decisive)

    value = replace(value, season=replace(value.season, competitions=(competition,)))
    summary = play(value, SeedTie())
    assert summary == play(value, SeedTie())
    assert summary.results[-1].fixture_id == FixtureId("group-final")


def test_incomplete_group_entry_bijection_is_rejected() -> None:
    value = group_request()
    assert value.season.group_entry_assignments is not None
    declaration = value.season.group_entry_assignments[0]
    assert declaration.entries is not None
    declaration = replace(declaration, entries=declaration.entries[:1])
    with pytest.raises(InvalidValueError):
        play(replace(value, season=replace(value.season, group_entry_assignments=(declaration,))))


def test_a_first_leg_prior_result_cannot_include_deciding_periods() -> None:
    value = cup_request()
    first = play(replace(value, end=START), OwnWins())
    invalid = replace(first.results[0], extra_time=(0, 0))
    with pytest.raises(InvalidValueError):
        play(replace(continuation(value, first), prior_results=(invalid,)), OwnWins())


def test_duplicate_slots_cannot_simulate_a_fixture_twice() -> None:
    value = cup_request()
    assert value.season.knockout_calendar is not None
    calendar = value.season.knockout_calendar[0]
    assert calendar.slots is not None
    calendar = replace(calendar, slots=(*calendar.slots, calendar.slots[0]))
    with pytest.raises(InvalidValueError):
        play(replace(value, season=replace(value.season, knockout_calendar=(calendar,))))


def test_unknown_group_calendar_does_not_promote_from_a_future_table() -> None:
    value = group_request()
    table = replace(value.season.historical_standings[0], as_of=date(2000, 9, 9))
    value = replace(
        value,
        end=FINAL_DAY,
        season=replace(value.season, head_to_head=None, historical_standings=(table,)),
    )
    with pytest.raises(InvalidValueError):
        play(value, SwapGroupPositions())


def test_a_knockout_slot_must_be_later_than_its_feeder_tie() -> None:
    value = cup_request()
    assert value.season.knockout_calendar is not None
    calendar = value.season.knockout_calendar[0]
    assert calendar.slots is not None
    slots = tuple(replace(s, date=START) if s.stage_id == "final" else s for s in calendar.slots)
    own = tuple(
        replace(f, date=START) if f.stage_id == "final" else f for f in value.season.fixtures
    )
    with pytest.raises(InvalidValueError, match=r"date|preced|feeder|chronolog"):
        play(
            replace(
                value,
                season=replace(
                    value.season, fixtures=own, knockout_calendar=(replace(calendar, slots=slots),)
                ),
            ),
            OwnWins(),
        )


def test_external_semifinal_projection_and_managed_winner_replace_both_final_slots() -> None:
    value = group_request()
    b1, b2, b3, b4 = tuple(ClubSeasonId(f"group-b-{i}-2000-01") for i in range(1, 5))
    competition = value.season.competitions[0]
    group_stage = replace(
        competition.stages[0],
        groups=(*competition.stages[0].groups, GroupInput("b", (b1, b2, b3, b4))),
    )
    semi = StageInput("semi", "semi_final", 1, False, True, True)
    competition = replace(
        competition,
        participants=(*competition.participants, b1, b2, b3, b4),
        stages=(group_stage, semi, competition.stages[1]),
        real_ties=(
            RealTieInput("semi", (ME, b2), ME),
            RealTieInput("semi", (RIVAL, b1), b1),
            RealTieInput("final", (ME, b1), b1),
        ),
    )
    semi_day = date(2000, 9, 5)
    historical_semi = FixtureInput(
        FixtureId("semi-historical-own"),
        semi_day,
        CUP,
        ME,
        b2,
        stage_id="semi",
        real_result=RealResultInput(1, 0),
    )
    historical_final = FixtureInput(
        FixtureId("mixed-final"),
        FINAL_DAY,
        CUP,
        ME,
        b1,
        venue="neutral",
        stage_id="final",
        real_result=RealResultInput(0, 1),
    )
    slots = (
        KnockoutSlotInput(
            historical_semi.fixture_id, "semi", semi_day, ME, b2, "home", None, SOURCES, "ok"
        ),
        KnockoutSlotInput(
            FixtureId("semi-historical-external"),
            "semi",
            semi_day,
            RIVAL,
            b1,
            "home",
            None,
            SOURCES,
            "ok",
        ),
        KnockoutSlotInput(
            historical_final.fixture_id, "final", FINAL_DAY, ME, b1, "neutral", None, SOURCES, "ok"
        ),
    )
    assert value.season.group_entry_assignments is not None
    own_entries = value.season.group_entry_assignments[0].entries or ()
    entries = tuple(replace(e, target_stage_id="semi") for e in own_entries) + tuple(
        GroupEntryAssignmentInput("groups", "b", i + 1, "semi", club, SOURCES, "ok")
        for i, club in enumerate((b1, b2))
    )
    external_rows = tuple(
        StandingRowDTO(club, i + 1, 3, 3 - i, 0, i, 3 - i, i, (3 - i) * 3)
        for i, club in enumerate((b1, b2, b3, b4))
    )
    season = replace(
        value.season,
        competitions=(competition,),
        teams=(
            *value.season.teams,
            *(AggregateTeamInput(club, 65, 65) for club in (b1, b2, b3, b4)),
        ),
        fixtures=(*value.season.fixtures[:3], historical_semi, historical_final),
        historical_standings=(
            *value.season.historical_standings,
            StandingsDTO(CUP, END, external_rows, "groups", "b"),
        ),
        knockout_calendar=(KnockoutCalendarInput(CUP, slots, SOURCES, "ok"),),
        group_entry_assignments=(GroupEntryAssignmentsInput(CUP, entries, SOURCES, "ok"),),
    )
    value = replace(value, season=season)
    summary = play(value, SwapGroupPositions())
    assert tuple(r.fixture_id for r in summary.results[-2:]) == (
        FixtureId("semi-historical-external"),
        FixtureId("mixed-final"),
    )
    semifinal, final = summary.results[-2:]
    assert (semifinal.home, semifinal.away, semifinal.date, semifinal.key) == (
        ME,
        b1,
        semi_day,
        True,
    )
    assert (final.home, final.away, final.date, final.venue) == (RIVAL, ME, FINAL_DAY, "neutral")
    assert len(summary.results) == 5
    assert len({r.fixture_id for r in summary.results}) == 5
    assert all(r.home != r.away for r in summary.results)
    assert tuple(e.kind for e in summary.events) == ("advanced", "advanced", "champion")
    first = play(replace(value, end=semi_day), SwapGroupPositions())
    continued = replace(continuation(value, first), start=date(2000, 9, 6), state_as_of=semi_day)
    second = play(continued, SwapGroupPositions())
    assert (*first.results, *second.results) == summary.results
    assert (*first.events, *second.events) == summary.events


def test_an_unplayed_second_leg_is_not_an_exhausted_unresolved_tie() -> None:
    summary = play(replace(cup_request(), end=START), FixedMatches(Score(0, 0)))
    assert summary.unresolved_knockout_ties == ()
    assert summary.events == ()


def test_extra_time_uses_120_minutes_for_each_actual_starter_and_no_substitutes() -> None:
    value = cup_request(legs=1)
    summary = play(replace(value, end=START), FixedMatches(Score(0, 0)))
    assert sum(p.minutes_played == 120 for p in summary.player_states) == 11
    assert sum(p.minutes_played == 0 for p in summary.player_states) == 7
    assert all(p.fitness == 85 for p in summary.player_states if p.minutes_played)
    assert all(p.fitness == 100 for p in summary.player_states if not p.minutes_played)


def test_prior_result_for_a_final_after_managed_elimination_is_rejected() -> None:
    value = cup_request()
    eliminated = play(value, OwnLoses())
    final = play(value, OwnWins()).results[-1]
    with pytest.raises(InvalidValueError, match="inactive"):
        play(
            replace(
                value,
                start=date(2000, 9, 8),
                end=date(2000, 9, 8),
                prior_results=(*eliminated.results, final),
            ),
            OwnWins(),
        )


def test_self_consistent_prior_report_still_needs_the_effective_group_seed_occupants() -> None:
    value = group_request()
    whole = play(value, SwapGroupPositions())
    final = replace(
        whole.results[-1], home=ME, away=RIVAL, regulation=(1, 0), winner="home", user_result="win"
    )
    with pytest.raises(InvalidValueError, match="effective knockout slot"):
        play(
            replace(
                value,
                start=date(2000, 9, 8),
                end=date(2000, 9, 8),
                prior_results=(*whole.results[:-1], final),
            ),
            SwapGroupPositions(),
        )
