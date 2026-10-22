"""Sanity of the Test FC oracle: it must say what the fixture content says."""

from mister.catalog.application.api import CompetitionKind, GoalStatsDTO
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season


def test_the_oracle_covers_the_whole_test_fc_season() -> None:
    season = build_expected_test_fc_season()

    assert season.id.value == "test-fc-2000-01"
    assert len(season.blocks) == 5
    assert [c.kind for c in season.competitions][0] is CompetitionKind.LEAGUE
    assert season.own_club_season.name == "Test FC"
    assert 8 <= len(season.dilemmas) <= 12
    assert all(d.id for d in season.dilemmas)
    assert season.market_players


def test_a_cup_baseline_from_a_league_is_resolved_to_its_stats() -> None:
    season = build_expected_test_fc_season()
    league = season.competitions[0]
    cup = next(c for c in season.competitions if c.kind is CompetitionKind.CUP)

    assert league.league is not None
    assert league.goal_baseline == league.league.league_stats == GoalStatsDTO(30, 40, 27)
    assert cup.goal_baseline == league.goal_baseline


def test_rivals_without_a_squad_are_published_as_aggregates() -> None:
    season = build_expected_test_fc_season()

    aggregates = [c for c in season.club_seasons if c.aggregate is not None]
    squads = [c for c in season.club_seasons if c.squad is not None]

    assert aggregates
    assert squads
    assert [c.id.value for c in season.club_seasons] == sorted(c.id.value for c in season.club_seasons)
