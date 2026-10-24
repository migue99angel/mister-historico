"""The scripted content validator runs the shared contract without reading YAML."""

from typing import Any

import pytest
from tests.contracts.suites.content_validator import (
    MULTIPLE_ISSUES,
    PENDING_ISSUE,
    ContentValidatorContract,
    ValidationScenario,
    ValidatorFactory,
)

from mister.catalog.application.ports import ContentValidator
from mister.catalog.application.validation_types import (
    ContentValidationReport,
    ContentValidationUnavailableError,
)
from mister.catalog.infrastructure.in_memory.content_validation import InMemoryContentValidator
from mister.shared_kernel.errors import InvalidValueError


class TestInMemoryContentValidator(ContentValidatorContract):
    @pytest.fixture
    def make_validator(self) -> ValidatorFactory:
        def make(scenario: ValidationScenario) -> ContentValidator:
            valid = ContentValidationReport((), 1)
            if scenario == "valid":
                return InMemoryContentValidator({False: valid, True: valid})
            if scenario == "empty":
                empty = ContentValidationReport((), 0)
                return InMemoryContentValidator({False: empty, True: empty})
            if scenario == "invalid":
                invalid = ContentValidationReport(tuple(reversed(MULTIPLE_ISSUES)), None)
                return InMemoryContentValidator({False: invalid, True: invalid})
            if scenario == "pending":
                return InMemoryContentValidator(
                    {False: valid, True: ContentValidationReport((PENDING_ISSUE,), None)}
                )
            unavailable = ContentValidationUnavailableError("content root cannot be read")
            return InMemoryContentValidator({False: unavailable, True: unavailable})

        return make


def test_the_fake_does_not_invent_an_outcome_for_an_unprogrammed_mode() -> None:
    validator = InMemoryContentValidator({False: ContentValidationReport((), 1)})

    with pytest.raises(InvalidValueError, match="scripted"):
        validator.validate(release=True)


def test_the_fake_copies_its_programmed_outcomes() -> None:
    original = ContentValidationReport((), 1)
    outcomes = {False: original}
    validator = InMemoryContentValidator(outcomes)
    outcomes[False] = ContentValidationReport((), 0)

    assert validator.validate(release=False) == original


@pytest.mark.parametrize("mode", [0, 1, None, "release"])
def test_the_fake_requires_an_explicit_boolean_release_mode(mode: Any) -> None:
    validator = InMemoryContentValidator({False: ContentValidationReport((), 1)})

    with pytest.raises(InvalidValueError):
        validator.validate(release=mode)


@pytest.mark.parametrize("outcomes", [{0: ContentValidationReport((), 1)}, {False: None}, {False: RuntimeError("failure")}])
def test_the_fake_program_accepts_only_boolean_modes_and_application_outcomes(outcomes: Any) -> None:
    with pytest.raises(InvalidValueError):
        InMemoryContentValidator(outcomes)


def test_operational_errors_in_one_mode_do_not_replace_a_report_in_the_other() -> None:
    validator = InMemoryContentValidator(
        {
            False: ContentValidationReport((), 0),
            True: ContentValidationUnavailableError("release root cannot be read"),
        }
    )

    with pytest.raises(ContentValidationUnavailableError, match="release root"):
        validator.validate(release=True)
    assert validator.validate(release=False) == ContentValidationReport((), 0)
