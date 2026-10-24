"""Cross-file integrity and release coverage of declared historical head-to-head evidence."""

from collections import defaultdict
from itertools import combinations
from typing import NamedTuple

from mister.catalog.infrastructure.content_schema.base import season_window
from mister.catalog.infrastructure.content_schema.context import SeasonContext, stage_of
from mister.catalog.infrastructure.content_schema.evidence import HeadToHeadEvidence
from mister.catalog.infrastructure.content_schema.season import LeagueCompetition
from mister.catalog.infrastructure.content_schema.standings import StandingsCutoff


class _Scope(NamedTuple):
    participants: frozenset[str]
    points_per_win: int
    points_per_draw: int
    direct: bool


def _scope(
    ctx: SeasonContext, competition: str, stage: str | None, group: str | None
) -> _Scope | None:
    rules = ctx.competitions.get(competition)
    if isinstance(rules, LeagueCompetition) and stage is None and group is None:
        return _Scope(
            frozenset(rules.participants),
            rules.points_per_win,
            rules.points_per_draw,
            any(t.value.startswith("head_to_head_") for t in rules.tiebreakers),
        )
    current = stage_of(rules, stage or "") if rules else None
    if current is None or not current.is_group_stage:
        return None
    selected = next((g for g in current.groups or () if g.id == group), None)
    if selected is None:
        return None
    return _Scope(
        frozenset(selected.participants),
        current.points_per_win or 3,
        current.points_per_draw or 0,
        any(t.value.startswith("head_to_head_") for t in current.tiebreakers or ()),
    )


def _key(evidence: HeadToHeadEvidence | StandingsCutoff) -> tuple[str, str | None, str | None]:
    return evidence.competition, evidence.stage, evidence.group


def check_evidence(ctx: SeasonContext) -> None:
    """Validate evidence against known scopes, managed fixtures and covered real tables."""
    entries = ctx.content.standings.head_to_head or ()
    for index, entry in enumerate(entries):
        field = f"head_to_head.{index}"
        scope = _scope(ctx, *_key(entry))
        if scope is None:
            part = "competition" if entry.competition not in ctx.competitions else "stage"
            ctx.add("standings", f"{field}.{part}", "unknown league or group evidence scope")
            continue
        if not set(entry.covered_clubs) <= scope.participants:
            ctx.add("standings", f"{field}.covered_clubs", "covered clubs must belong to the scope")
        start, end = season_window(ctx.content.season.season)
        if not start <= entry.complete_through <= end:
            ctx.add("standings", f"{field}.complete_through", "coverage must end within the season")
        if any(f.date < start for f in entry.schedule):
            ctx.add("standings", f"{field}.schedule", "calendar dates must fall within the season")
        _check_managed(ctx, field, entry)
        if set(entry.covered_clubs) == scope.participants:
            _check_tables(ctx, field, entry, scope)
    _check_overlaps(ctx, entries)


def _check_managed(ctx: SeasonContext, field: str, entry: HeadToHeadEvidence) -> None:
    calendar = {f.fixture_id: f for f in entry.schedule}
    scores = {r.fixture_id: r.score for r in entry.results}
    managed = {f.id: f for f in ctx.content.fixtures.fixtures}
    for fixture in managed.values():
        if (fixture.competition, fixture.stage, fixture.group) != _key(entry):
            continue
        if fixture.date > entry.complete_through or not {ctx.own, fixture.opponent} <= set(
            entry.covered_clubs
        ):
            continue
        actual = calendar.get(fixture.id)
        if actual is None:
            ctx.add("standings", field, f"missing managed fixture {fixture.id}")
            continue
        home, away = (
            (ctx.own, fixture.opponent) if fixture.venue == "home" else (fixture.opponent, ctx.own)
        )
        if (actual.date, actual.home, actual.away) != (fixture.date, home, away):
            ctx.add("standings", field, f"calendar contradicts managed fixture {fixture.id}")
        expected_venue = "neutral" if fixture.venue == "neutral" else "home"
        if actual.venue is not None and actual.venue != expected_venue:
            ctx.add("standings", field, f"venue contradicts managed fixture {fixture.id}")
        if fixture.result is not None and scores[fixture.id] is not None:
            own = fixture.result
            expected = (
                (own.goals_for, own.goals_against)
                if fixture.venue == "home"
                else (own.goals_against, own.goals_for)
            )
            if scores[fixture.id] != expected:
                ctx.add("standings", field, f"score contradicts managed fixture {fixture.id}")
    _check_managed_calendar_ids(ctx, field, entry)


def _check_managed_calendar_ids(ctx: SeasonContext, field: str, entry: HeadToHeadEvidence) -> None:
    managed = {f.id: f for f in ctx.content.fixtures.fixtures}
    for calendar_fixture in entry.schedule:
        if (
            ctx.own in (calendar_fixture.home, calendar_fixture.away)
            and calendar_fixture.fixture_id not in managed
        ):
            ctx.add(
                "standings",
                field,
                f"unknown managed fixture {calendar_fixture.fixture_id}",
            )
        if calendar_fixture.fixture_id in managed:
            own_calendar_fixture = managed[calendar_fixture.fixture_id]
            home, away = (
                (ctx.own, own_calendar_fixture.opponent)
                if own_calendar_fixture.venue == "home"
                else (own_calendar_fixture.opponent, ctx.own)
            )
            if (calendar_fixture.date, calendar_fixture.home, calendar_fixture.away) != (
                own_calendar_fixture.date,
                home,
                away,
            ):
                ctx.add(
                    "standings",
                    field,
                    f"calendar contradicts managed fixture {calendar_fixture.fixture_id}",
                )
            if (
                own_calendar_fixture.competition,
                own_calendar_fixture.stage,
                own_calendar_fixture.group,
            ) != _key(entry):
                ctx.add(
                    "standings",
                    field,
                    f"managed fixture {calendar_fixture.fixture_id} belongs to another scope",
                )


def _check_tables(ctx: SeasonContext, field: str, entry: HeadToHeadEvidence, scope: _Scope) -> None:
    results = {r.fixture_id: r.score for r in entry.results if r.score is not None}
    for cutoff in ctx.content.standings.cutoffs:
        if _key(cutoff) != _key(entry) or cutoff.date > entry.complete_through:
            continue
        played = [f for f in entry.schedule if f.date <= cutoff.date]
        if any(f.fixture_id not in results for f in played):
            continue  # Unknown scores remain unknown until editorial verification.
        totals: dict[str, list[int]] = defaultdict(lambda: [0] * 7)
        for fixture in played:
            score = results[fixture.fixture_id]
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
                    won * scope.points_per_win + drawn * scope.points_per_draw,
                )
                totals[club] = [a + b for a, b in zip(totals[club], values, strict=True)]
        for row in cutoff.table:
            stated = (
                row.played,
                row.won,
                row.drawn,
                row.lost,
                row.goals_for,
                row.goals_against,
                row.points,
            )
            if tuple(totals[row.club_season]) != stated:
                ctx.add(
                    "standings",
                    field,
                    f"covered table {cutoff.block} disagrees with evidence for {row.club_season}",
                )


def _check_shared_ids(
    ctx: SeasonContext, left: HeadToHeadEvidence, right: HeadToHeadEvidence
) -> None:
    """Fixture identity is global to the season, even across disjoint club coverage."""
    first = {f.fixture_id: f for f in left.schedule}
    second = {f.fixture_id: f for f in right.schedule}
    left_scores = {r.fixture_id: r.score for r in left.results}
    right_scores = {r.fixture_id: r.score for r in right.results}
    for fixture_id in first.keys() & second.keys():
        a, b = first[fixture_id], second[fixture_id]
        if (_key(left), a.date, a.home, a.away) != (_key(right), b.date, b.home, b.away) or (
            a.venue is not None and b.venue is not None and a.venue != b.venue
        ):
            ctx.add(
                "standings",
                "head_to_head",
                f"fixture id {fixture_id} has contradictory scope, date or sides",
            )
        if (
            left_scores[fixture_id] is not None
            and right_scores[fixture_id] is not None
            and left_scores[fixture_id] != right_scores[fixture_id]
        ):
            ctx.add(
                "standings",
                "head_to_head",
                f"fixture id {fixture_id} has contradictory non-null scores",
            )


def _check_overlaps(ctx: SeasonContext, entries: tuple[HeadToHeadEvidence, ...]) -> None:
    for left, right in combinations(entries, 2):
        _check_shared_ids(ctx, left, right)
        if _key(left) != _key(right):
            continue
        clubs = set(left.covered_clubs) & set(right.covered_clubs)
        through = min(left.complete_through, right.complete_through)
        calendars = [
            {
                f.fixture_id: (f.date, f.home, f.away)
                for f in entry.schedule
                if f.date <= through and {f.home, f.away} <= clubs
            }
            for entry in (left, right)
        ]
        if calendars[0] != calendars[1]:
            ctx.add("standings", "head_to_head", "overlapping calendar coverage is contradictory")
        if left.complete_through == right.complete_through and set(left.covered_clubs) == set(
            right.covered_clubs
        ):
            ctx.add("standings", "head_to_head", "duplicate coverage declaration")


def check_release_evidence(ctx: SeasonContext) -> None:
    """Each cutoff that can need a mini-league needs verified complete participant coverage."""
    for cutoff in ctx.content.standings.cutoffs:
        scope = _scope(ctx, *_key(cutoff))
        if scope is None or not scope.direct:
            continue
        if not any(
            _key(entry) == _key(cutoff)
            and entry.complete_through >= cutoff.date
            and set(entry.covered_clubs) == scope.participants
            and entry.verify == "ok"
            for entry in ctx.content.standings.head_to_head or ()
        ):
            ctx.add(
                "standings",
                "head_to_head",
                f"verified complete coverage is required for {cutoff.competition}/{cutoff.block}",
            )
