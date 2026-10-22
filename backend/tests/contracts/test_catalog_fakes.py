"""Catalog fakes run against the port contract suites, plus what only the fake does."""

import pytest

from mister.catalog.application.api import PlayableSeasonNotFoundError, SeasonContentProvider
from mister.catalog.infrastructure.in_memory.season_content import InMemorySeasonContentProvider
from tests.contracts.suites.expected_test_fc import build_expected_test_fc_season
from tests.contracts.suites.sample_content import make_sample_season
from tests.contracts.suites.season_content_provider import SeasonContentProviderContract


class TestInMemorySeasonContentProvider(SeasonContentProviderContract):
    @pytest.fixture
    def provider(self) -> SeasonContentProvider:
        return InMemorySeasonContentProvider([build_expected_test_fc_season()])


def test_the_fake_picks_the_requested_season_among_several() -> None:
    first = make_sample_season("test-fc", "2000-01")
    second = make_sample_season("mock-city", "2001-02")

    provider = InMemorySeasonContentProvider([first, second])

    assert provider.get_playable_season(second.id) == second
    assert provider.get_playable_season(first.id) == first


def test_the_fake_lists_summaries_ordered_by_id() -> None:
    later = make_sample_season("test-fc", "2000-01")
    earlier = make_sample_season("mock-city", "2001-02")

    provider = InMemorySeasonContentProvider([later, earlier])

    assert provider.list_playable_seasons() == (earlier.summary(), later.summary())


def test_an_empty_fake_lists_nothing_and_finds_nothing() -> None:
    provider = InMemorySeasonContentProvider()

    assert provider.list_playable_seasons() == ()
    with pytest.raises(PlayableSeasonNotFoundError):
        provider.get_playable_season(make_sample_season().id)
