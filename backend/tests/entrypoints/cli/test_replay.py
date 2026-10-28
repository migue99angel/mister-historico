"""The replay CLI adapter is injectable and emits only verification status."""

from typing import TYPE_CHECKING, cast

import pytest

from mister.entrypoints.cli import replay as cli_replay
from mister.game.application.replay import ReplayResult, ReplayRun
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import RunId

if TYPE_CHECKING:
    from mister.game.application.use_cases import RunSnapshot


class _ReplayFake:
    def __init__(self) -> None:
        self.calls: list[tuple[RunId, str]] = []

    def execute(self, run_id: RunId, token: str) -> ReplayResult:
        self.calls.append((run_id, token))
        return ReplayResult(run_id, True, cast("RunSnapshot", object()))


def test_cli_command_uses_the_injected_replay_and_reports_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = RunId.parse("00000000-0000-4000-8000-000000000001")
    replay = _ReplayFake()
    output: list[str] = []
    monkeypatch.setattr(cli_replay, "echo", output.append)

    result = cli_replay.build_replay_command(cast("ReplayRun", replay))(str(run_id), "secret")

    assert result.verified is True
    assert replay.calls == [(run_id, "secret")]
    assert output == [f"Replay verified: {run_id}"]
    assert not hasattr(cli_replay, "app")


def test_cli_command_rejects_an_invalid_run_id_before_calling_replay() -> None:
    replay = _ReplayFake()
    command = cli_replay.build_replay_command(cast("ReplayRun", replay))

    with pytest.raises(InvalidValueError):
        command("not-a-run-id", "secret")

    assert replay.calls == []
