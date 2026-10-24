"""Scripted content-validation fake; no YAML parsing or validation rules are reproduced."""

from collections.abc import Mapping

from mister.catalog.application.validation_types import (
    ContentValidationReport,
    ContentValidationUnavailableError,
)
from mister.shared_kernel.errors import InvalidValueError


class InMemoryContentValidator:
    """Return a preprogrammed application report or operational error for each mode."""

    def __init__(
        self,
        outcomes: Mapping[bool, ContentValidationReport | ContentValidationUnavailableError],
    ) -> None:
        if any(type(mode) is not bool for mode in outcomes) or any(
            not isinstance(outcome, ContentValidationReport | ContentValidationUnavailableError)
            for outcome in outcomes.values()
        ):
            raise InvalidValueError("scripted outcomes need boolean modes and application values")
        self._outcomes = dict(outcomes)

    def validate(self, *, release: bool) -> ContentValidationReport:
        """Repeated calls do not consume scripts or fall back to another mode's outcome."""
        if type(release) is not bool:
            raise InvalidValueError("release must be an explicit boolean")
        try:
            outcome = self._outcomes[release]
        except KeyError:
            raise InvalidValueError(
                f"no scripted validation outcome for release={release}"
            ) from None
        if isinstance(outcome, ContentValidationUnavailableError):
            raise ContentValidationUnavailableError(str(outcome))
        return outcome
