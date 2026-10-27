"""The Game ACL reconstructs Simulation inputs from the captured season."""

from dataclasses import replace
from datetime import date

import pytest
from tests.contracts.suites.game_samples import make_simulation_request, make_simulation_result

from mister.game.application.ports import (
    BlockSimulationRequest,
    BlockSimulationResult,
    Position,
    SquadPlayerState,
    StandingRow,
    Standings,
    TacticSetup,
    TacticStyle,
    TacticSystem,
    TeamSquad,
    UnresolvedKnockoutTie,
)
from mister.game.infrastructure.run_content_codec import decode_playable_season
from mister.game.infrastructure.simulation_mapping import (
    from_simulation_result,
    to_simulation_request,
)
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, FixtureId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.application.api import (
    BlockSummaryDTO,
    SimulationService,
    StandingRowDTO,
    StandingsDTO,
    UnresolvedKnockoutTieDTO,
)


def test_request_mapping_uses_captured_reference_and_preserves_cursor_and_changes() -> None:
    request = replace(make_simulation_request(), state_as_of=date(2000, 8, 1))

    mapped = to_simulation_request(request)

    assert mapped.season.managed_club_season_id.value == request.playable_season_id.value
    assert mapped.season.teams
    assert mapped.season.fixtures
    assert mapped.managed_team.club_season_id == request.managed_team.club_season_id
    assert mapped.team_overrides[0].club_season_id == request.team_overrides[0].club_season_id
    assert mapped.state_as_of == date(2000, 8, 1)
    assert mapped.competition_priorities == {
        key: value.value for key, value in request.competition_priorities.items()
    }


def test_catalog_goal_parameters_match_the_declared_test_fc_oracle() -> None:
    mapped = to_simulation_request(make_simulation_request())
    league = next(
        item for item in mapped.season.competitions if item.competition_id.value == "liga-test"
    )

    assert league.base_goals == pytest.approx(67 / 60)
    assert league.home_advantage == pytest.approx((40 / 27) ** 0.5)


def test_mapped_test_fc_request_runs_through_the_real_simulation_service() -> None:
    request = make_simulation_request()
    season = decode_playable_season(request.captured_content)
    own = season.own_club_season
    assert own.squad is not None
    block = season.blocks[0]
    game_request = BlockSimulationRequest(
        playable_season_id=request.playable_season_id,
        captured_content=request.captured_content,
        seed=Seed(99),
        block_id=block.id,
        start=block.start,
        end=block.end,
        managed_team=TeamSquad(
            own.id,
            tuple(
                SquadPlayerState(p.player_id, Position(p.position.value), p.rating, p.age, 50, 100)
                for p in own.squad
            ),
            TacticSetup(
                TacticStyle(own.default_tactic.style.value), TacticSystem(own.default_tactic.system)
            ),
        ),
        team_morale=50,
        team_overrides=(),
        competition_priorities={},
        forced_injuries_from_effects=(),
        prior_results=(),
    )

    summary = SimulationService().simulate_block(
        to_simulation_request(game_request), StdlibRandomSource(game_request.seed)
    )

    assert summary.block_id == block.id


@pytest.mark.parametrize(
    "unresolved",
    [
        None,
        (),
    ],
)
def test_result_mapping_preserves_none_and_empty_knockout_ties(
    unresolved: tuple[()] | None,
) -> None:
    result = make_simulation_result()
    mapped = from_simulation_result(
        BlockSummaryDTO(result.block_id, unresolved_knockout_ties=unresolved)
    )

    assert mapped.unresolved_knockout_ties == unresolved


def test_result_mapping_preserves_populated_knockout_ties_and_standings_evidence() -> None:
    own, rival = ClubSeasonId("test-fc-2000-01"), ClubSeasonId("sample-united-2000-01")
    competition = CompetitionId("copa-test")
    tie = UnresolvedKnockoutTie(competition, "semi-final", (own, rival), (FixtureId("cup-1"),))
    standings = Standings(
        CompetitionId("liga-test"),
        date(2000, 9, 30),
        (StandingRow(own, 1, 1, 1, 0, 0, 2, 0, 3), StandingRow(rival, 2, 1, 0, 0, 1, 0, 2, 0)),
        unresolved_ties=((own, rival),),
    )
    result = BlockSimulationResult(
        block_id=make_simulation_result().block_id,
        matches=(),
        key_matches=(),
        standings=(standings,),
        events=(),
        injuries=(),
        player_states=(),
        unresolved_knockout_ties=(tie,),
    )

    # Exercise the inverse with its API DTO shape as well as the Game value invariants.
    api_tie = UnresolvedKnockoutTieDTO(
        competition, "semi-final", (own, rival), (FixtureId("cup-1"),)
    )
    mapped = from_simulation_result(
        BlockSummaryDTO(
            result.block_id,
            standings=(
                StandingsDTO(
                    standings.competition_id,
                    standings.as_of,
                    (
                        StandingRowDTO(own, 1, 1, 1, 0, 0, 2, 0, 3),
                        StandingRowDTO(rival, 2, 1, 0, 0, 1, 0, 2, 0),
                    ),
                    unresolved_ties=((own, rival),),
                ),
            ),
            unresolved_knockout_ties=(api_tie,),
        )
    )
    assert mapped.unresolved_knockout_ties == (tie,)
    assert mapped.standings[0].unresolved_ties == ((own, rival),)
