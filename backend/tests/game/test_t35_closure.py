"""T3.5 application closure and history mapping."""

from datetime import UTC, datetime

from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.application.api import PlayableSeasonDTO, PlayableSeasonSummaryDTO
from mister.game.application.block_codec import decode_block
from mister.game.application.content_model import CapturedSeason
from mister.game.application.ports import BlockSimulationResult, PlayerOutcome
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import RunSnapshot, apply_choice
from mister.game.domain.board import GoalProgress, GoalStatus
from mister.game.domain.events import DomainEvent
from mister.game.domain.run import Run
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.season_simulator import ScriptedSeasonSimulator
from mister.shared_kernel.ids import PlayableSeasonId, RunId
from mister.shared_kernel.seed import Seed


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
            PlayerOutcome(player.player_id, player.fitness, player.injured_until, 0)
            for player in snapshot.run.run_state.players
        ),
    )
    simulator.script(expected)

    from mister.game.application.closure import advance_snapshot

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
    assert result.run.block_index == 1
    assert result.goals == snapshot.goals
    assert all(isinstance(event, DomainEvent) for event in events)
    request = simulator.requests[0]
    assert request.squad_memberships is not None
    assert request.player_pool is not None
    assert request.state_as_of == snapshot.run.run_state.state_as_of
