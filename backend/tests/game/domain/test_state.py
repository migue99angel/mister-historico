from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from mister.game.domain.state import CompetitionPriority, ForcedInjury, PlayerState, Position, Priority, RunState, Tactic, TacticStyle
from mister.game.domain.squad_registry import SquadRegistry
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, CompetitionId, PlayableSeasonId, PlayerId


def test_run_state_keeps_explicit_caller_values_and_is_frozen() -> None:
    player = PlayerId("player-a")
    state = RunState(
        PlayableSeasonId("test-fc-2000-01"), SquadRegistry(),
        (PlayerState(player, Position.GK, 70, 20, 55, 60),),
        Tactic(TacticStyle.BALANCED, (2, 4, 4)), (), 55, 48, date(2000, 1, 1),
    )

    assert state.players[0].player_id == player
    assert state.team_morale == 55
    with pytest.raises(FrozenInstanceError):
        state.team_morale = 1  # type: ignore[misc]


@pytest.mark.parametrize("system", [(0, 4, 6), (2, 2, 2, 2, 2), (1, 9)])
def test_tactic_requires_three_to_five_lines_each_from_one_to_six_summing_to_ten(system: tuple[int, ...]) -> None:
    with pytest.raises(InvalidValueError):
        Tactic(TacticStyle.POSSESSION, system)


def test_tactic_rejects_bool_as_line_value() -> None:
    with pytest.raises(InvalidValueError):
        Tactic(TacticStyle.PRESSING, (True, 4, 5))


@pytest.mark.parametrize("kwargs", [
    {"rating": 0}, {"rating": 100}, {"age": -1}, {"morale": -1},
    {"morale": 101}, {"fitness": -1}, {"fitness": 101},
    {"minutes_played": -1}, {"rating": True}, {"morale": True},
    {"age": True}, {"minutes_played": True},
])
def test_player_state_rejects_invalid_ranges_and_bool_integers(kwargs: dict[str, object]) -> None:
    values: dict[str, object] = dict(player_id=PlayerId("player-a"), position=Position.MF, rating=70, age=20, morale=50, fitness=50)
    values.update(kwargs)
    with pytest.raises(InvalidValueError):
        PlayerState(**values)  # type: ignore[arg-type]


def test_run_state_requires_known_unique_player_references_and_unique_priorities() -> None:
    p = PlayerId("player-a")
    competition = CompetitionId("league-test")
    base = dict(managed_club_season_id=PlayableSeasonId("test-fc-2000-01"), squad_registry=SquadRegistry(),
                players=(PlayerState(p, Position.DF, 60, None, 50, 50),),
                tactic=Tactic(TacticStyle.COUNTER, (4, 3, 3)), competition_priorities=(),
                team_morale=50, board_confidence=50, state_as_of=None)
    with pytest.raises(InvalidValueError):
        RunState(**(base | {"players": (base["players"][0], base["players"][0])}))  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        RunState(**(base | {"competition_priorities": (CompetitionPriority(competition, Priority.HIGH), CompetitionPriority(competition, Priority.LOW))}))  # type: ignore[arg-type]


def test_injuries_require_known_players_and_positive_integer_days() -> None:
    player = PlayerId("player-a")
    with pytest.raises(InvalidValueError):
        ForcedInjury(player, date(2000, 1, 1), True)
    with pytest.raises(InvalidValueError):
        ForcedInjury(player, date(2000, 1, 1), 0)
