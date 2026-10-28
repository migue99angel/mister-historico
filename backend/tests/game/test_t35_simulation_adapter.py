from tests.contracts.suites.game_samples import make_simulation_request, make_simulation_result

from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.simulation.application.api import SimulationService


class Service:
    def simulate_block(self, request, rng):
        self.request = request
        self.rng = rng
        return make_simulation_result()


def test_adapter_reuses_game_acl_mapping_and_calls_published_simulation_service() -> None:
    request = make_simulation_request()
    service = Service()
    result = SimulationServiceAdapter(service).simulate_block(request)
    assert result == SimulationServiceAdapter._map_result(make_simulation_result())
    assert service.request.season.managed_club_season_id == request.managed_team.club_season_id


def test_adapter_accepts_the_real_simulation_facade() -> None:
    adapter = SimulationServiceAdapter(SimulationService())
    request = make_simulation_request()
    assert adapter.simulate_block(request).block_id == request.block_id
