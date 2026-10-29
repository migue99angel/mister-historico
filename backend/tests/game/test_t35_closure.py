"""T3.5 application closure and history mapping."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.application.api import PlayableSeasonDTO, PlayableSeasonSummaryDTO
from mister.game.application.block_codec import decode_block
from mister.game.application.closure import (
    _goal_facts,
    _player_minutes,
    _resolve_goals,
    advance_snapshot,
)
from mister.game.application.content_model import CapturedSeason
from mister.game.application.ports import (
    BlockEvent,
    BlockSimulationResult,
    EventKind,
    InjuryOutcome,
    MatchOutcome,
    PlayerOutcome,
    ScoreLine,
    StandingRow,
    Standings,
    TeamVenue,
    UserResult,
)
from mister.game.application.rules import RulesConfiguration
from mister.game.application.use_cases import RunSnapshot, apply_choice
from mister.game.domain.board import GoalProgress, GoalStatus
from mister.game.domain.errors import InvalidRunTransitionError
from mister.game.domain.run import Run
from mister.game.domain.squad_registry import Membership, SquadRegistry
from mister.game.domain.state import ForcedInjury
from mister.game.infrastructure.catalog_adapter import CatalogRunContentAdapter
from mister.game.infrastructure.in_memory.season_simulator import ScriptedSeasonSimulator
from mister.game.infrastructure.simulation_adapter import SimulationServiceAdapter
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.events import DomainEvent
from mister.shared_kernel.ids import (
    BlockId,
    ClubSeasonId,
    CompetitionId,
    FixtureId,
    PlayableSeasonId,
    RunId,
)
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
            if any(decision.dilemma_id == dilemma.id for decision in snapshot.run.decisions):
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


def test_simulation_request_expands_transfer_intervals_and_filters_future_injury() -> None:
    captured, snapshot = _captured()
    block = captured.blocks[0]
    player = snapshot.run.run_state.players[0]
    club = captured.managed_club_season_id
    rival = next(item.id for item in captured.clubs if item.id != club and item.has_squad)
    first = block.start
    registry = SquadRegistry(
        (
            Membership(player.player_id, club, first, first + timedelta(days=10)),
            Membership(
                player.player_id, rival, first + timedelta(days=20), first + timedelta(days=24)
            ),
            Membership(player.player_id, club, first + timedelta(days=30), None),
        )
    )
    registry = registry.transfer(player.player_id, club, None, first + timedelta(days=5))
    registry = registry.transfer(player.player_id, None, club, first + timedelta(days=15))
    registry = registry.transfer(player.player_id, club, rival, first + timedelta(days=25))
    registry = registry.transfer(player.player_id, rival, club, first + timedelta(days=28))
    forced_current = ForcedInjury(player.player_id, first + timedelta(days=2), 3)
    forced_future = ForcedInjury(player.player_id, block.end + timedelta(days=2), 4)
    changed_state = replace(
        snapshot.run.run_state,
        squad_registry=registry,
        forced_injuries=(forced_current, forced_future),
    )
    changed_snapshot = replace(snapshot, run=replace(snapshot.run, run_state=changed_state))

    simulator = ScriptedSeasonSimulator()
    simulator.script(
        BlockSimulationResult(
            block.id,
            (),
            (),
            (),
            (),
            (),
            tuple(
                PlayerOutcome(item.player_id, item.fitness, item.injured_until, 0)
                for item in changed_state.players
            ),
        )
    )
    closed, _ = advance_snapshot(
        changed_snapshot,
        captured,
        simulator,
        RulesConfiguration.a_profile(),
        datetime(2026, 10, 28, tzinfo=UTC),
    )
    request = simulator.requests[0]

    intervals = tuple(
        item for item in request.squad_memberships or () if item.player_id == player.player_id
    )
    assert [(item.club_season_id, item.joined_on, item.left_on) for item in intervals] == [
        (club, first, first + timedelta(days=4)),
        (club, first + timedelta(days=15), first + timedelta(days=24)),
        (rival, first + timedelta(days=25), first + timedelta(days=27)),
        (club, first + timedelta(days=28), date.max),
    ]
    assert request.forced_injuries_from_effects == (
        type(request.forced_injuries_from_effects[0])(
            player.player_id, forced_current.injured_on, 3
        ),
    )
    assert (
        next(
            item for item in request.player_pool or () if item.player_id == player.player_id
        ).injured_until
        is None
    )
    assert request.state_as_of == changed_state.state_as_of
    assert request.state_as_of != block.end
    assert (
        next(
            item for item in closed.run.run_state.players if item.player_id == player.player_id
        ).injured_until
        is None
    )
    for on in (
        first,
        first + timedelta(days=5),
        first + timedelta(days=14),
        first + timedelta(days=15),
        first + timedelta(days=20),
        first + timedelta(days=25),
        first + timedelta(days=28),
        first + timedelta(days=30),
    ):
        owner = registry.owner_on(player.player_id, on)
        matches = [
            item
            for item in intervals
            if item.joined_on is not None
            and item.left_on is not None
            and item.joined_on <= on <= item.left_on
        ]
        assert len(matches) == (0 if owner is None else 1)
        if owner is not None:
            assert matches[0].club_season_id == owner


@pytest.mark.parametrize(("unresolved_ties", "expected_final"), [(None, False), ((), True)])
def test_league_table_requires_explicitly_resolved_ties_and_all_simulated_fixtures(
    unresolved_ties: tuple[tuple[ClubSeasonId, ...], ...] | None,
    expected_final: bool,
) -> None:
    captured, _ = _captured()
    competition = next(item for item in captured.competitions if item.kind == "league")
    fixtures = tuple(item for item in captured.fixtures if item.competition_id == competition.id)
    expected_played = len(fixtures)
    rows = tuple(
        StandingRow(club, index + 1, expected_played, 0, 0, 0, 0, 0, 0)
        for index, club in enumerate(competition.participants)
    )
    table = Standings(
        competition.id,
        fixtures[-1].date,
        rows,
        unresolved_ties=unresolved_ties,
    )
    matches = tuple(
        MatchOutcome(
            FixtureId(item.id),
            item.competition_id,
            item.date,
            captured.managed_club_season_id,
            item.opponent,
            ScoreLine(0, 0),
            TeamVenue.HOME,
            item.opponent,
            UserResult.DRAW,
        )
        for item in fixtures
    )
    summary = BlockSimulationResult(
        captured.blocks[-1].id,
        matches,
        (),
        (table,),
        (),
        (),
        (),
    )

    facts = _goal_facts(captured, [summary], competition.id.value)

    assert (facts.final_position is not None) is expected_final
    if expected_final:
        assert facts.position_status.value == "final"
    else:
        assert facts.position_status.value == "provisional"


def test_unresolved_standings_tie_does_not_finalise_a_goal_position() -> None:
    captured, _ = _captured()
    competition = next(item for item in captured.competitions if item.kind == "league")
    fixtures = tuple(item for item in captured.fixtures if item.competition_id == competition.id)
    rows = tuple(
        StandingRow(club, index + 1, len(fixtures), 0, 0, 0, 0, 0, 0)
        for index, club in enumerate(competition.participants)
    )
    table = Standings(
        competition.id,
        fixtures[-1].date,
        rows,
        unresolved_ties=((competition.participants[0], competition.participants[1]),),
    )
    matches = tuple(
        MatchOutcome(
            FixtureId(item.id),
            item.competition_id,
            item.date,
            captured.managed_club_season_id,
            item.opponent,
            ScoreLine(0, 0),
            TeamVenue.HOME,
            item.opponent,
            UserResult.DRAW,
        )
        for item in fixtures
    )

    facts = _goal_facts(
        captured,
        [
            BlockSimulationResult(
                captured.blocks[-1].id,
                matches,
                (),
                (table,),
                (),
                (),
                (),
            )
        ],
        competition.id.value,
    )

    assert facts.position is not None
    assert facts.final_position is None


def test_final_goal_progress_is_irreversible_and_not_awarded_twice() -> None:
    captured, snapshot = _captured()
    goal = captured.goals[0]
    captured = replace(captured, goals=(goal,))
    snapshot = replace(
        snapshot,
        goals=(GoalProgress(goal.goal_id, GoalStatus.MET),),
    )
    confidence = snapshot.run.run_state.board_confidence
    block = captured.blocks[0]
    simulator = ScriptedSeasonSimulator()
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

    result, _ = advance_snapshot(
        snapshot,
        captured,
        simulator,
        RulesConfiguration.a_profile(),
        datetime(2026, 10, 28, tzinfo=UTC),
    )

    assert result.goals == (GoalProgress(goal.goal_id, GoalStatus.MET),)
    assert result.run.run_state.board_confidence == confidence


def test_player_availability_uses_current_state_and_fixture_date_injury_rules() -> None:
    captured, snapshot = _captured()
    block = captured.blocks[0]
    own_fixtures = tuple(
        item for item in captured.fixtures if block.start <= item.date <= block.end
    )
    player = next(
        item
        for item in snapshot.run.run_state.players
        if snapshot.run.run_state.squad_registry.owner_on(item.player_id, block.start)
        == snapshot.run.run_state.managed_club_season_id
        and snapshot.run.run_state.squad_registry.owner_on(item.player_id, block.end)
        == snapshot.run.run_state.managed_club_season_id
        and not any(
            transfer.player_id == item.player_id
            and transfer.to_club_season_id == snapshot.run.run_state.managed_club_season_id
            and block.start <= transfer.effective_on <= block.end
            for transfer in snapshot.run.run_state.squad_registry.transfers
        )
    )
    other = next(
        item for item in snapshot.run.run_state.players if item.player_id != player.player_id
    )
    matches = tuple(
        MatchOutcome(
            FixtureId(item.id),
            item.competition_id,
            item.date,
            captured.managed_club_season_id,
            item.opponent,
            ScoreLine(0, 0),
            TeamVenue.HOME,
            item.opponent,
            UserResult.DRAW,
        )
        for item in own_fixtures
    )
    outcomes = tuple(
        PlayerOutcome(item.player_id, item.fitness, item.injured_until, 0)
        for item in snapshot.run.run_state.players
    )
    base_result = BlockSimulationResult(block.id, matches, (), (), (), (), outcomes)
    first_date = matches[0].date
    prior_ending_on_match = InjuryOutcome(player.player_id, first_date - timedelta(days=1), 1)
    same_day_non_forced = InjuryOutcome(player.player_id, first_date, 2, False)
    unrelated_active_injury = InjuryOutcome(other.player_id, first_date, 5, True)

    eligible = _player_minutes(
        snapshot,
        captured,
        block,
        replace(
            base_result,
            injuries=(unrelated_active_injury, prior_ending_on_match, same_day_non_forced),
        ),
        RulesConfiguration.a_profile(),
    )
    assert next(item for item in eligible if item.player_id == player.player_id).eligible

    forced_same_day = _player_minutes(
        snapshot,
        captured,
        block,
        replace(
            base_result,
            injuries=(InjuryOutcome(player.player_id, first_date, 2, True),),
        ),
        RulesConfiguration.a_profile(),
    )
    assert not next(item for item in forced_same_day if item.player_id == player.player_id).eligible

    injured_state = replace(
        snapshot,
        run=replace(
            snapshot.run,
            run_state=replace(
                snapshot.run.run_state,
                players=tuple(
                    replace(item, injured_until=first_date + timedelta(days=1))
                    if item.player_id == player.player_id
                    else item
                    for item in snapshot.run.run_state.players
                ),
            ),
        ),
    )
    currently_injured = _player_minutes(
        injured_state,
        captured,
        block,
        base_result,
        RulesConfiguration.a_profile(),
    )
    assert not next(
        item for item in currently_injured if item.player_id == player.player_id
    ).eligible


def test_same_day_base_membership_is_exempt_like_same_day_signing() -> None:
    captured, snapshot = _captured()
    block = captured.blocks[0]
    managed = snapshot.run.run_state.managed_club_season_id
    player = snapshot.run.run_state.players[0]
    player = replace(player, rating=90)
    players = tuple(
        player if item.player_id == player.player_id else item
        for item in snapshot.run.run_state.players
    )
    rules = RulesConfiguration.a_profile()
    rules = replace(
        rules,
        eligibility=replace(rules.eligibility, minimum_team_fixtures=0),
    )
    outcomes = tuple(
        PlayerOutcome(item.player_id, item.fitness, item.injured_until, 0) for item in players
    )
    result = BlockSimulationResult(block.id, (), (), (), (), (), outcomes)

    def eligible_for(registry: SquadRegistry) -> bool:
        state = replace(
            snapshot.run.run_state,
            players=players,
            squad_registry=registry,
        )
        changed = replace(snapshot, run=replace(snapshot.run, run_state=state))
        minutes = _player_minutes(changed, captured, block, result, rules)
        entry = next(item for item in minutes if item.player_id == player.player_id)
        assert entry.star
        assert entry.minutes == 0
        return entry.eligible

    joined_at_start = SquadRegistry((Membership(player.player_id, managed, block.start, None),))
    signed_at_start = SquadRegistry().transfer(player.player_id, None, managed, block.start)
    joined_before_start = SquadRegistry(
        (Membership(player.player_id, managed, block.start - timedelta(days=1), None),)
    )

    assert eligible_for(joined_at_start) is False
    assert eligible_for(signed_at_start) is False
    assert eligible_for(joined_before_start) is True


def test_preexisting_transfer_overrides_later_base_join_date() -> None:
    captured, snapshot = _captured()
    block = captured.blocks[0]
    managed = snapshot.run.run_state.managed_club_season_id
    player = replace(snapshot.run.run_state.players[0], rating=90)
    players = tuple(
        player if item.player_id == player.player_id else item
        for item in snapshot.run.run_state.players
    )
    rival = next(item.id for item in captured.clubs if item.id != managed)
    registry = SquadRegistry(
        (
            Membership(
                player.player_id,
                rival,
                None,
                block.start - timedelta(days=10),
            ),
            Membership(player.player_id, managed, block.start, None),
        )
    ).transfer(
        player.player_id,
        rival,
        managed,
        block.start - timedelta(days=10),
    )
    state = replace(snapshot.run.run_state, players=players, squad_registry=registry)
    changed = replace(snapshot, run=replace(snapshot.run, run_state=state))
    outcomes = tuple(
        PlayerOutcome(item.player_id, item.fitness, item.injured_until, 0) for item in players
    )
    result = BlockSimulationResult(block.id, (), (), (), (), (), outcomes)
    rules = replace(
        RulesConfiguration.a_profile(),
        eligibility=replace(
            RulesConfiguration.a_profile().eligibility,
            minimum_team_fixtures=0,
        ),
    )

    entry = next(
        item
        for item in _player_minutes(changed, captured, block, result, rules)
        if item.player_id == player.player_id
    )

    assert registry.owner_on(player.player_id, block.start - timedelta(days=1)) == managed
    assert registry.owner_on(player.player_id, block.start) == managed
    assert entry.star
    assert entry.minutes == 0
    assert entry.eligible is True


def test_membership_join_at_date_min_does_not_underflow_previous_day_check() -> None:
    captured, snapshot = _captured()
    block = replace(captured.blocks[0], start=date.min)
    managed = snapshot.run.run_state.managed_club_season_id
    player = replace(snapshot.run.run_state.players[0], rating=90)
    players = tuple(
        player if item.player_id == player.player_id else item
        for item in snapshot.run.run_state.players
    )
    registry = SquadRegistry((Membership(player.player_id, managed, date.min, None),))
    state = replace(snapshot.run.run_state, players=players, squad_registry=registry)
    changed = replace(snapshot, run=replace(snapshot.run, run_state=state))
    result = BlockSimulationResult(
        block.id,
        (),
        (),
        (),
        (),
        (),
        tuple(
            PlayerOutcome(item.player_id, item.fitness, item.injured_until, 0) for item in players
        ),
    )
    base_rules = RulesConfiguration.a_profile()
    rules = replace(
        base_rules,
        eligibility=replace(base_rules.eligibility, minimum_team_fixtures=0),
    )

    entry = next(
        item
        for item in _player_minutes(changed, captured, block, result, rules)
        if item.player_id == player.player_id
    )

    assert entry.star
    assert entry.eligible is False


@pytest.mark.parametrize("result_kind", ["wrong_block", "duplicate_player", "missing_player"])
def test_closure_rejects_invalid_simulator_result_without_closing(result_kind: str) -> None:
    captured, snapshot = _captured()
    block = captured.blocks[0]
    outcomes = [
        PlayerOutcome(player.player_id, player.fitness, player.injured_until, 0)
        for player in snapshot.run.run_state.players
    ]
    result_block_id = block.id
    if result_kind == "wrong_block":
        result_block_id = captured.blocks[1].id
    elif result_kind == "duplicate_player":
        outcomes[-1] = outcomes[0]
    else:
        outcomes.pop()
    result = BlockSimulationResult(result_block_id, (), (), (), (), (), tuple(outcomes))

    class ResultSimulator:
        def __init__(self) -> None:
            self.requests: list[object] = []

        def simulate_block(self, request: object) -> BlockSimulationResult:
            self.requests.append(request)
            return result

        def project_lineup(self, request: object, fixture_id: object) -> None:
            return None

    simulator = ResultSimulator()

    with pytest.raises(InvalidValueError):
        advance_snapshot(
            snapshot,
            captured,
            simulator,
            RulesConfiguration.a_profile(),
            datetime(2026, 10, 28, tzinfo=UTC),
        )

    assert len(simulator.requests) == 1
    assert snapshot.run.block_records == ()
    assert snapshot.run.cursor is None


def test_pending_decisions_are_rejected_before_simulator_io() -> None:
    captured, _ = _captured()
    run, _ = Run.start(
        RunId.parse("00000000-0000-4000-8000-000000000102"),
        captured.playable_season_id,
        Seed(773),
        captured.initial_state,
        captured.run_blocks,
        datetime(2026, 10, 28, tzinfo=UTC),
    )
    pending = RunSnapshot(
        run,
        tuple(GoalProgress(goal.goal_id, GoalStatus.PENDING) for goal in captured.goals),
    )
    simulator = ScriptedSeasonSimulator()

    with pytest.raises(InvalidRunTransitionError, match="all current block dilemmas"):
        advance_snapshot(
            pending,
            captured,
            simulator,
            RulesConfiguration.a_profile(),
            datetime(2026, 10, 28, tzinfo=UTC),
        )

    assert simulator.requests == []


@pytest.mark.parametrize("mismatch", ["blocks", "managed_club"])
def test_captured_content_mismatch_is_rejected_before_simulator_io(mismatch: str) -> None:
    captured, snapshot = _captured()
    if mismatch == "blocks":
        changed_blocks = (
            replace(captured.blocks[0], id=BlockId("changed-block")),
            *captured.blocks[1:],
        )
        changed_captured = replace(captured, blocks=changed_blocks)
    else:
        other_club = next(
            item.id for item in captured.clubs if item.id != captured.managed_club_season_id
        )
        changed_captured = replace(captured, managed_club_season_id=other_club)
    simulator = ScriptedSeasonSimulator()

    with pytest.raises(InvalidValueError, match="captured content"):
        advance_snapshot(
            snapshot,
            changed_captured,
            simulator,
            RulesConfiguration.a_profile(),
            datetime(2026, 10, 28, tzinfo=UTC),
        )

    assert simulator.requests == []


def test_terminal_rejection_happens_without_another_simulation_request() -> None:
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
    closed, _ = advance_snapshot(
        snapshot,
        captured,
        simulator,
        RulesConfiguration.a_profile(),
        datetime(2026, 10, 28, tzinfo=UTC),
    )
    assert len(simulator.requests) == 1

    with pytest.raises(InvalidRunTransitionError, match="terminal runs"):
        advance_snapshot(
            closed,
            captured,
            simulator,
            RulesConfiguration.a_profile(),
            datetime(2026, 10, 28, tzinfo=UTC),
        )

    assert len(simulator.requests) == 1
