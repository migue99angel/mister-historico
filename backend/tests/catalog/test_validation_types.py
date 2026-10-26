"""Application-owned validation diagnostics and immutable report invariants."""

from dataclasses import FrozenInstanceError
from pathlib import PurePosixPath
from typing import Any

import pytest

from mister.catalog.application import ports
from mister.catalog.application.validation_types import (
    ContentValidationReport,
    ContentValidationUnavailableError,
    ValidationIssue,
)
from mister.shared_kernel.errors import DomainError, InvalidValueError

_PATH = "seasons/test-fc-2000-01/season.yaml"


@pytest.mark.parametrize("path", [".", "clubs/test-fc.yaml", _PATH, "club-seasons/test-fc-2000-01"])
def test_an_issue_preserves_a_relative_posix_path_and_its_diagnostic(path: str) -> None:
    issue = ValidationIssue(path, "blocks.0.dilemmas", "at least one dilemma is required")

    assert (issue.path, issue.field, issue.message) == (
        path,
        "blocks.0.dilemmas",
        "at least one dilemma is required",
    )


def test_an_empty_field_identifies_a_whole_file_issue() -> None:
    assert ValidationIssue(_PATH, "", "file is missing").field == ""


@pytest.mark.parametrize(
    "path",
    [r"clubs/bad\name.yaml", r"seasons\season.yaml", r"..\season.yaml", r"\season.yaml"],
)
def test_backslashes_are_preserved_as_literal_posix_filename_characters(path: str) -> None:
    issue = ValidationIssue(path, "", "invalid file")

    assert issue.path == path
    assert issue.path != path.replace("\\", "/")


@pytest.mark.parametrize(
    "path",
    [
        "",
        " ",
        "/content/season.yaml",
        "../season.yaml",
        "seasons/../season.yaml",
        "./season.yaml",
        "seasons//season.yaml",
        "seasons/",
        "seasons/\x00.yaml",
        PurePosixPath("season.yaml"),
        None,
    ],
)
def test_issue_paths_cannot_escape_the_root_or_silently_change_representation(path: Any) -> None:
    with pytest.raises(InvalidValueError):
        ValidationIssue(path, "", "invalid file")


@pytest.mark.parametrize(
    ("field", "message"), [(None, "invalid"), (1, "invalid"), ("", None), ("", ""), ("", " \n")]
)
def test_fields_are_strings_and_messages_are_non_blank(field: Any, message: Any) -> None:
    with pytest.raises(InvalidValueError):
        ValidationIssue(_PATH, field, message)


@pytest.mark.parametrize("count", [0, 1, 2])
def test_successful_reports_know_the_number_of_seasons_including_an_empty_tree(count: int) -> None:
    report = ContentValidationReport((), count)

    assert report.valid
    assert report.issues == ()
    assert report.season_count == count


@pytest.mark.parametrize("count", [None, True, False, -1, 1.0, "1"])
def test_a_successful_report_requires_a_non_negative_non_boolean_integer(count: Any) -> None:
    with pytest.raises(InvalidValueError):
        ContentValidationReport((), count)


def test_invalid_reports_preserve_all_issues_and_leave_the_season_count_unknown() -> None:
    issues = (ValidationIssue(_PATH, "blocks", "missing dilemmas"),)

    report = ContentValidationReport(issues, None)

    assert not report.valid
    assert report.issues == issues
    assert report.season_count is None


@pytest.mark.parametrize("count", [0, 1, True, "unknown"])
def test_invalid_reports_cannot_publish_a_count_from_a_partial_tree(count: Any) -> None:
    with pytest.raises(InvalidValueError):
        ContentValidationReport((ValidationIssue(_PATH, "", "invalid"),), count)


@pytest.mark.parametrize(
    "issues", [[], [ValidationIssue(_PATH, "", "invalid")], ("invalid",), None]
)
def test_reports_require_an_immutable_tuple_of_application_issues(issues: Any) -> None:
    with pytest.raises(InvalidValueError):
        ContentValidationReport(issues, None)


def test_report_order_is_stable_by_path_then_field_then_message_and_retains_duplicates() -> None:
    a = ValidationIssue("clubs/test-fc.yaml", "", "missing file")
    b = ValidationIssue(_PATH, "blocks", "missing dilemmas")
    c = ValidationIssue(_PATH, "slug", "a problem")
    d = ValidationIssue(_PATH, "slug", "z problem")
    original = (d, b, c, a, b)

    report = ContentValidationReport(original, None)

    assert report.issues == (a, b, b, c, d)
    assert original == (d, b, c, a, b)


def test_issues_and_reports_cannot_be_mutated_or_override_derived_validity() -> None:
    issue = ValidationIssue(_PATH, "", "invalid")
    report = ContentValidationReport((issue,), None)

    with pytest.raises(FrozenInstanceError):
        issue.message = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        report.issues = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        report.valid = True  # type: ignore[misc]


def test_operational_failure_has_a_stable_application_error_code() -> None:
    error = ContentValidationUnavailableError("content root cannot be read")

    assert isinstance(error, DomainError)
    assert error.code == "content_validation_unavailable"
    assert str(error) == "content root cannot be read"


@pytest.mark.parametrize(
    "name",
    [
        "ContentValidator",
        "ContentValidationReport",
        "ContentValidationUnavailableError",
        "ValidationIssue",
    ],
)
def test_validation_contract_types_are_available_with_the_other_catalog_ports(name: str) -> None:
    assert name in ports.__all__
    assert hasattr(ports, name)
