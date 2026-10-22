"""Catalog fakes run against the port contract suites."""

import pytest

from mister.catalog.infrastructure.in_memory.season_content import InMemorySeasonContentProvider
from tests.contracts.suites.season_content_provider import (
    ProviderFactory,
    SeasonContentProviderContract,
)


class TestInMemorySeasonContentProvider(SeasonContentProviderContract):
    @pytest.fixture
    def make_provider(self) -> ProviderFactory:
        return InMemorySeasonContentProvider
