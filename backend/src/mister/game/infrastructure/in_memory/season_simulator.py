"""`SeasonSimulator` fake that answers with programmed results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mister.shared_kernel.errors import InvalidValueError

if TYPE_CHECKING:
    from mister.game.application.ports import (
        BlockSimulationRequest,
        BlockSimulationResult,
        LineupProjection,
    )
    from mister.shared_kernel.ids import BlockId, FixtureId


class UnscriptedBlockError(LookupError):
    """The test asked for a block it did not script a result for."""


class ScriptedSeasonSimulator:
    """Returns the result scripted for the requested block and records every request."""

    def __init__(self) -> None:
        self._results: dict[BlockId, BlockSimulationResult] = {}
        self._failure: Exception | None = None
        self._projections: dict[tuple[BlockId, FixtureId], LineupProjection | None] = {}
        self.requests: list[BlockSimulationRequest] = []
        self.projection_requests: list[tuple[BlockSimulationRequest, FixtureId]] = []

    def script(self, result: BlockSimulationResult) -> None:
        """Answer requests for `result.block_id` with `result`."""
        self._results[result.block_id] = result

    def script_projection(
        self, block_id: BlockId, fixture_id: FixtureId, projection: LineupProjection | None
    ) -> None:
        """Answer projections of `fixture_id` in `block_id`; other fixtures are invalid."""
        self._projections[block_id, fixture_id] = projection

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

    def project_lineup(
        self, request: BlockSimulationRequest, fixture_id: FixtureId
    ) -> LineupProjection | None:
        self.projection_requests.append((request, fixture_id))
        key = request.block_id, fixture_id
        if key not in self._projections:
            raise InvalidValueError(f"fixture {fixture_id} is not projectable in this block")
        return self._projections[key]
