"""Checks of `season.yaml`: participants, objectives, forced events and the historical outcome.

The historical outcome is also compared with what the real tables and brackets say: the
season cannot claim a title that its own standings contradict.
"""

from collections import Counter
from dataclasses import dataclass

from mister.catalog.infrastructure.content_schema.context import SeasonContext, stage_of
from mister.catalog.infrastructure.content_schema.season import (
    Competition,
    CompetitionOutcome,
    LeagueCompetition,
)

MARKET_PREFIX = "_market-"


@dataclass(frozen=True)
class Derived:
    """What the real tables and brackets say about the own team in a competition."""

    champion: bool
    final_position: int | None = None
    eliminated_in: str | None = None


def check_season_file(ctx: SeasonContext) -> None:
    """Participants, outcomes, objectives and forced events of `season.yaml`."""
    _check_participants(ctx)
    _check_outcomes(ctx)
    _check_objectives(ctx)
    _check_forced_events(ctx)


def _check_participants(ctx: SeasonContext) -> None:
    for ci, competition in enumerate(ctx.content.season.competitions):
        for pi, participant in enumerate(competition.participants):
            field = f"competitions.{ci}.participants.{pi}"
            if not ctx.exists(participant) or participant.startswith(MARKET_PREFIX):
                ctx.add("season", field, f"unknown club-season {participant!r}")
            elif isinstance(competition, LeagueCompetition) and not ctx.has_squad(participant):
                ctx.add("season", field, f"league participant {participant!r} needs a squad.yaml")


def _check_objectives(ctx: SeasonContext) -> None:
    for index, objective in enumerate(ctx.content.season.board_objectives):
        if objective.competition not in ctx.competitions:
            ctx.add(
                "season",
                f"board_objectives.{index}.competition",
                f"unknown competition {objective.competition!r}",
            )


def _check_forced_events(ctx: SeasonContext) -> None:
    for index, event in enumerate(ctx.content.season.forced_events):
        if event.player_id not in ctx.own_players:
            ctx.add(
                "season",
                f"forced_events.{index}.player_id",
                f"player {event.player_id!r} is not in the own squad",
            )


def _check_outcomes(ctx: SeasonContext) -> None:
    seen: Counter[str] = Counter()
    for index, outcome in enumerate(ctx.content.season.historical_outcome):
        seen[outcome.competition] += 1
        field = f"historical_outcome.{index}"
        competition = ctx.competitions.get(outcome.competition)
        if competition is None:
            ctx.add(
                "season", f"{field}.competition", f"unknown competition {outcome.competition!r}"
            )
            continue
        _check_outcome_shape(ctx, field, competition, outcome)
        if outcome.verify == "ok":
            _check_outcome_against_data(ctx, field, competition, outcome)
    for competition_id in ctx.competitions:
        if seen[competition_id] != 1:
            ctx.add(
                "season",
                "historical_outcome",
                f"competition {competition_id!r} needs exactly one outcome, "
                f"found {seen[competition_id]}",
            )


def _check_outcome_shape(
    ctx: SeasonContext, field: str, competition: Competition, outcome: CompetitionOutcome
) -> None:
    if isinstance(competition, LeagueCompetition):
        if outcome.final_position is None and outcome.verify == "ok":
            ctx.add("season", f"{field}.final_position", "a league outcome needs final_position")
        if outcome.eliminated_in is not None:
            ctx.add("season", f"{field}.eliminated_in", "a league has no elimination stage")
        return
    if outcome.final_position is not None:
        ctx.add("season", f"{field}.final_position", "final_position only applies to leagues")
    if outcome.eliminated_in is not None and stage_of(competition, outcome.eliminated_in) is None:
        ctx.add("season", f"{field}.eliminated_in", f"unknown stage {outcome.eliminated_in!r}")
    if not outcome.champion and outcome.eliminated_in is None and outcome.verify == "ok":
        ctx.add("season", f"{field}.eliminated_in", "a cup outcome needs champion or eliminated_in")


def _check_outcome_against_data(
    ctx: SeasonContext, field: str, competition: Competition, outcome: CompetitionOutcome
) -> None:
    derived = _derive(ctx, competition)
    if derived is None:
        return
    if outcome.champion != derived.champion:
        ctx.add(
            "season",
            f"{field}.champion",
            f"contradicts the real standings or bracket (derived champion: {derived.champion})",
        )
    if isinstance(competition, LeagueCompetition):
        if outcome.final_position is not None and outcome.final_position != derived.final_position:
            ctx.add(
                "season",
                f"{field}.final_position",
                f"contradicts the final real table (derived position: {derived.final_position})",
            )
    elif outcome.eliminated_in != derived.eliminated_in:
        ctx.add(
            "season",
            f"{field}.eliminated_in",
            f"contradicts the real standings or bracket (derived: {derived.eliminated_in})",
        )


def _derive(ctx: SeasonContext, competition: Competition) -> Derived | None:
    """Work out the own result from the tables and ties, or None when they are incomplete."""
    if isinstance(competition, LeagueCompetition):
        return _derive_league(ctx, competition)
    for stage in competition.stages:
        if stage.is_group_stage:
            verdict = _group_stage_verdict(
                ctx, competition.id, stage.id, stage.advance_per_group or 1
            )
        else:
            verdict = _tie_verdict(ctx, competition.id, stage.id)
        if verdict is None:
            return None
        if not verdict:
            return Derived(champion=False, eliminated_in=stage.id)
    if competition.stages[-1].round != "final":
        return None
    return Derived(champion=True)


def _derive_league(ctx: SeasonContext, league: LeagueCompetition) -> Derived | None:
    tables = [
        c for c in ctx.content.standings.cutoffs if c.competition == league.id and c.stage is None
    ]
    if not tables:
        return None
    latest = max(tables, key=lambda c: c.date)
    row = next((r for r in latest.table if r.club_season == ctx.own), None)
    if row is None or row.played != (len(league.participants) - 1) * league.rounds:
        return None
    return Derived(champion=row.position == 1, final_position=row.position)


def _group_stage_verdict(
    ctx: SeasonContext, competition_id: str, stage_id: str, advance: int
) -> bool | None:
    """True if the own team advanced, False if not, None if the tables cannot say."""
    tables = [
        c
        for c in ctx.content.standings.cutoffs
        if (c.competition, c.stage) == (competition_id, stage_id)
        and any(r.club_season == ctx.own for r in c.table)
    ]
    if not tables:
        return None
    latest = max(tables, key=lambda c: c.date)
    row = next(r for r in latest.table if r.club_season == ctx.own)
    return row.position <= advance


def _tie_verdict(ctx: SeasonContext, competition_id: str, stage_id: str) -> bool | None:
    ties = [
        t
        for t in ctx.content.standings.ties
        if (t.competition, t.stage) == (competition_id, stage_id) and ctx.own in t.clubs
    ]
    if not ties or ties[0].winner is None:
        return None
    return ties[0].winner == ctx.own
