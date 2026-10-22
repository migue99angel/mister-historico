"""In-memory `LeaderboardRepository`."""

from mister.leaderboard.application.ports import (
    MAX_PAGE_SIZE,
    SCORE_BUCKETS,
    AliasAlreadySetError,
    LeaderboardEntry,
    LeaderboardPage,
    RankedEntry,
    ScoreHistogram,
    require_score,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId, RunId


def _order(entry: LeaderboardEntry) -> tuple[int, object, str]:
    """Sort key: best score first, then earliest finish, then run id for a total order."""
    return (-entry.mister_score, entry.finished_at, str(entry.run_id))


class InMemoryLeaderboardRepository:
    """Keeps entries and recorded scores in dictionaries."""

    def __init__(self) -> None:
        self._entries: dict[RunId, LeaderboardEntry] = {}
        self._scores: dict[PlayableSeasonId, dict[RunId, int]] = {}

    def add_entry(self, entry: LeaderboardEntry) -> None:
        if entry.run_id in self._entries:
            raise AliasAlreadySetError(entry.run_id)
        self._entries[entry.run_id] = entry

    def top(self, season_id: PlayableSeasonId, page: int, page_size: int) -> LeaderboardPage:
        if page < 1 or not 1 <= page_size <= MAX_PAGE_SIZE:
            raise InvalidValueError(
                f"page must be >= 1 and page_size between 1 and {MAX_PAGE_SIZE}"
            )
        ranked = self._ranking(season_id)
        start = (page - 1) * page_size
        return LeaderboardPage(
            season_id=season_id,
            page=page,
            page_size=page_size,
            total=len(ranked),
            items=tuple(ranked[start : start + page_size]),
        )

    def get_entry(self, run_id: RunId) -> RankedEntry | None:
        entry = self._entries.get(run_id)
        if entry is None:
            return None
        return next(item for item in self._ranking(entry.season_id) if item.entry == entry)

    def record_score(self, season_id: PlayableSeasonId, run_id: RunId, mister_score: int) -> None:
        require_score(mister_score)
        self._scores.setdefault(season_id, {}).setdefault(run_id, mister_score)

    def histogram(self, season_id: PlayableSeasonId) -> ScoreHistogram:
        counts = [0] * SCORE_BUCKETS
        for score in self._scores.get(season_id, {}).values():
            counts[score] += 1
        return ScoreHistogram(season_id, tuple(counts))

    def _ranking(self, season_id: PlayableSeasonId) -> list[RankedEntry]:
        entries = sorted(
            (entry for entry in self._entries.values() if entry.season_id == season_id),
            key=_order,
        )
        return [RankedEntry(rank, entry) for rank, entry in enumerate(entries, start=1)]
