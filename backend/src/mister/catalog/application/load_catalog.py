"""Use case for publishing release-validated catalog content."""

from pathlib import Path

from mister.catalog.application.load_types import CatalogLoadReport
from mister.catalog.application.ports import CatalogPublisher


class LoadCatalog:
    def __init__(self, publisher: CatalogPublisher) -> None:
        self._publisher = publisher

    def execute(self, root: Path) -> CatalogLoadReport:
        """Return the publisher's report or its application-owned error unchanged."""
        return self._publisher.load(root)
