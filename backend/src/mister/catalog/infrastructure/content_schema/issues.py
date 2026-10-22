"""Validation issues: every problem found in a content tree, with file path and field."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContentIssue:
    """One problem in one file. `path` is relative to the content root (POSIX style)."""

    path: str
    field: str
    message: str

    def __str__(self) -> str:
        if self.field:
            return f"{self.path}: {self.field}: {self.message}"
        return f"{self.path}: {self.message}"


class ContentValidationError(Exception):
    """Raised when a content tree is invalid. It carries *all* the issues, not just the first."""

    def __init__(self, issues: list[ContentIssue]) -> None:
        self.issues: tuple[ContentIssue, ...] = tuple(issues)
        lines = [f"{len(issues)} content issue(s):", *(f"  - {issue}" for issue in issues)]
        super().__init__("\n".join(lines))


class IssueSink:
    """Collects issues while the tree is read and checked."""

    def __init__(self) -> None:
        self.issues: list[ContentIssue] = []

    def add(self, path: str, field: str, message: str) -> None:
        self.issues.append(ContentIssue(path, field, message))
