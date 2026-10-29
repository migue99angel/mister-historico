"""Contract of `SeasonSimulator.project_lineup`.

Reuse: subclass `LineupProjectionContract` and override `projection_case` with a simulator,
a block request and one unplayed managed fixture of that block the simulator can project.
The fake is scripted for it; the real adapter projects the Test FC fixture with the engine.
"""

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from mister.game.application.ports import BlockSimulationRequest, SeasonSimulator
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import FixtureId


@dataclass(frozen=True)
class ProjectionCase:
    make_simulator: Callable[[], SeasonSimulator]
    request: BlockSimulationRequest
    fixture_id: FixtureId


class LineupProjectionContract:
    """Behaviour every projection of the default eleven must have."""

    @pytest.fixture
    def projection_case(self) -> ProjectionCase:
        raise NotImplementedError

    def test_a_known_fixture_projects_eleven_starters_and_disjoint_reserves(
        self, projection_case: ProjectionCase
    ) -> None:
        case = projection_case
        projection = case.make_simulator().project_lineup(case.request, case.fixture_id)

        assert projection is not None
        assert len(set(projection.starter_ids)) == 11
        assert set(projection.starter_ids).isdisjoint(projection.reserve_ids)

    def test_projected_players_come_from_the_managed_state(
        self, projection_case: ProjectionCase
    ) -> None:
        case = projection_case
        projection = case.make_simulator().project_lineup(case.request, case.fixture_id)

        known = {p.player_id for p in case.request.player_pool or case.request.managed_team.players}
        assert projection is not None
        assert {*projection.starter_ids, *projection.reserve_ids} <= known

    def test_the_same_request_gives_the_same_projection(
        self, projection_case: ProjectionCase
    ) -> None:
        case = projection_case
        simulator = case.make_simulator()

        assert simulator.project_lineup(case.request, case.fixture_id) == (
            case.make_simulator().project_lineup(case.request, case.fixture_id)
        )

    def test_an_unknown_fixture_is_invalid(self, projection_case: ProjectionCase) -> None:
        case = projection_case

        with pytest.raises(InvalidValueError):
            case.make_simulator().project_lineup(case.request, FixtureId("not-in-the-block"))
