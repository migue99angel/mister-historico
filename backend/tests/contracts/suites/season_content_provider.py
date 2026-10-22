"""Contract of the `SeasonContentProvider` port, over the synthetic Test FC 2000-01 content.

Reuse: subclass `SeasonContentProviderContract` in a `Test...` class and override the
`provider` fixture with a provider that serves `backend/tests/fixtures/content/`:

- the in-memory fake is built from `build_expected_test_fc_season()`;
- the YAML adapter (T2.20) loads the directory `CONTENT_ROOT`;
- the SQL adapter (T2.21) loads the same tree into its tables first.

Every adapter must publish exactly `build_expected_test_fc_season()` (see that module for the
mapping rules), so the three cannot drift apart.
"""

import pytest

from mister.catalog.application.api import (
    PlayableSeasonNotFoundError,
    SeasonContentProvider,
)
from mister.shared_kernel.errors import DomainError
from mister.shared_kernel.ids import PlayableSeasonId
from tests.contracts.suites.expected_test_fc import TEST_FC_SEASON, build_expected_test_fc_season


class SeasonContentProviderContract:
    """Behaviour every `SeasonContentProvider` must have."""

    @pytest.fixture
    def provider(self) -> SeasonContentProvider:
        raise NotImplementedError

    def test_get_returns_the_season_the_content_describes(
        self, provider: SeasonContentProvider
    ) -> None:
        assert provider.get_playable_season(TEST_FC_SEASON) == build_expected_test_fc_season()

    def test_get_is_repeatable(self, provider: SeasonContentProvider) -> None:
        assert provider.get_playable_season(TEST_FC_SEASON) == provider.get_playable_season(
            TEST_FC_SEASON
        )

    def test_get_unknown_season_raises_a_domain_error_with_its_code(
        self, provider: SeasonContentProvider
    ) -> None:
        with pytest.raises(PlayableSeasonNotFoundError) as caught:
            provider.get_playable_season(PlayableSeasonId("nobody-1999-00"))

        assert isinstance(caught.value, DomainError)
        assert caught.value.code == "season_not_found"

    def test_the_content_has_exactly_one_playable_season(
        self, provider: SeasonContentProvider
    ) -> None:
        assert provider.list_playable_seasons() == (build_expected_test_fc_season().summary(),)

    def test_the_summary_carries_what_the_season_picker_shows(
        self, provider: SeasonContentProvider
    ) -> None:
        (summary,) = provider.list_playable_seasons()

        assert summary.id == TEST_FC_SEASON
        assert summary.club_name == "Test FC"
        assert summary.short_name == "TFC"
        assert summary.season == "2000-01"
        assert summary.historical_manager == "Mister Ficticio"
        assert (summary.primary_color, summary.secondary_color) == ("#1F4E79", "#FFFFFF")
