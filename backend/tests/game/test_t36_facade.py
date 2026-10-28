"""Published facade keeps private run failures behind stable public errors."""

import pytest

from mister.game.application.api import GameApi, RunAlreadyFinishedError
from mister.game.domain.errors import InvalidRunTransitionError


class _Noop:
    def execute(self, *args: object) -> object:
        raise InvalidRunTransitionError("terminal runs reject commands")


class _Presentation:
    def present_run(self, view: object, content: object) -> object:
        raise AssertionError("run presentation is not reached")


class _Seasons:
    def list_seasons(self) -> tuple[object, ...]:
        return ()

    def get_season(self, season_id: object) -> object:
        raise AssertionError("season presentation is not reached")


class _Hasher:
    def verify(self, token: str, token_hash: str) -> bool:
        return True


def test_decision_on_terminal_run_uses_public_finished_error() -> None:
    api = GameApi(
        start_run=_Noop(),
        get_run=_Noop(),
        take_decision=_Noop(),
        advance_block=_Noop(),
        uow=object(),
        token_hasher=_Hasher(),
        presentation=_Presentation(),
        seasons=_Seasons(),
    )

    with pytest.raises(RunAlreadyFinishedError):
        api.take_decision(None, "token", "idem-key-123", 0, None, None)
