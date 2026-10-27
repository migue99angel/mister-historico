from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest

from mister.game.domain.squad_registry import SquadRegistry
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


def test_run_state_keeps_explicit_caller_values_and_is_frozen() -> None:
    player = PlayerId("player-a")
    state = RunState(
        ClubSeasonId("test-fc-2000-01"),
        SquadRegistry(),
        (PlayerState(player, Position.GK, 70, 20, 55, 60),),
        Tactic(TacticStyle.BALANCED, (2, 4, 4)),
        (),
        55,
        48,
        date(2000, 1, 1),
    )

    assert state.players[0].player_id == player
    assert state.team_morale == 55
    with pytest.raises(FrozenInstanceError):
        state.team_morale = 1  # type: ignore[misc]


@pytest.mark.parametrize("system", [(0, 4, 6), (1, 1, 1, 1, 1), (1, 9)])
def test_tactic_requires_three_to_five_lines_each_from_one_to_six_summing_to_ten(
    system: tuple[int, ...],
) -> None:
    with pytest.raises(InvalidValueError):
        Tactic(TacticStyle.POSSESSION, system)


def test_tactic_rejects_bool_as_line_value() -> None:
    with pytest.raises(InvalidValueError):
        Tactic(TacticStyle.PRESSING, (True, 4, 5))


@pytest.mark.parametrize(
    "change_player",
    [
        pytest.param(lambda player: replace(player, rating=0), id="rating-low"),
        pytest.param(lambda player: replace(player, rating=100), id="rating-high"),
        pytest.param(lambda player: replace(player, age=-1), id="negative-age"),
        pytest.param(lambda player: replace(player, morale=-1), id="morale-low"),
        pytest.param(lambda player: replace(player, morale=101), id="morale-high"),
        pytest.param(lambda player: replace(player, fitness=-1), id="fitness-low"),
        pytest.param(lambda player: replace(player, fitness=101), id="fitness-high"),
        pytest.param(lambda player: replace(player, minutes_played=-1), id="minutes-negative"),
    ],
)
def test_player_state_rejects_out_of_range_values(
    change_player: Callable[[PlayerState], PlayerState],
) -> None:
    player = PlayerState(PlayerId("player-a"), Position.MF, 70, 20, 50, 50)
    with pytest.raises(InvalidValueError):
        change_player(player)


@pytest.mark.parametrize(
    "change_player",
    [
        pytest.param(lambda player: replace(player, rating=cast("int", True)), id="rating"),
        pytest.param(lambda player: replace(player, age=cast("int", True)), id="age"),
        pytest.param(lambda player: replace(player, morale=cast("int", True)), id="morale"),
        pytest.param(lambda player: replace(player, fitness=cast("int", True)), id="fitness"),
        pytest.param(
            lambda player: replace(player, minutes_played=cast("int", True)), id="minutes"
        ),
    ],
)
def test_player_state_rejects_bool_for_integer_fields(
    change_player: Callable[[PlayerState], PlayerState],
) -> None:
    player = PlayerState(PlayerId("player-a"), Position.MF, 70, 20, 50, 50)
    with pytest.raises(InvalidValueError):
        change_player(player)


def test_run_state_requires_known_unique_player_references_and_unique_priorities() -> None:
    p = PlayerId("player-a")
    competition = CompetitionId("league-test")
    base = _make_run_state(p)
    with pytest.raises(InvalidValueError):
        replace(base, players=(base.players[0], base.players[0]))
    with pytest.raises(InvalidValueError):
        replace(
            base,
            competition_priorities=(
                CompetitionPriority(competition, Priority.HIGH),
                CompetitionPriority(competition, Priority.LOW),
            ),
        )


def test_injuries_require_known_players_and_positive_integer_days() -> None:
    player = PlayerId("player-a")
    with pytest.raises(InvalidValueError):
        ForcedInjury(player, date(2000, 1, 1), True)
    with pytest.raises(InvalidValueError):
        ForcedInjury(player, date(2000, 1, 1), 0)


def test_run_state_pool_player_without_base_membership_can_be_transferred_in() -> None:
    player = PlayerId("market-player")
    state = RunState(
        ClubSeasonId("test-fc-2000-01"),
        SquadRegistry(),
        (PlayerState(player, Position.FW, 70, None, 50, 50),),
        Tactic(TacticStyle.BALANCED, (2, 4, 4)),
        (),
        50,
        50,
        None,
    )

    moved = state.squad_registry.transfer(
        player, None, state.managed_club_season_id, date(2000, 1, 1)
    )

    assert moved.owner_on(player, date(2000, 1, 1)) == state.managed_club_season_id


def test_run_state_rejects_transfer_history_for_player_outside_known_pool() -> None:
    unknown_player = PlayerId("unknown-player")
    registry = SquadRegistry().transfer(
        unknown_player,
        None,
        ClubSeasonId("test-fc-2000-01"),
        date(2000, 1, 1),
    )

    with pytest.raises(InvalidValueError):
        RunState(
            ClubSeasonId("test-fc-2000-01"),
            registry,
            (),
            Tactic(TacticStyle.BALANCED, (2, 4, 4)),
            (),
            50,
            50,
            None,
        )


def test_run_state_rejects_non_tuple_collections_and_invalid_dates() -> None:
    player = PlayerId("player-a")
    base = _make_run_state(player)
    with pytest.raises(InvalidValueError):
        replace(base, players=cast("tuple[PlayerState, ...]", [base.players[0]]))
    with pytest.raises(InvalidValueError):
        replace(base, state_as_of=cast("date", "2000-01-01"))


def test_player_minutes_default_to_zero_without_changing_cursor() -> None:
    player = PlayerState(PlayerId("player-a"), Position.MF, 70, None, 50, 50)
    state = RunState(
        ClubSeasonId("test-fc-2000-01"),
        SquadRegistry(),
        (player,),
        Tactic(TacticStyle.BALANCED, (2, 4, 4)),
        (),
        50,
        50,
        None,
        (ForcedInjury(player.player_id, date(2000, 1, 1), 3),),
    )

    assert player.minutes_played == 0
    assert state.state_as_of is None


def test_state_value_objects_reject_invalid_enum_types() -> None:
    player = PlayerId("player-a")
    with pytest.raises(InvalidValueError):
        Tactic("balanced", (2, 4, 4))  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        Tactic(TacticStyle.BALANCED, [2, 4, 4])  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        PlayerState(player, "MF", 70, None, 50, 50)  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        PlayerState("player-a", Position.MF, 70, None, 50, 50)  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        PlayerState(player, Position.MF, 70, None, 50, 50, youth_minutes=1)  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        PlayerState(
            player,
            Position.MF,
            70,
            None,
            50,
            50,
            injured_until="2000-01-01",  # type: ignore[arg-type]
        )
    with pytest.raises(InvalidValueError):
        CompetitionPriority("league-test", Priority.HIGH)  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        CompetitionPriority(CompetitionId("league-test"), "high")  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        ForcedInjury(player, date(2000, 1, 1), True)
    with pytest.raises(InvalidValueError):
        ForcedInjury(player, "2000-01-01", 3)  # type: ignore[arg-type]


def test_run_state_rejects_invalid_collection_and_reference_types() -> None:
    player = PlayerId("player-a")
    competition = CompetitionId("league-test")
    base = _make_run_state(player)
    invalid_state_factories: tuple[Callable[[], RunState], ...] = (
        lambda: replace(base, managed_club_season_id=cast("ClubSeasonId", "test-fc-2000-01")),
        lambda: replace(base, squad_registry=cast("SquadRegistry", object())),
        lambda: replace(base, tactic=cast("Tactic", object())),
        lambda: replace(
            base,
            competition_priorities=cast(
                "tuple[CompetitionPriority, ...]",
                [CompetitionPriority(competition, Priority.HIGH)],
            ),
        ),
        lambda: replace(
            base, competition_priorities=cast("tuple[CompetitionPriority, ...]", (object(),))
        ),
        lambda: replace(
            base,
            forced_injuries=cast(
                "tuple[ForcedInjury, ...]", [ForcedInjury(player, date(2000, 1, 1), 1)]
            ),
        ),
        lambda: replace(base, forced_injuries=cast("tuple[ForcedInjury, ...]", (object(),))),
        lambda: replace(
            base,
            forced_injuries=(ForcedInjury(PlayerId("other-player"), date(2000, 1, 1), 1),),
        ),
    )
    for make_invalid_state in invalid_state_factories:
        with pytest.raises(InvalidValueError):
            make_invalid_state()


def _make_run_state(player_id: PlayerId) -> RunState:
    return RunState(
        ClubSeasonId("test-fc-2000-01"),
        SquadRegistry(),
        (PlayerState(player_id, Position.MF, 70, None, 50, 50),),
        Tactic(TacticStyle.COUNTER, (4, 3, 3)),
        (),
        50,
        50,
        None,
    )
