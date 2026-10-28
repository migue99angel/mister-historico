from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import cast

import pytest

from mister.game.domain.board import BlockResults
from mister.game.domain.morale import MoraleRules, PlayerMinutes
from mister.game.domain.squad_registry import Membership, SquadRegistry
from mister.game.domain.state import PlayerState, Position, RunState, Tactic, TacticStyle
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayerId


def test_results_change_team_and_managed_players_and_star_without_minutes_is_penalized() -> None:
    state = _state()
    result = MoraleRules(4, 1, -3, 80, 30, -5).apply(
        state,
        BlockResults(2, 1, 1),
        (
            PlayerMinutes(PlayerId("star"), 0, star=True),
            PlayerMinutes(PlayerId("regular"), 60, star=False),
        ),
        date(2000, 1, 31),
    )
    assert result.team_morale == 56
    assert [player.morale for player in result.players] == [51, 56, 50]
    assert result.players[0].fitness == 60
    assert result.players[0].minutes_played == 0


def test_star_penalty_requires_exact_threshold_eligibility_and_no_minutes() -> None:
    state = _state()
    result = MoraleRules(0, 0, 0, 80, 30, -5).apply(
        state,
        BlockResults(0, 0, 0),
        (
            PlayerMinutes(PlayerId("star"), 0, True, eligible=False),
            PlayerMinutes(PlayerId("regular"), 0, True, eligible=False),
            PlayerMinutes(PlayerId("rival"), 0, True),
        ),
        date(2000, 1, 31),
    )
    assert [p.morale for p in result.players] == [50, 50, 50]


def test_star_at_rating_threshold_and_exact_minimum_minutes_is_not_penalized() -> None:
    state = _state()
    state = replace(state, players=(replace(state.players[0], rating=80), *state.players[1:]))
    result = MoraleRules(0, 0, 0, 80, 30, -5).apply(
        state,
        BlockResults(0, 0, 0),
        (PlayerMinutes(PlayerId("star"), 30, True),),
        date(2000, 1, 31),
    )
    assert result.players[0].morale == 50


def test_morale_is_saturated_and_unlisted_players_and_fields_are_unchanged() -> None:
    state = _state(morale=99, team_morale=99)
    result = MoraleRules(10, 10, -10, 90, 20, -10).apply(
        state,
        BlockResults(1, 0, 0),
        (PlayerMinutes(PlayerId("star"), 20, True),),
        date(2000, 1, 31),
    )
    assert result.team_morale == 100
    assert result.players[0].morale == 100
    assert result.players[0].fitness == state.players[0].fitness
    assert result.tactic == state.tactic
    assert result.squad_registry == state.squad_registry


def test_morale_saturates_at_zero_after_losses_and_unused_star_penalty() -> None:
    state = _state(morale=1, team_morale=1)
    result = MoraleRules(0, 0, -3, 80, 30, -5).apply(
        state,
        BlockResults(0, 0, 2),
        (PlayerMinutes(PlayerId("star"), 0, True),),
        date(2000, 1, 31),
    )
    assert result.team_morale == 0
    assert result.players[0].morale == 0
    assert state.team_morale == 1
    assert state.players[0].morale == 1


@pytest.mark.parametrize(
    "args",
    [
        (PlayerId("star"), True, True),
        (PlayerId("star"), -1, True),
        (PlayerId("star"), 0, 1),
        (PlayerId("star"), 0, True, 1),
    ],
)
def test_player_minutes_reject_invalid_values(args: tuple[object, ...]) -> None:
    with pytest.raises(InvalidValueError):
        PlayerMinutes(*args)  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        PlayerMinutes(cast("PlayerId", "star"), 0, True)


@pytest.mark.parametrize(
    "args",
    [
        (1, 1, 1, 0, 1, 1),
        (1, 1, 1, 100, 1, 1),
        (1, 1, 1, 80, -1, 1),
        (True, 1, 1, 80, 1, 1),
    ],
)
def test_morale_rules_reject_invalid_threshold_or_deltas(args: tuple[object, ...]) -> None:
    with pytest.raises(InvalidValueError):
        MoraleRules(*args)  # type: ignore[arg-type]


def test_morale_rejects_bad_minutes_date_and_duplicate_ids() -> None:
    state = _state()
    rules = MoraleRules(1, 1, 1, 80, 20, -1)
    valid = PlayerMinutes(PlayerId("star"), 0, True)
    with pytest.raises(InvalidValueError):
        rules.apply(
            state, BlockResults(0, 0, 0), cast("tuple[PlayerMinutes, ...]", [valid]), date.today()
        )
    with pytest.raises(InvalidValueError):
        rules.apply(state, BlockResults(0, 0, 0), (valid, valid), date.today())
    with pytest.raises(InvalidValueError):
        rules.apply(state, BlockResults(0, 0, 0), (), cast("date", "2000-01-01"))
    with pytest.raises(InvalidValueError):
        rules.apply(cast("RunState", object()), BlockResults(0, 0, 0), (), date.today())
    with pytest.raises(InvalidValueError):
        rules.apply(state, cast("BlockResults", object()), (), date.today())


def _state(*, morale: int = 50, team_morale: int = 50) -> RunState:
    managed = ClubSeasonId("test-fc-2000-01")
    rival = ClubSeasonId("rival-fc-2000-01")
    star = PlayerId("star")
    regular = PlayerId("regular")
    registry = SquadRegistry(
        (
            Membership(star, managed),
            Membership(regular, managed),
            Membership(PlayerId("rival"), rival),
        )
    )
    return RunState(
        managed,
        registry,
        (
            PlayerState(star, Position.FW, 90, 25, morale, 60),
            PlayerState(regular, Position.MF, 70, 20, 50, 70),
            PlayerState(PlayerId("rival"), Position.FW, 80, 25, 50, 50),
        ),
        Tactic(TacticStyle.BALANCED, (2, 4, 4)),
        (),
        team_morale,
        50,
        None,
    )
