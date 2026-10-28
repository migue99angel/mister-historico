from __future__ import annotations

from mister.game.domain.morale import MoraleRules, PlayerMinutes
from mister.game.domain.board import BlockResults
from mister.game.domain.state import PlayerState, Position, RunState, Tactic, TacticStyle
from mister.game.domain.squad_registry import Membership, SquadRegistry
from mister.shared_kernel.ids import ClubSeasonId, PlayerId


def test_results_change_team_and_managed_players_and_star_without_minutes_is_penalized() -> None:
    state = _state()
    result = MoraleRules(4, 1, -3, 80, 30, -5).apply(
        state,
        BlockResults(2, 1, 1),
        (PlayerMinutes(PlayerId("star"), 0, star=True),
         PlayerMinutes(PlayerId("regular"), 60, star=False)),
    )
    assert result.team_morale == 53
    assert [player.morale for player in result.players] == [49, 52]
    assert result.players[0].fitness == 60
    assert result.players[0].minutes_played == 0


def test_star_penalty_requires_exact_threshold_eligibility_and_no_minutes() -> None:
    state = _state()
    result = MoraleRules(0, 0, 0, 80, 30, -5).apply(
        state, BlockResults(0, 0, 0),
        (PlayerMinutes(PlayerId("star"), 0, True),
         PlayerMinutes(PlayerId("regular"), 0, True, eligible=False),
         PlayerMinutes(PlayerId("rival"), 0, True)),
    )
    assert [p.morale for p in result.players] == [45, 50]


def test_morale_is_saturated_and_unlisted_players_and_fields_are_unchanged() -> None:
    state = _state(morale=99)
    result = MoraleRules(10, 10, -10, 90, 20, -10).apply(
        state, BlockResults(1, 0, 0), (PlayerMinutes(PlayerId("star"), 20, True),)
    )
    assert result.team_morale == 100
    assert result.players[0].morale == 100
    assert result.players[0].fitness == state.players[0].fitness
    assert result.tactic == state.tactic
    assert result.squad_registry == state.squad_registry


def _state(*, morale: int = 50) -> RunState:
    managed = ClubSeasonId("test-fc-2000-01")
    rival = ClubSeasonId("rival-fc-2000-01")
    star = PlayerId("star")
    regular = PlayerId("regular")
    registry = SquadRegistry((Membership(star, managed), Membership(regular, managed)))
    return RunState(
        managed, registry,
        (PlayerState(star, Position.FW, 90, 25, morale, 60),
         PlayerState(regular, Position.MF, 70, 20, 50, 70)),
        Tactic(TacticStyle.BALANCED, (2, 4, 4)), (), 50, 50, None,
    )
