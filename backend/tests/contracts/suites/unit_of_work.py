"""Contract of the `UnitOfWork` port.

Reuse: subclass `UnitOfWorkContract` and override `make_uow` with a factory of a unit of work
over an empty store. The same unit of work object is entered several times (one transaction
per `with`), as the use cases do.
"""

from collections.abc import Callable

import pytest

from mister.game.application.ports import UnitOfWork
from tests.contracts.suites.game_samples import (
    make_idempotency_record,
    make_run_record,
    next_version,
)

UowFactory = Callable[[], UnitOfWork]


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
    def make_uow(self) -> UowFactory:
        raise NotImplementedError

    def test_committed_changes_are_visible_to_the_next_transaction(
        self, make_uow: UowFactory
    ) -> None:
        uow = make_uow()
        record = make_run_record()

        with uow:
            uow.runs.add(record)
            uow.commit()

        with uow:
            assert uow.runs.get(record.run_id) == record

    def test_leaving_the_block_without_commit_rolls_back(self, make_uow: UowFactory) -> None:
        uow = make_uow()
        record = make_run_record()

        with uow:
            uow.runs.add(record)

        with uow:
            assert uow.runs.get(record.run_id) is None

    def test_explicit_rollback_discards_the_changes(self, make_uow: UowFactory) -> None:
        uow = make_uow()
        record = make_run_record()

        with uow:
            uow.runs.add(record)
            uow.rollback()

        with uow:
            assert uow.runs.get(record.run_id) is None

    def test_an_exception_rolls_back_and_propagates(self, make_uow: UowFactory) -> None:
        uow = make_uow()
        record = make_run_record()

        _fail_inside_transaction(uow, lambda tx: tx.runs.add(record))

        with uow:
            assert uow.runs.get(record.run_id) is None

    def test_a_rollback_keeps_what_an_earlier_transaction_committed(
        self, make_uow: UowFactory
    ) -> None:
        uow = make_uow()
        first = make_run_record()
        with uow:
            uow.runs.add(first)
            uow.commit()

        with uow:
            uow.runs.save(next_version(first), expected_version=1)
            uow.rollback()

        with uow:
            assert uow.runs.get(first.run_id) == first

    def test_a_run_and_its_idempotency_record_commit_together(self, make_uow: UowFactory) -> None:
        uow = make_uow()
        first = make_run_record()
        with uow:
            uow.runs.add(first)
            uow.commit()
        reply = make_idempotency_record(first, "key-1")

        with uow:
            uow.runs.save(next_version(first), expected_version=1)
            uow.runs.put_idempotent(reply)
            uow.commit()

        with uow:
            assert uow.runs.get_idempotent(first.run_id, "key-1") == reply
            loaded = uow.runs.get(first.run_id)
            assert loaded is not None
            assert loaded.version == 2

    def test_a_failure_after_a_save_leaves_neither_the_run_nor_the_reply(
        self, make_uow: UowFactory
    ) -> None:
        uow = make_uow()
        first = make_run_record()
        with uow:
            uow.runs.add(first)
            uow.commit()

        def work(tx: UnitOfWork) -> None:
            tx.runs.save(next_version(first), expected_version=1)
            tx.runs.put_idempotent(make_idempotency_record(first, "key-1"))

        _fail_inside_transaction(uow, work)

        with uow:
            assert uow.runs.get(first.run_id) == first
            assert uow.runs.get_idempotent(first.run_id, "key-1") is None
