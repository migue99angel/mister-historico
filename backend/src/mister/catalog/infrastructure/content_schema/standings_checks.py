"""Checks of `standings.yaml`: league tables, group tables, real brackets and real league goals."""

from collections.abc import Sequence

from mister.catalog.infrastructure.content_schema.context import SeasonContext, stage_of
from mister.catalog.infrastructure.content_schema.fixtures import Fixture
from mister.catalog.infrastructure.content_schema.integrity import squad_path
from mister.catalog.infrastructure.content_schema.season import LeagueCompetition
from mister.catalog.infrastructure.content_schema.standings import StandingRow, StandingsCutoff


def check_standings(ctx: SeasonContext) -> None:
    """Report every inconsistency of the real tables and brackets."""
    _check_missing_league_cutoffs(ctx)
    for index, cutoff in enumerate(ctx.content.standings.cutoffs):
        field = f"cutoffs.{index}"
        if cutoff.stage is None:
            _check_league_cutoff(ctx, field, cutoff)
        else:
            _check_group_cutoff(ctx, field, cutoff)
    _check_final_group_tables(ctx)
    _check_ties(ctx)
    _check_real_league_goals(ctx)


def _check_missing_league_cutoffs(ctx: SeasonContext) -> None:
    present = {(c.block, c.competition) for c in ctx.content.standings.cutoffs if c.stage is None}
    for block in ctx.blocks:
        for league_id in ctx.leagues:
            if (block.id, league_id) not in present:
                ctx.add(
                    "standings",
                    "cutoffs",
                    f"missing cutoff for block {block.id} and {league_id}",
                )


def _check_cutoff_date(ctx: SeasonContext, field: str, cutoff: StandingsCutoff) -> None:
    block = next((b for b in ctx.blocks if b.id == cutoff.block), None)
    if block is None:
        ctx.add("standings", f"{field}.block", f"unknown block {cutoff.block!r}")
    elif cutoff.date != block.end:
        ctx.add(
            "standings",
            f"{field}.date",
            f"must be the end of block {block.id} ({block.end})",
        )


def _check_league_cutoff(ctx: SeasonContext, field: str, cutoff: StandingsCutoff) -> None:
    _check_cutoff_date(ctx, field, cutoff)
    league = ctx.leagues.get(cutoff.competition)
    if league is None:
        ctx.add("standings", f"{field}.competition", f"{cutoff.competition!r} is not a league")
        return
    fixtures = [f for f in ctx.content.fixtures.fixtures if f.competition == league.id]
    _check_table(
        ctx,
        field,
        cutoff,
        set(league.participants),
        (league.points_per_win, league.points_per_draw),
        fixtures,
    )


def _check_group_cutoff(ctx: SeasonContext, field: str, cutoff: StandingsCutoff) -> None:
    _check_cutoff_date(ctx, field, cutoff)
    competition = ctx.competitions.get(cutoff.competition)
    stage = stage_of(competition, cutoff.stage or "") if competition else None
    if competition is None or stage is None or not stage.is_group_stage:
        ctx.add("standings", f"{field}.stage", f"{cutoff.stage!r} is not a group stage")
        return
    group = next((g for g in stage.groups or () if g.id == cutoff.group), None)
    if group is None:
        ctx.add("standings", f"{field}.group", f"unknown group {cutoff.group!r}")
        return
    fixtures = [
        f
        for f in ctx.content.fixtures.fixtures
        if (f.competition, f.stage, f.group) == (competition.id, stage.id, group.id)
    ]
    points = (stage.points_per_win or 3, stage.points_per_draw or 0)
    _check_table(ctx, field, cutoff, set(group.participants), points, fixtures)


def _check_table(
    ctx: SeasonContext,
    field: str,
    cutoff: StandingsCutoff,
    expected: set[str],
    points: tuple[int, int],
    fixtures: Sequence[Fixture],
) -> None:
    listed = {row.club_season for row in cutoff.table}
    if listed != expected:
        ctx.add(
            "standings",
            f"{field}.table",
            "the table must list exactly the participants of the competition "
            f"(missing: {sorted(expected - listed)}, unexpected: {sorted(listed - expected)})",
        )
    played = [f for f in fixtures if f.date <= cutoff.date]
    for row_index, row in enumerate(cutoff.table):
        row_field = f"{field}.table.{row_index}"
        wanted = row.won * points[0] + row.drawn * points[1]
        if row.points != wanted:
            ctx.add("standings", f"{row_field}.points", f"expected {wanted} points")
        if row.club_season == ctx.own:
            _check_own_row(ctx, row_field, row, played)


def _check_own_row(
    ctx: SeasonContext, field: str, row: StandingRow, fixtures: Sequence[Fixture]
) -> None:
    results = [f.result for f in fixtures]
    if any(r is None for r in results):
        return  # a pending result cannot be compared
    won = sum(1 for r in results if r and r.goals_for > r.goals_against)
    drawn = sum(1 for r in results if r and r.goals_for == r.goals_against)
    actual = (
        len(results),
        won,
        drawn,
        len(results) - won - drawn,
        sum(r.goals_for for r in results if r),
        sum(r.goals_against for r in results if r),
    )
    stated = (row.played, row.won, row.drawn, row.lost, row.goals_for, row.goals_against)
    if actual != stated:
        ctx.add(
            "standings",
            field,
            "the own row does not match the own fixtures "
            f"(played, won, drawn, lost, gf, ga): table {stated}, fixtures {actual}",
        )


def _check_final_group_tables(ctx: SeasonContext) -> None:
    """Every group needs a real table, and the latest one must be the complete one (P2)."""
    for competition in ctx.content.season.competitions:
        if isinstance(competition, LeagueCompetition):
            continue
        for stage in competition.stages:
            for group in stage.groups or ():
                tables = [
                    c
                    for c in ctx.content.standings.cutoffs
                    if (c.competition, c.stage, c.group) == (competition.id, stage.id, group.id)
                ]
                label = f"{competition.id}/{stage.id}/{group.id}"
                if not tables:
                    ctx.add("standings", "cutoffs", f"group {label} has no standings")
                    continue
                latest = max(tables, key=lambda c: c.date)
                total = (len(group.participants) - 1) * stage.legs
                if any(row.played != total for row in latest.table):
                    ctx.add(
                        "standings",
                        "cutoffs",
                        f"the latest table of group {label} is incomplete "
                        f"(every team must have played {total})",
                    )


def _check_ties(ctx: SeasonContext) -> None:
    for index, tie in enumerate(ctx.content.standings.ties):
        field = f"ties.{index}"
        competition = ctx.competitions.get(tie.competition)
        if competition is None or isinstance(competition, LeagueCompetition):
            ctx.add(
                "standings",
                f"{field}.competition",
                f"{tie.competition!r} is not a knockout competition",
            )
            continue
        stage = stage_of(competition, tie.stage)
        if stage is None or stage.is_group_stage:
            ctx.add("standings", f"{field}.stage", f"unknown knockout stage {tie.stage!r}")
        for club in tie.clubs:
            if club not in competition.participants:
                ctx.add(
                    "standings",
                    f"{field}.clubs",
                    f"{club!r} is not a participant of {competition.id!r}",
                )


def _check_real_league_goals(ctx: SeasonContext) -> None:
    """A squad's real league data must match the final table when it is this season's league."""
    for league in ctx.leagues.values():
        cutoffs = [
            c
            for c in ctx.content.standings.cutoffs
            if c.competition == league.id and c.stage is None
        ]
        if not cutoffs:
            continue
        final = max(cutoffs, key=lambda c: c.date)
        total = (len(league.participants) - 1) * league.rounds
        for row in final.table:
            squad = ctx.tree.squads.get(row.club_season)
            if squad is None or squad.real_league is None or row.played != total:
                continue
            real = squad.real_league
            if real.competition_label != league.name:
                continue  # the club's real league is another one: nothing to compare
            for name, value in (
                ("played", row.played),
                ("goals_for", row.goals_for),
                ("goals_against", row.goals_against),
            ):
                stated = getattr(real, name)
                if stated is not None and stated != value:
                    ctx.sink.add(
                        squad_path(row.club_season),
                        f"real_league.{name}",
                        f"{stated} differs from the final real standings ({value}) in "
                        f"seasons/{ctx.slug}/standings.yaml",
                    )
