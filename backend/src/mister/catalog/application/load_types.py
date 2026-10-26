"""Application-owned reports and errors for publishing the catalog."""

from dataclasses import dataclass

from mister.catalog.application.validation_types import ValidationIssue
from mister.shared_kernel.errors import DomainError, InvalidValueError

SHA256_HEX_LENGTH = 64


@dataclass(frozen=True, slots=True)
class CatalogLoadReport:
    content_hash: str
    season_count: int
    changed: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.content_hash, str)
            or len(self.content_hash) != SHA256_HEX_LENGTH
            or any(character not in "0123456789abcdef" for character in self.content_hash)
        ):
            raise InvalidValueError("catalog load report needs a SHA-256 content hash")
        if type(self.season_count) is not int or self.season_count < 1:
            raise InvalidValueError("published catalog needs at least one playable season")
        if type(self.changed) is not bool:
            raise InvalidValueError("catalog load change flag must be boolean")


class CatalogContentInvalidError(DomainError):
    """The release content cannot be published; existing rows stay intact."""

    code = "catalog_content_invalid"

    def __init__(self, message: str, issues: tuple[ValidationIssue, ...] = ()) -> None:
        super().__init__(message)
        self.issues = tuple(
            sorted(issues, key=lambda issue: (issue.path, issue.field, issue.message))
        )


class CatalogLoadUnavailableError(DomainError):
    """The source or database cannot be accessed during a catalog load."""

    code = "catalog_load_unavailable"
