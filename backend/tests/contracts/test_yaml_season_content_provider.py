"""The YAML provider must satisfy the published season content contract."""

from pathlib import Path

import pytest

from mister.catalog.application.api import SeasonContentProvider
from mister.catalog.infrastructure.yaml_season_content import YamlSeasonContentProvider
from tests.contracts.suites.season_content_provider import SeasonContentProviderContract

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "content"


class TestYamlSeasonContentProvider(SeasonContentProviderContract):
    @pytest.fixture
    def provider(self) -> SeasonContentProvider:
        return YamlSeasonContentProvider(CONTENT_ROOT)
