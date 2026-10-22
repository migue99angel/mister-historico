"""Application ports of the Leaderboard context, with the DTOs they exchange.

Decisions:

- **Who is in the ranking.** Only runs published under an alias (`add_entry`); the alias is set
  once per run (`AliasAlreadySetError` otherwise). Alias *text* validation (3 to 20 characters,
  insult filter) is the `Alias` value object of T5.2 and happens before `add_entry`.
- **Order.** Score descending, then the run that finished first, then run id (so the order is
  total and stable). `rank` is the one-based position in that order.
- **Percentile.** It compares a run with every finished run of the season, not only with the
  published ones, so scores are recorded separately (`record_score`, first write per run wins)
  into a histogram with one bucket per score from 0 to 100. The percentile formula is T5.2's.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId, RunId

MIN_SCORE = 0
MAX_SCORE = 100
SCORE_BUCKETS = MAX_SCORE - MIN_SCORE + 1
MAX_PAGE_SIZE = 100


class AliasAlreadySetError(DomainError):
    """The run is already published under an alias (API: `409 alias_already_set`)."""

    code = "alias_already_set"

    def __init__(self, run_id: RunId) -> None:
        super().__init__(f"run {run_id} already has an alias")
        self.run_id = run_id


def require_score(score: int) -> None:
    """Shared check of a Mister score; raises `InvalidValueError` outside 0..100."""
    if not MIN_SCORE <= score <= MAX_SCORE:
        raise InvalidValueError(f"score must be between {MIN_SCORE} and {MAX_SCORE}, got {score}")


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    """A run published in the leaderboard under its alias."""

    run_id: RunId
    season_id: PlayableSeasonId
    alias: str
    mister_score: int
    verdict_kind: str
    finished_at: datetime

    def __post_init__(self) -> None:
        require_score(self.mister_score)
        if self.finished_at.tzinfo is None or self.finished_at.utcoffset() is None:
            raise InvalidValueError("finished_at must be a timezone-aware datetime")


@dataclass(frozen=True, slots=True)
class RankedEntry:
    rank: int
    entry: LeaderboardEntry


@dataclass(frozen=True, slots=True)
class LeaderboardPage:
    """One page of a season leaderboard (`total` counts all pages)."""

    season_id: PlayableSeasonId
    page: int
    page_size: int
    total: int
    items: tuple[RankedEntry, ...]


@dataclass(frozen=True, slots=True)
class ScoreHistogram:
    """Finished runs of a season per Mister score: `counts[score]` for score 0..100."""

    season_id: PlayableSeasonId
    counts: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.counts) != SCORE_BUCKETS:
            raise InvalidValueError(f"a histogram has {SCORE_BUCKETS} buckets")
        if any(count < 0 for count in self.counts):
            raise InvalidValueError("a histogram cannot have negative counts")

    @property
    def total(self) -> int:
        return sum(self.counts)


class LeaderboardRepository(Protocol):
    """Persistence of the leaderboard and of the score histogram."""

    def add_entry(self, entry: LeaderboardEntry) -> None:
        """Publish a run; raises `AliasAlreadySetError` if the run already has an entry."""
        ...

    def top(self, season_id: PlayableSeasonId, page: int, page_size: int) -> LeaderboardPage:
        """A page of the ranking (`page` from 1, `page_size` from 1 to 100).

        Raises `InvalidValueError` for invalid paging. A page past the end is empty.
        """
        ...

    def get_entry(self, run_id: RunId) -> RankedEntry | None:
        """The entry of a published run with its current rank, or `None`."""
        ...

    def record_score(self, season_id: PlayableSeasonId, run_id: RunId, mister_score: int) -> None:
        """Add a finished run to the season histogram; later calls for the same run are ignored.

        Raises `InvalidValueError` for a score outside 0..100.
        """
        ...

    def histogram(self, season_id: PlayableSeasonId) -> ScoreHistogram:
        """The score histogram of the season (all zeros if empty)."""
        ...
