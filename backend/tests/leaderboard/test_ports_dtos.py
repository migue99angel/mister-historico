"""Invariants of the Leaderboard DTOs."""

from dataclasses import replace
from datetime import datetime

import pytest
from tests.contracts.suites.leaderboard_repository import make_entry

from mister.leaderboard.application.ports import (
    SCORE_BUCKETS,
    AliasAlreadySetError,
    ScoreHistogram,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId, RunId


@pytest.mark.parametrize("score", [-1, 101])
def test_an_entry_score_is_between_0_and_100(score: int) -> None:
    with pytest.raises(InvalidValueError, match="score"):
        replace(make_entry(1, 50), mister_score=score)


def test_an_entry_finish_time_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidValueError, match="timezone"):
        replace(make_entry(1, 50), finished_at=datetime(2026, 10, 22))


def test_a_histogram_has_one_bucket_per_score() -> None:
    season = PlayableSeasonId("test-fc-2000-01")

    with pytest.raises(InvalidValueError, match="buckets"):
        ScoreHistogram(season, counts=(0, 0, 0))
    assert SCORE_BUCKETS == 101


def test_a_histogram_cannot_have_negative_counts() -> None:
    counts = (0,) * 100 + (-1,)

    with pytest.raises(InvalidValueError, match="negative"):
        ScoreHistogram(PlayableSeasonId("test-fc-2000-01"), counts=counts)


def test_the_alias_error_carries_its_stable_code() -> None:
    error = AliasAlreadySetError(RunId.new())

    assert error.code == "alias_already_set"
