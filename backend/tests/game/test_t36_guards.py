"""Guard paths for the public facade and immutable JSON response values."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from tests.game.test_t36_facade import _api

from mister.game.application.api import (
    GameApi,
    InvalidOptionError,
    RunAlreadyFinishedError,
    SeasonQueries,
)
from mister.game.application.ports import RunNotFoundError
from mister.game.application.presentation_types import Presented
from mister.game.domain.errors import InvalidDecisionError, InvalidRunTransitionError
from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import DilemmaId, OptionId, PlayableSeasonId, RunId

_RUN_TOKEN = PlayableSeasonId("fixture-run-token").value
_TOKEN_HASH = PlayableSeasonId("fixture-token-hash").value

if TYPE_CHECKING:
    from types import TracebackType

    from tests.game.test_t36_facade import _Noop

    from mister.game.application import ports
    from mister.game.application.presentation import GamePresentation
    from mister.game.application.use_cases import AdvanceBlock, GetRun, StartRun, TakeDecision


class _MissingRuns:
    def get(self, run_id: RunId) -> None:
        del run_id


class _ExistingThenMissingRuns:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, run_id: RunId) -> _StoredRecord | None:
        del run_id
        self.calls += 1
        return _StoredRecord(_TOKEN_HASH) if self.calls == 1 else None


@dataclass(frozen=True)
class _StoredRecord:
    run_token_hash: str


class _Uow:
    def __init__(self, runs: _MissingRuns | _ExistingThenMissingRuns) -> None:
        self.runs = runs

    def __enter__(self) -> _Uow:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback


class _TruthyHasher:
    def verify(self, token: str, token_hash: str) -> bool:
        return bool(token == _RUN_TOKEN and token_hash == _TOKEN_HASH)


class _Start:
    def execute(self, season_id: PlayableSeasonId) -> object:
        del season_id
        return SimpleNamespace(
            run_id=RunId.parse("00000000-0000-4000-8000-000000000001"),
            token=_RUN_TOKEN,
            view=object(),
        )


class _Get:
    def execute(self, run_id: RunId, token: str) -> object:
        del run_id, token
        return object()


class _UnusedPresentation:
    def present_run(self, view: object, content: object) -> object:
        del view, content
        raise AssertionError("presentation should not run after the run disappears")


class _UnavailableSeasons:
    def list_seasons(self) -> tuple[Presented, ...]:
        return ()

    def get_season(self, season_id: PlayableSeasonId) -> Presented:
        del season_id
        raise _OtherDomainError("storage unavailable")


class _OtherDomainError(DomainError):
    code = "storage_unavailable"


def _api_with_uow(
    uow: object, *, start: object | None = None, get: object | None = None
) -> GameApi:
    return GameApi(
        start_run=cast("StartRun", start if start is not None else object()),
        get_run=cast("GetRun", get if get is not None else object()),
        take_decision=cast("TakeDecision", object()),
        advance_block=cast("AdvanceBlock", object()),
        uow=cast("ports.UnitOfWork", uow),
        token_hasher=cast("ports.RunTokenHasher", _TruthyHasher()),
        presentation=cast("GamePresentation", _UnusedPresentation()),
        seasons=cast("SeasonQueries", _UnavailableSeasons()),
    )


def test_catalog_domain_errors_other_than_not_found_propagate_unchanged() -> None:
    assert _api(seasons=_UnavailableSeasons()).list_seasons() == ()
    with pytest.raises(_OtherDomainError) as raised:
        _api(seasons=_UnavailableSeasons()).get_season(PlayableSeasonId("season"))
    assert raised.value.code == "storage_unavailable"


def test_start_and_get_translate_records_that_disappear_between_steps() -> None:
    start_api = _api_with_uow(_Uow(_MissingRuns()), start=_Start())
    with pytest.raises(RunNotFoundError):
        start_api.start_run(PlayableSeasonId("season"))

    run_id = RunId.parse("00000000-0000-4000-8000-000000000001")
    disappearing_uow = _Uow(_ExistingThenMissingRuns())
    get_api = _api_with_uow(disappearing_uow, get=_Get())
    with pytest.raises(RunNotFoundError):
        get_api.get_run(run_id, _RUN_TOKEN)


def test_public_command_error_guards_preserve_unrecognized_private_errors() -> None:
    run_id = RunId.parse("00000000-0000-4000-8000-000000000001")
    with pytest.raises(InvalidOptionError):
        _api(take=cast("_Noop", _NoopError(InvalidDecisionError("bad decision")))).take_decision(
            run_id, _RUN_TOKEN, "idem-key-123", 0, DilemmaId("dilemma"), OptionId("option")
        )
    with pytest.raises(InvalidValueError, match="unrelated invalid value"):
        _api(
            take=cast("_Noop", _NoopError(InvalidValueError("unrelated invalid value")))
        ).take_decision(
            run_id, _RUN_TOKEN, "idem-key-123", 0, DilemmaId("dilemma"), OptionId("option")
        )
    with pytest.raises(InvalidRunTransitionError, match="not the expected terminal case"):
        _api(
            take=cast(
                "_Noop", _NoopError(InvalidRunTransitionError("not the expected terminal case"))
            )
        ).take_decision(
            run_id, _RUN_TOKEN, "idem-key-123", 0, DilemmaId("dilemma"), OptionId("option")
        )
    with pytest.raises(RunAlreadyFinishedError):
        _api(
            advance=cast(
                "_Noop", _NoopError(InvalidRunTransitionError("terminal runs reject commands"))
            )
        ).advance_block(run_id, _RUN_TOKEN, "idem-key-123", 0)
    with pytest.raises(InvalidRunTransitionError, match="not a recognized transition"):
        _api(
            advance=cast(
                "_Noop", _NoopError(InvalidRunTransitionError("not a recognized transition"))
            )
        ).advance_block(run_id, _RUN_TOKEN, "idem-key-123", 0)


class _NoopError:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def execute(self, *args: object) -> object:
        del args
        raise self.error


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({"value": float("inf")}, "JSON numbers must be finite"),
        ({1: "non-string key"}, "JSON object keys must be strings"),
        ({"value": object()}, "unsupported JSON value: object"),
    ],
)
def test_presented_rejects_values_that_cannot_be_json(value: object, message: str) -> None:
    with pytest.raises(TypeError, match=message):
        Presented(cast("dict[str, object]", value))


def test_presented_requires_a_mapping_at_the_response_root() -> None:
    with pytest.raises(TypeError, match="presented value must be a JSON object"):
        Presented(cast("dict[str, object]", ["not", "an", "object"]))
