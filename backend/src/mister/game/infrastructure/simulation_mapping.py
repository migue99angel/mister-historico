"""ACL mapping between Game DTOs and Simulation's published application API."""

import math
from typing import Literal, cast

from mister.catalog.application import api as c
from mister.game.application import ports as g
from mister.game.infrastructure.run_content_codec import decode_playable_season
from mister.shared_kernel.errors import InvalidValueError
from mister.simulation.application import api as s


def _team(team: g.TeamSquad) -> s.SquadTeamInput:
    return s.SquadTeamInput(
        team.club_season_id,
        tuple(
            s.SquadPlayerInput(
                p.player_id,
                p.position.value,
                p.rating,
                p.age,
                p.morale,
                p.fitness,
                p.injured_until,
                p.youth_minutes,
            )
            for p in team.players
        ),
        s.TacticDTO(team.tactic.style.value, team.tactic.system.value),
    )


def _season(content: c.PlayableSeasonDTO) -> s.SeasonSimInput:
    teams: list[s.TeamInput] = []
    for club in content.club_seasons:
        if club.squad is None:
            if club.aggregate is None:
                raise InvalidValueError(f"captured club season {club.id} has no playable strength")
            teams.append(
                s.AggregateTeamInput(
                    club.id, float(club.aggregate.attack), float(club.aggregate.defense)
                )
            )
        else:
            teams.append(
                s.SquadTeamInput(
                    club.id,
                    tuple(
                        s.SquadPlayerInput(p.player_id, p.position.value, p.rating, p.age)
                        for p in club.squad
                    ),
                    s.TacticDTO(club.default_tactic.style.value, club.default_tactic.system),
                )
            )
    competitions: list[s.CompetitionInput] = []
    for comp in content.competitions:
        stages = tuple(
            s.StageInput(
                stage.id,
                stage.round.value,
                cast("Literal[1, 2]", stage.legs),
                stage.away_goals_rule,
                stage.extra_time,
                stage.penalties,
                tuple(
                    s.GroupInput(group.id, group.participants) for group in stage.group_stage.groups
                )
                if stage.group_stage
                else (),
                stage.group_stage.points_per_win if stage.group_stage else None,
                stage.group_stage.points_per_draw if stage.group_stage else None,
                tuple(t.value for t in stage.group_stage.tiebreakers) if stage.group_stage else (),
                stage.group_stage.advance_per_group if stage.group_stage else None,
                stage.away_goals_in_extra_time,
                stage.group_stage.reapply_head_to_head if stage.group_stage else None,
                stage.group_stage.coefficients if stage.group_stage else (),
            )
            for stage in comp.stages
        )
        real_ties = tuple(
            s.RealTieInput(tie.stage, tie.clubs, tie.winner)
            for tie in content.real_ties
            if tie.competition_id == comp.id
        )
        total = comp.goal_baseline.matches
        competitions.append(
            s.CompetitionInput(
                comp.id,
                comp.kind.value,
                comp.tier.value,
                comp.participants,
                (comp.goal_baseline.home_goals + comp.goal_baseline.away_goals) / (2 * total),
                math.sqrt(comp.goal_baseline.home_goals / comp.goal_baseline.away_goals),
                cast("Literal[1, 2] | None", comp.league.rounds if comp.league else None),
                comp.league.points_per_win if comp.league else None,
                comp.league.points_per_draw if comp.league else None,
                tuple(t.value for t in comp.league.tiebreakers) if comp.league else (),
                stages,
                real_ties,
            )
        )
    fixtures: list[s.FixtureInput] = []
    for fixture in content.fixtures:
        own = content.club_season_id
        if fixture.venue.value == "neutral":
            slots = tuple(
                slot
                for calendar in content.knockout_calendar or ()
                for slot in calendar.slots or ()
                if slot.fixture_id == fixture.id
            )
            if len(slots) != 1:
                raise InvalidValueError(
                    f"neutral fixture {fixture.id} needs exactly one captured calendar slot"
                )
            slot = slots[0]
            home, away = slot.home, slot.away
            if {home, away} != {own, fixture.opponent}:
                raise InvalidValueError(
                    f"neutral fixture {fixture.id} calendar sides do not match its participants"
                )
        else:
            home, away = (
                (own, fixture.opponent)
                if fixture.venue.value == "home"
                else (fixture.opponent, own)
            )
        real = fixture.result
        fixtures.append(
            s.FixtureInput(
                fixture.id,
                fixture.date,
                fixture.competition_id,
                home,
                away,
                "neutral" if fixture.venue.value == "neutral" else "home",
                fixture.key,
                fixture.round,
                cast("Literal[1, 2] | None", fixture.leg),
                fixture.stage,
                fixture.group,
                s.RealResultInput(
                    real.goals_for,
                    real.goals_against,
                    real.extra_time,
                    real.penalties_for,
                    real.penalties_against,
                )
                if real
                else None,
            )
        )
    forced = tuple(
        s.ForcedInjuryDTO(event.player_id, event.date, event.days)
        for event in content.forced_events
    )
    historical = tuple(
        s.StandingsDTO(
            table.competition_id,
            table.date,
            tuple(
                s.StandingRowDTO(
                    row.club_season_id,
                    row.position,
                    row.played,
                    row.won,
                    row.drawn,
                    row.lost,
                    row.goals_for,
                    row.goals_against,
                    row.points,
                )
                for row in table.table
            ),
            table.stage,
            table.group,
        )
        for table in content.standings
    )
    evidence = (
        None
        if content.head_to_head is None
        else tuple(
            s.HeadToHeadEvidenceInput(
                item.competition_id,
                item.complete_through,
                item.covered_clubs,
                tuple(
                    s.HeadToHeadFixtureInput(
                        f.fixture_id, f.date, f.home, f.away, f.sources, f.verify, f.venue
                    )
                    for f in item.schedule
                ),
                tuple(
                    s.HeadToHeadResultInput(r.fixture_id, r.score, r.sources, r.verify)
                    for r in item.results
                ),
                item.sources,
                item.verify,
                item.stage_id,
                item.group_id,
            )
            for item in content.head_to_head
        )
    )
    calendars = (
        None
        if content.knockout_calendar is None
        else tuple(
            s.KnockoutCalendarInput(
                item.competition_id,
                None
                if item.slots is None
                else tuple(
                    s.KnockoutSlotInput(
                        slot.fixture_id,
                        slot.stage_id,
                        slot.date,
                        slot.home,
                        slot.away,
                        slot.venue,
                        slot.leg,
                        slot.sources,
                        slot.verify,
                    )
                    for slot in item.slots
                ),
                item.sources,
                item.verify,
            )
            for item in content.knockout_calendar
        )
    )
    assignments = (
        None
        if content.group_entry_assignments is None
        else tuple(
            s.GroupEntryAssignmentsInput(
                item.competition_id,
                None
                if item.entries is None
                else tuple(
                    s.GroupEntryAssignmentInput(
                        entry.source_stage_id,
                        entry.group_id,
                        entry.qualifying_position,
                        entry.target_stage_id,
                        entry.historical_representative,
                        entry.sources,
                        entry.verify,
                    )
                    for entry in item.entries
                ),
                item.sources,
                item.verify,
            )
            for item in content.group_entry_assignments
        )
    )
    return s.SeasonSimInput(
        content.club_season_id,
        tuple(teams),
        tuple(competitions),
        tuple(fixtures),
        forced,
        historical,
        evidence,
        calendars,
        assignments,
    )


def to_simulation_request(request: g.BlockSimulationRequest) -> s.BlockSimRequest:
    if request.captured_content.playable_season_id != request.playable_season_id:
        raise InvalidValueError("simulation content identity mismatch")
    content = decode_playable_season(request.captured_content)
    return s.BlockSimRequest(
        _season(content),
        request.block_id,
        request.start,
        request.end,
        _team(request.managed_team),
        request.team_morale,
        tuple(_team(team) for team in request.team_overrides),
        {key: value.value for key, value in request.competition_priorities.items()},
        tuple(
            s.ForcedInjuryDTO(i.player_id, i.date, i.days)
            for i in request.forced_injuries_from_effects
        ),
        tuple(_to_sim_result(match) for match in request.prior_results),
        request.state_as_of,
    )


def _to_sim_result(match: g.MatchOutcome) -> s.MatchResultDTO:
    return s.MatchResultDTO(
        match.fixture_id,
        match.competition_id,
        match.date,
        match.home,
        match.away,
        (match.regulation.home, match.regulation.away),
        match.venue.value,
        match.opponent,
        match.user_result.value,
        (match.extra_time.home, match.extra_time.away) if match.extra_time else None,
        (match.penalties.home, match.penalties.away) if match.penalties else None,
        match.winner.value if match.winner else None,
        match.key,
        match.round,
        match.stage_id,
        match.group_id,
        cast("Literal[1, 2] | None", match.leg),
    )


def from_simulation_result(result: s.BlockSummaryDTO) -> g.BlockSimulationResult:
    matches = tuple(
        g.MatchOutcome(
            m.fixture_id,
            m.competition_id,
            m.date,
            m.home,
            m.away,
            g.ScoreLine(*m.regulation),
            g.TeamVenue(m.venue),
            m.opponent,
            g.UserResult(m.user_result),
            g.ScoreLine(*m.extra_time) if m.extra_time else None,
            g.ScoreLine(*m.penalties) if m.penalties else None,
            g.Side(m.winner) if m.winner else None,
            m.key,
            m.round,
            m.stage_id,
            m.group_id,
            m.leg,
        )
        for m in result.results
    )
    standings = tuple(
        g.Standings(
            table.competition_id,
            table.as_of,
            tuple(
                g.StandingRow(
                    row.club_season_id,
                    row.position,
                    row.played,
                    row.won,
                    row.drawn,
                    row.lost,
                    row.goals_for,
                    row.goals_against,
                    row.points,
                )
                for row in table.rows
            ),
            table.stage_id,
            table.group_id,
            table.unresolved_ties,
        )
        for table in result.standings
    )
    ties = (
        None
        if result.unresolved_knockout_ties is None
        else tuple(
            g.UnresolvedKnockoutTie(tie.competition_id, tie.stage_id, tie.clubs, tie.fixture_ids)
            for tie in result.unresolved_knockout_ties
        )
    )
    return g.BlockSimulationResult(
        result.block_id,
        matches,
        result.key_matches,
        standings,
        tuple(
            g.BlockEvent(
                g.EventKind(event.kind),
                event.date,
                event.club_season_id,
                event.competition_id,
                event.stage_id,
            )
            for event in result.events
        ),
        tuple(
            g.InjuryOutcome(injury.player_id, injury.date, injury.days, injury.forced)
            for injury in result.injuries
        ),
        tuple(
            g.PlayerOutcome(
                state.player_id, state.fitness, state.injured_until, state.minutes_played
            )
            for state in result.player_states
        ),
        ties,
    )
