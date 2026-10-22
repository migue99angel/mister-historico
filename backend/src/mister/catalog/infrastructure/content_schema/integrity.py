"""Referential integrity between club-season files (clubs, squads, players across squads)."""

from collections import defaultdict
from datetime import date

from mister.catalog.infrastructure.content_schema.base import season_window
from mister.catalog.infrastructure.content_schema.issues import IssueSink
from mister.catalog.infrastructure.content_schema.squad import PlayerEntry, SquadFile
from mister.catalog.infrastructure.content_schema.tree import ContentTree


def squad_path(club_season: str) -> str:
    return f"club-seasons/{club_season}/squad.yaml"


def aggregate_path(club_season: str) -> str:
    return f"club-seasons/{club_season}/aggregate.yaml"


def check_club_references(tree: ContentTree, sink: IssueSink) -> None:
    """Every club-season points to an existing `clubs/<club>.yaml` (market squads have none)."""
    for slug, squad in tree.squads.items():
        if squad.club is not None and squad.club not in tree.clubs:
            sink.add(squad_path(slug), "club", f"club {squad.club!r} has no file in clubs/")
    for slug, aggregate in tree.aggregates.items():
        if aggregate.club is not None and aggregate.club not in tree.clubs:
            sink.add(aggregate_path(slug), "club", f"club {aggregate.club!r} has no file in clubs/")


def _interval(squad: SquadFile, entry: PlayerEntry) -> tuple[date, date]:
    first, last = season_window(squad.season)
    return entry.joined_on or first, entry.left_on or last


def check_players_across_squads(tree: ContentTree, sink: IssueSink) -> None:
    """A `player_id` is one person: same names everywhere, never in two squads at once."""
    memberships: dict[str, list[tuple[str, int, PlayerEntry]]] = defaultdict(list)
    for slug in sorted(tree.squads):
        for index, entry in enumerate(tree.squads[slug].players):
            memberships[entry.player_id].append((slug, index, entry))
    for player_id, items in memberships.items():
        first_slug, _, first_entry = items[0]
        for slug, index, entry in items[1:]:
            if (entry.display_name, entry.alias_name) != (
                first_entry.display_name,
                first_entry.alias_name,
            ):
                sink.add(
                    squad_path(slug),
                    f"players.{index}.display_name",
                    f"{player_id}: name differs from the one in {first_slug}",
                )
        _check_overlaps(tree, player_id, items, sink)


def _check_overlaps(
    tree: ContentTree,
    player_id: str,
    items: list[tuple[str, int, PlayerEntry]],
    sink: IssueSink,
) -> None:
    for position, (slug, index, entry) in enumerate(items):
        squad = tree.squads[slug]
        start, end = _interval(squad, entry)
        for other_slug, _, other_entry in items[:position]:
            other_squad = tree.squads[other_slug]
            if other_squad.season != squad.season:
                continue
            other_start, other_end = _interval(other_squad, other_entry)
            if start <= other_end and other_start <= end:
                sink.add(
                    squad_path(slug),
                    f"players.{index}.player_id",
                    f"{player_id} also belongs to {other_slug} on the same dates; "
                    "a transfer needs joined_on and left_on without overlap",
                )
