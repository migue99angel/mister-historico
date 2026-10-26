"""Regression probes from independent review of sourced block continuity."""

from dataclasses import replace
from datetime import date

import pytest
from tests.simulation.unit.test_season_competitions import (
    FOURTH,
    OTHER,
    SOURCES,
    OwnWins,
    group_request,
)
from tests.simulation.unit.test_simulate_block import END, LEAGUE, ME, RIVAL, START, play, request

from mister.shared_kernel.errors import InvalidValueError
from mister.simulation.application.api import (
    HeadToHeadEvidenceInput,
    HeadToHeadFixtureInput,
    HeadToHeadResultInput,
    RealResultInput,
)


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
