"""Pure board confidence and objective evaluation rules."""

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import cast

from mister.game.domain.run import ClosureOutcome
from mister.game.domain.state import RunState
from mister.shared_kernel.errors import InvalidValueError

_MAX_CONFIDENCE = 100


class GoalKind(StrEnum):
    """Supported private objective forms."""

    WIN = "win"
    FINISH_TOP = "finish_top"
    REACH_STAGE = "reach_stage"


class GoalStatus(StrEnum):
    """Whether an objective remains open or has a final result."""

    PENDING = "pending"
    MET = "met"
    MISSED = "missed"


class ChampionshipStatus(StrEnum):
    """Whether the relevant title is still available or has been decided."""

    OPEN = "open"
    CONFIRMED = "confirmed"
    ELIMINATED = "eliminated"


class PositionStatus(StrEnum):
    """Whether a table position is provisional or final."""

    PROVISIONAL = "provisional"
    FINAL = "final"


@dataclass(frozen=True, slots=True)
class BlockResults:
    """Non-negative match counters for one completed block."""

    wins: int
    draws: int
    losses: int

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0 for value in (self.wins, self.draws, self.losses)
        ):
            raise InvalidValueError("block result counters must be non-negative integers")


@dataclass(frozen=True, slots=True)
class GoalDefinition:
    """Minimal private objective definition."""

    goal_id: str
    competition_id: str
    kind: GoalKind
    target: int | str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.goal_id, str)
            or not self.goal_id
            or not isinstance(self.competition_id, str)
            or not self.competition_id
        ):
            raise InvalidValueError("goal and competition IDs must be non-empty strings")
        if not isinstance(self.kind, GoalKind):
            raise InvalidValueError("kind must be a GoalKind")
        valid = (
            self.target is None
            if self.kind is GoalKind.WIN
            else type(self.target) is int and self.target >= 1
            if self.kind is GoalKind.FINISH_TOP
            else isinstance(self.target, str) and bool(self.target)
        )
        if not valid:
            raise InvalidValueError("goal target is invalid for its kind")


@dataclass(frozen=True, slots=True)
class GoalProgress:
    """A goal's status at a block boundary."""

    goal_id: str
    status: GoalStatus

    def __post_init__(self) -> None:
        if (
            not isinstance(self.goal_id, str)
            or not self.goal_id
            or not isinstance(self.status, GoalStatus)
        ):
            raise InvalidValueError("goal progress requires an ID and GoalStatus")


@dataclass(frozen=True, slots=True)
class GoalFacts:
    """Explicit status, table position and ordered competition phase evidence."""

    competition_id: str
    championship: ChampionshipStatus
    position: int | None
    final_position: int | None
    stages: tuple[str, ...]
    reached_stages: tuple[str, ...]
    position_status: PositionStatus = PositionStatus.PROVISIONAL

    def __post_init__(self) -> None:
        if not isinstance(self.competition_id, str) or not self.competition_id:
            raise InvalidValueError("goal facts require a competition ID")
        if not isinstance(self.championship, ChampionshipStatus) or not isinstance(
            self.position_status, PositionStatus
        ):
            raise InvalidValueError("goal facts require valid statuses")
        if self.position_status is PositionStatus.FINAL and self.final_position is None:
            raise InvalidValueError("final position status requires final_position")
        if self.position_status is PositionStatus.PROVISIONAL and self.final_position is not None:
            raise InvalidValueError("provisional position cannot carry final_position")
        for value in (self.position, self.final_position):
            if value is not None and (type(value) is not int or value < 1):
                raise InvalidValueError("positions must be positive integers or None")
        if not isinstance(self.stages, tuple) or not isinstance(self.reached_stages, tuple):
            raise InvalidValueError("stages must be tuples")
        if any(not isinstance(s, str) or not s for s in self.stages):
            raise InvalidValueError("stages must be unique non-empty names in competition order")
        if len(set(self.stages)) != len(self.stages):
            raise InvalidValueError("stages must be unique non-empty names in competition order")
        if any(stage not in self.stages for stage in self.reached_stages):
            raise InvalidValueError("reached stages must appear in competition order")
        if tuple(s for s in self.stages if s in self.reached_stages) != self.reached_stages:
            raise InvalidValueError("reached stages must follow competition order")


@dataclass(frozen=True, slots=True)
class BoardResolution:
    """Updated immutable state and the aggregate's explicit closure decision."""

    state: RunState
    outcome: ClosureOutcome


@dataclass(frozen=True, slots=True)
class BoardRules:
    """Required balancing parameters for board confidence."""

    sacking_threshold: int
    win_delta: int
    draw_delta: int
    loss_delta: int
    objective_met_delta: int
    objective_missed_delta: int

    def __post_init__(self) -> None:
        if (
            type(self.sacking_threshold) is not int
            or not 0 <= self.sacking_threshold <= _MAX_CONFIDENCE
        ):
            raise InvalidValueError("sacking_threshold must be from 0 to 100")
        if any(
            type(v) is not int
            for v in (
                self.win_delta,
                self.draw_delta,
                self.loss_delta,
                self.objective_met_delta,
                self.objective_missed_delta,
            )
        ):
            raise InvalidValueError("board deltas must be integers")

    def resolve(
        self,
        state: RunState,
        results: BlockResults,
        previous_goals: tuple[GoalProgress, ...],
        current_goals: tuple[GoalProgress, ...],
    ) -> BoardResolution:
        """Calculate confidence from this block and objective status transitions."""
        _validate_progress(previous_goals)
        _validate_progress(current_goals)
        if {g.goal_id for g in previous_goals} != {g.goal_id for g in current_goals}:
            raise InvalidValueError("previous and current goal sets must match")
        delta = (
            results.wins * self.win_delta
            + results.draws * self.draw_delta
            + results.losses * self.loss_delta
        )
        old = {g.goal_id: g.status for g in previous_goals}
        for goal in current_goals:
            before = old[goal.goal_id]
            if before is not GoalStatus.PENDING and goal.status is not before:
                raise InvalidValueError("a finalized objective status cannot change")
            if before is GoalStatus.PENDING and goal.status is GoalStatus.MET:
                delta += self.objective_met_delta
            elif before is GoalStatus.PENDING and goal.status is GoalStatus.MISSED:
                delta += self.objective_missed_delta
        confidence = max(0, min(_MAX_CONFIDENCE, state.board_confidence + delta))
        updated = replace(state, board_confidence=confidence)
        outcome = (
            ClosureOutcome.SACKED
            if confidence < self.sacking_threshold
            else ClosureOutcome.CONTINUE
        )
        return BoardResolution(updated, outcome)


def evaluate_goals(
    goals: tuple[GoalDefinition, ...], facts: tuple[GoalFacts, ...]
) -> tuple[GoalProgress, ...]:
    """Evaluate supported goals using explicit, private competition evidence."""
    if not isinstance(goals, tuple) or any(not isinstance(goal, GoalDefinition) for goal in goals):
        raise InvalidValueError("goals must be a tuple of GoalDefinition values")
    if not isinstance(facts, tuple) or any(not isinstance(item, GoalFacts) for item in facts):
        raise InvalidValueError("facts must be a tuple of GoalFacts")
    by_competition = {item.competition_id: item for item in facts}
    if len({goal.goal_id for goal in goals}) != len(goals) or len(by_competition) != len(facts):
        raise InvalidValueError("goals and competition facts must be unique")
    evaluated: list[GoalProgress] = []
    for goal in goals:
        if goal.competition_id not in by_competition:
            raise InvalidValueError("missing facts for goal competition")
        competition = by_competition[goal.competition_id]
        if goal.kind is GoalKind.WIN:
            status = (
                GoalStatus.MET
                if competition.championship is ChampionshipStatus.CONFIRMED
                else GoalStatus.MISSED
                if competition.championship is ChampionshipStatus.ELIMINATED
                else GoalStatus.PENDING
            )
        elif goal.kind is GoalKind.FINISH_TOP:
            target = cast("int", goal.target)
            rank = (
                competition.final_position
                if competition.position_status is PositionStatus.FINAL
                else competition.position
            )
            is_final = competition.position_status is PositionStatus.FINAL
            status = (
                GoalStatus.MET
                if is_final and rank is not None and rank <= target
                else GoalStatus.MISSED
                if is_final and rank is not None
                else GoalStatus.PENDING
            )
        else:
            stage = cast("str", goal.target)
            if stage not in competition.stages:
                raise InvalidValueError(
                    "reach_stage target must be an ordered phase in its competition"
                )
            status = (
                GoalStatus.MET
                if stage in competition.reached_stages
                else GoalStatus.MISSED
                if competition.championship is not ChampionshipStatus.OPEN
                else GoalStatus.PENDING
            )
        evaluated.append(GoalProgress(goal.goal_id, status))
    return tuple(evaluated)


def _validate_progress(progress: tuple[GoalProgress, ...]) -> None:
    if not isinstance(progress, tuple) or any(
        not isinstance(item, GoalProgress) for item in progress
    ):
        raise InvalidValueError("goal progress must be a tuple of GoalProgress values")
    if len({item.goal_id for item in progress}) != len(progress):
        raise InvalidValueError("goal progress IDs must be unique")
