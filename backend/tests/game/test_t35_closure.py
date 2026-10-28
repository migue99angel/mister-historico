"""T3.5 application closure and history mapping."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.application.api import PlayableSeasonDTO, PlayableSeasonSummaryDTO
from mister.game.application.block_codec import decode_block
from mister.game.application.closure import _resolve_goals, advance_snapshot
from mister.game.application.content_model import CapturedSeason
from mister.game.application.ports import (
    BlockEvent,
    BlockSimulationResult,
    EventKind,
    PlayerOutcome,
)
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import RunSnapshot, apply_choice
from mister.game.domain.board import GoalProgress, GoalStatus
from mister.game.domain.errors import InvalidRunTransitionError
from mister.game.domain.run import Run
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.season_simulator import ScriptedSeasonSimulator
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.shared_kernel.events import DomainEvent
from mister.shared_kernel.ids import CompetitionId, PlayableSeasonId, RunId
from mister.shared_kernel.seed import Seed
from mister.simulation.application.api import SimulationService


def _captured() -> tuple[CapturedSeason, RunSnapshot]:
    season = build_expected_test_fc_season()
    rules = RulesConfiguration.a_profile()

    class Provider:
        def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
            assert season_id == season.id
            return season

        def list_playable_seasons(self) -> tuple[PlayableSeasonSummaryDTO, ...]:
            return ()

    captured = CatalogRunContentAdapter(Provider()).capture_game(season.id, rules)
    run, _ = Run.start(
        RunId.parse("00000000-0000-4000-8000-000000000101"),
        season.id,
        Seed(772),
        captured.initial_state,
        captured.run_blocks,
        datetime(2026, 10, 28, tzinfo=UTC),
    )
    snapshot = RunSnapshot(
        run,
        tuple(GoalProgress(goal.goal_id, GoalStatus.PENDING) for goal in captured.goals),
    )
    for dilemma in captured.blocks[0].dilemmas:
        snapshot, _ = apply_choice(
            snapshot,
            captured,
            dilemma.id,
            dilemma.historical_option,
            datetime(2026, 10, 28, tzinfo=UTC),
        )
    return captured, snapshot


def test_advance_snapshot_simulates_and_persists_full_block_payload_and_cursor() -> None:
    captured, snapshot = _captured()
    simulator = ScriptedSeasonSimulator()
    expected = BlockSimulationResult(
        captured.blocks[0].id,
        (),
        (),
        (),
        (),
        (),
        tuple(
            PlayerOutcome(player.player_id, player.fitness, player.injured_until, 90)
            for player in snapshot.run.run_state.players
        ),
    )
    simulator.script(expected)

    result, events = advance_snapshot(
        snapshot,
        captured,
        simulator,
        RulesConfiguration.a_profile(),
        datetime(2026, 10, 28, tzinfo=UTC),
    )

    closed = result.run.block_records[-1]
    assert closed.block_id == captured.blocks[0].id
    assert decode_block(closed.payload) == expected
    assert result.run.cursor == captured.blocks[0].end
    assert result.run.run_state.state_as_of == captured.blocks[0].end
    assert all(player.minutes_played == 90 for player in result.run.run_state.players)
    assert result.run.block_index == 1
    assert result.goals == snapshot.goals
    assert all(isinstance(event, DomainEvent) for event in events)
    request = simulator.requests[0]
    assert request.squad_memberships is not None
    assert request.player_pool is not None
    assert request.state_as_of == snapshot.run.run_state.state_as_of


def test_test_fc_closure_runs_through_real_simulation_service() -> None:
    captured, snapshot = _captured()

    result, _ = advance_snapshot(
        snapshot,
        captured,
        SimulationServiceAdapter(SimulationService()),
        RulesConfiguration.a_profile(),
        datetime(2026, 10, 28, tzinfo=UTC),
    )

    assert len(result.run.block_records) == 1
    assert decode_block(result.run.block_records[0].payload).block_id == captured.blocks[0].id


def test_sacking_closes_the_current_block_and_keeps_terminal_status() -> None:
    captured, snapshot = _captured()
    low_confidence = replace(snapshot.run.run_state, board_confidence=10)
    snapshot = replace(snapshot, run=replace(snapshot.run, run_state=low_confidence))
    simulator = ScriptedSeasonSimulator()
    simulator.script(
        BlockSimulationResult(
            captured.blocks[0].id,
            (),
            (),
            (),
            (),
            (),
            tuple(
                PlayerOutcome(player.player_id, player.fitness, player.injured_until, 0)
                for player in snapshot.run.run_state.players
            ),
        )
    )

    result, events = advance_snapshot(
        snapshot,
        captured,
        simulator,
        RulesConfiguration.a_profile(),
        datetime(2026, 10, 28, tzinfo=UTC),
    )

    assert result.run.status.value == "sacked"
    assert result.run.block_index == 0
    assert len(result.run.block_records) == 1
    assert [type(event).__name__ for event in events] == ["BlockSimulated", "ManagerSacked"]
    with pytest.raises(InvalidRunTransitionError, match="terminal runs"):
        advance_snapshot(
            result,
            captured,
            simulator,
            RulesConfiguration.a_profile(),
            datetime(2026, 10, 28, tzinfo=UTC),
        )


def test_sacking_on_last_block_keeps_final_cursor_and_full_closure_history() -> None:
    captured, snapshot = _captured()
    rules = RulesConfiguration.a_profile()
    simulator = ScriptedSeasonSimulator()
    for index, block in enumerate(captured.blocks[:-1]):
        for dilemma in captured.blocks[index].dilemmas:
            if any(
                decision.dilemma_id == dilemma.id
                for decision in snapshot.run.decisions
            ):
                continue
            snapshot, _ = apply_choice(
                snapshot,
                captured,
                dilemma.id,
                dilemma.historical_option,
                datetime(2026, 10, 28, tzinfo=UTC),
            )
        simulator.script(
            BlockSimulationResult(
                block.id,
                (),
                (),
                (),
                (),
                (),
                tuple(
                    PlayerOutcome(player.player_id, player.fitness, player.injured_until, 0)
                    for player in snapshot.run.run_state.players
                ),
            )
        )
        snapshot, _ = advance_snapshot(
            snapshot, captured, simulator, rules, datetime(2026, 10, 28, tzinfo=UTC)
        )
    for dilemma in captured.blocks[-1].dilemmas:
        snapshot, _ = apply_choice(
            snapshot,
            captured,
            dilemma.id,
            dilemma.historical_option,
            datetime(2026, 10, 28, tzinfo=UTC),
        )
    snapshot = replace(
        snapshot,
        run=replace(
            snapshot.run,
            run_state=replace(snapshot.run.run_state, board_confidence=0),
        ),
    )
    final_block = captured.blocks[-1]
    simulator.script(
        BlockSimulationResult(
            final_block.id,
            (),
            (),
            (),
            (),
            (),
            tuple(
                PlayerOutcome(player.player_id, player.fitness, player.injured_until, 0)
                for player in snapshot.run.run_state.players
            ),
        )
    )
    rules = replace(rules, board=replace(rules.board, sacking_threshold=100))

    result, events = advance_snapshot(
        snapshot,
        captured,
        simulator,
        rules,
        datetime(2026, 10, 28, tzinfo=UTC),
    )

    assert result.run.status.value == "sacked"
    assert result.run.block_index == len(captured.blocks) - 1
    assert len(result.run.block_records) == len(captured.blocks)
    assert result.run.cursor == final_block.end
    assert type(events[-1]).__name__ == "ManagerSacked"


def test_advancing_from_semifinal_marks_final_stage_reached() -> None:
    captured, snapshot = _captured()
    cup_goal = next(goal for goal in captured.goals if goal.goal_id == "obj-copa")
    semifinal_result = BlockSimulationResult(
        captured.blocks[2].id,
        (),
        (),
        (),
        (
            BlockEvent(
                EventKind.ADVANCED,
                captured.blocks[2].end,
                captured.managed_club_season_id,
                CompetitionId(cup_goal.competition_id),
                "semifinal",
            ),
        ),
        (),
        (),
    )

    goals = _resolve_goals(snapshot, captured, semifinal_result)

    assert next(item for item in goals if item.goal_id == cup_goal.goal_id).status is GoalStatus.MET
