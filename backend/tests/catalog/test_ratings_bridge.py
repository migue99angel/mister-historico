"""Mapping of content models to the inputs of the rating formula."""

from tests.catalog.test_squad_models import player, season_stats, squad

from mister.catalog.domain.ratings import AwardTier, LevelTier, Position
from mister.catalog.infrastructure.content_schema.ratings_bridge import (
    club_context,
    player_stats,
)
from mister.catalog.infrastructure.content_schema.squad import SquadFile

_SOURCE = "https://example.org/sources/test"


def test_a_player_maps_to_the_statistics_of_the_formula() -> None:
    award = {"name": "Fictional award", "tier": "W", "source": _SOURCE}
    parsed = SquadFile.model_validate(
        squad(players=[player(0, season_stats=season_stats(awards=[award], caps=3))])
    )

    stats = player_stats(parsed.players[0])

    assert stats.position is Position.GK
    assert stats.caps == 3
    assert stats.awards == (AwardTier.W,)
    assert stats.minutes_all == 2500


def test_a_club_maps_to_its_match_counts_and_level() -> None:
    context = club_context(SquadFile.model_validate(squad()))

    assert (context.club_matches_all, context.club_matches_league) == (42, 38)
    assert context.level_tier is LevelTier.C


def test_a_market_player_and_a_market_squad_map_to_unknown_data() -> None:
    market = SquadFile.model_validate(
        squad(
            club_season="_market-2000-01",
            club=None,
            real_league=None,
            club_data=None,
            players=[player(1, season_stats=None)],
        )
    )

    stats = player_stats(market.players[0])
    context = club_context(market)

    assert stats.position is Position.MF
    assert stats.minutes_all is None
    assert stats.awards is None
    assert (context.club_matches_all, context.level_tier) == (None, None)
