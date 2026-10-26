"""Translate SQL/YAML loading outcomes to the Catalog application port."""

from pathlib import Path

import sqlalchemy as sa

from mister.catalog.application.load_types import (
    CatalogContentInvalidError,
    CatalogLoadReport,
    CatalogLoadUnavailableError,
)
from mister.catalog.application.validation_types import ValidationIssue
from mister.catalog.infrastructure.content_schema import ContentValidationError
from mister.catalog.infrastructure.sqlalchemy.catalog import SqlCatalogLoader
from mister.shared_kernel.errors import InvalidValueError


class SqlCatalogPublisher:
    """Adapt the transactional SQL loader to application reports and errors."""

    def __init__(self, engine: sa.Engine) -> None:
        self._loader = SqlCatalogLoader(engine)

    def load(self, root: Path) -> CatalogLoadReport:
        if not root.is_dir():
            raise CatalogLoadUnavailableError(f"content root {root} is not a directory")
        try:
            result = self._loader.load(root)
        except ContentValidationError as error:
            issues = tuple(
                ValidationIssue(issue.path, issue.field, issue.message) for issue in error.issues
            )
            raise CatalogContentInvalidError("release content is invalid", issues) from error
        except InvalidValueError as error:
            raise CatalogContentInvalidError(str(error)) from error
        except (OSError, UnicodeError, sa.exc.SQLAlchemyError) as error:
            raise CatalogLoadUnavailableError(f"catalog load unavailable: {error}") from error
        return CatalogLoadReport(result.content_hash, result.season_count, result.changed)
