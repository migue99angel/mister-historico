"""Contract of the `SeasonSimulator` port.

Reuse: subclass `SeasonSimulatorContract` and override `make_simulator` with a factory that
returns a simulator able to answer the request `make_simulation_request()` builds. The fake is
scripted for it; the real adapter of T3.5 runs the engine over the Test FC fixture.
"""

from collections.abc import Callable

import pytest

from mister.game.application.ports import SeasonSimulator
from tests.contracts.suites.game_samples import make_simulation_request

SimulatorFactory = Callable[[], SeasonSimulator]


class SeasonSimulatorContract:
    """Behaviour every `SeasonSimulator` must have."""

    @pytest.fixture
    def make_simulator(self) -> SimulatorFactory:
        raise NotImplementedError

    def test_the_result_belongs_to_the_requested_block(
        self, make_simulator: SimulatorFactory
    ) -> None:
        request = make_simulation_request("b1")

        result = make_simulator().simulate_block(request)

        assert result.block_id == request.block_id

    def test_the_same_request_gives_the_same_result(self, make_simulator: SimulatorFactory) -> None:
        simulator = make_simulator()
        request = make_simulation_request("b1")

        assert simulator.simulate_block(request) == simulator.simulate_block(request)

    def test_a_fresh_simulator_agrees_with_another_one(
        self, make_simulator: SimulatorFactory
    ) -> None:
        request = make_simulation_request("b1")

        assert make_simulator().simulate_block(request) == make_simulator().simulate_block(request)
