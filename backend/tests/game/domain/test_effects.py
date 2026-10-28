from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mister.game.domain.effects import (
    BoardConfidenceEffect,
    CompetitionPriorityEffect,
    FitnessEffect,
    InjuryEffect,
    MoraleEffect,
    PlayerMoraleEffect,
    SellPlayerEffect,
    SetTacticEffect,
    SignPlayerEffect,
    YouthMinutesEffect,
    apply,
)
from mister.game.domain.squad_registry import Membership, SquadRegistry
from mister.game.domain.state import (
    CompetitionPriority,
    ForcedInjury,
    PlayerState,
    Position,
    Priority,
    RunState,
    Tactic,
    TacticStyle,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, PlayerId

if TYPE_CHECKING:
    from collections.abc import Callable

OWN = ClubSeasonId("own-season")
RIVAL = ClubSeasonId("rival-season")
PLAYER = PlayerId("player-one")
RIVAL_PLAYER = PlayerId("rival-player")
AS_OF = date(2000, 8, 1)


def state(*, as_of: date | None = AS_OF) -> RunState:
    players = (
        PlayerState(PLAYER, Position.MF, 80, 25, 50, 50),
        PlayerState(RIVAL_PLAYER, Position.FW, 70, 22, 40, 60),
    )
    return RunState(
        OWN,
        SquadRegistry((Membership(PLAYER, OWN), Membership(RIVAL_PLAYER, RIVAL))),
        players,
        Tactic(TacticStyle.BALANCED, (4, 4, 2)),
        (), 50, 50, as_of,
    )


@pytest.mark.parametrize("effect", [MoraleEffect(5), BoardConfidenceEffect(-5)])
def test_collective_effects_change_only_their_target(
    effect: MoraleEffect | BoardConfidenceEffect,
) -> None:
    result = apply(effect, state())
    if isinstance(effect, MoraleEffect):
        assert result.team_morale == 55
        assert result.board_confidence == 50
        assert result.players == state().players
    else:
        assert result.board_confidence == 45
        assert result.team_morale == 50


def test_player_morale_requires_effective_own_membership() -> None:
    result = apply(PlayerMoraleEffect(PLAYER, 8), state())
    assert next(p for p in result.players if p.player_id == PLAYER).morale == 58
    with pytest.raises(InvalidValueError):
        apply(PlayerMoraleEffect(RIVAL_PLAYER, 8), state())


def test_fitness_changes_only_own_effective_squad() -> None:
    result = apply(FitnessEffect(10), state())
    assert next(p for p in result.players if p.player_id == PLAYER).fitness == 60
    assert next(p for p in result.players if p.player_id == RIVAL_PLAYER).fitness == 60
    assert result.players[0].fitness == 60


def test_sign_from_rival_moves_ownership_at_effective_date() -> None:
    initial = state()
    result = apply(SignPlayerEffect(RIVAL_PLAYER, RIVAL, date(2000, 9, 1)), initial)
    assert result.squad_registry.owner_on(RIVAL_PLAYER, date(2000, 8, 31)) == RIVAL
    assert result.squad_registry.owner_on(RIVAL_PLAYER, date(2000, 9, 1)) == OWN
    assert initial.squad_registry.owner_on(RIVAL_PLAYER, date(2000, 9, 1)) == RIVAL


def test_explicit_resolution_date_sees_future_transfer_without_advancing_cursor() -> None:
    initial = state()
    effective = date(2000, 9, 1)
    transferred = apply(
        SignPlayerEffect(RIVAL_PLAYER, RIVAL, effective), initial, on=effective
    )
    changed = apply(PlayerMoraleEffect(RIVAL_PLAYER, 5), transferred, on=effective)
    assert next(p for p in changed.players if p.player_id == RIVAL_PLAYER).morale == 45
    assert changed.state_as_of == AS_OF
    assert initial.state_as_of == AS_OF


def test_sign_from_market_requires_player_to_be_unowned() -> None:
    free = replace(state(), squad_registry=SquadRegistry((Membership(PLAYER, OWN),)))
    signed = apply(SignPlayerEffect(RIVAL_PLAYER, None, date(2000, 9, 1)), free)
    assert signed.squad_registry.owner_on(RIVAL_PLAYER, date(2000, 9, 1)) == OWN
    with pytest.raises(InvalidValueError):
        apply(SignPlayerEffect(PLAYER, None, date(2000, 9, 1)), free)


def test_sell_player_moves_own_player_to_rival() -> None:
    result = apply(SellPlayerEffect(PLAYER, RIVAL, date(2000, 9, 1)), state())
    assert result.squad_registry.owner_on(PLAYER, date(2000, 8, 31)) == OWN
    assert result.squad_registry.owner_on(PLAYER, date(2000, 9, 1)) == RIVAL


def test_set_tactic_replaces_only_tactic() -> None:
    tactic = Tactic(TacticStyle.PRESSING, (3, 5, 2))
    result = apply(SetTacticEffect(tactic), state())
    assert result.tactic == tactic


def test_competition_priority_adds_new_competition() -> None:
    competition = CompetitionId("league")
    result = apply(CompetitionPriorityEffect(competition, Priority.HIGH), state())
    assert result.competition_priorities == (CompetitionPriority(competition, Priority.HIGH),)


def test_youth_minutes_marks_player_without_changing_rating_or_minutes() -> None:
    result = apply(YouthMinutesEffect(PLAYER), state())
    assert result.players[0].youth_minutes is True
    assert result.players[0].rating == 80
    assert result.players[0].minutes_played == 0


def test_injury_is_scheduled_without_premature_player_injury() -> None:
    result = apply(InjuryEffect(PLAYER, date(2000, 10, 1), 14), state())
    assert result.forced_injuries == (ForcedInjury(PLAYER, date(2000, 10, 1), 14),)
    assert result.players[0].injured_until is None


@given(
    st.lists(
        st.tuples(
            st.integers(-20, 20),
            st.integers(-25, 25),
            st.integers(-30, 30),
            st.integers(-30, 30),
        ),
        min_size=0,
        max_size=40,
    )
)
def test_morale_confidence_and_fitness_stay_bounded_after_any_effect_sequence(
    deltas: list[tuple[int, int, int, int]],
) -> None:
    current = state()
    for morale_delta, board_delta, fitness_delta, player_fitness_delta in deltas:
        current = apply(MoraleEffect(morale_delta), current)
        current = apply(BoardConfidenceEffect(board_delta), current)
        current = apply(FitnessEffect(fitness_delta), current)
        current = apply(FitnessEffect(player_fitness_delta, PLAYER), current)
    assert 0 <= current.team_morale <= 100
    assert 0 <= current.board_confidence <= 100
    assert 0 <= current.players[0].fitness <= 100


def test_effect_numeric_bounds_accept_their_endpoints() -> None:
    assert MoraleEffect(-20).delta == -20
    assert MoraleEffect(20).delta == 20
    assert PlayerMoraleEffect(PLAYER, -30).delta == -30
    assert PlayerMoraleEffect(PLAYER, 30).delta == 30
    assert BoardConfidenceEffect(-25).delta == -25
    assert BoardConfidenceEffect(25).delta == 25
    assert FitnessEffect(-30).delta == -30
    assert FitnessEffect(30).delta == 30
    assert InjuryEffect(PLAYER, AS_OF, 365).days == 365
    invalid_effects: tuple[Callable[[], object], ...] = (
        lambda: MoraleEffect(True),
        lambda: PlayerMoraleEffect(PLAYER, True),
        lambda: BoardConfidenceEffect(False),
        lambda: FitnessEffect(True),
        lambda: InjuryEffect(PLAYER, AS_OF, True),
        lambda: InjuryEffect(PLAYER, AS_OF, 366),
    )
    for invalid in invalid_effects:
        with pytest.raises(InvalidValueError):
            invalid()


def test_effect_deltas_saturate_without_accepting_bool_as_number() -> None:
    current = replace(state(), team_morale=95, board_confidence=5)
    assert apply(MoraleEffect(20), current).team_morale == 100
    assert apply(BoardConfidenceEffect(-25), current).board_confidence == 0
    changed_player = replace(current.players[0], fitness=95)
    current = replace(current, players=(changed_player, current.players[1]))
    assert apply(FitnessEffect(30, PLAYER), current).players[0].fitness == 100
    with pytest.raises(InvalidValueError):
        MoraleEffect(True)
    with pytest.raises(InvalidValueError):
        FitnessEffect(False)


def test_individual_membership_requires_state_date_and_rejects_unknown_or_rival() -> None:
    with pytest.raises(InvalidValueError):
        apply(PlayerMoraleEffect(PLAYER, 1), state(as_of=None))
    with pytest.raises(InvalidValueError):
        apply(PlayerMoraleEffect(RIVAL_PLAYER, 1), state())


def test_sign_rejects_wrong_origin_and_unknown_player() -> None:
    with pytest.raises(InvalidValueError):
        apply(SignPlayerEffect(RIVAL_PLAYER, OWN, date(2000, 9, 1)), state())
    with pytest.raises(InvalidValueError):
        apply(SignPlayerEffect(PlayerId("missing-player"), None, date(2000, 9, 1)), state())


def test_two_transfers_for_one_player_cannot_share_effective_date() -> None:
    effective = date(2000, 9, 1)
    free = replace(state(), squad_registry=SquadRegistry((Membership(RIVAL_PLAYER, RIVAL),)))
    signed = apply(SignPlayerEffect(PLAYER, None, effective), free)
    with pytest.raises(InvalidValueError):
        apply(SellPlayerEffect(PLAYER, RIVAL, effective), signed)


def test_market_sale_removes_player_from_all_squads() -> None:
    result = apply(SellPlayerEffect(PLAYER, None, date(2000, 9, 1)), state())
    assert result.squad_registry.owner_on(PLAYER, date(2000, 9, 1)) is None


def test_competition_priority_update_keeps_stable_order() -> None:
    first, second = CompetitionId("league"), CompetitionId("cup")
    current = replace(
        state(),
        competition_priorities=(
            CompetitionPriority(first, Priority.LOW),
            CompetitionPriority(second, Priority.NORMAL),
        ),
    )
    result = apply(CompetitionPriorityEffect(first, Priority.HIGH), current)
    assert result.competition_priorities == (
        CompetitionPriority(first, Priority.HIGH),
        CompetitionPriority(second, Priority.NORMAL),
    )
