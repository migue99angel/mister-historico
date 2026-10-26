"""Persisted catalog snapshots preserve every published DTO type."""

from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season

from mister.catalog.infrastructure.sqlalchemy.codec import decode_season, encode_season


def test_full_test_fc_season_round_trips_through_json() -> None:
    season = build_expected_test_fc_season()

    restored = decode_season(encode_season(season))

    assert restored == season
    assert [
        type(effect)
        for dilemma in restored.dilemmas
        for option in dilemma.options
        for effect in option.effects
    ] == [
        type(effect)
        for dilemma in season.dilemmas
        for option in dilemma.options
        for effect in option.effects
    ]
