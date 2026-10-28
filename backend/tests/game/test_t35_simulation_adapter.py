from typing import cast

from tests.contracts.suites.game_samples import make_simulation_request

from mister.game.application.ports import BlockSimulationResult
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.shared_kernel.randomness import RandomSource
from mister.simulation.application.api import BlockSimRequest, BlockSummaryDTO, SimulationService


class Service:
    mapped: BlockSimRequest

    def simulate_block(self, request: BlockSimRequest, rng: RandomSource) -> BlockSummaryDTO:
        self.mapped = request
        self.rng = rng
        return BlockSummaryDTO(block_id=request.block_id)


def test_adapter_reuses_game_acl_mapping_and_calls_published_simulation_service() -> None:
    request = make_simulation_request()
    service = Service()
    result = SimulationServiceAdapter(cast("SimulationService", service)).simulate_block(request)
    assert isinstance(result, BlockSimulationResult)
    assert result.block_id == request.block_id
    assert service.mapped.season.managed_club_season_id == request.managed_team.club_season_id
    assert service.mapped.state_as_of == request.state_as_of
