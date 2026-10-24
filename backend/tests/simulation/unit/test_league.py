"""Test FC league arithmetic, ranking and declared historical evidence."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from typing import Any

import pytest
from tests.simulation.unit.test_external_results_contract import (
    ExternalResultsContract,
    PolicyFactory,
    make_accumulated_request,
    make_request,
)

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.domain.league import (
    HeadToHeadEvidence,
    HeadToHeadFixture,
    HeadToHeadResult,
    HistoricalExternalResults,
    LeagueTable,
)
from mister.simulation.domain.league_types import (
    ExternalResultsRequest,
    LeagueRow,
    ResultReplacement,
)
from mister.simulation.domain.model import Score, Venue

_ME = ClubSeasonId("test-fc-2000-01")
_A = ClubSeasonId("sample-united-2000-01")
_B = ClubSeasonId("mock-city-2000-01")
_C = ClubSeasonId("example-town-2000-01")
_COMPETITION = CompetitionId("liga-test")
_CUTOFF = date(2000, 9, 30)
_SOURCES = ("https://example.org/test-content/liga-test",)


class TestHistoricalExternalResults(ExternalResultsContract):
    pytestmark = pytest.mark.contract

    @pytest.fixture
    def make_policy(self) -> PolicyFactory:
        return HistoricalExternalResults


def _row(  # noqa: PLR0913 - Named league counters keep fixture intent explicit.
    club: ClubSeasonId,
    *,
    won: int = 1,
    drawn: int = 0,
    lost: int = 0,
    goals_for: int = 1,
    goals_against: int = 1,
) -> LeagueRow:
    return LeagueRow(
        club, won + drawn + lost, won, drawn, lost, goals_for, goals_against, 3 * won + drawn
    )


def _request(
    rows: tuple[LeagueRow, ...], replacements: tuple[ResultReplacement, ...] = ()
) -> ExternalResultsRequest:
    return ExternalResultsRequest(
        _COMPETITION,
        _CUTOFF,
        _ME,
        tuple(row.club_season_id for row in rows),
        3,
        1,
        rows,
        replacements,
    )


def _table(
    rows: tuple[LeagueRow, ...],
    *,
    criteria: tuple[str, ...] = (),
    final_order: tuple[ClubSeasonId, ...] | None = None,
    evidence: HeadToHeadEvidence | None = None,
    replacements: tuple[ResultReplacement, ...] = (),
) -> LeagueTable:
    return LeagueTable(
        _request(rows, replacements),
        rows,
        criteria,
        final_order if final_order is not None else tuple(row.club_season_id for row in rows),
        evidence,
    )


def _clubs(table: LeagueTable) -> tuple[ClubSeasonId, ...]:
    return tuple(row.club_season_id for row in table.rows)


def _fixture(
    fixture_id: str,
    home: ClubSeasonId,
    away: ClubSeasonId,
    when: date = _CUTOFF,
) -> HeadToHeadFixture:
    return HeadToHeadFixture(FixtureId(fixture_id), when, home, away)


def _result(fixture: HeadToHeadFixture, score: Score) -> HeadToHeadResult:
    return HeadToHeadResult(
        fixture.fixture_id, fixture.date, fixture.home, fixture.away, score, _SOURCES
    )


def _evidence(
    matches: tuple[tuple[HeadToHeadFixture, Score], ...] = (),
    clubs: tuple[ClubSeasonId, ...] = (_ME, _A, _B),
) -> HeadToHeadEvidence:
    return HeadToHeadEvidence(
        _COMPETITION,
        _CUTOFF,
        clubs,
        tuple(fixture for fixture, _ in matches),
        tuple(_result(fixture, score) for fixture, score in matches),
        _SOURCES,
    )


def _replacement(
    fixture: HeadToHeadFixture, historical: Score, simulated: Score
) -> ResultReplacement:
    return ResultReplacement(
        fixture.fixture_id, fixture.date, fixture.home, fixture.away, historical, simulated
    )


def test_a_real_defeat_becoming_a_home_win_transfers_three_points() -> None:
    fixture = _fixture("test-fc-sample-united", _ME, _A)
    request = _request(
        (_row(_ME, won=0, lost=1, goals_for=0), _row(_A, goals_against=0)),
        (_replacement(fixture, Score(0, 1), Score(2, 0)),),
    )

    assert HistoricalExternalResults().standings(request) == (
        _row(_ME, goals_for=2, goals_against=0),
        _row(_A, won=0, lost=1, goals_for=0, goals_against=2),
    )


def test_changing_a_win_to_a_draw_changes_the_total_points_awarded() -> None:
    request = make_request()
    request = replace(
        request,
        points_per_win=3,
        historical_rows=(replace(request.historical_rows[0], points=3), request.historical_rows[1]),
        replacements=(replace(request.replacements[0], simulated_score=Score(2, 2)),),
    )

    rows = HistoricalExternalResults().standings(request)

    assert tuple(row.points for row in rows) == (1, 1)
    assert sum(row.points for row in rows) == 2
    assert all(row.played == row.drawn == 1 for row in rows)


def test_all_historical_contributions_are_subtracted_before_simulated_additions() -> None:
    request = make_accumulated_request()
    # Each original contribution fits alone; together they exceed the original baseline.
    request = replace(
        request,
        historical_rows=(
            LeagueRow(_A, 1, 1, 0, 0, 1, 0, 2),
            LeagueRow(_B, 0, 0, 0, 0, 0, 0, 0),
            LeagueRow(_ME, 1, 0, 0, 1, 0, 1, 0),
        ),
        replacements=tuple(
            replace(result, historical_score=Score(1, 0), simulated_score=Score(1, 0))
            if result.home == _A
            else replace(result, historical_score=Score(0, 1), simulated_score=Score(0, 1))
            for result in request.replacements
        ),
    )

    with pytest.raises(InvalidValueError, match="historical contributions"):
        HistoricalExternalResults().standings(request)


@pytest.mark.parametrize("counter", ["won", "drawn", "lost", "goals_for", "goals_against"])
def test_each_historical_counter_must_fit_the_baseline(counter: str) -> None:
    request = make_request(reproduce_history=True)
    if counter == "drawn":
        request = replace(
            request,
            replacements=(replace(request.replacements[0], historical_score=Score(1, 1)),),
        )
    elif counter == "won":
        request = replace(request, historical_rows=tuple(reversed(request.historical_rows)))
        request = replace(
            request,
            replacements=(replace(request.replacements[0], historical_score=Score(0, 1)),),
        )
    elif counter in ("goals_for", "goals_against"):
        request = replace(
            request,
            replacements=(replace(request.replacements[0], historical_score=Score(2, 0)),),
        )
    else:
        request = replace(
            request,
            replacements=(replace(request.replacements[0], historical_score=Score(0, 1)),),
        )

    with pytest.raises(InvalidValueError):
        HistoricalExternalResults().standings(request)


def test_league_orders_points_before_all_other_criteria() -> None:
    table = _table((_row(_ME, goals_for=20), _row(_A, won=2, goals_for=0)))

    assert _clubs(table) == (_A, _ME)
    assert table.unresolved_groups == ()


def test_rival_only_ties_use_the_separate_final_order_instead_of_cutoff_order() -> None:
    table = _table(
        (_row(_ME, won=0), _row(_A, goals_for=9), _row(_B)),
        criteria=("head_to_head_points", "goal_difference"),
        final_order=(_B, _ME, _A),
    )

    assert _clubs(table) == (_B, _A, _ME)
    assert table.unresolved_groups == ()


@pytest.mark.parametrize(
    ("criterion", "first", "second"),
    [
        ("goal_difference", _row(_A, goals_for=1, goals_against=3), _row(_ME)),
        ("goals_for", _row(_A, goals_for=1), _row(_ME, goals_for=2, goals_against=4)),
        ("wins", _row(_A, won=0, drawn=3), _row(_ME)),
    ],
)
def test_global_criteria_need_no_head_to_head_evidence(
    criterion: str, first: LeagueRow, second: LeagueRow
) -> None:
    table = _table((first, second), criteria=(criterion,))

    assert _clubs(table) == (_ME, _A)
    assert table.unresolved_groups == ()


def test_criteria_are_applied_in_the_configured_order() -> None:
    rows = (_row(_ME, goals_for=3, goals_against=4), _row(_A, goals_for=2, goals_against=0))

    assert _clubs(_table(rows, criteria=("goals_for", "goal_difference"))) == (_ME, _A)
    assert _clubs(_table(rows, criteria=("goal_difference", "goals_for"))) == (_A, _ME)


def test_unresolved_ties_have_stable_id_order_and_are_explicit() -> None:
    rows = (_row(_ME), _row(_A), _row(_B))
    expected = tuple(sorted((_ME, _A, _B), key=str))

    table = _table(rows, criteria=("wins",), final_order=(_ME, _A, _B))

    assert _clubs(table) == expected
    assert table.unresolved_groups == (expected,)
    assert _clubs(_table(tuple(reversed(rows)), criteria=("wins",))) == expected


def test_a_known_empty_schedule_is_distinct_from_unknown_history() -> None:
    rows = (_row(_ME), _row(_A))

    with pytest.raises(InvalidValueError, match="head-to-head evidence"):
        _table(rows, criteria=("head_to_head_points",))

    table = _table(rows, criteria=("head_to_head_points",), evidence=_evidence(clubs=(_ME, _A)))

    assert table.unresolved_groups == ((_A, _ME),)


def test_unreached_direct_criteria_do_not_require_evidence() -> None:
    table = _table(
        (_row(_ME, goals_for=2), _row(_A)),
        criteria=("goal_difference", "head_to_head_points"),
    )

    assert _clubs(table) == (_ME, _A)


def test_head_to_head_uses_simulated_managed_results_and_historical_rival_results() -> None:
    ma = _fixture("test-fc-sample-united", _ME, _A)
    ab = _fixture("sample-united-mock-city", _A, _B)
    mb = _fixture("test-fc-mock-city", _ME, _B)
    evidence = _evidence(((ma, Score(0, 1)), (ab, Score(2, 0)), (mb, Score(0, 1))))
    replacements = (
        _replacement(ma, Score(0, 1), Score(3, 0)),
        _replacement(mb, Score(0, 1), Score(2, 0)),
    )

    table = _table(
        (_row(_A), _row(_B), _row(_ME)),
        criteria=("head_to_head_points",),
        evidence=evidence,
        replacements=replacements,
    )

    assert _clubs(table) == (_ME, _A, _B)


@pytest.mark.parametrize(
    ("criterion", "score", "expected"),
    [
        ("head_to_head_goal_difference", Score(3, 0), (_ME, _A)),
        ("head_to_head_goals_for", Score(3, 0), (_ME, _A)),
        ("head_to_head_away_goals", Score(2, 2), (_A, _ME)),
    ],
)
def test_direct_goal_criteria_respect_home_and_away(
    criterion: str, score: Score, expected: tuple[ClubSeasonId, ...]
) -> None:
    fixture = replace(_fixture("test-fc-sample-united", _ME, _A), venue=Venue.HOME)

    table = _table(
        (_row(_ME), _row(_A)),
        criteria=(criterion,),
        evidence=_evidence(((fixture, score),), (_ME, _A)),
        replacements=(_replacement(fixture, score, score),),
    )

    assert _clubs(table) == expected


def test_a_triple_tie_keeps_the_original_mini_league_after_partitioning() -> None:
    ma = _fixture("test-fc-sample-united", _ME, _A)
    ab = _fixture("sample-united-mock-city", _A, _B)
    bm = _fixture("mock-city-test-fc", _B, _ME)
    # A has six mini-league points; ME and B have one. ME's goal difference over
    # the original three is -1, B's is -3; their own fixture is a draw.
    evidence = _evidence(((ma, Score(0, 1)), (ab, Score(3, 0)), (bm, Score(0, 0))))
    replacements = (
        _replacement(ma, Score(0, 1), Score(0, 1)),
        _replacement(bm, Score(0, 0), Score(0, 0)),
    )

    table = _table(
        (_row(_ME), _row(_A), _row(_B)),
        criteria=("head_to_head_points", "head_to_head_goal_difference"),
        evidence=evidence,
        replacements=replacements,
    )

    assert _clubs(table) == (_A, _ME, _B)
    assert table.unresolved_groups == ()


def test_rivals_in_a_managed_points_group_keep_sporting_criteria_after_partitioning() -> None:
    ma = _fixture("test-fc-sample-united", _ME, _A)
    mb = _fixture("test-fc-mock-city", _ME, _B)
    table = _table(
        (_row(_ME), _row(_A), _row(_B)),
        criteria=("head_to_head_points", "head_to_head_goal_difference"),
        final_order=(_B, _A, _ME),
        evidence=_evidence(((ma, Score(1, 0)), (mb, Score(3, 0)))),
        replacements=(
            _replacement(ma, Score(1, 0), Score(1, 0)),
            _replacement(mb, Score(3, 0), Score(3, 0)),
        ),
    )

    assert _clubs(table) == (_ME, _A, _B)
    assert table.unresolved_groups == ()


def test_direct_evidence_covers_the_original_group_even_after_a_global_criterion_splits_it() -> (
    None
):
    with pytest.raises(InvalidValueError, match="original points group"):
        _table(
            (_row(_ME), _row(_A), _row(_B, goals_for=2)),
            criteria=("goals_for", "head_to_head_points"),
            evidence=_evidence(clubs=(_ME, _A)),
        )


def test_replaying_original_results_preserves_the_historical_points_ranking() -> None:
    request = make_request(reproduce_history=True)
    adjusted_rows = HistoricalExternalResults().standings(request)

    table = LeagueTable(request, adjusted_rows, (), (_A, _ME))

    assert table.rows == request.historical_rows
    assert table.unresolved_groups == ()


def test_direct_criterion_requires_coverage_of_the_original_points_group() -> None:
    with pytest.raises(InvalidValueError, match="cover"):
        _table(
            (_row(_ME), _row(_A), _row(_B)),
            criteria=("head_to_head_points",),
            evidence=_evidence(clubs=(_ME, _A)),
        )


@pytest.mark.parametrize("changed", ["date", "home", "historical_score", "fixture_id"])
def test_a_managed_overlay_must_match_the_historical_fixture(changed: str) -> None:
    fixture = _fixture("test-fc-sample-united", _ME, _A)
    replacement = _replacement(fixture, Score(0, 1), Score(2, 0))
    changes: dict[str, Any] = {
        "date": date(2000, 9, 29),
        "home": _A,
        "historical_score": Score(1, 0),
        "fixture_id": FixtureId("different-fixture"),
    }
    if changed == "home":
        replacement = replace(replacement, home=_A, away=_ME)
    else:
        replacement = replace(replacement, **{changed: changes[changed]})

    with pytest.raises(InvalidValueError, match="managed"):
        _table(
            (_row(_ME), _row(_A)),
            criteria=("head_to_head_points",),
            evidence=_evidence(((fixture, Score(0, 1)),), (_ME, _A)),
            replacements=(replacement,),
        )


def test_a_managed_historical_fixture_cannot_silently_miss_its_replacement() -> None:
    fixture = _fixture("test-fc-sample-united", _ME, _A)

    with pytest.raises(InvalidValueError, match="managed"):
        _table(
            (_row(_ME), _row(_A)),
            criteria=("head_to_head_points",),
            evidence=_evidence(((fixture, Score(0, 1)),), (_ME, _A)),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("competition_id", CompetitionId("other-test-league")),
        ("as_of", date(2000, 10, 1)),
        ("covered_clubs", (_ME, _A, _C)),
    ],
)
def test_evidence_must_belong_to_the_requested_competition_cutoff_and_participants(
    field: str, value: Any
) -> None:
    with pytest.raises(InvalidValueError):
        _table((_row(_ME), _row(_A), _row(_B)), evidence=replace(_evidence(), **{field: value}))


@pytest.mark.parametrize(
    "order",
    [(_ME,), (_ME, _ME), (_ME, _A, _B), (_ME, _B), [_ME, _A], ("test-fc-2000-01", _A)],
)
def test_the_historical_final_order_must_be_an_exact_immutable_permutation(order: Any) -> None:
    with pytest.raises(InvalidValueError):
        _table((_row(_ME), _row(_A)), final_order=order)


@pytest.mark.parametrize("criteria", [("unknown",), ("wins", "wins"), ["wins"]])
def test_criteria_must_use_the_exact_vocabulary_without_duplicates(criteria: Any) -> None:
    with pytest.raises(InvalidValueError):
        _table((_row(_ME), _row(_A)), criteria=criteria)


@pytest.mark.parametrize(
    "rows",
    [
        (_row(_ME),),
        (_row(_ME), _row(_ME)),
        (_row(_ME), _row(_B)),
        [_row(_ME), _row(_A)],
        (_row(_ME), replace(_row(_A), points=4)),
    ],
)
def test_adjusted_rows_must_cover_every_participant_and_obey_point_rules(rows: Any) -> None:
    with pytest.raises(InvalidValueError):
        LeagueTable(_request((_row(_ME), _row(_A))), rows, (), (_ME, _A))


def test_table_and_evidence_are_immutable() -> None:
    table = _table((_row(_ME), _row(_A)))

    with pytest.raises(FrozenInstanceError):
        table.rows = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        _evidence().results = ()  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fixture_id", "match"),
        ("date", datetime(2000, 9, 30)),
        ("home", "test-fc-2000-01"),
        ("away", _ME),
    ],
)
def test_historical_fixture_validates_its_identifiers_date_and_sides(
    field: str, value: Any
) -> None:
    with pytest.raises(InvalidValueError):
        replace(_fixture("test-fc-sample-united", _ME, _A), **{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [("score", None), ("sources", ()), ("sources", (" ",)), ("sources", ["source"])],
)
def test_historical_result_requires_a_score_and_explicit_immutable_provenance(
    field: str, value: Any
) -> None:
    result = _result(_fixture("test-fc-sample-united", _ME, _A), Score(0, 0))

    with pytest.raises(InvalidValueError):
        replace(result, **{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("competition_id", "liga-test"),
        ("as_of", datetime(2000, 9, 30)),
        ("covered_clubs", ()),
        ("covered_clubs", (_ME, _ME)),
        ("covered_clubs", (_ME, "sample-united-2000-01")),
        ("schedule", None),
        ("results", None),
        ("sources", ()),
    ],
)
def test_evidence_requires_typed_metadata_and_a_declared_immutable_calendar(
    field: str, value: Any
) -> None:
    with pytest.raises(InvalidValueError):
        replace(_evidence(), **{field: value})


@pytest.mark.parametrize(
    "inconsistency", ["missing", "orphan", "duplicate-fixture", "duplicate-result"]
)
def test_evidence_requires_exactly_one_result_per_declared_fixture(inconsistency: str) -> None:
    fixture = _fixture("sample-united-mock-city", _A, _B)
    evidence = _evidence(((fixture, Score(2, 1)),))
    changes: dict[str, Any] = {
        "missing": {"results": ()},
        "orphan": {"schedule": ()},
        "duplicate-fixture": {"schedule": (fixture, fixture)},
        "duplicate-result": {"results": evidence.results * 2},
    }

    with pytest.raises(InvalidValueError):
        replace(evidence, **changes[inconsistency])


@pytest.mark.parametrize("changed", ["future", "unknown-side", "date", "sides"])
def test_evidence_rejects_fixture_result_or_cutoff_inconsistency(changed: str) -> None:
    fixture = _fixture("sample-united-mock-city", _A, _B)
    evidence = _evidence(((fixture, Score(2, 1)),))
    changes: dict[str, Any] = {
        "future": {"as_of": date(2000, 9, 29)},
        "unknown-side": {"covered_clubs": (_ME, _A)},
        "date": {"results": (replace(evidence.results[0], date=date(2000, 9, 29)),)},
        "sides": {"results": (replace(evidence.results[0], home=_B, away=_A),)},
    }

    with pytest.raises(InvalidValueError):
        replace(evidence, **changes[changed])


def test_the_declared_schedule_can_contain_a_single_leg_on_the_inclusive_cutoff() -> None:
    fixture = _fixture("sample-united-mock-city", _A, _B)

    evidence = _evidence(((fixture, Score(2, 1)),))

    assert evidence.schedule == (fixture,)
    assert evidence.results[0].score == Score(2, 1)


@pytest.mark.parametrize("venue", ["home", True, 1])
def test_direct_fixture_requires_a_typed_venue_when_provided(venue: Any) -> None:
    with pytest.raises(InvalidValueError):
        HeadToHeadFixture(FixtureId("test-fixture"), _CUTOFF, _ME, _A, venue=venue)


def test_unknown_venue_is_allowed_for_other_direct_criteria_but_not_away_goals() -> None:
    fixture = _fixture("test-fc-sample-united", _ME, _A)
    evidence = _evidence(((fixture, Score(1, 1)),), (_ME, _A))
    replacements = (_replacement(fixture, Score(1, 1), Score(1, 1)),)
    assert _table(
        (_row(_ME), _row(_A)),
        criteria=("head_to_head_points",),
        evidence=evidence,
        replacements=replacements,
    ).unresolved_groups
    with pytest.raises(InvalidValueError, match="venue"):
        _table(
            (_row(_ME), _row(_A)),
            criteria=("head_to_head_away_goals",),
            evidence=evidence,
            replacements=replacements,
        )


def test_neutral_direct_match_contributes_no_away_goals_even_for_simulated_scores() -> None:
    fixture = replace(_fixture("neutral-test", _ME, _A), venue=Venue.NEUTRAL)
    table = _table(
        (_row(_ME), _row(_A)),
        criteria=("head_to_head_away_goals",),
        evidence=_evidence(((fixture, Score(0, 0)),), (_ME, _A)),
        replacements=(_replacement(fixture, Score(0, 0), Score(3, 7)),),
    )
    assert table.unresolved_groups == ((_A, _ME),)


@pytest.mark.parametrize(("home", "away", "expected"), [(_ME, _A, (_A, _ME)), (_A, _ME, (_ME, _A))])
def test_known_home_venue_counts_only_the_effective_away_clubs_goals(
    home: ClubSeasonId, away: ClubSeasonId, expected: tuple[ClubSeasonId, ...]
) -> None:
    fixture = replace(_fixture("home-test", home, away), venue=Venue.HOME)
    table = _table(
        (_row(_ME), _row(_A)),
        criteria=("head_to_head_away_goals",),
        evidence=_evidence(((fixture, Score(0, 0)),), (_ME, _A)),
        replacements=(_replacement(fixture, Score(0, 0), Score(0, 2)),),
    )
    assert _clubs(table) == expected
