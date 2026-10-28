"""Public Game presentation never exposes private domain or catalog data."""

from mister.catalog.application.api import present_person_name
from dataclasses import replace

from mister.game.infrastructure.presentation_adapter import CatalogPresentationAdapter
from mister.settings import Settings
from mister.shared_kernel.ids import PlayableSeasonId
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season


def test_published_name_helper_uses_alias_when_real_names_are_disabled() -> None:
    assert present_person_name("Real Person", "Alias Person", real_names=False) == "Alias Person"


class _Catalog:
    def __init__(self, season: object) -> None:
        self.season = season

    def list_playable_seasons(self) -> tuple[object, ...]:
        return (self.season.summary(),)

    def get_playable_season(self, season_id: PlayableSeasonId) -> object:
        assert self.season.id == season_id
        return self.season


def test_season_detail_uses_aliases_when_real_names_are_disabled() -> None:
    season = build_expected_test_fc_season()
    adapter = CatalogPresentationAdapter(_Catalog(season), Settings(real_names=False))

    result = adapter.get_season(season.id).to_json()

    assert result["historicalManager"] == season.manager.alias_name
    assert (
        result["squad"]["keyPlayers"][0]["displayName"]
        == next(item for item in season.own_club_season.squad if item.key).alias_name
    )


def test_run_presentation_uses_the_run_capture_after_catalog_changes() -> None:
    season = build_expected_test_fc_season()
    provider = _Catalog(season)
    adapter = CatalogPresentationAdapter(provider, Settings())
    from tests.game.test_t35_use_cases import _setup

    original, _, store, _, start, _, _ = _setup()
    created = start.execute(original.id)
    captured = store.runs[created.run_id].replay_inputs.content
    original_player = original.own_club_season.squad[0]
    changed_clubs = tuple(
        replace(
            club,
            squad=tuple(replace(item, display_name="Changed Name") for item in club.squad),
        )
        if club.id == season.club_season_id
        else club
        for club in season.club_seasons
    )
    provider.season = replace(season, club_seasons=changed_clubs)

    result = adapter.present_run(created.view, captured).to_json()

    assert result["squad"]["players"][0]["displayName"] == original_player.display_name
    assert "seed" not in result
    assert all("effects" not in item for item in result["pendingDilemmas"])
