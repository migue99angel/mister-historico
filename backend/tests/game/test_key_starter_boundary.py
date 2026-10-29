"""Key starter across the Game-Simulation boundary: ports, ACL, codec and projection."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season
from tests.contracts.suites.game_samples import make_simulation_request, make_simulation_result
from tests.contracts.suites.lineup_projection import LineupProjectionContract, ProjectionCase

from mister.catalog.application.api import PlayableSeasonDTO, PlayableSeasonSummaryDTO
from mister.game.application import ports
from mister.game.application.block_codec import BlockSimulationCodec, decode_block, encode_block
from mister.game.application.closure import _simulation_request
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import RunSnapshot
from mister.game.domain.board import GoalProgress, GoalStatus
from mister.game.domain.run import Run
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.season_simulator import (
    ScriptedSeasonSimulator,
    UnscriptedBlockError,
)
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.game.infrastructure.simulation_mapping import (
    from_simulation_result,
    to_simulation_request,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import BlockId, FixtureId, PlayableSeasonId, PlayerId, RunId
from mister.shared_kernel.randomness import RandomSource
from mister.shared_kernel.seed import Seed
from mister.simulation.application import api as simulation

# Bytes of `make_simulation_result()` encoded before the key starter existed.
_LEGACY_BLOCK_SHA256 = "09f8f3f13bfff61491bd03c5243f72598b3482b711a2a337a2a46b864349f7ae"
ELEVEN = tuple(PlayerId(f"tfc-{i:02}") for i in range(1, 12))
LIGA_01 = FixtureId("tfc-liga-01")


def _outcome() -> ports.KeyStarterOutcome:
    match = make_simulation_result().matches[0]
    return ports.KeyStarterOutcome(match.fixture_id, match.date, ELEVEN[0], ELEVEN)


def _selection() -> ports.KeyStarterSelection:
    match = make_simulation_result().matches[0]
    return ports.KeyStarterSelection(match.fixture_id, match.date, ELEVEN[0])


# --------------------------------------------------------------------------- ports


def test_a_request_carries_only_a_typed_key_starter() -> None:
    request = replace(make_simulation_request(), key_starter=_selection())
    assert request.key_starter == _selection()
    with pytest.raises(InvalidValueError):
        replace(make_simulation_request(), key_starter=("fixture", "player"))


def test_a_result_carries_only_typed_key_starter_evidence() -> None:
    result = replace(make_simulation_result(), key_starter_outcome=_outcome())
    assert result.key_starter_outcome == _outcome()
    with pytest.raises(InvalidValueError):
        replace(make_simulation_result(), key_starter_outcome=object())


def test_a_projection_needs_eleven_distinct_starters_outside_the_reserves() -> None:
    with pytest.raises(InvalidValueError):
        ports.LineupProjection(ELEVEN[:10], ())
    with pytest.raises(InvalidValueError):
        ports.LineupProjection(ELEVEN, (ELEVEN[0],))
    with pytest.raises(InvalidValueError):
        ports.LineupProjection(ELEVEN, (PlayerId("r"), PlayerId("r")))
    assert ports.LineupProjection(ELEVEN, ()).reserve_ids == ()


# --------------------------------------------------------------------------- ACL


def test_the_acl_sends_the_selection_to_the_engine_and_omits_it_otherwise() -> None:
    request = make_simulation_request()

    assert to_simulation_request(request).key_starter is None
    mapped = to_simulation_request(replace(request, key_starter=_selection()))
    assert mapped.key_starter == simulation.KeyStarterSelection(
        _selection().fixture_id, _selection().date, _selection().player_id
    )


def test_the_acl_returns_the_engine_evidence_without_loss() -> None:
    outcome = simulation.KeyStarterOutcome(
        LIGA_01, _outcome().date, ELEVEN[0], ELEVEN[1:], "injured"
    )
    summary = simulation.BlockSummaryDTO(BlockId("b1"), key_starter_outcome=outcome)

    assert from_simulation_result(summary).key_starter_outcome == ports.KeyStarterOutcome(
        LIGA_01, _outcome().date, ELEVEN[0], ELEVEN[1:], "injured"
    )
    assert (
        from_simulation_result(simulation.BlockSummaryDTO(BlockId("b1"))).key_starter_outcome
        is None
    )


def test_the_adapter_projects_through_the_published_engine_api() -> None:
    class Service:
        def project_lineup(
            self, request: simulation.BlockSimRequest, fixture_id: FixtureId
        ) -> simulation.LineupProjectionDTO | None:
            self.mapped = request
            return simulation.LineupProjectionDTO(ELEVEN, (PlayerId("tfc-12"),))

        def simulate_block(
            self, request: simulation.BlockSimRequest, rng: RandomSource
        ) -> simulation.BlockSummaryDTO:
            raise AssertionError("projection must not simulate")

    service = Service()
    adapter = SimulationServiceAdapter(cast("simulation.SimulationService", service))

    projection = adapter.project_lineup(make_simulation_request(), LIGA_01)

    assert projection == ports.LineupProjection(ELEVEN, (PlayerId("tfc-12"),))
    assert service.mapped.block_id == make_simulation_request().block_id


# --------------------------------------------------------------------------- codec


def test_a_block_without_evidence_keeps_its_legacy_bytes() -> None:
    payload = encode_block(make_simulation_result())

    assert hashlib.sha256(payload).hexdigest() == _LEGACY_BLOCK_SHA256
    assert decode_block(payload).key_starter_outcome is None


def test_a_block_with_evidence_round_trips() -> None:
    result = replace(make_simulation_result(), key_starter_outcome=_outcome())

    assert decode_block(encode_block(result)) == result


def test_an_explicit_null_evidence_is_rejected_as_noncanonical() -> None:
    envelope = json.loads(encode_block(make_simulation_result()))
    envelope["result"]["fields"]["key_starter_outcome"] = None
    payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()

    with pytest.raises(InvalidValueError):
        BlockSimulationCodec.decode(payload)


# --------------------------------------------------------------------------- fake


def test_the_scripted_simulator_answers_scripted_projections_and_records_them() -> None:
    simulator = ScriptedSeasonSimulator()
    request = make_simulation_request()
    projection = ports.LineupProjection(ELEVEN, ())
    simulator.script_projection(request.block_id, LIGA_01, projection)

    assert simulator.project_lineup(request, LIGA_01) == projection
    assert simulator.projection_requests == [(request, LIGA_01)]


def test_the_scripted_simulator_can_script_an_absent_projection() -> None:
    simulator = ScriptedSeasonSimulator()
    request = make_simulation_request()
    simulator.script_projection(request.block_id, LIGA_01, None)

    assert simulator.project_lineup(request, LIGA_01) is None


def test_the_scripted_simulator_rejects_unscripted_projections_like_the_engine() -> None:
    with pytest.raises(InvalidValueError):
        ScriptedSeasonSimulator().project_lineup(make_simulation_request(), LIGA_01)
    assert issubclass(UnscriptedBlockError, LookupError)


# --------------------------------------------------------------------------- contract


def _real_case() -> ProjectionCase:
    season = build_expected_test_fc_season()
    rules = RulesConfiguration.a_profile()

    class Provider:
        def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
            return season

        def list_playable_seasons(self) -> tuple[PlayableSeasonSummaryDTO, ...]:
            return ()

    captured = CatalogRunContentAdapter(Provider()).capture_game(season.id, rules)
    run, _ = Run.start(
        RunId.parse("00000000-0000-4000-8000-000000000159"),
        season.id,
        Seed(159),
        captured.initial_state,
        captured.run_blocks,
        datetime(2026, 10, 29, tzinfo=UTC),
    )
    snapshot = RunSnapshot(
        run, tuple(GoalProgress(goal.goal_id, GoalStatus.PENDING) for goal in captured.goals)
    )
    block = captured.blocks[0]
    request = _simulation_request(snapshot, captured, block, rules)
    fixture = next(f for f in captured.fixtures if block.start <= f.date <= block.end)
    return ProjectionCase(
        lambda: SimulationServiceAdapter(simulation.SimulationService()),
        request,
        FixtureId(fixture.id),
    )


class TestScriptedLineupProjection(LineupProjectionContract):
    @pytest.fixture
    def projection_case(self) -> ProjectionCase:
        request = make_simulation_request()
        players = tuple(PlayerId(f"p-{i:02}") for i in range(14))
        pool = tuple(replace(request.managed_team.players[0], player_id=p) for p in players)
        request = replace(request, managed_team=replace(request.managed_team, players=pool))

        def make() -> ports.SeasonSimulator:
            simulator = ScriptedSeasonSimulator()
            simulator.script_projection(
                request.block_id, LIGA_01, ports.LineupProjection(players[:11], players[11:])
            )
            return simulator

        return ProjectionCase(make, request, LIGA_01)


class TestEngineLineupProjection(LineupProjectionContract):
    @pytest.fixture
    def projection_case(self) -> ProjectionCase:
        return _real_case()
