"""Pure application step that simulates and closes exactly one run block."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from mister.game.application import ports
from mister.game.application.block_codec import decode_block, encode_block
from mister.game.application.use_cases import RunSnapshot
from mister.game.domain.board import (
    BlockResults,
    ChampionshipStatus,
    GoalFacts,
    GoalProgress,
    GoalStatus,
    PositionStatus,
    evaluate_goals,
)
from mister.game.domain.errors import InvalidRunTransitionError
from mister.game.domain.morale import MoraleRules, PlayerMinutes
from mister.game.domain.run import BlockResolution, RunStatus
from mister.shared_kernel.errors import InvalidValueError

if TYPE_CHECKING:
    from mister.game.application.content_model import CapturedBlock, CapturedClub, CapturedSeason
    from mister.game.application.rules import RulesConfiguration
    from mister.game.domain.state import PlayerState, RunState, Tactic
    from mister.shared_kernel.events import DomainEvent
    from mister.shared_kernel.ids import PlayerId


def advance_snapshot(
    snapshot: RunSnapshot,
    captured: CapturedSeason,
    simulator: ports.SeasonSimulator,
    rules: RulesConfiguration,
    occurred_at: datetime,
) -> tuple[RunSnapshot, tuple[DomainEvent, ...]]:
    """Run the next block, resolve its objectives and morale, then advance the Run aggregate."""
    run = snapshot.run
    if run.status is not RunStatus.IN_PROGRESS:
        raise InvalidRunTransitionError("terminal runs reject commands")
    if run.pending_dilemmas:
        raise InvalidRunTransitionError("all current block dilemmas must be decided first")
    if run.blocks != captured.run_blocks:
        raise InvalidValueError("run blocks do not match captured content")
    if run.run_state.managed_club_season_id != captured.managed_club_season_id:
        raise InvalidValueError("run state managed club does not match captured content")
    block = captured.blocks[run.block_index]
    request = _simulation_request(snapshot, captured, block, rules)
    result = simulator.simulate_block(request)
    if result.block_id != block.id:
        raise InvalidValueError("simulator returned a result for another block")
    _validate_player_outcomes(run.run_state.players, result)

    goals = _resolve_goals(snapshot, captured, result)
    updated_state = _apply_physical_result(run.run_state, result)
    minutes = _player_minutes(snapshot, captured, block, result, rules)
    result_counts = BlockResults(
        sum(item.user_result is ports.UserResult.WIN for item in result.matches),
        sum(item.user_result is ports.UserResult.DRAW for item in result.matches),
        sum(item.user_result is ports.UserResult.LOSS for item in result.matches),
    )
    morale = MoraleRules(
        rules.morale.win_delta,
        rules.morale.draw_delta,
        rules.morale.loss_delta,
        rules.morale.star_rating_threshold,
        rules.morale.minimum_minutes,
        rules.morale.unused_star_delta,
    )
    updated_state = morale.apply(updated_state, result_counts, minutes, block.end)
    board = rules.board.resolve(run.run_state, result_counts, snapshot.goals, goals)
    updated_state = replace(
        updated_state,
        board_confidence=board.state.board_confidence,
        state_as_of=block.end,
    )
    resolution = BlockResolution(
        block.id,
        updated_state,
        encode_block(result),
        board.outcome,
        block.end,
    )
    advanced, events = run.advance_block(resolution, occurred_at)
    return RunSnapshot(advanced, goals), tuple(events)


def _simulation_request(
    snapshot: RunSnapshot,
    captured: CapturedSeason,
    block: CapturedBlock,
    rules: RulesConfiguration,
) -> ports.BlockSimulationRequest:
    state = snapshot.run.run_state
    active_ids = state.squad_registry.squad_on(state.managed_club_season_id, block.start)
    players = {player.player_id: player for player in state.players}
    player_pool = tuple(_pool_player(player) for player in state.players)
    managed_team = ports.TeamSquad(
        state.managed_club_season_id,
        tuple(_pool_player(players[player_id]) for player_id in active_ids),
        _tactic_setup(state.tactic),
    )
    team_overrides = tuple(
        _team_override(club, state, players, block.start)
        for club in captured.clubs
        if club.id != state.managed_club_season_id and club.has_squad
    )
    prior_results = tuple(
        match for item in snapshot.run.block_records for match in decode_block(item.payload).matches
    )
    priorities = {
        item.competition_id: ports.Priority(item.priority.value)
        for item in state.competition_priorities
    }
    forced = tuple(
        ports.ForcedInjury(item.player_id, item.injured_on, item.days)
        for item in state.forced_injuries
        if block.start <= item.injured_on <= block.end
    )
    memberships = _effective_memberships(state)
    return ports.BlockSimulationRequest(
        captured.playable_season_id,
        captured.snapshot,
        snapshot.run.seed,
        block.id,
        block.start,
        block.end,
        managed_team,
        state.team_morale,
        team_overrides,
        priorities,
        forced,
        prior_results,
        state.state_as_of,
        memberships,
        player_pool,
    )


def _team_override(
    club: CapturedClub,
    state: RunState,
    players: dict[PlayerId, PlayerState],
    on: date,
) -> ports.TeamSquad:
    player_ids = state.squad_registry.squad_on(club.id, on)
    return ports.TeamSquad(
        club.id,
        tuple(_pool_player(players[player_id]) for player_id in player_ids),
        _tactic_setup(club.default_tactic),
    )


def _effective_memberships(state: RunState) -> tuple[ports.SquadMembership, ...]:
    registry = state.squad_registry
    output: list[ports.SquadMembership] = []
    for player_id in sorted(registry.player_ids, key=lambda item: item.value):
        cuts = {date.min}
        cuts.update(
            item.joined_on
            for item in registry.base_memberships
            if item.player_id == player_id and item.joined_on is not None
        )
        for item in registry.base_memberships:
            if item.player_id == player_id and item.left_on is not None and item.left_on < date.max:
                cuts.add(item.left_on + timedelta(days=1))
        cuts.update(item.effective_on for item in registry.transfers if item.player_id == player_id)
        ordered = sorted(cuts)
        for index, start in enumerate(ordered):
            end = ordered[index + 1] - timedelta(days=1) if index + 1 < len(ordered) else date.max
            owner = registry.owner_on(player_id, start)
            if owner is None:
                continue
            interval = ports.SquadMembership(player_id, owner, start, end)
            if output and output[-1].player_id == player_id and output[-1].club_season_id == owner:
                previous = output[-1]
                if (
                    previous.left_on is not None
                    and previous.left_on < date.max
                    and previous.left_on + timedelta(days=1) == start
                ):
                    output[-1] = ports.SquadMembership(player_id, owner, previous.joined_on, end)
                    continue
            output.append(interval)
    return tuple(output)


def _pool_player(player: PlayerState) -> ports.SquadPlayerState:
    return ports.SquadPlayerState(
        player.player_id,
        ports.Position(player.position.value),
        player.rating,
        player.age,
        player.morale,
        player.fitness,
        player.injured_until,
        player.youth_minutes,
    )


def _tactic_setup(tactic: Tactic) -> ports.TacticSetup:
    return ports.TacticSetup(
        ports.TacticStyle(tactic.style.value),
        ports.TacticSystem("-".join(str(line) for line in tactic.system)),
    )


def _validate_player_outcomes(
    players: tuple[PlayerState, ...], result: ports.BlockSimulationResult
) -> None:
    player_ids = tuple(item.player_id for item in result.player_states)
    if len(player_ids) != len(set(player_ids)):
        raise InvalidValueError("simulation returned duplicate player states")
    if set(player_ids) != {item.player_id for item in players}:
        raise InvalidValueError("simulation must return state for every player in the pool")


def _apply_physical_result(state: RunState, result: ports.BlockSimulationResult) -> RunState:
    outcomes = {item.player_id: item for item in result.player_states}
    players = tuple(
        replace(
            player,
            fitness=outcomes[player.player_id].fitness,
            injured_until=outcomes[player.player_id].injured_until,
            minutes_played=player.minutes_played + outcomes[player.player_id].minutes_played,
        )
        for player in state.players
    )
    return replace(state, players=players)


def _player_minutes(
    snapshot: RunSnapshot,
    captured: CapturedSeason,
    block: CapturedBlock,
    result: ports.BlockSimulationResult,
    rules: RulesConfiguration,
) -> tuple[PlayerMinutes, ...]:
    state = snapshot.run.run_state
    outcomes = {item.player_id: item for item in result.player_states}
    own_fixtures = tuple(item for item in result.matches if item.date >= block.start)
    minutes: list[PlayerMinutes] = []
    for player in state.players:
        start_member = (
            state.squad_registry.owner_on(player.player_id, block.start)
            == state.managed_club_season_id
        )
        end_member = (
            state.squad_registry.owner_on(player.player_id, block.end)
            == state.managed_club_season_id
        )
        signed_during = any(
            item.player_id == player.player_id
            and item.to_club_season_id == state.managed_club_season_id
            and block.start <= item.effective_on <= block.end
            for item in state.squad_registry.transfers
        )
        eligible = (
            (not rules.eligibility.require_membership_at_block_start or start_member)
            and (not rules.eligibility.require_membership_at_block_end or end_member)
            and (not rules.eligibility.exempt_players_signed_during_block or not signed_during)
            and len(own_fixtures) >= rules.eligibility.minimum_team_fixtures
            and (
                not rules.eligibility.require_availability_for_all_fixtures
                or _available_for_fixtures(player, own_fixtures, result.injuries)
            )
        )
        outcome = outcomes[player.player_id]
        minutes.append(
            PlayerMinutes(
                player.player_id,
                outcome.minutes_played,
                player.rating >= rules.morale.star_rating_threshold,
                eligible,
            )
        )
    return tuple(minutes)


def _available_for_fixtures(
    player: PlayerState,
    fixtures: tuple[ports.MatchOutcome, ...],
    injuries: tuple[ports.InjuryOutcome, ...],
) -> bool:
    for fixture in fixtures:
        if player.injured_until is not None and player.injured_until > fixture.date:
            return False
        for injury in injuries:
            if injury.player_id != player.player_id:
                continue
            if (
                injury.date < fixture.date or (injury.forced and injury.date == fixture.date)
            ) and injury.date + timedelta(days=injury.days) > fixture.date:
                return False
    return True


def _resolve_goals(
    snapshot: RunSnapshot,
    captured: CapturedSeason,
    current: ports.BlockSimulationResult,
) -> tuple[GoalProgress, ...]:
    summaries = [decode_block(item.payload) for item in snapshot.run.block_records]
    summaries.append(current)
    competition_ids = tuple(dict.fromkeys(goal.competition_id for goal in captured.goals))
    facts = tuple(
        _goal_facts(captured, summaries, competition_id) for competition_id in competition_ids
    )
    evaluated = evaluate_goals(captured.goals, facts)
    previous = {item.goal_id: item.status for item in snapshot.goals}
    return tuple(
        GoalProgress(item.goal_id, previous[item.goal_id])
        if previous[item.goal_id] is not GoalStatus.PENDING
        else item
        for item in evaluated
    )


def _goal_facts(
    captured: CapturedSeason,
    summaries: list[ports.BlockSimulationResult],
    competition_id: str,
) -> GoalFacts:
    competition = next(item for item in captured.competitions if item.id.value == competition_id)
    events = tuple(
        event
        for summary in summaries
        for event in summary.events
        if event.competition_id.value == competition_id
        and event.club_season_id == captured.managed_club_season_id
    )
    championship = (
        ChampionshipStatus.CONFIRMED
        if any(item.kind is ports.EventKind.CHAMPION for item in events)
        else ChampionshipStatus.ELIMINATED
        if any(item.kind is ports.EventKind.ELIMINATED for item in events)
        else ChampionshipStatus.OPEN
    )
    stage_order = tuple(stage.id for stage in competition.stages)
    stage_matches = {
        match.stage_id
        for summary in summaries
        for match in summary.matches
        if match.competition_id.value == competition_id and match.stage_id is not None
    }
    reached_set = {item.stage_id for item in events if item.stage_id in stage_order} | (
        stage_matches & set(stage_order)
    )
    for event in events:
        if event.kind is not ports.EventKind.ADVANCED or event.stage_id not in stage_order:
            continue
        next_stage_index = stage_order.index(event.stage_id) + 1
        if next_stage_index < len(stage_order):
            reached_set.add(stage_order[next_stage_index])
    reached = tuple(stage for stage in stage_order if stage in reached_set)
    matching_tables = [
        table
        for summary in summaries
        for table in summary.standings
        if table.competition_id.value == competition_id
        and any(row.club_season_id == captured.managed_club_season_id for row in table.rows)
    ]
    if not matching_tables:
        return GoalFacts(competition_id, championship, None, None, stage_order, reached)
    table = max(matching_tables, key=lambda item: item.as_of)
    row = next(
        item for item in table.rows if item.club_season_id == captured.managed_club_season_id
    )
    final = _table_is_final(captured, summaries, table)
    if final and competition.kind == "league":
        championship = (
            ChampionshipStatus.CONFIRMED if row.position == 1 else ChampionshipStatus.ELIMINATED
        )
    return GoalFacts(
        competition_id,
        championship,
        row.position,
        row.position if final else None,
        stage_order,
        reached,
        PositionStatus.FINAL if final else PositionStatus.PROVISIONAL,
    )


def _table_is_final(
    captured: CapturedSeason,
    summaries: list[ports.BlockSimulationResult],
    table: ports.Standings,
) -> bool:
    if table.stage_id is None and table.group_id is not None:
        return False
    if table.stage_id is not None and table.group_id is None:
        return False
    if table.unresolved_ties != ():
        return False
    fixtures = tuple(
        item
        for item in captured.fixtures
        if item.competition_id.value == table.competition_id.value
        and item.stage_id == table.stage_id
        and item.group_id == table.group_id
    )
    if not fixtures:
        return False
    played = {match.fixture_id.value for summary in summaries for match in summary.matches}
    expected_played = len(fixtures)
    rows = table.rows
    return (
        bool(rows)
        and all(row.played == expected_played for row in rows)
        and all(item.id in played for item in fixtures)
    )
