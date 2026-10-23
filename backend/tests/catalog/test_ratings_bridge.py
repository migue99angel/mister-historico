"""Mapping of content models to the inputs of the rating formula."""

from tests.catalog.test_squad_models import club_data, player, season_stats, squad

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
    context = club_context(SquadFile.model_validate(squad()).club_data)

    assert (context.club_matches_all, context.club_matches_league) == (42, 38)
    assert context.level_tier is LevelTier.C


def test_a_market_player_maps_to_his_own_club() -> None:
    market = SquadFile.model_validate(
        squad(
            club_season="_market-2000-01",
            club=None,
            real_league=None,
            club_data=None,
            players=[
                player(1, club_data=club_data(club_name="Fictional Origin FC", level_tier="A"))
            ],
        )
    )

    context = club_context(market.players[0].club_data)

    assert context.level_tier is LevelTier.A
    assert context.club_matches_all == 42


def test_no_club_data_maps_to_unknown_data() -> None:
    context = club_context(None)

    assert (context.club_matches_all, context.club_matches_league, context.level_tier) == (
        None,
        None,
        None,
    )
