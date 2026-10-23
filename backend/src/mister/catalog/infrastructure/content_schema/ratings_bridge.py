"""Maps validated content models to the inputs of the rating formula (`catalog.domain.ratings`)."""

from mister.catalog.domain.ratings import (
    AwardTier,
    ClubContext,
    LevelTier,
    PlayerStats,
    Position,
)
from mister.catalog.infrastructure.content_schema.season_stats import ClubData
from mister.catalog.infrastructure.content_schema.squad import PlayerEntry


def player_stats(entry: PlayerEntry) -> PlayerStats:
    """The formula's view of a player: his position and age plus his `season_stats`."""
    stats = entry.season_stats
    position = None if entry.position is None else Position(entry.position.value)
    return PlayerStats(
        position=position,
        age=entry.age,
        minutes_league=stats.minutes_league,
        starts_league=stats.starts_league,
        appearances_league=stats.appearances_league,
        minutes_all=stats.minutes_all,
        starts_all=stats.starts_all,
        appearances_all=stats.appearances_all,
        goals_all=stats.goals_all,
        assists_all=stats.assists_all,
        clean_sheets_all=stats.clean_sheets_all,
        caps=stats.caps,
        awards=None if stats.awards is None else tuple(AwardTier(a.tier) for a in stats.awards),
        available_matches_all=stats.available_matches_all,
    )


def club_context(data: ClubData | None) -> ClubContext:
    """The formula's view of a club-season; unknown when there is no `club_data`."""
    if data is None:
        return ClubContext(None, None, None)
    return ClubContext(
        club_matches_all=data.club_matches_all,
        club_matches_league=data.club_matches_league,
        level_tier=None if data.level_tier is None else LevelTier(data.level_tier),
    )
