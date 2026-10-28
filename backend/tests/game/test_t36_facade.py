"""Published facade keeps private run failures behind stable public errors."""

from typing import TYPE_CHECKING, cast

import pytest

from mister.game.application.api import (
    DilemmaAlreadyDecidedError,
    GameApi,
    InvalidOptionError,
    PendingDilemmasError,
    RunAlreadyFinishedError,
    SeasonQueries,
)
from mister.game.application.presentation_types import Presented, Started
from mister.game.domain.errors import AlreadyDecidedError, InvalidRunTransitionError
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import DilemmaId, OptionId, RunId

if TYPE_CHECKING:
    from mister.game.application import ports
    from mister.game.application.presentation import GamePresentation
    from mister.game.application.use_cases import AdvanceBlock, GetRun, StartRun, TakeDecision


class _Noop:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error or InvalidRunTransitionError("terminal runs reject commands")

    def execute(self, *args: object) -> object:
        raise self.error


class _Presentation:
    def present_run(self, view: object, content: object) -> object:
        raise AssertionError("run presentation is not reached")


class _Seasons:
    def list_seasons(self) -> tuple[object, ...]:
        return ()

    def get_season(self, season_id: object) -> object:
        raise AssertionError("season presentation is not reached")


class _Hasher:
    def hash(self, token: str) -> str:
        return token

    def verify(self, token: str, token_hash: str) -> bool:
        return True


def test_start_response_nests_the_run_view_beside_its_token() -> None:
    result = Started("secret-token", Presented({"runId": "run-id"})).to_json()

    assert result == {"runToken": "secret-token", "run": {"runId": "run-id"}}


def test_decision_on_terminal_run_uses_public_finished_error() -> None:
    api = _api()

    with pytest.raises(RunAlreadyFinishedError):
        api.take_decision(
            RunId.parse("00000000-0000-4000-8000-000000000001"),
            "token",
            "idem-key-123",
            0,
            DilemmaId("dilemma"),
            OptionId("option"),
        )


def test_advance_with_unresolved_dilemmas_uses_public_error() -> None:
    api = _api(
        advance=_Noop(InvalidRunTransitionError("all current block dilemmas must be decided first"))
    )

    with pytest.raises(PendingDilemmasError):
        api.advance_block(
            RunId.parse("00000000-0000-4000-8000-000000000001"), "token", "idem-key-123", 0
        )


@pytest.mark.parametrize(
    ("error", "public_error"),
    [
        (InvalidValueError("dilemma does not belong to the current block"), InvalidOptionError),
        (InvalidValueError("option does not belong to the selected dilemma"), InvalidOptionError),
        (AlreadyDecidedError("dilemma has already been decided"), DilemmaAlreadyDecidedError),
    ],
)
def test_invalid_decision_errors_are_translated_without_leaking_domain_codes(
    error: Exception, public_error: type[Exception]
) -> None:
    api = _api(take=_Noop(error))

    with pytest.raises(public_error):
        api.take_decision(
            RunId.parse("00000000-0000-4000-8000-000000000001"),
            "token",
            "idem-key-123",
            0,
            DilemmaId("dilemma"),
            OptionId("option"),
        )


def _api(*, take: _Noop | None = None, advance: _Noop | None = None) -> GameApi:
    return GameApi(
        start_run=cast("StartRun", _Noop()),
        get_run=cast("GetRun", _Noop()),
        take_decision=cast("TakeDecision", take or _Noop()),
        advance_block=cast("AdvanceBlock", advance or _Noop()),
        uow=cast("ports.UnitOfWork", object()),
        token_hasher=cast("ports.RunTokenHasher", _Hasher()),
        presentation=cast("GamePresentation", _Presentation()),
        seasons=cast("SeasonQueries", _Seasons()),
    )
