"""Presentation policy for real and fictionalized names (ADR-008)."""

from dataclasses import dataclass

from mister.shared_kernel.errors import InvalidValueError


@dataclass(frozen=True, slots=True)
class NamePolicy:
    """Choose the visible name without changing catalog identities or historical records."""

    real_names: bool

    def __post_init__(self) -> None:
        if type(self.real_names) is not bool:
            raise InvalidValueError("real_names must be a boolean")

    def display(self, display_name: str, alias_name: str) -> str:
        """Return the configured visible name for a player or manager."""
        return display_name if self.real_names else alias_name
