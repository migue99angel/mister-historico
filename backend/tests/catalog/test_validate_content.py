"""Content validation orchestration uses only the application port and scripted outcomes."""

import pytest

from mister.catalog.application.validate_content import ValidateContent
from mister.catalog.application.validation_types import (
    ContentValidationReport,
    ContentValidationUnavailableError,
    ValidationIssue,
)
from mister.catalog.infrastructure.in_memory.content_validation import InMemoryContentValidator


@pytest.mark.parametrize("release", [False, True])
def test_the_use_case_returns_the_report_for_the_requested_mode(release: bool) -> None:
    normal = ContentValidationReport((), 1)
    strict = ContentValidationReport(
        (ValidationIssue("seasons/test-fc-2000-01/texts.yaml", "texts.0.status", "draft text"),),
        None,
    )
    use_case = ValidateContent(InMemoryContentValidator({False: normal, True: strict}))

    report = use_case.execute(release=release)

    assert report is (strict if release else normal)


def test_a_known_empty_catalog_remains_a_success_with_zero_seasons() -> None:
    report = ContentValidationReport((), 0)

    assert ValidateContent(InMemoryContentValidator({False: report})).execute(release=False) is report


def test_all_content_issues_and_an_unknown_count_reach_the_caller() -> None:
    report = ContentValidationReport(
        (
            ValidationIssue("clubs/test-fc.yaml", "", "file is missing"),
            ValidationIssue("seasons/test-fc-2000-01/season.yaml", "slug", "wrong directory"),
        ),
        None,
    )

    actual = ValidateContent(InMemoryContentValidator({True: report})).execute(release=True)

    assert actual is report
    assert len(actual.issues) == 2
    assert actual.season_count is None


@pytest.mark.parametrize("release", [False, True])
def test_operational_failure_is_preserved_without_a_fallback_report(release: bool) -> None:
    validator = InMemoryContentValidator(
        {release: ContentValidationUnavailableError("test root cannot be read")}
    )

    with pytest.raises(ContentValidationUnavailableError, match="test root cannot be read"):
        ValidateContent(validator).execute(release=release)
