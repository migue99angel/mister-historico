from __future__ import annotations

import pytest

from mister.game.domain.board import (
    BlockResults,
    BoardRules,
    ChampionshipStatus,
    GoalDefinition,
    GoalFacts,
    GoalKind,
    GoalProgress,
    GoalStatus,
    PositionStatus,
    evaluate_goals,
)
from mister.game.domain.run import ClosureOutcome
from mister.game.domain.squad_registry import SquadRegistry
from mister.game.domain.state import (
    PlayerState,
    Position,
    RunState,
    Tactic,
    TacticStyle,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayerId


def test_losing_streak_decreases_confidence_and_sacks_below_threshold() -> None:
    state = _state(confidence=20)
    outcome = BoardRules(15, 2, 0, -3, 4, -2).resolve(state, BlockResults(0, 0, 3), (), ())
    assert outcome.state.board_confidence == 11
    assert outcome.outcome is ClosureOutcome.SACKED


def test_equality_with_sacking_threshold_continues() -> None:
    result = BoardRules(10, 1, 0, -2, 0, 0).resolve(
        _state(confidence=12), BlockResults(0, 0, 1), (), ()
    )
    assert result.state.board_confidence == 10
    assert result.outcome is ClosureOutcome.CONTINUE


def test_met_goal_is_rewarded_only_on_transition_and_confidence_saturates() -> None:
    old = (GoalProgress("cup", GoalStatus.PENDING),)
    new = (GoalProgress("cup", GoalStatus.MET),)
    rules = BoardRules(10, 0, 0, 0, 5, -2)
    first = rules.resolve(_state(confidence=98), BlockResults(0, 0, 0), old, new)
    repeated = rules.resolve(_state(confidence=98), BlockResults(0, 0, 0), new, new)
    assert first.state.board_confidence == 100
    assert repeated.state.board_confidence == 98


def test_goal_evaluation_handles_open_and_final_win_top_and_stage() -> None:
    goals = (
        GoalDefinition("win", "cup", GoalKind.WIN),
        GoalDefinition("top", "league", GoalKind.FINISH_TOP, 2),
        GoalDefinition("stage", "cup", GoalKind.REACH_STAGE, "group"),
    )
    open_facts = (
        GoalFacts("cup", ChampionshipStatus.OPEN, None, None, ("group", "final"), ("group",)),
        GoalFacts("league", ChampionshipStatus.OPEN, 1, None, (), ()),
    )
    assert [g.status for g in evaluate_goals(goals, open_facts)] == [
        GoalStatus.PENDING,
        GoalStatus.PENDING,
        GoalStatus.MET,
    ]
    final_facts = (
        GoalFacts("cup", ChampionshipStatus.ELIMINATED, None, None, ("group", "final"), ("group",)),
        GoalFacts(
            "league", ChampionshipStatus.OPEN, 3, 3, (), (), position_status=PositionStatus.FINAL
        ),
    )
    assert [g.status for g in evaluate_goals(goals, final_facts)] == [
        GoalStatus.MISSED,
        GoalStatus.MISSED,
        GoalStatus.MET,
    ]


def test_block_results_reject_negative_counters() -> None:
    with pytest.raises(InvalidValueError):
        BlockResults(1, -1, 0)


def test_open_objectives_are_neutral_and_new_miss_is_penalized_once() -> None:
    pending = (GoalProgress("cup", GoalStatus.PENDING),)
    missed = (GoalProgress("cup", GoalStatus.MISSED),)
    rules = BoardRules(1, 0, 0, 0, 7, -4)
    neutral = rules.resolve(_state(confidence=50), BlockResults(0, 0, 0), pending, pending)
    failed = rules.resolve(_state(confidence=50), BlockResults(0, 0, 0), pending, missed)
    repeated = rules.resolve(_state(confidence=50), BlockResults(0, 0, 0), missed, missed)
    assert neutral.state.board_confidence == 50
    assert failed.state.board_confidence == 46
    assert repeated.state.board_confidence == 50


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (GoalStatus.MET, GoalStatus.PENDING),
        (GoalStatus.MISSED, GoalStatus.PENDING),
        (GoalStatus.MET, GoalStatus.MISSED),
        (GoalStatus.MISSED, GoalStatus.MET),
    ],
)
def test_final_goal_status_cannot_change(
    before: GoalStatus, after: GoalStatus
) -> None:
    rules = BoardRules(1, 0, 0, 0, 7, -4)
    with pytest.raises(InvalidValueError):
        rules.resolve(
            _state(), BlockResults(0, 0, 0),
            (GoalProgress("goal", before),), (GoalProgress("goal", after),),
        )


def test_provisional_top_position_stays_pending_until_final() -> None:
    goal = (GoalDefinition("top", "league", GoalKind.FINISH_TOP, 2),)
    provisional = (GoalFacts("league", ChampionshipStatus.OPEN, 1, None, (), ()),)
    assert evaluate_goals(goal, provisional) == (GoalProgress("top", GoalStatus.PENDING),)


def test_final_position_requires_final_position_fact() -> None:
    with pytest.raises(InvalidValueError):
        GoalFacts(
            "league", ChampionshipStatus.OPEN, 1, None, (), (),
            position_status=PositionStatus.FINAL,
        )


def test_confirmed_win_and_final_top_goal_are_met() -> None:
    goals = (
        GoalDefinition("winner", "cup", GoalKind.WIN),
        GoalDefinition("top", "league", GoalKind.FINISH_TOP, 2),
    )
    facts = (
        GoalFacts("cup", ChampionshipStatus.CONFIRMED, None, None, ("final",), ("final",)),
        GoalFacts(
            "league", ChampionshipStatus.OPEN, 1, 1, (), (),
            position_status=PositionStatus.FINAL,
        ),
    )
    assert evaluate_goals(goals, facts) == (
        GoalProgress("winner", GoalStatus.MET), GoalProgress("top", GoalStatus.MET),
    )


def test_elimination_misses_a_future_stage_but_keeps_reached_stage_met() -> None:
    goals = (
        GoalDefinition("semi", "cup", GoalKind.REACH_STAGE, "semi"),
        GoalDefinition("final", "cup", GoalKind.REACH_STAGE, "final"),
    )
    facts = (
        GoalFacts(
            "cup", ChampionshipStatus.ELIMINATED, None, None, ("group", "semi", "final"), ("group",)
        ),
    )
    assert evaluate_goals(goals, facts) == (
        GoalProgress("semi", GoalStatus.MISSED),
        GoalProgress("final", GoalStatus.MISSED),
    )


def test_block_without_matches_has_no_result_delta() -> None:
    state = _state(confidence=52)
    resolved = BoardRules(10, 2, 1, -3, 0, 0).resolve(state, BlockResults(0, 0, 0), (), ())
    assert resolved.state.board_confidence == 52


def _state(*, confidence: int = 50) -> RunState:
    return RunState(
        ClubSeasonId("test-fc-2000-01"),
        SquadRegistry(),
        (PlayerState(PlayerId("player-a"), Position.MF, 70, 20, 50, 60),),
        Tactic(TacticStyle.BALANCED, (2, 4, 4)),
        (),
        50,
        confidence,
        None,
    )
