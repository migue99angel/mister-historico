"""Contract of the `RunRepository` port (snapshot + decision log + optimistic locking).

Reuse: subclass `RunRepositoryContract` in a `Test...` class and override the `make_repo`
fixture with a factory of an empty repository (T3.4 returns one backed by Postgres).
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta
from typing import cast

import pytest

from mister.game.application.ports import (
    ConcurrencyError,
    DecisionLogRewrittenError,
    IdempotencyKeyExistsError,
    RunAlreadyExistsError,
    RunNotFoundError,
    RunRepository,
    RunStatus,
)
from mister.shared_kernel.errors import DomainError, InvalidValueError
from mister.shared_kernel.ids import PlayableSeasonId, RunId
from mister.shared_kernel.seed import Seed
from tests.contracts.suites.game_samples import (
    T0,
    make_decision,
    make_idempotency_record,
    make_run_record,
    next_version,
)

RepoFactory = Callable[[], RunRepository]


class RunRepositoryContract:
    """Behaviour every `RunRepository` must have."""

    @pytest.fixture
    def make_repo(self) -> RepoFactory:
        raise NotImplementedError

    # ------------------------------------------------------------------ add and get

    def test_get_returns_an_added_run_equivalent_to_what_was_stored(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        record = make_run_record(decisions=2)

        repo.add(record)

        assert repo.get(record.run_id) == record

    def test_get_unknown_run_returns_none(self, make_repo: RepoFactory) -> None:
        assert make_repo().get(RunId.new()) is None

    def test_adding_the_same_run_twice_is_rejected(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        repo.add(make_run_record())

        with pytest.raises(RunAlreadyExistsError) as caught:
            repo.add(make_run_record())

        assert isinstance(caught.value, DomainError)
        assert caught.value.code == "run_already_exists"

    def test_runs_do_not_interfere_with_each_other(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        first, second = make_run_record(run_number=1), make_run_record(run_number=2)
        repo.add(first)
        repo.add(second)

        repo.save(next_version(first), expected_version=0)

        assert repo.get(second.run_id) == second

    def test_the_stored_snapshot_is_isolated_from_the_caller(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        record = make_run_record()
        repo.add(record)

        loaded = repo.get(record.run_id)
        assert loaded is not None
        cast("dict[str, object]", loaded.snapshot)["block"] = 99

        reloaded = repo.get(record.run_id)
        assert reloaded == record

    # ------------------------------------------------------------------ save

    def test_save_then_get_returns_the_new_snapshot_version_and_decisions(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        first = make_run_record(decisions=1)
        repo.add(first)
        second = next_version(first, extra_decisions=2)

        repo.save(second, expected_version=first.version)

        saved = repo.get(first.run_id)
        assert saved == second
        assert saved is not None
        assert saved.version == 1
        assert [d.sequence for d in saved.decisions] == [1, 2, 3]

    def test_save_persists_the_final_status(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        first = make_run_record()
        repo.add(first)
        finished = replace(next_version(first), status=RunStatus.FINISHED)

        repo.save(finished, expected_version=0)

        saved = repo.get(first.run_id)
        assert saved is not None
        assert saved.status is RunStatus.FINISHED

    def test_save_with_a_stale_version_raises_concurrency_error_and_keeps_the_stored_run(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        first = make_run_record()
        repo.add(first)
        second = next_version(first)
        repo.save(second, expected_version=0)

        with pytest.raises(ConcurrencyError) as caught:
            repo.save(next_version(first, extra_decisions=1), expected_version=0)

        assert caught.value.code == "version_conflict"
        assert repo.get(first.run_id) == second

    def test_two_writers_that_read_the_same_version_cannot_both_save(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        base = make_run_record()
        repo.add(base)
        loaded_by_a = repo.get(base.run_id)
        loaded_by_b = repo.get(base.run_id)
        assert loaded_by_a is not None
        assert loaded_by_b is not None

        repo.save(next_version(loaded_by_a), expected_version=loaded_by_a.version)

        with pytest.raises(ConcurrencyError):
            repo.save(next_version(loaded_by_b, extra_decisions=1), loaded_by_b.version)

    def test_the_saved_version_must_follow_the_expected_one(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        first = make_run_record()
        repo.add(first)

        with pytest.raises(InvalidValueError, match="version"):
            repo.save(replace(next_version(first), version=5), expected_version=0)

        assert repo.get(first.run_id) == first

    def test_saving_an_unknown_run_raises_run_not_found(self, make_repo: RepoFactory) -> None:
        repo = make_repo()

        with pytest.raises(RunNotFoundError) as caught:
            repo.save(next_version(make_run_record()), expected_version=0)

        assert caught.value.code == "run_not_found"

    def test_the_decision_log_is_append_only(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        first = make_run_record(decisions=2)
        repo.add(first)
        rewritten = replace(
            next_version(first), decisions=(make_decision(1, option="z"), make_decision(2))
        )

        with pytest.raises(DecisionLogRewrittenError) as caught:
            repo.save(rewritten, expected_version=0)

        assert caught.value.code == "decision_log_rewritten"
        assert repo.get(first.run_id) == first

    def test_the_decision_log_cannot_shrink(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        first = make_run_record(decisions=2)
        repo.add(first)

        with pytest.raises(DecisionLogRewrittenError):
            repo.save(replace(next_version(first), decisions=first.decisions[:1]), 0)

    # ------------------------------------------------------------------ idempotency

    def test_an_unknown_idempotency_key_returns_none(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        record = make_run_record()
        repo.add(record)

        assert repo.get_idempotent(record.run_id, "never-used") is None

    def test_idempotency_returns_the_same_response_that_was_stored(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        run = make_run_record()
        repo.add(run)
        stored = make_idempotency_record(run, "idem-key-1", request_hash="abc")

        repo.put_idempotent(stored)

        first = repo.get_idempotent(run.run_id, "idem-key-1")
        again = repo.get_idempotent(run.run_id, "idem-key-1")
        assert first == stored
        assert again == first

    def test_idempotency_keys_are_scoped_to_their_run(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        one, two = make_run_record(run_number=1), make_run_record(run_number=2)
        repo.add(one)
        repo.add(two)
        repo.put_idempotent(make_idempotency_record(one, "same-key-x", request_hash="for-one"))
        repo.put_idempotent(make_idempotency_record(two, "same-key-x", request_hash="for-two"))

        stored_one = repo.get_idempotent(one.run_id, "same-key-x")
        stored_two = repo.get_idempotent(two.run_id, "same-key-x")

        assert stored_one is not None
        assert stored_two is not None
        assert (stored_one.request_hash, stored_two.request_hash) == ("for-one", "for-two")

    def test_a_used_idempotency_key_is_never_overwritten(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        run = make_run_record()
        repo.add(run)
        original = make_idempotency_record(run, "idem-key-1", request_hash="original")
        repo.put_idempotent(original)

        with pytest.raises(IdempotencyKeyExistsError) as caught:
            repo.put_idempotent(make_idempotency_record(run, "idem-key-1", request_hash="other"))

        assert caught.value.code == "idempotency_key_exists"
        assert repo.get_idempotent(run.run_id, "idem-key-1") == original

    def test_idempotency_does_not_depend_on_the_run_version(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        run = make_run_record()
        repo.add(run)
        stored = make_idempotency_record(run, "idem-key-1")
        repo.put_idempotent(stored)

        repo.save(next_version(run), expected_version=0)

        assert repo.get_idempotent(run.run_id, "idem-key-1") == stored

    # ------------------------------------------------------------------ what the fake must not hide

    def test_idempotency_of_an_unknown_run_cannot_be_stored(self, make_repo: RepoFactory) -> None:
        repo = make_repo()

        with pytest.raises(RunNotFoundError):
            repo.put_idempotent(make_idempotency_record(make_run_record()))

    def test_the_snapshot_is_stored_as_json_would_return_it(self, make_repo: RepoFactory) -> None:
        repo = make_repo()
        record = replace(
            make_run_record(), snapshot={"squad": ("a", "b"), 7: {"nested": (1, 2)}, "ok": True}
        )
        repo.add(record)

        loaded = repo.get(record.run_id)

        expected = {"squad": ["a", "b"], "7": {"nested": [1, 2]}, "ok": True}
        assert loaded is not None
        assert loaded.snapshot == expected
        assert record.snapshot == expected

    def test_the_idempotent_response_is_stored_as_json_would_return_it(
        self, make_repo: RepoFactory
    ) -> None:
        repo = make_repo()
        run = make_run_record()
        repo.add(run)
        reply = replace(make_idempotency_record(run), response={"ids": (1, 2), 3: None})

        repo.put_idempotent(reply)

        stored = repo.get_idempotent(run.run_id, reply.key)
        assert stored is not None
        assert stored.response == {"ids": [1, 2], "3": None}

    @pytest.mark.parametrize(
        "change",
        [
            {"seed": Seed(999)},
            {"run_token_hash": "another-hash"},
            {"playable_season_id": PlayableSeasonId("other-1999-00")},
            {"created_at": T0 + timedelta(days=1), "updated_at": T0 + timedelta(days=2)},
        ],
        ids=["seed", "run_token_hash", "playable_season_id", "created_at"],
    )
    def test_save_cannot_change_what_identifies_the_run(
        self, make_repo: RepoFactory, change: dict[str, object]
    ) -> None:
        repo = make_repo()
        first = make_run_record()
        repo.add(first)

        with pytest.raises(InvalidValueError, match="immutable"):
            repo.save(replace(next_version(first), **change), expected_version=0)  # type: ignore[arg-type]

        assert repo.get(first.run_id) == first
