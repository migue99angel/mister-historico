"""Validate explicit competition calendars and qualifying assignments without inventing paths."""

from collections import defaultdict
from datetime import date
from itertools import pairwise
from typing import NamedTuple

from mister.catalog.infrastructure.content_schema.base import season_window
from mister.catalog.infrastructure.content_schema.competitions import (
    GroupEntryAssignment,
    GroupEntryAssignments,
    KnockoutCalendar,
    KnockoutSlot,
)
from mister.catalog.infrastructure.content_schema.context import SeasonContext, stage_of
from mister.catalog.infrastructure.content_schema.season import TWO_LEGS, LeagueCompetition, Stage
from mister.catalog.infrastructure.content_schema.standings import StandingsCutoff


def check_competition_completion(ctx: SeasonContext) -> None:
    """Check every supplied declaration; omission remains unknown in development."""
    seen: set[str] = set()
    for index, declaration in enumerate(ctx.content.standings.knockout_calendar or ()):
        field = f"knockout_calendar.{index}"
        if declaration.competition in seen:
            ctx.add("standings", field, "duplicate competition calendar")
        seen.add(declaration.competition)
        _check_calendar(ctx, field, declaration)
    _check_global_ids(ctx)
    seen.clear()
    for index, assignments in enumerate(ctx.content.standings.group_entry_assignments or ()):
        field = f"group_entry_assignments.{index}"
        if assignments.competition in seen:
            ctx.add("standings", field, "duplicate competition entry assignments")
        seen.add(assignments.competition)
        _check_entries(ctx, field, assignments)


def _check_calendar(ctx: SeasonContext, field: str, declaration: KnockoutCalendar) -> None:
    competition = ctx.competitions.get(declaration.competition)
    if competition is None or isinstance(competition, LeagueCompetition):
        ctx.add("standings", field, "calendar requires a knockout competition")
        return
    grouped: dict[tuple[str, frozenset[str]], list[KnockoutSlot]] = defaultdict(list)
    historical = {
        (t.stage, frozenset(t.clubs))
        for t in ctx.content.standings.ties
        if t.competition == competition.id
    }
    for index, slot in enumerate(declaration.slots or ()):
        part = f"{field}.slots.{index}"
        stage = stage_of(competition, slot.stage_id)
        if stage is None or stage.is_group_stage:
            ctx.add("standings", part, "slot requires a known knockout stage")
            continue
        if not {slot.home, slot.away} <= set(competition.participants):
            ctx.add("standings", part, "slot clubs must be competition participants")
        start, end = season_window(ctx.content.season.season)
        if slot.date is not None and (
            not start <= slot.date <= end or ctx.block_of(slot.date) is None
        ):
            ctx.add("standings", part, "slot date must fall inside the season and a block")
        key = slot.stage_id, frozenset((slot.home, slot.away))
        if key not in historical:
            ctx.add("standings", part, "slot has no matching historical tie")
        grouped[key].append(slot)
        _check_owned_slot(ctx, part, declaration.competition, slot)
    for key, slots in grouped.items():
        stage = stage_of(competition, key[0])
        if stage is not None:
            _check_legs(ctx, field, slots, stage.legs)
    _check_feeder_chronology(ctx, declaration)
    if declaration.verify == "ok":
        for key in historical:
            stage = stage_of(competition, key[0])
            if stage is not None and len(grouped.get(key, ())) != stage.legs:
                ctx.add(
                    "standings", field, "calendar must contain all legs of every historical tie"
                )


def _check_feeder_chronology(ctx: SeasonContext, calendar: KnockoutCalendar) -> None:
    """Compare only actual feeder edges, never unrelated branches of the bracket."""
    competition = ctx.competitions[calendar.competition]
    if isinstance(competition, LeagueCompetition):
        return
    ties = [tie for tie in ctx.content.standings.ties if tie.competition == competition.id]
    for source, target in pairwise(competition.stages):
        if source.is_group_stage or target.is_group_stage:
            continue
        for destination in calendar.slots or ():
            if destination.stage_id != target.id or destination.date is None:
                continue
            for club in (destination.home, destination.away):
                origins = [
                    tie
                    for tie in ties
                    if tie.stage == source.id and tie.winner == club and tie.verify == "ok"
                ]
                if len(origins) != 1:
                    continue  # No invented link when the predecessor is unknown or ambiguous.
                origin = origins[0]
                dates = [
                    slot.date
                    for slot in calendar.slots or ()
                    if slot.stage_id == source.id
                    and {slot.home, slot.away} == set(origin.clubs)
                    and slot.date is not None
                ]
                if dates and destination.date <= max(dates):
                    ctx.add(
                        "standings",
                        "knockout_calendar",
                        "a destination must follow every feeding predecessor tie",
                    )


def _check_legs(ctx: SeasonContext, field: str, slots: list[KnockoutSlot], legs: int) -> None:
    if len(slots) > legs:
        ctx.add("standings", field, "too many legs for one stage and pair")
    if legs == 1:
        if any(s.leg not in (None, 1) for s in slots):
            ctx.add("standings", field, "a single match cannot declare a second leg")
        return
    numbers = [slot.leg for slot in slots]
    if any(n not in (1, TWO_LEGS) for n in numbers) or len(set(numbers)) != len(numbers):
        ctx.add("standings", field, "two-legged slots require distinct legs 1 and 2")
        return
    if any(slot.venue == "neutral" for slot in slots):
        ctx.add("standings", field, "two legs require home venues")
    if len(slots) == TWO_LEGS:
        first, second = sorted(slots, key=lambda slot: slot.leg or 0)
        if (first.home, first.away) != (second.away, second.home) or (
            first.date is not None and second.date is not None and first.date >= second.date
        ):
            ctx.add("standings", field, "two legs require inverted sides and increasing dates")


def _check_owned_slot(ctx: SeasonContext, field: str, competition: str, slot: KnockoutSlot) -> None:
    managed = {f.id: f for f in ctx.content.fixtures.fixtures}
    known = managed.get(slot.fixture_id)
    if known is None:
        if ctx.own in (slot.home, slot.away):
            ctx.add("standings", field, "unknown managed fixture id")
        return
    expected_venue = "neutral" if known.venue == "neutral" else "home"
    expected_sides = (
        (known.opponent, ctx.own) if known.venue == "away" else (ctx.own, known.opponent)
    )
    sides_match = (
        {slot.home, slot.away} == set(expected_sides)
        if known.venue == "neutral"
        else (slot.home, slot.away) == expected_sides
    )
    if (
        (competition, slot.stage_id, slot.leg) != (known.competition, known.stage, known.leg)
        or not sides_match
        or (slot.date is not None and slot.date != known.date)
        or (slot.venue is not None and slot.venue != expected_venue)
    ):
        ctx.add("standings", field, "slot contradicts managed fixture identity, date or venue")


def _check_global_ids(ctx: SeasonContext) -> None:
    direct = {
        f.fixture_id
        for evidence in ctx.content.standings.head_to_head or ()
        for f in evidence.schedule
    }
    seen: set[str] = set()
    for declaration in ctx.content.standings.knockout_calendar or ():
        for slot in declaration.slots or ():
            if slot.fixture_id in seen or slot.fixture_id in direct:
                ctx.add(
                    "standings", "knockout_calendar", "duplicate or incompatible global fixture id"
                )
            seen.add(slot.fixture_id)


def _check_entries(ctx: SeasonContext, field: str, declaration: GroupEntryAssignments) -> None:
    competition = ctx.competitions.get(declaration.competition)
    if competition is None or isinstance(competition, LeagueCompetition):
        ctx.add("standings", field, "entry assignments require a knockout competition")
        return
    order = [s.id for s in competition.stages]
    for index, entry in enumerate(declaration.entries or ()):
        part = f"{field}.entries.{index}"
        source = stage_of(competition, entry.source_stage_id)
        target = stage_of(competition, entry.target_stage_id)
        if (
            source is None
            or not source.is_group_stage
            or target is None
            or target.is_group_stage
            or order.index(source.id) >= order.index(target.id)
        ):
            ctx.add(
                "standings", part, "entry requires an earlier group stage and later knockout stage"
            )
            continue
        group = next((g for g in source.groups or () if g.id == entry.group_id), None)
        if group is None or entry.qualifying_position > (source.advance_per_group or 0):
            ctx.add("standings", part, "entry needs a known group and qualifying position")
            continue
        tables = [
            c
            for c in ctx.content.standings.cutoffs
            if (c.competition, c.stage, c.group) == (competition.id, source.id, group.id)
        ]
        row = None
        if tables:
            final = max(tables, key=lambda table: table.date)
            row = next((r for r in final.table if r.position == entry.qualifying_position), None)
        if row is None or row.club_season != entry.historical_representative:
            ctx.add("standings", part, "entry contradicts the final historical group position")
        _check_entry_chronology(ctx, competition.id, entry)
        ties = [
            t
            for t in ctx.content.standings.ties
            if (t.competition, t.stage) == (competition.id, target.id)
            and entry.historical_representative in t.clubs
        ]
        if len(ties) != 1:
            ctx.add(
                "standings", part, "entry representative needs exactly one historical target tie"
            )


def check_release_completion(ctx: SeasonContext) -> None:
    """Require explicit calendars and all qualifying positions for reachable knockout paths."""
    _check_reapplication(ctx)
    calendars = {d.competition: d for d in ctx.content.standings.knockout_calendar or ()}
    for competition in ctx.content.season.competitions:
        if isinstance(competition, LeagueCompetition):
            continue
        stages = competition.stages
        knockouts = [s for s in stages if not s.is_group_stage]
        if not knockouts:
            continue
        calendar = calendars.get(competition.id)
        if calendar is None or calendar.slots is None or calendar.verify != "ok":
            ctx.add(
                "standings", "knockout_calendar", f"complete calendar required for {competition.id}"
            )
        ties = [t for t in ctx.content.standings.ties if t.competition == competition.id]
        for stage in knockouts:
            if not any(t.stage == stage.id for t in ties):
                ctx.add(
                    "standings",
                    "knockout_calendar",
                    "every reachable stage requires historical ties",
                )
        if not stages[0].is_group_stage:
            first_clubs = {club for t in ties if t.stage == stages[0].id for club in t.clubs}
            if first_clubs != set(competition.participants):
                ctx.add(
                    "standings",
                    "knockout_calendar",
                    "initial stage participants require explicit coverage",
                )
        for previous, current in pairwise(stages):
            if previous.is_group_stage or current.is_group_stage:
                continue
            winners = {t.winner for t in ties if t.stage == previous.id and t.winner is not None}
            following = {club for t in ties if t.stage == current.id for club in t.clubs}
            if winners != following:
                ctx.add(
                    "standings",
                    "knockout_calendar",
                    "reachable progression requires all predecessor winners",
                )
        _check_group_coverage(ctx, competition.id, stages)


def _check_reapplication(ctx: SeasonContext) -> None:
    for ci, competition in enumerate(ctx.content.season.competitions):
        if isinstance(competition, LeagueCompetition):
            continue
        stages = competition.stages
        for si, stage in enumerate(stages):
            direct = any(t.value.startswith("head_to_head_") for t in stage.tiebreakers or ())
            if (
                stage.is_group_stage
                and direct
                and (
                    stage.reapply_head_to_head is None
                    or stage.reapply_head_to_head.value is None
                    or stage.reapply_head_to_head.verify != "ok"
                )
            ):
                ctx.add(
                    "season",
                    f"competitions.{ci}.stages.{si}.reapply_head_to_head",
                    "an explicit verified reapplication policy is required",
                )


def _check_group_coverage(
    ctx: SeasonContext, competition_id: str, stages: tuple[Stage, ...]
) -> None:
    entries = {d.competition: d for d in ctx.content.standings.group_entry_assignments or ()}
    declaration = entries.get(competition_id)
    if declaration is not None and declaration.entries is not None:
        _check_entry_target_occupants(ctx, declaration)
        for entry in declaration.entries:
            _check_entry_chronology(ctx, competition_id, entry, required=True)
    for stage in stages:
        later = stages[stages.index(stage) + 1 :]
        if not stage.is_group_stage or not any(not s.is_group_stage for s in later):
            continue
        declaration = entries.get(competition_id)
        if declaration is None or declaration.entries is None or declaration.verify != "ok":
            ctx.add(
                "standings",
                "group_entry_assignments",
                f"group entry assignments required for {competition_id}",
            )
            continue
        provided = {
            (e.source_stage_id, e.group_id, e.qualifying_position) for e in declaration.entries
        }
        required = {
            (stage.id, group.id, position)
            for group in stage.groups or ()
            for position in range(1, (stage.advance_per_group or 0) + 1)
        }
        if not required <= provided:
            ctx.add(
                "standings",
                "group_entry_assignments",
                "every qualifying position requires an assignment",
            )


def _check_entry_target_occupants(ctx: SeasonContext, assignments: GroupEntryAssignments) -> None:
    targets = {entry.target_stage_id for entry in assignments.entries or ()}
    competition = ctx.competitions.get(assignments.competition)
    if competition is not None and not isinstance(competition, LeagueCompetition):
        targets.update(
            target.id
            for source, target in pairwise(competition.stages)
            if source.is_group_stage and not target.is_group_stage
        )
    for target in targets:
        representatives = {
            entry.historical_representative
            for entry in assignments.entries or ()
            if entry.target_stage_id == target
        }
        contenders = {
            club
            for tie in ctx.content.standings.ties
            if (tie.competition, tie.stage) == (assignments.competition, target)
            for club in tie.clubs
        }
        if representatives != contenders:
            ctx.add(
                "standings",
                "group_entry_assignments",
                "entry assignments must cover exactly the historical target contenders",
            )


class _GroupCalendarCompletion(NamedTuple):
    """Keep an absent proof distinct from an explicit conflict with the final table."""

    last_match: date | None = None
    contradictory: bool = False


def _check_entry_chronology(
    ctx: SeasonContext, competition_id: str, entry: GroupEntryAssignment, *, required: bool = False
) -> None:
    tables = [
        table
        for table in ctx.content.standings.cutoffs
        if (table.competition, table.stage, table.group)
        == (competition_id, entry.source_stage_id, entry.group_id)
    ]
    if not tables:
        return
    final = max(tables, key=lambda table: table.date)
    completion = _group_calendar_end(ctx, competition_id, entry, final)
    if completion.contradictory:
        ctx.add(
            "standings",
            "group_entry_assignments",
            "verified group calendar contradicts the accredited final table totals",
        )
        return  # An earlier table cannot override contradictory verified calendar evidence.
    last_match = completion.last_match
    dates = [
        slot.date
        for calendar in ctx.content.standings.knockout_calendar or ()
        if calendar.competition == competition_id
        for slot in calendar.slots or ()
        if slot.stage_id == entry.target_stage_id
        and entry.historical_representative in (slot.home, slot.away)
        and slot.date is not None
    ]
    if last_match is not None:
        if any(day <= last_match for day in dates):
            ctx.add(
                "standings",
                "group_entry_assignments",
                "target slots must follow the last accredited group match",
            )
    elif required and any(day <= final.date for day in dates):
        ctx.add(
            "standings",
            "group_entry_assignments",
            "insufficient calendar evidence to establish group completion before the target",
        )


def _group_calendar_end(
    ctx: SeasonContext, competition_id: str, entry: GroupEntryAssignment, final: StandingsCutoff
) -> _GroupCalendarCompletion:
    """Inspect all complete declarations, preserving explicit conflicts even beside valid proofs."""
    competition = ctx.competitions.get(competition_id)
    source = stage_of(competition, entry.source_stage_id) if competition else None
    group = (
        next((g for g in source.groups or () if g.id == entry.group_id), None) if source else None
    )
    if source is None or group is None or final.verify != "ok":
        return _GroupCalendarCompletion()
    last_match: date | None = None
    contradictory = False
    for history in ctx.content.standings.head_to_head or ():
        if (
            (history.competition, history.stage, history.group)
            != (competition_id, source.id, group.id)
            or set(history.covered_clubs) != set(group.participants)
            or history.complete_through < final.date
            or history.verify != "ok"
            or any(f.verify != "ok" for f in history.schedule)
            or any(r.verify != "ok" or r.score is None for r in history.results)
        ):
            continue
        scores = {r.fixture_id: r.score for r in history.results if r.score is not None}
        totals = {club: [0] * 7 for club in group.participants}
        for fixture in history.schedule:
            score = scores[fixture.fixture_id]
            for club, gf, ga in (
                (fixture.home, score[0], score[1]),
                (fixture.away, score[1], score[0]),
            ):
                won, drawn, lost = int(gf > ga), int(gf == ga), int(gf < ga)
                values = (
                    1,
                    won,
                    drawn,
                    lost,
                    gf,
                    ga,
                    won * (source.points_per_win or 0) + drawn * (source.points_per_draw or 0),
                )
                totals[club] = [a + b for a, b in zip(totals[club], values, strict=True)]
        coherent = {row.club_season for row in final.table} == set(group.participants) and all(
            totals[row.club_season]
            == [
                row.played,
                row.won,
                row.drawn,
                row.lost,
                row.goals_for,
                row.goals_against,
                row.points,
            ]
            for row in final.table
        )
        if coherent:
            end = max((fixture.date for fixture in history.schedule), default=None)
            if end is not None and (last_match is None or end > last_match):
                last_match = end
        else:
            contradictory = True
    return _GroupCalendarCompletion(last_match, contradictory)
