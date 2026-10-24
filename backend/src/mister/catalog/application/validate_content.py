"""Content validation use case; IO and content rules belong to the injected port."""

from mister.catalog.application.ports import ContentValidationReport, ContentValidator


class ValidateContent:
    """Expose the configured validator's report and operational errors unchanged."""

    def __init__(self, validator: ContentValidator) -> None:
        self._validator = validator

    def execute(self, *, release: bool) -> ContentValidationReport:
        """Validate in the requested mode without interpreting or replacing the report."""
        return self._validator.validate(release=release)
