"""Integrity checks of the content tree that need the playable seasons."""

from mister.catalog.infrastructure.content_schema.context import SeasonContext
from mister.catalog.infrastructure.content_schema.dilemma_checks import check_dilemmas
from mister.catalog.infrastructure.content_schema.fixture_checks import check_fixtures
from mister.catalog.infrastructure.content_schema.integrity import squad_path
from mister.catalog.infrastructure.content_schema.issues import IssueSink
from mister.catalog.infrastructure.content_schema.outcome_checks import check_season_file
from mister.catalog.infrastructure.content_schema.squad import Position
from mister.catalog.infrastructure.content_schema.standings_checks import check_standings
from mister.catalog.infrastructure.content_schema.tree import ContentTree

MIN_RIVAL_SQUAD = 18
MAX_RIVAL_SQUAD = 22
MIN_KEY_PLAYERS = 6
MAX_KEY_PLAYERS = 10
MIN_BY_POSITION: dict[Position, int] = {
    Position.GK: 2,
    Position.DF: 6,
    Position.MF: 6,
    Position.FW: 4,
}


def check_season(
    tree: ContentTree, failed_club_seasons: set[str], slug: str, sink: IssueSink
) -> None:
    """Run every integrity rule of one playable season."""
    ctx = SeasonContext(tree, frozenset(failed_club_seasons), slug, sink)
    if ctx.own not in tree.squads:
        if ctx.own not in ctx.failed_club_seasons:
            ctx.add("season", "club_season", f"{ctx.own!r} must be a club-season with a squad")
        return
    check_season_file(ctx)
    check_fixtures(ctx)
    check_standings(ctx)
    check_dilemmas(ctx)


def check_playable_rationales(tree: ContentTree, sink: IssueSink) -> None:
    """The playable club-season is rated in detail: a rationale for every verified player."""
    for content in tree.seasons.values():
        squad = tree.squads.get(content.season.club_season)
        if squad is None:
            continue
        for index, player in enumerate(squad.players):
            if player.verify == "ok" and not player.rating_rationale:
                sink.add(
                    squad_path(squad.club_season),
                    f"players.{index}.rating_rationale",
                    "required for every player of a playable club-season",
                )


def check_rival_squads(tree: ContentTree, sink: IssueSink) -> None:
    """P6 lightweight procedure: rival squads have 18-22 players and a minimum coverage.

    The playable squad and the market squads are exempt.
    """
    playable = {c.season.club_season for c in tree.seasons.values()}
    for slug, squad in tree.squads.items():
        if squad.is_market or slug in playable:
            continue
        path = squad_path(slug)
        size = len(squad.players)
        if not MIN_RIVAL_SQUAD <= size <= MAX_RIVAL_SQUAD:
            sink.add(
                path,
                "players",
                f"a rival squad has between {MIN_RIVAL_SQUAD} and {MAX_RIVAL_SQUAD} players, "
                f"found {size}",
            )
        keys = sum(1 for p in squad.players if p.key)
        if not MIN_KEY_PLAYERS <= keys <= MAX_KEY_PLAYERS:
            sink.add(
                path,
                "players",
                f"a rival squad has between {MIN_KEY_PLAYERS} and {MAX_KEY_PLAYERS} key players, "
                f"found {keys}",
            )
        for position, minimum in MIN_BY_POSITION.items():
            count = sum(1 for p in squad.players if p.position is position)
            if count < minimum:
                sink.add(
                    path,
                    "players",
                    f"a rival squad needs at least {minimum} {position}, found {count}",
                )
