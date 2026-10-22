"""`Clock` port: the current time, always timezone-aware."""

from datetime import UTC, datetime, timedelta
from typing import Protocol

from mister.shared_kernel.errors import InvalidValueError


class Clock(Protocol):
    """Port that gives the current instant, as a timezone-aware `datetime`."""

    def now(self) -> datetime: ...


class SystemClock:
    """Real time, in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Test fake: returns a fixed instant until it is explicitly advanced."""

    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise InvalidValueError("FixedClock needs a timezone-aware datetime")
        self._instant = instant

    def now(self) -> datetime:
        return self._instant

    def advance(self, delta: timedelta) -> None:
        """Move the clock forward (or backward, with a negative delta)."""
        self._instant += delta
