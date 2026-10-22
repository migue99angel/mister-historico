"""Contract of the `LeaderboardRepository` port.

Reuse: subclass `LeaderboardRepositoryContract` and override `make_repo` with a factory of an
empty repository (T5.2 returns one backed by Postgres).
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from mister.leaderboard.application.ports import (
    AliasAlreadySetError,
    LeaderboardEntry,
    LeaderboardRepository,
    VerdictKind,
)
from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId, RunId

RepoFactory = Callable[[], LeaderboardRepository]

SEASON = PlayableSeasonId("test-fc-2000-01")
OTHER_SEASON = PlayableSeasonId("mock-city-2001-02")
T0 = datetime(2026, 10, 22, 10, 0, tzinfo=UTC)


def make_entry(
    number: int,
    score: int,
    *,
    finished_after: int = 0,
    season: PlayableSeasonId = SEASON,
    alias: str | None = None,
) -> LeaderboardEntry:
    """An entry; `finished_after` is the number of minutes after `T0` the run ended."""
    return LeaderboardEntry(
        run_id=RunId(uuid.UUID(int=number)),
        season_id=season,
        alias=alias or f"Mister {number}",
        mister_score=score,
        verdict_kind=VerdictKind.SURPASSED_HISTORY,
        finished_at=T0 + timedelta(minutes=finished_after),
    )


class LeaderboardRepositoryContract:
    """Behaviour every `LeaderboardRepository` must have."""

    @pytest.fixture
    def make_repo(self) -> RepoFactory:
        raise NotImplementedError

    # ------------------------------------------------------------------ ranking

    def test_top_orders_by_score_descending(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        for entry in (make_entry(1, 40), make_entry(2, 90), make_entry(3, 65)):
            repo.add_entry(entry)

        page = repo.top(SEASON, page=1, page_size=10)

        assert [item.entry.mister_score for item in page.items] == [90, 65, 40]
        assert [item.rank for item in page.items] == [1, 2, 3]

    def test_a_tie_on_score_is_won_by_the_run_that_finished_first(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        repo.add_entry(make_entry(1, 70, finished_after=30))
        repo.add_entry(make_entry(2, 70, finished_after=10))
        repo.add_entry(make_entry(3, 70, finished_after=20))

        page = repo.top(SEASON, page=1, page_size=10)

        assert [item.entry.run_id for item in page.items] == [
            make_entry(2, 0).run_id,
            make_entry(3, 0).run_id,
            make_entry(1, 0).run_id,
        ]

    def test_a_full_tie_is_ordered_the_same_way_every_time(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        for number in (3, 1, 2):
            repo.add_entry(make_entry(number, 70))

        first = repo.top(SEASON, page=1, page_size=10)
        again = repo.top(SEASON, page=1, page_size=10)

        assert first == again

    def test_score_beats_finishing_earlier(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        repo.add_entry(make_entry(1, 50, finished_after=0))
        repo.add_entry(make_entry(2, 80, finished_after=99))

        page = repo.top(SEASON, page=1, page_size=10)

        assert page.items[0].entry.run_id == make_entry(2, 0).run_id

    def test_pages_are_consecutive_slices_with_continuing_ranks(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        for number in range(1, 6):
            repo.add_entry(make_entry(number, number * 10))

        second = repo.top(SEASON, page=2, page_size=2)

        assert (second.page, second.page_size, second.total) == (2, 2, 5)
        assert [item.rank for item in second.items] == [3, 4]
        assert [item.entry.mister_score for item in second.items] == [30, 20]

    def test_a_page_past_the_end_is_empty_but_reports_the_total(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        repo.add_entry(make_entry(1, 10))

        page = repo.top(SEASON, page=5, page_size=20)

        assert page.items == ()
        assert page.total == 1

    def test_an_empty_season_has_an_empty_page(self, make_repo: RepoFactory) -> None:
        page = make_repo().top(SEASON, page=1, page_size=20)

        assert (page.items, page.total, page.season_id) == ((), 0, SEASON)

    def test_seasons_have_independent_leaderboards(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        repo.add_entry(make_entry(1, 10, season=SEASON))
        repo.add_entry(make_entry(2, 99, season=OTHER_SEASON))

        page = repo.top(SEASON, page=1, page_size=10)

        assert page.total == 1
        assert page.items[0].entry.run_id == make_entry(1, 0).run_id

    @pytest.mark.parametrize(("page", "page_size"), [(0, 20), (-1, 20), (1, 0), (1, 101)])
    def test_invalid_paging_is_rejected(
        self, make_repo: RepoFactory, page: int, page_size: int
    ) -> None:
        with pytest.raises(InvalidValueError):
            make_repo().top(SEASON, page=page, page_size=page_size)

    # ------------------------------------------------------------------ entries and alias

    def test_get_entry_returns_the_entry_with_its_rank(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        repo.add_entry(make_entry(1, 40))
        repo.add_entry(make_entry(2, 90))

        ranked = repo.get_entry(make_entry(1, 0).run_id)

        assert ranked is not None
        assert ranked.rank == 2
        assert ranked.entry == make_entry(1, 40)

    def test_get_entry_of_an_unpublished_run_is_none(self, make_repo: RepoFactory) -> None:
        assert make_repo().get_entry(RunId.new()) is None

    def test_a_run_can_set_its_alias_only_once(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        repo.add_entry(make_entry(1, 40, alias="First Alias"))

        with pytest.raises(AliasAlreadySetError) as caught:
            repo.add_entry(make_entry(1, 99, alias="Second Alias"))

        assert isinstance(caught.value, DomainError)
        assert caught.value.code == "alias_already_set"
        stored = repo.get_entry(make_entry(1, 0).run_id)
        assert stored is not None
        assert stored.entry.alias == "First Alias"
        assert repo.top(SEASON, page=1, page_size=10).total == 1

    # ------------------------------------------------------------------ histogram

    def test_the_histogram_of_an_empty_season_has_a_zero_bucket_per_score(
        self, make_repo: RepoFactory
    ) -> None:
        histogram = make_repo().histogram(SEASON)

        assert histogram.counts == (0,) * 101
        assert histogram.total == 0

    def test_the_histogram_counts_how_many_runs_got_each_score(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        for number, score in enumerate((0, 50, 50, 50, 100), start=1):
            repo.record_score(SEASON, make_entry(number, score).run_id, score)

        histogram = repo.histogram(SEASON)

        assert histogram.season_id == SEASON
        assert (histogram.counts[0], histogram.counts[50], histogram.counts[100]) == (1, 3, 1)
        assert histogram.total == 5
        assert sum(histogram.counts) == 5

    def test_a_run_counts_once_in_the_histogram(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        run_id = make_entry(1, 0).run_id

        repo.record_score(SEASON, run_id, 40)
        repo.record_score(SEASON, run_id, 90)

        histogram = repo.histogram(SEASON)
        assert histogram.total == 1
        assert histogram.counts[40] == 1

    def test_the_histogram_includes_runs_that_never_published_an_alias(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        repo.record_score(SEASON, RunId.new(), 70)

        assert repo.histogram(SEASON).total == 1
        assert repo.top(SEASON, page=1, page_size=10).total == 0

    def test_histograms_are_per_season(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        repo.record_score(SEASON, RunId.new(), 70)
        repo.record_score(OTHER_SEASON, RunId.new(), 20)

        assert repo.histogram(SEASON).counts[70] == 1
        assert repo.histogram(SEASON).counts[20] == 0
        assert repo.histogram(OTHER_SEASON).total == 1

    @pytest.mark.parametrize("score", [-1, 101])
    def test_a_score_outside_0_to_100_is_rejected(self, make_repo: RepoFactory, score: int) -> None:
        with pytest.raises(InvalidValueError):
            make_repo().record_score(SEASON, RunId.new(), score)
