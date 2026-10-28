"""Injectable CLI command factory for deterministic run replay verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer import echo

from mister.shared_kernel.ids import RunId

if TYPE_CHECKING:
    from collections.abc import Callable

    from mister.game.application.replay import ReplayResult, ReplayRun


def build_replay_command(replay_run: ReplayRun) -> Callable[[str, str], ReplayResult]:
    """Bind ReplayRun for a CLI composition root without registering a global command."""

    def replay_command(run_id: str, token: str) -> ReplayResult:
        result = replay_run.execute(RunId.parse(run_id), token)
        echo(f"Replay verified: {result.run_id}")
        return result

    return replay_command
