"""Reusable `ContentValidator` contract over synthetic Test FC validation scenarios.

Subclass and provide `make_validator`. The fake scripts these outcomes; the future YAML
adapter will copy the Test FC tree for valid/pending/invalid scenarios, use a directory
without files for empty, and arrange an operational read failure for unavailable.
The invalid tree has an unknown `unexpected` field in fixtures.yaml and texts.yaml;
the pending tree has its first text in draft. Expected messages match the current loader.
"""

from collections.abc import Callable
from typing import Literal

import pytest

from mister.catalog.application.ports import ContentValidator
from mister.catalog.application.validation_types import (
    ContentValidationUnavailableError,
    ValidationIssue,
)
from mister.shared_kernel.errors import DomainError

type ValidationScenario = Literal["valid", "empty", "invalid", "pending", "unavailable"]
type ValidatorFactory = Callable[[ValidationScenario], ContentValidator]

MULTIPLE_ISSUES = (
    ValidationIssue(
        "seasons/test-fc-2000-01/fixtures.yaml", "unexpected", "Extra inputs are not permitted"
    ),
    ValidationIssue(
        "seasons/test-fc-2000-01/texts.yaml", "unexpected", "Extra inputs are not permitted"
    ),
)
PENDING_ISSUE = ValidationIssue(
    "seasons/test-fc-2000-01/texts.yaml",
    "texts.0.status",
    "draft texts are not allowed in release mode",
)


class ContentValidatorContract:
    """Observable report/error semantics, independent of the validation implementation."""

    @pytest.fixture
    def make_validator(self) -> ValidatorFactory:
        raise NotImplementedError

    @pytest.mark.parametrize("release", [False, True])
    def test_valid_content_reports_the_known_season_count(
        self, make_validator: ValidatorFactory, release: bool
    ) -> None:
        report = make_validator("valid").validate(release=release)

        assert report.valid
        assert report.issues == ()
        assert report.season_count == 1

    @pytest.mark.parametrize("release", [False, True])
    def test_a_known_empty_tree_reports_zero_seasons(
        self, make_validator: ValidatorFactory, release: bool
    ) -> None:
        report = make_validator("empty").validate(release=release)

        assert report.valid
        assert report.season_count == 0

    @pytest.mark.parametrize("release", [False, True])
    def test_content_errors_accumulate_in_stable_order_without_a_partial_count(
        self, make_validator: ValidatorFactory, release: bool
    ) -> None:
        report = make_validator("invalid").validate(release=release)

        assert not report.valid
        assert report.issues == MULTIPLE_ISSUES
        assert report.season_count is None

    def test_release_adds_requirements_to_content_accepted_during_development(
        self, make_validator: ValidatorFactory
    ) -> None:
        validator = make_validator("pending")

        normal = validator.validate(release=False)
        release = validator.validate(release=True)

        assert normal.valid
        assert normal.season_count == 1
        assert not release.valid
        assert release.issues == (PENDING_ISSUE,)
        assert release.season_count is None

    @pytest.mark.parametrize("scenario", ["valid", "empty", "invalid", "pending"])
    def test_repeated_validation_does_not_consume_or_cross_contaminate_modes(
        self, make_validator: ValidatorFactory, scenario: ValidationScenario
    ) -> None:
        validator = make_validator(scenario)
        normal = validator.validate(release=False)
        release = validator.validate(release=True)

        assert validator.validate(release=False) == normal
        assert validator.validate(release=True) == release
        assert make_validator(scenario).validate(release=False) == normal

    @pytest.mark.parametrize("release", [False, True])
    def test_operational_failures_raise_the_application_error_instead_of_a_content_report(
        self, make_validator: ValidatorFactory, release: bool
    ) -> None:
        validator = make_validator("unavailable")

        for _ in range(2):
            with pytest.raises(ContentValidationUnavailableError) as caught:
                validator.validate(release=release)

            assert isinstance(caught.value, DomainError)
            assert caught.value.code == "content_validation_unavailable"
