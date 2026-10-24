"""Private league values reject incomplete or inconsistent Test FC inputs."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from typing import Any

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.domain.league_types import (
    ExternalResultsRequest,
    LeagueRow,
    ResultReplacement,
)
from mister.simulation.domain.model import Score

_ME = ClubSeasonId("test-fc-2000-01")
_RIVAL = ClubSeasonId("sample-united-2000-01")
_OTHER = ClubSeasonId("mock-city-2000-01")
_LEAGUE = CompetitionId("liga-test")
_CUTOFF = date(2000, 9, 30)


def _row(**overrides: Any) -> LeagueRow:
    fields: dict[str, Any] = {
        "club_season_id": _ME,
        "played": 1,
        "won": 0,
        "drawn": 0,
        "lost": 1,
        "goals_for": 0,
        "goals_against": 1,
        "points": 0,
    }
    return LeagueRow(**(fields | overrides))


def _replacement(**overrides: Any) -> ResultReplacement:
    fields: dict[str, Any] = {
        "fixture_id": FixtureId("test-fc-sample-united"),
        "date": date(2000, 9, 2),
        "home": _ME,
        "away": _RIVAL,
        "historical_score": Score(0, 1),
        "simulated_score": Score(2, 0),
    }
    return ResultReplacement(**(fields | overrides))


def _request(**overrides: Any) -> ExternalResultsRequest:
    fields: dict[str, Any] = {
        "competition_id": _LEAGUE,
        "as_of": _CUTOFF,
        "managed_club_season_id": _ME,
        "participants": (_ME, _RIVAL),
        "points_per_win": 2,
        "points_per_draw": 1,
        "historical_rows": (
            _row(club_season_id=_RIVAL, won=1, lost=0, goals_for=1, goals_against=0, points=2),
            _row(),
        ),
        "replacements": (_replacement(),),
    }
    return ExternalResultsRequest(**(fields | overrides))


def test_league_rows_keep_accumulated_totals() -> None:
    row = _row()

    assert (row.club_season_id, row.played, row.won, row.drawn, row.lost) == (_ME, 1, 0, 0, 1)
    assert (row.goals_for, row.goals_against, row.points) == (0, 1, 0)


@pytest.mark.parametrize(
    "field", ["played", "won", "drawn", "lost", "goals_for", "goals_against", "points"]
)
@pytest.mark.parametrize("value", [-1, True, 0.5, "0"])
def test_league_totals_are_non_negative_integers(field: str, value: Any) -> None:
    with pytest.raises(InvalidValueError):
        _row(**{field: value})


def test_played_equals_wins_draws_and_losses() -> None:
    with pytest.raises(InvalidValueError):
        _row(played=2)


def test_a_row_requires_a_club_season_identifier() -> None:
    with pytest.raises(InvalidValueError):
        _row(club_season_id="test-fc-2000-01")


def test_replacement_preserves_both_scores_in_home_away_orientation() -> None:
    replacement = _replacement(home=_RIVAL, away=_ME)

    assert replacement.home == _RIVAL
    assert replacement.away == _ME
    assert replacement.historical_score == Score(0, 1)
    assert replacement.simulated_score == Score(2, 0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"fixture_id": "fixture-1"},
        {"date": "2000-09-02"},
        {"date": datetime(2000, 9, 2)},
        {"home": "test-fc-2000-01"},
        {"away": "sample-united-2000-01"},
        {"away": _ME},
        {"historical_score": None},
        {"simulated_score": (2, 0)},
    ],
)
def test_replacements_require_a_dated_fixture_and_two_known_scores(overrides: dict[str, Any]) -> None:
    with pytest.raises(InvalidValueError):
        _replacement(**overrides)


@pytest.mark.parametrize("factory", [_row, _replacement, _request])
def test_league_values_are_immutable_and_compare_by_value(factory: Any) -> None:
    value = factory()

    assert value == factory()
    assert hash(value) == hash(factory())
    with pytest.raises(FrozenInstanceError):
        value.points = 100


def test_request_uses_configured_points_instead_of_assuming_three_for_a_win() -> None:
    request = _request()

    assert (request.points_per_win, request.points_per_draw) == (2, 1)
    assert request.historical_rows[0].points == 2


def test_request_preserves_the_historical_order_without_ranking_by_totals() -> None:
    request = _request()

    assert tuple(row.club_season_id for row in request.historical_rows) == (_RIVAL, _ME)
    assert request.participants == (_ME, _RIVAL)


@pytest.mark.parametrize("field", ["points_per_win", "points_per_draw"])
@pytest.mark.parametrize("value", [-1, True, 1.5, "1"])
def test_point_rules_require_non_negative_integers(field: str, value: Any) -> None:
    with pytest.raises(InvalidValueError):
        _request(**{field: value})


@pytest.mark.parametrize(
    "overrides",
    [
        {"competition_id": "liga-test"},
        {"as_of": "2000-09-30"},
        {"as_of": datetime(2000, 9, 30)},
        {"managed_club_season_id": "test-fc-2000-01"},
        {"managed_club_season_id": _OTHER},
        {"participants": ()},
        {"participants": (_ME,)},
        {"participants": (_ME, _ME)},
        {"participants": (_ME, "sample-united-2000-01")},
        {"participants": [_ME, _RIVAL]},
        {"historical_rows": ()},
        {"historical_rows": (_row(),)},
        {"historical_rows": (_row(), _row())},
        {"historical_rows": (_row(), _row(club_season_id=_OTHER))},
        {"historical_rows": [ _row(), _row(club_season_id=_RIVAL)]},
        {"historical_rows": (_row(), None)},
        {"replacements": [_replacement()]},
        {"replacements": (None,)},
        {"replacements": (_replacement(), _replacement())},
        {"replacements": (_replacement(date=date(2000, 10, 1)),)},
        {"replacements": (_replacement(away=_OTHER),)},
        {
            "participants": (_ME, _RIVAL, _OTHER),
            "historical_rows": (_row(), _row(club_season_id=_RIVAL), _row(club_season_id=_OTHER)),
            "replacements": (_replacement(home=_RIVAL, away=_OTHER),),
        },
    ],
)
def test_request_rejects_incomplete_or_incoherent_inputs(overrides: dict[str, Any]) -> None:
    with pytest.raises(InvalidValueError):
        _request(**overrides)


def test_historical_points_must_match_the_configured_rules() -> None:
    with pytest.raises(InvalidValueError):
        _request(points_per_win=3)


def test_replacements_on_the_cutoff_date_are_included() -> None:
    replacement = _replacement(date=_CUTOFF)

    assert _request(replacements=(replacement,)).replacements == (replacement,)


def test_initial_request_can_have_no_played_fixtures() -> None:
    rows = tuple(
        _row(club_season_id=club, played=0, lost=0, goals_against=0)
        for club in (_RIVAL, _ME)
    )

    assert _request(historical_rows=rows, replacements=()).replacements == ()


def test_replacement_ids_must_be_unique_even_if_scores_differ() -> None:
    first = _replacement()
    second = replace(first, simulated_score=Score(1, 1))

    with pytest.raises(InvalidValueError):
        _request(replacements=(first, second))
