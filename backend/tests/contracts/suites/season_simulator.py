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

    def test_every_match_is_dated_inside_the_block(self, make_simulator: SimulatorFactory) -> None:
        request = make_simulation_request("b1")

        result = make_simulator().simulate_block(request)

        assert result.matches
        assert all(request.start <= m.date <= request.end for m in result.matches)

    def test_key_matches_are_matches_of_the_block(self, make_simulator: SimulatorFactory) -> None:
        result = make_simulator().simulate_block(make_simulation_request("b1"))

        fixtures = {m.fixture_id for m in result.matches}
        assert set(result.key_matches) <= fixtures
        assert {m.fixture_id for m in result.matches if m.key} == set(result.key_matches)

    def test_the_managed_players_come_back_with_their_state(
        self, make_simulator: SimulatorFactory
    ) -> None:
        request = make_simulation_request("b1")

        result = make_simulator().simulate_block(request)

        assert {s.player_id for s in result.player_states} == {
            p.player_id for p in request.managed_team.players
        }

    def test_the_opponent_of_a_match_is_one_of_its_two_sides(
        self, make_simulator: SimulatorFactory
    ) -> None:
        result = make_simulator().simulate_block(make_simulation_request("b1"))

        for match in result.matches:
            assert match.opponent in {match.home, match.away}
