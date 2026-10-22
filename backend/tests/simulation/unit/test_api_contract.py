"""Published API of the simulation context: DTO shape and the facade."""

import dataclasses
from datetime import date
from typing import get_type_hints

import pytest

from mister.shared_kernel.ids import BlockId, ClubSeasonId, CompetitionId, FixtureId, PlayerId
from mister.shared_kernel.randomness import StdlibRandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.application import api, simulate_block
from mister.simulation.application.api import (
    AggregateTeamInput,
    BlockSimRequest,
    BlockSummaryDTO,
    CompetitionInput,
    FixtureInput,
    ForcedInjuryDTO,
    GroupInput,
    MatchResultDTO,
    PlayerStateDTO,
    RealResultInput,
    RealTieInput,
    SeasonSimInput,
    SimulationService,
    SquadPlayerInput,
    SquadTeamInput,
    StageInput,
    StandingsDTO,
    TacticDTO,
)

_ME = ClubSeasonId("test-fc-2000-01")
_RIVAL = ClubSeasonId("demo-athletic-2000-01")
_LEAGUE = CompetitionId("liga-test")


def _me() -> SquadTeamInput:
    players = tuple(
        SquadPlayerInput(PlayerId(f"player-{i}"), position="MF", rating=70) for i in range(11)
    )
    return SquadTeamInput(_ME, players=players, tactic=TacticDTO("balanced", "4-4-2"))


def _request(**overrides: object) -> BlockSimRequest:
    league = CompetitionInput(
        _LEAGUE,
        kind="league",
        tier="domestic_league",
        participants=(_ME, _RIVAL),
        base_goals=1.3,
        home_advantage=1.15,
        rounds=2,
        points_per_win=3,
        points_per_draw=1,
        tiebreakers=("head_to_head_points", "goal_difference"),
    )
    season = SeasonSimInput(
        managed_club_season_id=_ME,
        teams=(_me(), AggregateTeamInput(_RIVAL, attack=65.0, defense=66.0)),
        competitions=(league,),
        fixtures=(
            FixtureInput(
                FixtureId("fx-1"),
                date(2000, 9, 3),
                _LEAGUE,
                home=_ME,
                away=_RIVAL,
                real_result=RealResultInput(goals_for=2, goals_against=1),
            ),
        ),
    )
    fields: dict[str, object] = {
        "season": season,
        "block_id": BlockId("block-1"),
        "start": date(2000, 8, 1),
        "end": date(2000, 10, 31),
        "managed_team": _me(),
    }
    return BlockSimRequest(**{**fields, **overrides})  # type: ignore[arg-type]


def test_simulate_block_delegates_to_the_use_case_module_until_t2_6() -> None:
    rng = StdlibRandomSource(Seed(1))

    with pytest.raises(NotImplementedError, match=r"T2\.6"):
        SimulationService().simulate_block(_request(), rng)
    with pytest.raises(NotImplementedError, match=r"T2\.6"):
        simulate_block.simulate_block(_request(), rng)


def test_the_facade_only_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """T2.6 implements `simulate_block.py` without touching `api.py`."""
    sentinel = BlockSummaryDTO(block_id=BlockId("block-1"))
    monkeypatch.setattr(simulate_block, "simulate_block", lambda request, rng: sentinel)

    result = SimulationService().simulate_block(_request(), StdlibRandomSource(Seed(1)))

    assert result is sentinel


def test_input_dtos_are_immutable_and_default_to_a_neutral_state() -> None:
    request = _request()
    player = request.managed_team.players[0]

    assert (player.morale, player.fitness) == (50, 100)
    assert (player.age, player.injured_until, player.youth_minutes) == (None, None, False)
    assert request.team_morale == 50
    assert request.team_overrides == ()
    assert request.forced_injuries_from_effects == ()
    assert request.competition_priorities == {}
    assert request.prior_results == ()
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.block_id = BlockId("block-2")  # type: ignore[misc]


def test_player_input_carries_age_injury_date_and_youth_minutes() -> None:
    player = SquadPlayerInput(
        PlayerId("p-1"),
        position="FW",
        rating=80,
        age=19,
        injured_until=date(2000, 10, 1),
        youth_minutes=True,
    )

    assert (player.age, player.injured_until, player.youth_minutes) == (19, date(2000, 10, 1), True)


def test_request_carries_overrides_team_morale_and_effect_injuries() -> None:
    injury = ForcedInjuryDTO(PlayerId("p-1"), date(2000, 9, 1), days=14)
    request = _request(
        team_morale=70,
        team_overrides=(_me(),),
        forced_injuries_from_effects=(injury,),
    )

    assert request.team_morale == 70
    assert request.team_overrides == (_me(),)
    assert request.forced_injuries_from_effects == (injury,)


def test_fixture_input_carries_the_real_result_for_p2() -> None:
    fixture = _request().season.fixtures[0]
    penalties = RealResultInput(0, 1, extra_time=True, penalties_for=4, penalties_against=3)

    assert fixture.real_result == RealResultInput(2, 1)
    assert (penalties.extra_time, penalties.penalties_for) == (True, 4)
    assert fixture.round is None


def test_competition_input_describes_league_rules_and_knockout_stages() -> None:
    league = _request().season.competitions[0]
    cup = CompetitionInput(
        CompetitionId("copa-test"),
        kind="continental_cup",
        tier="continental_primary",
        participants=(_ME, _RIVAL),
        base_goals=1.2,
        home_advantage=1.1,
        stages=(
            StageInput(
                "groups",
                round="group_stage",
                legs=2,
                away_goals_rule=False,
                extra_time=False,
                penalties=False,
                groups=(GroupInput("a", (_ME, _RIVAL)),),
                points_per_win=3,
                points_per_draw=1,
                tiebreakers=("goal_difference",),
                advance_per_group=1,
            ),
        ),
        real_ties=(RealTieInput("groups", clubs=(_ME, _RIVAL), winner=_ME),),
    )

    assert (league.kind, league.tier, league.rounds) == ("league", "domestic_league", 2)
    assert league.stages == ()
    assert league.real_ties == ()
    assert cup.stages[0].advance_per_group == 1
    assert cup.real_ties[0].winner == _ME


def test_output_dto_can_be_empty() -> None:
    summary = BlockSummaryDTO(block_id=BlockId("block-1"))

    assert summary.results == ()
    assert summary.key_matches == ()
    assert summary.standings == ()
    assert summary.events == ()
    assert summary.injuries == ()
    assert summary.player_states == ()


def test_match_result_separates_regulation_from_extra_time_and_names_venue_and_opponent() -> None:
    result = MatchResultDTO(
        fixture_id=FixtureId("fx-1"),
        competition_id=_LEAGUE,
        date=date(2000, 9, 3),
        home=_RIVAL,
        away=_ME,
        regulation=(1, 1),
        extra_time=(0, 1),
        venue="away",
        opponent=_RIVAL,
        user_result="win",
        winner="away",
        key=True,
    )

    assert (result.regulation, result.extra_time, result.penalties) == ((1, 1), (0, 1), None)
    assert (result.venue, result.opponent, result.user_result, result.key) == (
        "away",
        _RIVAL,
        "win",
        True,
    )


def test_standings_carry_stage_and_group_ids() -> None:
    table = StandingsDTO(_LEAGUE, date(2000, 10, 31), rows=(), stage_id="groups", group_id="a")

    assert (table.stage_id, table.group_id) == ("groups", "a")


def test_player_state_reports_the_minutes_played_in_the_block() -> None:
    state = PlayerStateDTO(PlayerId("p-1"), fitness=88, minutes_played=270)

    assert (state.minutes_played, state.injured_until) == (270, None)


def test_published_api_does_not_leak_domain_value_objects() -> None:
    dtos = [obj for obj in vars(api).values() if dataclasses.is_dataclass(obj)]

    assert dtos
    for dto in dtos:
        assert "mister.simulation.domain" not in repr(get_type_hints(dto)), dto
