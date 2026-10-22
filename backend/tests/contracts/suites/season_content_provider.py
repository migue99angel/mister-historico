"""Contract of the `SeasonContentProvider` port.

Reuse: subclass `SeasonContentProviderContract` in a `Test...` class and override the
`make_provider` fixture with a factory that returns a provider loaded with the given seasons
(the fake takes them directly; the real adapter of T2.21 loads them into its store first).
"""

from collections.abc import Callable, Sequence

import pytest

from mister.catalog.application.api import (
    PlayableSeasonDTO,
    PlayableSeasonNotFoundError,
    SeasonContentProvider,
)
from mister.shared_kernel.errors import DomainError
from mister.shared_kernel.ids import PlayableSeasonId
from tests.contracts.suites.sample_content import make_sample_season

ProviderFactory = Callable[[Sequence[PlayableSeasonDTO]], SeasonContentProvider]


class SeasonContentProviderContract:
    """Behaviour every `SeasonContentProvider` must have."""

    @pytest.fixture
    def make_provider(self) -> ProviderFactory:
        raise NotImplementedError

    def test_get_returns_exactly_the_season_it_was_given(
        self, make_provider: ProviderFactory
    ) -> None:
        season = make_sample_season()

        provider = make_provider([season])

        assert provider.get_playable_season(season.id) == season

    def test_get_picks_the_requested_season_among_several(
        self, make_provider: ProviderFactory
    ) -> None:
        first = make_sample_season("test-fc", "2000-01")
        second = make_sample_season("mock-city", "2001-02")

        provider = make_provider([first, second])

        assert provider.get_playable_season(second.id) == second
        assert provider.get_playable_season(first.id) == first

    def test_get_unknown_season_raises_a_domain_error_with_its_code(
        self, make_provider: ProviderFactory
    ) -> None:
        provider = make_provider([make_sample_season()])

        with pytest.raises(PlayableSeasonNotFoundError) as caught:
            provider.get_playable_season(PlayableSeasonId("nobody-1999-00"))

        assert isinstance(caught.value, DomainError)
        assert caught.value.code == "season_not_found"

    def test_list_returns_one_summary_per_season_ordered_by_id(
        self, make_provider: ProviderFactory
    ) -> None:
        later = make_sample_season("test-fc", "2000-01")
        earlier = make_sample_season("mock-city", "2001-02")

        provider = make_provider([later, earlier])

        assert provider.list_playable_seasons() == (earlier.summary(), later.summary())

    def test_list_is_empty_without_seasons(self, make_provider: ProviderFactory) -> None:
        assert make_provider([]).list_playable_seasons() == ()

    def test_summary_carries_what_the_season_picker_shows(
        self, make_provider: ProviderFactory
    ) -> None:
        season = make_sample_season()

        (summary,) = make_provider([season]).list_playable_seasons()

        assert summary.id == season.id
        assert summary.club_name == "Test FC"
        assert summary.season == "2000-01"
        assert summary.historical_manager == season.manager.display_name
        assert (summary.primary_color, summary.secondary_color) == ("#1F4E79", "#FFFFFF")
