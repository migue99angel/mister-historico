from __future__ import annotations

from dataclasses import replace

import pytest

from mister.game.domain.board import (
    BoardRules,
    BlockResults,
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
from mister.game.domain.state import (
    PlayerState, Position, RunState, Tactic, TacticStyle,
)
from mister.game.domain.squad_registry import SquadRegistry
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import ClubSeasonId, PlayerId


def test_losing_streak_decreases_confidence_and_sacks_below_threshold() -> None:
    state = _state(confidence=20)
    outcome = BoardRules(15, 2, 0, -3, 4, -2).resolve(
        state, BlockResults(0, 0, 3), (), ()
    )
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
        GoalDefinition("win", GoalKind.WIN),
        GoalDefinition("top", GoalKind.FINISH_TOP, 2),
        GoalDefinition("stage", GoalKind.REACH_STAGE, 1),
    )
    open_facts = GoalFacts(ChampionshipStatus.OPEN, 1, None, ("group", "final"), ("group",))
    assert [g.status for g in evaluate_goals(goals, open_facts)] == [
        GoalStatus.PENDING, GoalStatus.PENDING, GoalStatus.MET
    ]
    final_facts = GoalFacts(
        ChampionshipStatus.CONFIRMED, 3, 3, ("group", "final"), ("group",)
    )
    assert [g.status for g in evaluate_goals(goals, final_facts)] == [
        GoalStatus.MISSED, GoalStatus.MISSED, GoalStatus.MET
    ]


def test_block_results_reject_negative_counters() -> None:
    with pytest.raises(InvalidValueError):
        BlockResults(1, -1, 0)


def _state(*, confidence: int = 50) -> RunState:
    return RunState(
        ClubSeasonId("test-fc-2000-01"), SquadRegistry(),
        (PlayerState(PlayerId("player-a"), Position.MF, 70, 20, 50, 60),),
        Tactic(TacticStyle.BALANCED, (2, 4, 4)), (), 50, confidence, None,
    )
