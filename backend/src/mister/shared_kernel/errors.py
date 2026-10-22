"""Domain errors.

Every business-rule violation derives from `DomainError` and carries a stable, machine-readable
`code`. The API layer maps it to `problem+json` using that code, so codes are part of the public
contract: never rename one, add a new subclass instead.
"""


class DomainError(Exception):
    """Base class of every domain error.

    Subclasses override the class attribute `code` with a stable snake_case identifier.
    """

    code: str = "domain_error"


class InvalidValueError(DomainError, ValueError):
    """A value object received a value that breaks its invariants (bad ID, seed range...)."""

    code = "invalid_value"
