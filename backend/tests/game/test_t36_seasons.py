"""Contract checks for Game's published season query port and Catalog ACL."""

from collections.abc import Sequence
from dataclasses import replace

import pytest
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season
from tests.game.test_t36_facade import _api

from mister.catalog.application.api import (
    PlayableSeasonDTO,
    PlayableSeasonNotFoundError,
    PlayableSeasonSummaryDTO,
)
from mister.game.application.api import SeasonNotFoundError, SeasonQueries
from mister.game.application.presentation_types import Presented
from mister.game.infrastructure.presentation_adapter import CatalogPresentationAdapter
from mister.settings import Settings
from mister.shared_kernel.errors import DomainError
from mister.shared_kernel.ids import PlayableSeasonId


class _CatalogProvider:
    def __init__(self, seasons: tuple[PlayableSeasonDTO, ...]) -> None:
        self.seasons = {item.id: item for item in seasons}

    def list_playable_seasons(self) -> Sequence[PlayableSeasonSummaryDTO]:
        return tuple(item.summary() for item in reversed(tuple(self.seasons.values())))

    def get_playable_season(self, season_id: PlayableSeasonId) -> PlayableSeasonDTO:
        try:
            return self.seasons[season_id]
        except KeyError:
            raise PlayableSeasonNotFoundError(season_id) from None


class _FakeSeasonQueries:
    def __init__(self, items: tuple[Presented, ...]) -> None:
        self.items = items

    def list_seasons(self) -> tuple[Presented, ...]:
        return tuple(sorted(self.items, key=lambda item: str(item.value["id"])))

    def get_season(self, season_id: PlayableSeasonId) -> Presented:
        for item in self.items:
            if item.value["id"] == season_id.value:
                return item
        raise SeasonNotFoundError("playable season not found")


def _assert_season_query_contract(queries: SeasonQueries) -> None:
    items = queries.list_seasons()
    identifiers = [str(item.value["id"]) for item in items]
    assert identifiers == sorted(identifiers)
    with pytest.raises(DomainError) as error:
        queries.get_season(PlayableSeasonId("season-not-published"))
    assert error.value.code == "season_not_found"


def test_season_query_contract_holds_for_fake_and_catalog_acl() -> None:
    season = build_expected_test_fc_season()
    second = replace(season, id=PlayableSeasonId("another-test-season"))
    adapter = CatalogPresentationAdapter(_CatalogProvider((season, second)), Settings())
    fake = _FakeSeasonQueries(
        (Presented({"id": second.id.value}), Presented({"id": season.id.value}))
    )

    _assert_season_query_contract(fake)
    _assert_season_query_contract(adapter)


def test_game_api_translates_catalog_not_found_to_game_error() -> None:
    season = build_expected_test_fc_season()
    adapter = CatalogPresentationAdapter(_CatalogProvider((season,)), Settings())
    api = _api(seasons=adapter)

    with pytest.raises(SeasonNotFoundError):
        api.get_season(PlayableSeasonId("season-not-published"))
