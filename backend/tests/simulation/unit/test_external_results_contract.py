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
from mister.simulation.domain.ports import ExternalResultsPolicy  # noqa: TC001

pytestmark = pytest.mark.contract

_ME = ClubSeasonId("test-fc-2000-01")
_RIVAL = ClubSeasonId("sample-united-2000-01")


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
