"""Shared behavioral contract for the catalog publication port."""

from pathlib import Path

import pytest

from mister.catalog.application.load_types import (
    CatalogContentInvalidError,
    CatalogLoadReport,
    CatalogLoadUnavailableError,
)
from mister.catalog.application.ports import CatalogPublisher


class CatalogPublisherContract:
    @pytest.fixture
    def valid(self) -> tuple[CatalogPublisher, Path]:
        raise NotImplementedError

    @pytest.fixture
    def invalid(self) -> tuple[CatalogPublisher, Path]:
        raise NotImplementedError

    @pytest.fixture
    def unavailable(self) -> tuple[CatalogPublisher, Path]:
        raise NotImplementedError

    def test_valid_release_returns_a_versioned_report(
        self, valid: tuple[CatalogPublisher, Path]
    ) -> None:
        publisher, root = valid

        report = publisher.load(root)

        assert isinstance(report, CatalogLoadReport)
        assert len(report.content_hash) == 64
        assert report.season_count >= 1

    def test_invalid_release_raises_an_application_error(
        self, invalid: tuple[CatalogPublisher, Path]
    ) -> None:
        publisher, root = invalid

        with pytest.raises(CatalogContentInvalidError) as caught:
            publisher.load(root)

        assert caught.value.code == "catalog_content_invalid"

    def test_unavailable_source_raises_an_application_error(
        self, unavailable: tuple[CatalogPublisher, Path]
    ) -> None:
        publisher, root = unavailable

        with pytest.raises(CatalogLoadUnavailableError) as caught:
            publisher.load(root)

        assert caught.value.code == "catalog_load_unavailable"
