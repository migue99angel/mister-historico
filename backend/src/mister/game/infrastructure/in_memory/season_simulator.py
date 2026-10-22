"""`SeasonSimulator` fake that answers with programmed results."""

from typing import TYPE_CHECKING

from mister.game.application.ports import BlockSimulationRequest, BlockSimulationResult

if TYPE_CHECKING:
    from mister.shared_kernel.ids import BlockId


class UnscriptedBlockError(LookupError):
    """The test asked for a block it did not script a result for."""


class ScriptedSeasonSimulator:
    """Returns the result scripted for the requested block and records every request."""

    def __init__(self) -> None:
        self._results: dict[BlockId, BlockSimulationResult] = {}
        self._failure: Exception | None = None
        self.requests: list[BlockSimulationRequest] = []

    def script(self, result: BlockSimulationResult) -> None:
        """Answer requests for `result.block_id` with `result`."""
        self._results[result.block_id] = result

    def fail_with(self, error: Exception | None) -> None:
        """Make every call raise `error` (until called again with `None`)."""
        self._failure = error

    def simulate_block(self, request: BlockSimulationRequest) -> BlockSimulationResult:
        self.requests.append(request)
        if self._failure is not None:
            raise self._failure
        try:
            return self._results[request.block_id]
        except KeyError:
            raise UnscriptedBlockError(f"no result scripted for block {request.block_id}") from None
