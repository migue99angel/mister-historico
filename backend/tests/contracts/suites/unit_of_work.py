"""Contract of the `UnitOfWork` port.

Reuse: subclass `UnitOfWorkContract` and override `make_uows` with a factory that returns
**two units of work over the same empty store** (two connections to the same database). Each
unit of work is entered once per transaction, as the use cases do. Repositories are only usable
inside a transaction: `uow.runs` outside a `with` raises `NoActiveTransactionError`.

The concurrency cases (isolation and the lost update) are what T3.4 must satisfy with Postgres:
an `UPDATE` without `WHERE version = :expected` would fail them.
"""

from collections.abc import Callable

import pytest

from mister.game.application.ports import (
    ConcurrencyError,
    NoActiveTransactionError,
    UnitOfWork,
)
from tests.contracts.suites.game_samples import (
    make_idempotency_record,
    make_run_record,
    next_version,
)

UowPairFactory = Callable[[], tuple[UnitOfWork, UnitOfWork]]


class _Boom(Exception):  # noqa: N818
    """Raised inside a transaction to prove it is rolled back."""


def _fail_inside_transaction(uow: UnitOfWork, work: Callable[[UnitOfWork], None]) -> None:
    """Run `work` in a transaction that then fails, and check the failure propagates."""

    def transaction() -> None:
        with uow:
            work(uow)
            raise _Boom

    with pytest.raises(_Boom):
        transaction()


class UnitOfWorkContract:
    """Behaviour every `UnitOfWork` must have."""

    @pytest.fixture
    def make_uows(self) -> UowPairFactory:
        raise NotImplementedError

    # ------------------------------------------------------------------ one unit of work

    def test_committed_changes_are_visible_to_the_next_transaction(
        self, make_uows: UowPairFactory
    ) -> None:
        uow, _ = make_uows()
        record = make_run_record()

        with uow:
            uow.runs.add(record)
            uow.commit()

        with uow:
            assert uow.runs.get(record.run_id) == record

    def test_a_transaction_sees_its_own_uncommitted_changes(
        self, make_uows: UowPairFactory
    ) -> None:
        uow, _ = make_uows()
        record = make_run_record()

        with uow:
            uow.runs.add(record)

            assert uow.runs.get(record.run_id) == record

    def test_leaving_the_block_without_commit_rolls_back(self, make_uows: UowPairFactory) -> None:
        uow, _ = make_uows()
        record = make_run_record()

        with uow:
            uow.runs.add(record)

        with uow:
            assert uow.runs.get(record.run_id) is None

    def test_explicit_rollback_discards_the_changes(self, make_uows: UowPairFactory) -> None:
        uow, _ = make_uows()
        record = make_run_record()

        with uow:
            uow.runs.add(record)
            uow.rollback()

        with uow:
            assert uow.runs.get(record.run_id) is None

    def test_an_exception_rolls_back_and_propagates(self, make_uows: UowPairFactory) -> None:
        uow, _ = make_uows()
        record = make_run_record()

        _fail_inside_transaction(uow, lambda tx: tx.runs.add(record))

        with uow:
            assert uow.runs.get(record.run_id) is None

    def test_a_rollback_keeps_what_an_earlier_transaction_committed(
        self, make_uows: UowPairFactory
    ) -> None:
        uow, _ = make_uows()
        first = make_run_record()
        with uow:
            uow.runs.add(first)
            uow.commit()

        with uow:
            uow.runs.save(next_version(first), expected_version=0)
            uow.rollback()

        with uow:
            assert uow.runs.get(first.run_id) == first

    def test_a_run_and_its_idempotency_record_commit_together(
        self, make_uows: UowPairFactory
    ) -> None:
        uow, _ = make_uows()
        first = make_run_record()
        with uow:
            uow.runs.add(first)
            uow.commit()
        reply = make_idempotency_record(first, "idem-key-1")

        with uow:
            uow.runs.save(next_version(first), expected_version=0)
            uow.runs.put_idempotent(reply)
            uow.commit()

        with uow:
            assert uow.runs.get_idempotent(first.run_id, "idem-key-1") == reply
            loaded = uow.runs.get(first.run_id)
            assert loaded is not None
            assert loaded.version == 1

    def test_a_failure_after_a_save_leaves_neither_the_run_nor_the_reply(
        self, make_uows: UowPairFactory
    ) -> None:
        uow, _ = make_uows()
        first = make_run_record()
        with uow:
            uow.runs.add(first)
            uow.commit()

        def work(tx: UnitOfWork) -> None:
            tx.runs.save(next_version(first), expected_version=0)
            tx.runs.put_idempotent(make_idempotency_record(first, "idem-key-1"))

        _fail_inside_transaction(uow, work)

        with uow:
            assert uow.runs.get(first.run_id) == first
            assert uow.runs.get_idempotent(first.run_id, "idem-key-1") is None

    def test_repositories_are_not_available_outside_a_transaction(
        self, make_uows: UowPairFactory
    ) -> None:
        uow, _ = make_uows()

        with pytest.raises(NoActiveTransactionError):
            _ = uow.runs

    def test_repositories_are_not_available_after_the_transaction_ended(
        self, make_uows: UowPairFactory
    ) -> None:
        uow, _ = make_uows()
        with uow:
            pass

        with pytest.raises(NoActiveTransactionError):
            _ = uow.runs

    # ------------------------------------------------------------------ two units of work

    def test_uncommitted_changes_are_invisible_to_another_transaction(
        self, make_uows: UowPairFactory
    ) -> None:
        writer, reader = make_uows()
        record = make_run_record()

        with writer, reader:
            writer.runs.add(record)

            assert reader.runs.get(record.run_id) is None

    def test_changes_become_visible_to_others_once_committed(
        self, make_uows: UowPairFactory
    ) -> None:
        writer, reader = make_uows()
        record = make_run_record()

        with writer, reader:
            writer.runs.add(record)
            writer.commit()

            assert reader.runs.get(record.run_id) == record

    def test_a_rollback_does_not_undo_what_another_transaction_committed(
        self, make_uows: UowPairFactory
    ) -> None:
        loser, winner = make_uows()
        record = make_run_record()

        with loser, winner:
            winner.runs.add(record)
            winner.commit()
            loser.rollback()

        with loser:
            assert loser.runs.get(record.run_id) == record

    def test_a_rollback_keeps_the_commit_of_another_transaction_made_after_it_began(
        self, make_uows: UowPairFactory
    ) -> None:
        first, second = make_uows()
        a, b = make_run_record(run_number=1), make_run_record(run_number=2)

        with first:
            first.runs.add(a)
            with second:
                second.runs.add(b)
                second.commit()
            # `first` rolls back on exit: only `a` may disappear.

        with second:
            assert second.runs.get(a.run_id) is None
            assert second.runs.get(b.run_id) == b

    def test_two_transactions_that_read_the_same_version_cannot_both_save(
        self, make_uows: UowPairFactory
    ) -> None:
        first, second = make_uows()
        base = make_run_record()
        with first:
            first.runs.add(base)
            first.commit()

        with first, second:
            read_by_first = first.runs.get(base.run_id)
            read_by_second = second.runs.get(base.run_id)
            assert read_by_first is not None
            assert read_by_second is not None
            first.runs.save(next_version(read_by_first), expected_version=read_by_first.version)
            first.commit()

            with pytest.raises(ConcurrencyError):
                second.runs.save(
                    next_version(read_by_second, extra_decisions=1),
                    expected_version=read_by_second.version,
                )

        with first:
            stored = first.runs.get(base.run_id)
            assert stored is not None
            assert stored.version == 1
            assert stored.decisions == ()
