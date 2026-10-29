"""Game-to-Simulation ACL around the published SimulationService facade."""

from mister.game.application.ports import (
    BlockSimulationRequest,
    BlockSimulationResult,
    LineupProjection,
)
from mister.game.infrastructure.simulation_mapping import (
    from_lineup_projection,
    from_simulation_result,
    to_simulation_request,
)
from mister.shared_kernel.ids import FixtureId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.simulation.application.api import SimulationService


class SimulationServiceAdapter:
    """Run Game requests through the existing mapping and published engine API."""

    def __init__(self, service: SimulationService) -> None:
        self._service = service

    def simulate_block(self, request: BlockSimulationRequest) -> BlockSimulationResult:
        mapped = to_simulation_request(request)
        result = self._service.simulate_block(mapped, StdlibRandomSource(request.seed))
        return from_simulation_result(result)

    def project_lineup(
        self, request: BlockSimulationRequest, fixture_id: FixtureId
    ) -> LineupProjection | None:
        projection = self._service.project_lineup(to_simulation_request(request), fixture_id)
        return None if projection is None else from_lineup_projection(projection)
