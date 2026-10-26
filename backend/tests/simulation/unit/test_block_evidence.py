"""Regression probes from independent review of sourced block continuity."""

from dataclasses import replace
from datetime import date

import pytest
from tests.simulation.unit.test_season_competitions import (
    CUP,
    FINAL_DAY,
    FOURTH,
    OTHER,
    SOURCES,
    OwnWins,
    group_request,
)
from tests.simulation.unit.test_simulate_block import (
    END,
    LEAGUE,
    ME,
    RIVAL,
    START,
    FixedMatches,
    play,
    request,
)

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, FixtureId
from mister.simulation.application import api
from mister.simulation.application.api import (
    HeadToHeadEvidenceInput,
    HeadToHeadFixtureInput,
    HeadToHeadResultInput,
    RealResultInput,
)
from mister.simulation.domain.model import MatchResult, MatchSetup, Score


def test_group_calendar_cannot_close_after_its_knockout_destination() -> None:
    value = group_request()
    evidence = value.season.head_to_head or ()
    late = replace(
        evidence[0],
        complete_through=date(2000, 9, 12),
        schedule=(
            *evidence[0].schedule[:-1],
            replace(evidence[0].schedule[-1], date=date(2000, 9, 10)),
        ),
    )
    snapshot = replace(value.season.historical_standings[0], as_of=date(2000, 9, 12))
    with pytest.raises(InvalidValueError):
        play(
            replace(
                value,
                end=date(2000, 9, 12),
                season=replace(
                    value.season, head_to_head=(late,), historical_standings=(snapshot,)
                ),
            ),
            OwnWins(),
        )


def test_partial_later_declaration_cannot_hide_a_contradictory_group_fixture() -> None:
    value = group_request()
    original = (value.season.head_to_head or ())[0]
    late = replace(
        original,
        complete_through=date(2000, 9, 12),
        covered_clubs=(OTHER, FOURTH),
        schedule=(replace(original.schedule[-1], date=date(2000, 9, 10)),),
        results=(original.results[-1],),
    )
    with pytest.raises(InvalidValueError):
        play(replace(value, season=replace(value.season, head_to_head=(original, late))), OwnWins())


def test_complete_historical_group_scores_must_match_original_snapshot_totals() -> None:
    value = group_request()
    snapshot = value.season.historical_standings[0]
    snapshot = replace(
        snapshot,
        rows=(*snapshot.rows[:2], replace(snapshot.rows[2], goals_for=99), snapshot.rows[3]),
    )
    with pytest.raises(InvalidValueError):
        play(
            replace(value, season=replace(value.season, historical_standings=(snapshot,))),
            OwnWins(),
        )


def test_unknown_external_evidence_group_is_rejected_before_ranking() -> None:
    value = group_request()
    evidence = (value.season.head_to_head or ())[0]
    evidence = replace(
        evidence,
        group_id="missing",
        covered_clubs=(OTHER, FOURTH),
        schedule=evidence.schedule[-1:],
        results=evidence.results[-1:],
    )
    with pytest.raises(InvalidValueError):
        play(replace(value, season=replace(value.season, head_to_head=(evidence,))), OwnWins())


def test_historical_unresolved_qualifying_positions_cannot_justify_seed_assignments() -> None:
    value = group_request()
    snapshot = value.season.historical_standings[0]
    first = replace(
        snapshot.rows[0], won=2, drawn=1, lost=0, goals_for=2, goals_against=0, points=7
    )
    second = replace(
        snapshot.rows[1], won=2, drawn=1, lost=0, goals_for=2, goals_against=0, points=7
    )
    snapshot = replace(
        snapshot, rows=(first, second, *snapshot.rows[2:]), unresolved_ties=((ME, RIVAL),)
    )
    evidence = (value.season.head_to_head or ())[0]
    evidence = replace(
        evidence, results=(replace(evidence.results[0], score=(0, 0)), *evidence.results[1:])
    )
    fixtures = (
        replace(value.season.fixtures[0], real_result=RealResultInput(0, 0)),
        *value.season.fixtures[1:],
    )
    with pytest.raises(InvalidValueError):
        play(
            replace(
                value,
                season=replace(
                    value.season,
                    head_to_head=(evidence,),
                    fixtures=fixtures,
                    historical_standings=(snapshot,),
                ),
            ),
            OwnWins(),
        )


def test_unknown_league_evidence_venue_is_allowed_without_away_goals() -> None:
    value = request()
    schedule = tuple(
        HeadToHeadFixtureInput(f.fixture_id, f.date, f.home, f.away, SOURCES, "ok", None)
        for f in value.season.fixtures
    )
    scores = tuple(
        HeadToHeadResultInput(f.fixture_id, (1, 0) if f.home == ME else (0, 1), SOURCES, "ok")
        for f in value.season.fixtures
    )
    evidence = HeadToHeadEvidenceInput(LEAGUE, END, (ME, RIVAL), schedule, scores, SOURCES, "ok")
    assert (
        len(play(replace(value, season=replace(value.season, head_to_head=(evidence,)))).results)
        == 2
    )


def test_managed_group_fixture_must_identify_a_declared_group() -> None:
    value = group_request()
    bad = replace(value.season.fixtures[0], group_id="missing")
    with pytest.raises(InvalidValueError):
        play(
            replace(
                value,
                season=replace(
                    value.season, head_to_head=None, fixtures=(bad, *value.season.fixtures[1:])
                ),
            ),
            OwnWins(),
        )


def test_state_cursor_cannot_precede_any_prior_match() -> None:
    value = request()
    results = play(value).results
    with pytest.raises(InvalidValueError):
        play(
            replace(
                value,
                start=date(2000, 9, 10),
                end=date(2000, 9, 12),
                state_as_of=START,
                prior_results=results,
            )
        )


def test_group_qualifying_position_is_an_exact_positive_integer() -> None:
    value = group_request()
    declaration = (value.season.group_entry_assignments or ())[0]
    entries = declaration.entries or ()
    bad = replace(entries[0], qualifying_position=True)
    with pytest.raises(InvalidValueError):
        play(
            replace(
                value,
                season=replace(
                    value.season,
                    group_entry_assignments=(replace(declaration, entries=(bad, *entries[1:])),),
                ),
            )
        )


def test_group_snapshot_must_cover_every_participant_before_seed_lookup() -> None:
    value = group_request()
    snapshot = value.season.historical_standings[0]
    snapshot = replace(snapshot, rows=snapshot.rows[:1])
    with pytest.raises(InvalidValueError):
        play(
            replace(value, season=replace(value.season, historical_standings=(snapshot,))),
            OwnWins(),
        )


def test_group_away_goals_cannot_treat_unknown_external_venue_as_neutral() -> None:
    value = group_request()
    competition = value.season.competitions[0]
    group = replace(
        competition.stages[0], tiebreakers=("head_to_head_away_goals",), reapply_head_to_head=False
    )
    competition = replace(
        competition,
        stages=(group, competition.stages[1]),
        real_ties=(api.RealTieInput("final", (OTHER, RIVAL), OTHER),),
    )
    evidence = (value.season.head_to_head or ())[0]
    actual = ((2, 1), (1, 2), (1, 0), (2, 1), (1, 0), (1, 0))
    evidence = replace(
        evidence,
        schedule=(
            *evidence.schedule[:3],
            replace(evidence.schedule[3], venue=None),
            *evidence.schedule[4:],
        ),
        results=tuple(
            replace(r, score=score) for r, score in zip(evidence.results, actual, strict=True)
        ),
    )
    snapshot = api.StandingsDTO(
        CUP,
        END,
        tuple(
            api.StandingRowDTO(
                club,
                i + 1,
                3,
                2 if i < 3 else 0,
                0,
                1 if i < 3 else 3,
                4 if i < 3 else 0,
                3,
                6 if i < 3 else 0,
            )
            for i, club in enumerate((OTHER, RIVAL, ME, FOURTH))
        ),
        "groups",
        "a",
        (),
    )
    own = tuple(
        replace(f, real_result=RealResultInput(*score))
        for f, score in zip(value.season.fixtures[:3], actual[:3], strict=True)
    )
    calendar = (value.season.knockout_calendar or ())[0]
    calendar = replace(
        calendar, slots=tuple(replace(slot, home=OTHER) for slot in calendar.slots or ())
    )
    entries = (value.season.group_entry_assignments or ())[0]
    entries = replace(
        entries,
        entries=tuple(
            replace(entry, historical_representative=club)
            for entry, club in zip(entries.entries or (), (OTHER, RIVAL), strict=True)
        ),
    )
    value = replace(
        value,
        season=replace(
            value.season,
            competitions=(competition,),
            fixtures=own,
            head_to_head=(evidence,),
            historical_standings=(snapshot,),
            knockout_calendar=(calendar,),
            group_entry_assignments=(entries,),
        ),
    )

    class Exact(FixedMatches):
        def simulate(
            self, setup: MatchSetup, rng: object, *, decisive: bool = False
        ) -> MatchResult:
            scores = {f.fixture_id: Score(*score) for f, score in zip(own, actual[:3], strict=True)}
            return MatchResult(scores.get(setup.fixture.fixture_id, Score(1, 0)))

    with pytest.raises(InvalidValueError, match=r"venue|unknown"):
        play(value, Exact())


def test_verified_declarations_cannot_disagree_on_a_known_external_venue() -> None:
    value = group_request()
    evidence = (value.season.head_to_head or ())[0]
    conflicting = replace(
        evidence,
        complete_through=FINAL_DAY,
        schedule=(*evidence.schedule[:-1], replace(evidence.schedule[-1], venue="neutral")),
    )
    with pytest.raises(InvalidValueError, match=r"venue|contradict"):
        play(
            replace(value, season=replace(value.season, head_to_head=(evidence, conflicting))),
            OwnWins(),
        )


def test_a_known_venue_can_complete_unknown_evidence_without_changing_other_facts() -> None:
    value = group_request()
    evidence = (value.season.head_to_head or ())[0]
    incomplete = replace(
        evidence, schedule=(*evidence.schedule[:-1], replace(evidence.schedule[-1], venue=None))
    )
    completed = replace(evidence, complete_through=FINAL_DAY)
    summary = play(
        replace(value, season=replace(value.season, head_to_head=(incomplete, completed))),
        OwnWins(),
    )
    assert summary.results == play(value, OwnWins()).results


def test_an_unreached_group_away_goal_criterion_does_not_require_unknown_venues() -> None:
    value = group_request()
    competition = value.season.competitions[0]
    group = replace(
        competition.stages[0], tiebreakers=("head_to_head_away_goals",), reapply_head_to_head=False
    )
    competition = replace(competition, stages=(group, competition.stages[1]))
    evidence = (value.season.head_to_head or ())[0]
    evidence = replace(
        evidence, schedule=(*evidence.schedule[:-1], replace(evidence.schedule[-1], venue=None))
    )
    summary = play(
        replace(
            value,
            season=replace(value.season, competitions=(competition,), head_to_head=(evidence,)),
        ),
        OwnWins(),
    )
    assert tuple(row.points for row in summary.standings[0].rows) == (9, 6, 3, 0)


def test_a_pending_historical_score_cannot_complete_an_original_group_table() -> None:
    value = group_request()
    evidence = (value.season.head_to_head or ())[0]
    evidence = replace(
        evidence, results=(*evidence.results[:-1], replace(evidence.results[-1], score=None))
    )
    with pytest.raises(InvalidValueError, match="missing historical score"):
        play(replace(value, season=replace(value.season, head_to_head=(evidence,))))


def test_verified_declarations_cannot_disagree_on_a_known_historical_score() -> None:
    value = group_request()
    evidence = (value.season.head_to_head or ())[0]
    conflicting = replace(
        evidence,
        complete_through=FINAL_DAY,
        results=(*evidence.results[:-1], replace(evidence.results[-1], score=(2, 0))),
    )
    with pytest.raises(InvalidValueError, match="same fixture score"):
        play(replace(value, season=replace(value.season, head_to_head=(evidence, conflicting))))


@pytest.mark.parametrize(
    ("criteria", "leader"),
    [
        (("head_to_head_away_goals",), RIVAL),
        (("goal_difference", "head_to_head_away_goals"), ME),
    ],
)
def test_unknown_venues_outside_the_evaluated_mini_table_do_not_block_group_ranking(
    criteria: tuple[api.TiebreakerName, ...],
    leader: ClubSeasonId,
) -> None:
    value = group_request()
    competition = value.season.competitions[0]
    group = replace(competition.stages[0], tiebreakers=criteria, reapply_head_to_head=False)
    competition = replace(competition, stages=(group, competition.stages[1]))
    evidence = (value.season.head_to_head or ())[0]
    evidence = replace(
        evidence, schedule=(*evidence.schedule[:-1], replace(evidence.schedule[-1], venue=None))
    )
    value = replace(
        value, season=replace(value.season, competitions=(competition,), head_to_head=(evidence,))
    )

    class DirectDraw(OwnWins):
        def simulate(
            self, setup: MatchSetup, rng: object, *, decisive: bool = False
        ) -> MatchResult:
            if setup.fixture.group is not None:
                return MatchResult(
                    Score(2, 2) if setup.fixture.fixture_id == FixtureId("group-0") else Score(2, 0)
                )
            return super().simulate(setup, rng, decisive=decisive)

    summary = play(value, DirectDraw())
    assert summary.standings[0].rows[0].club_season_id == leader
