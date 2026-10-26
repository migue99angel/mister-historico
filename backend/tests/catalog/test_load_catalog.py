"""Catalog loading use case exposes a stable application report and errors."""

from pathlib import Path

import pytest

from mister.catalog.application.load_catalog import LoadCatalog
from mister.catalog.application.load_types import (
    CatalogContentInvalidError,
    CatalogLoadReport,
    CatalogLoadUnavailableError,
)
from mister.catalog.infrastructure.in_memory.catalog_publisher import InMemoryCatalogPublisher


def test_use_case_returns_the_publishers_report(tmp_path: Path) -> None:
    expected = CatalogLoadReport("a" * 64, 1, changed=True)
    publisher = InMemoryCatalogPublisher(expected)

    result = LoadCatalog(publisher).execute(tmp_path)

    assert result is expected
    assert publisher.roots == [tmp_path]


def test_use_case_preserves_content_issues(tmp_path: Path) -> None:
    error = CatalogContentInvalidError("invalid content")
    publisher = InMemoryCatalogPublisher(error)

    with pytest.raises(CatalogContentInvalidError) as caught:
        LoadCatalog(publisher).execute(tmp_path)

    assert caught.value is error


def test_use_case_preserves_unavailable_database_error(tmp_path: Path) -> None:
    error = CatalogLoadUnavailableError("database unavailable")

    with pytest.raises(CatalogLoadUnavailableError) as caught:
        LoadCatalog(InMemoryCatalogPublisher(error)).execute(tmp_path)

    assert caught.value is error
