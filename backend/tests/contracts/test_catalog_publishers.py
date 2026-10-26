"""The in-memory publisher satisfies the same application contract as SQL."""

from pathlib import Path

import pytest

from mister.catalog.application.load_types import (
    CatalogContentInvalidError,
    CatalogLoadReport,
    CatalogLoadUnavailableError,
)
from mister.catalog.application.ports import CatalogPublisher
from mister.catalog.infrastructure.in_memory.catalog_publisher import InMemoryCatalogPublisher
from tests.contracts.suites.catalog_publisher import CatalogPublisherContract


class TestInMemoryCatalogPublisher(CatalogPublisherContract):
    @pytest.fixture
    def valid(self, tmp_path: Path) -> tuple[CatalogPublisher, Path]:
        return InMemoryCatalogPublisher(CatalogLoadReport("a" * 64, 1, True)), tmp_path

    @pytest.fixture
    def invalid(self, tmp_path: Path) -> tuple[CatalogPublisher, Path]:
        return InMemoryCatalogPublisher(CatalogContentInvalidError("invalid")), tmp_path

    @pytest.fixture
    def unavailable(self, tmp_path: Path) -> tuple[CatalogPublisher, Path]:
        return InMemoryCatalogPublisher(CatalogLoadUnavailableError("unavailable")), tmp_path
