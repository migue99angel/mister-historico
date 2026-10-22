"""Published API of the simulation context: DTO shape and the not-yet-implemented facade."""

import dataclasses
from datetime import date
from typing import get_type_hints

import pytest

from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.application import api
from mister.simulation.application.api import (
    AggregateTeamInput,
    BlockSimRequest,
    BlockSummaryDTO,
    CompetitionParamsDTO,
    FixtureInput,
    SeasonSimInput,
    SimulationService,
    SquadPlayerInput,
    SquadTeamInput,
    TacticDTO,
)

_ME = ClubSeasonId("test-fc-2000-01")
_RIVAL = ClubSeasonId("demo-athletic-2000-01")
_LEAGUE = CompetitionId("liga-test")


def _request() -> BlockSimRequest:
    players = tuple(
        SquadPlayerInput(PlayerId(f"player-{i}"), position="MF", rating=70) for i in range(11)
    )
    me = SquadTeamInput(_ME, players=players, tactic=TacticDTO("balanced", "4-4-2"))
    season = SeasonSimInput(
        teams=(AggregateTeamInput(_RIVAL, attack=65.0, defense=66.0),),
        competitions=(CompetitionParamsDTO(_LEAGUE, base_goals=1.3, home_advantage=1.15),),
        fixtures=(
            FixtureInput(
                FixtureId("fx-1"),
                date(2000, 9, 3),
                _LEAGUE,
                home=_ME,
                away=_RIVAL,
            ),
        ),
    )
    return BlockSimRequest(
        season=season,
        block_id=BlockId("block-1"),
        start=date(2000, 8, 1),
        end=date(2000, 10, 31),
        managed_team=me,
    )


def test_simulate_block_is_not_implemented_until_t2_6() -> None:
    rng = StdlibRandomSource(Seed(1))

    with pytest.raises(NotImplementedError, match=r"T2\.6"):
        SimulationService().simulate_block(_request(), rng)


def test_input_dtos_are_immutable_and_default_to_a_neutral_state() -> None:
    request = _request()
    player = request.managed_team.players[0]

    assert (player.morale, player.fitness, player.injured) == (50, 100, False)
    assert request.managed_team.morale == 50
    assert request.prior_results == ()
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.block_id = BlockId("block-2")  # type: ignore[misc]


def test_output_dto_can_be_empty() -> None:
    summary = BlockSummaryDTO(block_id=BlockId("block-1"))

    assert summary.results == ()
    assert summary.key_matches == ()
    assert summary.standings == ()
    assert summary.events == ()
    assert summary.injuries == ()
    assert summary.player_states == ()


def test_published_api_does_not_leak_domain_value_objects() -> None:
    dtos = [obj for obj in vars(api).values() if dataclasses.is_dataclass(obj)]

    assert dtos
    for dto in dtos:
        assert "mister.simulation.domain" not in repr(get_type_hints(dto)), dto
