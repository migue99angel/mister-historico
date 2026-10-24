"""Reusable pure-policy contract; T2.3 also runs it against HistoricalExternalResults.

Subclass ExternalResultsContract and override make_policy to check an implementation.
The structural fake uses explicit Test FC scripts, never an alternative P2 algorithm.
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import date

import pytest

from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.simulation.domain.league_types import (
    ExternalResultsRequest,
    LeagueRow,
    ResultReplacement,
)
from mister.simulation.domain.model import Score
from mister.simulation.domain.ports import ExternalResultsPolicy

pytestmark = pytest.mark.contract

_ME = ClubSeasonId("test-fc-2000-01")
_RIVAL = ClubSeasonId("sample-united-2000-01")
_OTHER = ClubSeasonId("mock-city-2000-01")


def make_request(*, reproduce_history: bool = False) -> ExternalResultsRequest:
    """An away defeat becomes a win, using two points per victory in Liga Test."""
    replacement = ResultReplacement(
        FixtureId("sample-united-test-fc"),
        date(2000, 9, 2),
        _RIVAL,
        _ME,
        historical_score=Score(1, 0),
        simulated_score=Score(1, 0) if reproduce_history else Score(0, 2),
    )
    return ExternalResultsRequest(
        competition_id=CompetitionId("liga-test"),
        as_of=date(2000, 9, 30),
        managed_club_season_id=_ME,
        participants=(_ME, _RIVAL),
        points_per_win=2,
        points_per_draw=1,
        historical_rows=(
            LeagueRow(_RIVAL, 1, 1, 0, 0, 1, 0, 2),
            LeagueRow(_ME, 1, 0, 0, 1, 0, 1, 0),
        ),
        replacements=(replacement,),
    )


def expected_rows() -> tuple[LeagueRow, ...]:
    """Accumulated rows retain baseline order even after the lead changes."""
    return (
        LeagueRow(_RIVAL, 1, 0, 0, 1, 0, 2, 0),
        LeagueRow(_ME, 1, 1, 0, 0, 2, 0, 2),
    )


def make_draw_request() -> ExternalResultsRequest:
    """A draw awards two points under a five-for-a-win Liga Test rule."""
    request = make_request()
    return replace(
        request,
        points_per_win=5,
        points_per_draw=2,
        historical_rows=(replace(request.historical_rows[0], points=5), request.historical_rows[1]),
        replacements=(replace(request.replacements[0], simulated_score=Score(1, 1)),),
    )


def expected_draw_rows() -> tuple[LeagueRow, ...]:
    return (
        LeagueRow(_RIVAL, 1, 0, 1, 0, 1, 1, 2),
        LeagueRow(_ME, 1, 0, 1, 0, 1, 1, 2),
    )


def make_accumulated_request() -> ExternalResultsRequest:
    """Two managed fixtures from different blocks plus an unaffected participant."""
    return ExternalResultsRequest(
        competition_id=CompetitionId("liga-test"),
        as_of=date(2000, 10, 31),
        managed_club_season_id=_ME,
        participants=(_ME, _RIVAL, _OTHER),
        points_per_win=2,
        points_per_draw=1,
        historical_rows=(
            LeagueRow(_RIVAL, 2, 1, 1, 0, 2, 1, 3),
            LeagueRow(_OTHER, 0, 0, 0, 0, 0, 0, 0),
            LeagueRow(_ME, 2, 0, 1, 1, 1, 2, 1),
        ),
        replacements=(
            ResultReplacement(
                FixtureId("sample-united-test-fc"),
                date(2000, 9, 2),
                _RIVAL,
                _ME,
                historical_score=Score(1, 0),
                simulated_score=Score(0, 2),
            ),
            ResultReplacement(
                FixtureId("test-fc-sample-united"),
                date(2000, 10, 2),
                _ME,
                _RIVAL,
                historical_score=Score(1, 1),
                simulated_score=Score(0, 3),
            ),
        ),
    )


def expected_accumulated_rows() -> tuple[LeagueRow, ...]:
    return (
        LeagueRow(_RIVAL, 2, 1, 0, 1, 3, 2, 2),
        LeagueRow(_OTHER, 0, 0, 0, 0, 0, 0, 0),
        LeagueRow(_ME, 2, 1, 0, 1, 2, 3, 2),
    )


PolicyFactory = Callable[[], ExternalResultsPolicy]


class ExternalResultsContract:
    """The minimal guarantees of the pure accumulated-results strategy."""

    @pytest.fixture
    def make_policy(self) -> PolicyFactory:
        raise NotImplementedError

    def test_reproducing_history_preserves_the_original_rows(
        self, make_policy: PolicyFactory
    ) -> None:
        request = make_request(reproduce_history=True)

        assert make_policy().standings(request) == request.historical_rows

    def test_replacements_use_configured_points_and_adjust_both_sides(
        self, make_policy: PolicyFactory
    ) -> None:
        assert make_policy().standings(make_request()) == expected_rows()

    def test_draws_use_the_configured_award(self, make_policy: PolicyFactory) -> None:
        assert make_policy().standings(make_draw_request()) == expected_draw_rows()

    def test_rows_are_complete_and_stay_in_baseline_order(self, make_policy: PolicyFactory) -> None:
        request = make_request()
        rows = make_policy().standings(request)

        assert isinstance(rows, tuple)
        assert tuple(row.club_season_id for row in rows) == tuple(
            row.club_season_id for row in request.historical_rows
        )
        assert {row.club_season_id for row in rows} == set(request.participants)
        assert rows[0].points < rows[1].points

    def test_repeated_calls_always_start_from_the_original_baseline(
        self, make_policy: PolicyFactory
    ) -> None:
        request = make_request()
        baseline = request.historical_rows
        policy = make_policy()
        first = policy.standings(request)
        policy.standings(make_request(reproduce_history=True))

        assert policy.standings(request) == first
        assert request.historical_rows == baseline
        assert request.replacements[0].historical_score == Score(1, 0)

    def test_all_prior_block_replacements_are_applied_and_other_rows_are_preserved(
        self, make_policy: PolicyFactory
    ) -> None:
        request = make_accumulated_request()

        rows = make_policy().standings(request)

        assert rows == expected_accumulated_rows()
        assert rows[1] == request.historical_rows[1]
        assert tuple(row.club_season_id for row in rows) == (_RIVAL, _OTHER, _ME)

    def test_a_baseline_without_the_historical_contributions_is_rejected(
        self, make_policy: PolicyFactory
    ) -> None:
        request = make_request()
        zero_rows = tuple(LeagueRow(club, 0, 0, 0, 0, 0, 0, 0) for club in (_RIVAL, _ME))
        insufficient = replace(request, historical_rows=zero_rows)

        with pytest.raises(InvalidValueError):
            make_policy().standings(insufficient)

    def test_fresh_policies_agree(self, make_policy: PolicyFactory) -> None:
        request = make_request()

        assert make_policy().standings(request) == make_policy().standings(request)


class ScriptedExternalResults:
    """Plain structural fake: complete requests must have a preprogrammed answer."""

    def __init__(self) -> None:
        historical = make_request(reproduce_history=True)
        self._scripts = {
            historical: historical.historical_rows,
            make_request(): expected_rows(),
            make_draw_request(): expected_draw_rows(),
        }

    def standings(self, request: ExternalResultsRequest) -> tuple[LeagueRow, ...]:
        try:
            return self._scripts[request]
        except KeyError as error:
            raise InvalidValueError("no scripted standings for this request") from error


class TestScriptedExternalResults(ExternalResultsContract):
    @pytest.fixture
    def make_policy(self) -> PolicyFactory:
        return ScriptedExternalResults


def test_an_unscripted_request_fails_instead_of_inventing_a_table() -> None:
    policy: ExternalResultsPolicy = ScriptedExternalResults()
    request = replace(make_request(), as_of=date(2000, 10, 31))

    with pytest.raises(InvalidValueError, match="no scripted standings"):
        policy.standings(request)
