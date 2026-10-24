"""Root-bound YAML content validator translating the existing loader's outcomes."""

from pathlib import Path

from mister.catalog.application.validation_types import (
    ContentValidationReport,
    ContentValidationUnavailableError,
    ValidationIssue,
)
from mister.catalog.infrastructure.content_schema import ContentValidationError, load_content_tree
from mister.shared_kernel.errors import InvalidValueError


class YamlContentValidator:
    """Use `load_content_tree` as the sole authority for content-validation rules."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def validate(self, *, release: bool) -> ContentValidationReport:
        """Report content issues completely and distinguish unavailable IO from invalid data."""
        if type(release) is not bool:
            raise InvalidValueError("release must be an explicit boolean")
        try:
            if not self._root.is_dir():
                raise ContentValidationUnavailableError(
                    f"content root {self._root} is not an available directory"
                )
            # Globbing may suppress directory access errors; probe the root explicitly.
            next(self._root.iterdir(), None)
            tree = load_content_tree(self._root, release=release)
        except ContentValidationError as error:
            return ContentValidationReport(
                tuple(
                    ValidationIssue(issue.path, issue.field, issue.message)
                    for issue in error.issues
                ),
                None,
            )
        except (OSError, UnicodeError) as error:
            raise ContentValidationUnavailableError(
                f"content root {self._root} cannot be read: {error}"
            ) from error
        return ContentValidationReport((), len(tree.seasons))
