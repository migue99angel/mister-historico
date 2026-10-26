"""Application-owned reports and operational errors for content validation."""

from dataclasses import dataclass
from pathlib import PurePosixPath

from mister.shared_kernel.errors import DomainError, InvalidValueError


class ContentValidationUnavailableError(DomainError):
    """The validator cannot read or access its content root for operational reasons."""

    code = "content_validation_unavailable"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A content diagnostic with a root-relative POSIX path; `.` identifies the root."""

    path: str
    field: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path.strip():
            raise InvalidValueError("a validation issue needs a relative POSIX path")
        path = PurePosixPath(self.path)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\x00" in self.path
            or path.as_posix() != self.path
        ):
            raise InvalidValueError("a validation issue needs a canonical relative POSIX path")
        if not isinstance(self.field, str):
            raise InvalidValueError("a validation field must be a string, possibly empty")
        if not isinstance(self.message, str) or not self.message.strip():
            raise InvalidValueError("a validation message must be a non-blank string")


@dataclass(frozen=True)
class ContentValidationReport:
    """All content issues in stable order; only a valid tree has a known season count."""

    issues: tuple[ValidationIssue, ...]
    season_count: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.issues, tuple) or not all(
            isinstance(issue, ValidationIssue) for issue in self.issues
        ):
            raise InvalidValueError(
                "validation issues must be an immutable tuple of ValidationIssue"
            )
        if self.issues:
            if self.season_count is not None:
                raise InvalidValueError("an invalid content tree has an unknown season count")
        elif (
            isinstance(self.season_count, bool)
            or not isinstance(self.season_count, int)
            or self.season_count < 0
        ):
            raise InvalidValueError(
                "a valid content tree needs a non-negative integer season count"
            )
        object.__setattr__(
            self,
            "issues",
            tuple(sorted(self.issues, key=lambda issue: (issue.path, issue.field, issue.message))),
        )

    @property
    def valid(self) -> bool:
        """Validity follows from the absence of content issues, never from the count."""
        return not self.issues
