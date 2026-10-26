"""Programmable in-memory catalog publisher for application tests."""

from pathlib import Path

from mister.catalog.application.load_types import (
    CatalogContentInvalidError,
    CatalogLoadReport,
    CatalogLoadUnavailableError,
)


class InMemoryCatalogPublisher:
    def __init__(
        self,
        outcome: CatalogLoadReport | CatalogContentInvalidError | CatalogLoadUnavailableError,
    ) -> None:
        self._outcome = outcome
        self.roots: list[Path] = []

    def load(self, root: Path) -> CatalogLoadReport:
        self.roots.append(root)
        if isinstance(self._outcome, (CatalogContentInvalidError, CatalogLoadUnavailableError)):
            raise self._outcome
        return self._outcome
