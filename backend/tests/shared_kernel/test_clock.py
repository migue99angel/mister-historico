"""`Clock`: timezone-aware time, with a fixed fake for tests."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from mister.shared_kernel.clock import Clock, FixedClock, SystemClock
from mister.shared_kernel.errors import InvalidValueError


def test_system_clock_returns_the_current_time_in_utc() -> None:
    before = datetime.now(UTC)

    now = SystemClock().now()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)
    assert before <= now <= datetime.now(UTC)


def test_fixed_clock_always_returns_the_same_aware_instant() -> None:
    instant = datetime(2012, 12, 13, 20, 0, tzinfo=UTC)
    clock = FixedClock(instant)

    assert clock.now() == instant
    assert clock.now() == instant
    assert clock.now().tzinfo is not None


def test_fixed_clock_rejects_naive_datetimes() -> None:
    with pytest.raises(InvalidValueError):
        FixedClock(datetime(2012, 12, 13, 20, 0))


def test_fixed_clock_can_be_advanced() -> None:
    clock = FixedClock(datetime(2012, 12, 13, tzinfo=UTC))

    clock.advance(timedelta(hours=2))

    assert clock.now() == datetime(2012, 12, 13, 2, tzinfo=UTC)


def test_fixed_clock_keeps_the_timezone_it_was_given() -> None:
    cet = timezone(timedelta(hours=1))

    assert FixedClock(datetime(2012, 12, 13, tzinfo=cet)).now().utcoffset() == timedelta(hours=1)


def test_clocks_satisfy_the_protocol() -> None:
    clocks: list[Clock] = [SystemClock(), FixedClock(datetime(2000, 1, 1, tzinfo=UTC))]

    assert all(clock.now().tzinfo is not None for clock in clocks)
