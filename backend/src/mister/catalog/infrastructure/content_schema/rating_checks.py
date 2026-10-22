"""Ratings checks of the tree: the stored rating is the formula's, or the override's (ADR-006)."""

from mister.catalog.domain.ratings import RatingResult, compute_rating, override_problem
from mister.catalog.infrastructure.content_schema.integrity import squad_path
from mister.catalog.infrastructure.content_schema.issues import IssueSink
from mister.catalog.infrastructure.content_schema.ratings_bridge import (
    club_context,
    player_stats,
)
from mister.catalog.infrastructure.content_schema.season_stats import RatingOverride
from mister.catalog.infrastructure.content_schema.squad import PlayerEntry, SquadFile
from mister.catalog.infrastructure.content_schema.tree import ContentTree


def check_ratings(tree: ContentTree, sink: IssueSink) -> None:
    """Every stored rating equals `compute_rating` of its statistics, unless it is overridden.

    Market squads are exempt: they have no club, so there is nothing to compute from.
    """
    for squad in tree.squads.values():
        if squad.is_market:
            continue
        club = club_context(squad)
        for index, player in enumerate(squad.players):
            result = compute_rating(player_stats(player), club)
            _check_player(squad, index, player, result, sink)


def _check_player(
    squad: SquadFile, index: int, player: PlayerEntry, result: RatingResult, sink: IssueSink
) -> None:
    path = squad_path(squad.club_season)
    override = player.rating_override
    if override is not None:
        problem = _override_problem(override, result)
        if problem is not None:
            sink.add(path, f"players.{index}.rating_override", f"{player.player_id}: {problem}")
        expected: int | None = override.value
        why = " (the rating_override)"
    else:
        expected = result.rating
        why = f" (missing: {', '.join(result.missing)})" if result.rating is None else ""
    if player.rating != expected:
        sink.add(
            path,
            f"players.{index}.rating",
            f"{player.player_id}: rating {player.rating} does not match the formula; "
            f"expected {'null' if expected is None else expected}{why}",
        )


def _override_problem(override: RatingOverride, result: RatingResult) -> str | None:
    if result.rating is None:
        return (
            "an override cannot replace a missing statistic; "
            f"statistics are missing: {', '.join(result.missing)}"
        )
    distinct_sources = len({str(url) for url in override.sources})
    return override_problem(result.rating, override.value, distinct_sources)
