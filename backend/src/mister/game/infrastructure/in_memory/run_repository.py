"""In-memory `RunRepository` and `UnitOfWork`.

- `InMemoryRunStore` is the shared "database": committed runs and idempotent replies.
- `InMemoryRunRepository(store)` used on its own writes straight into the store (autocommit).
- `InMemoryUnitOfWork(store)` opens a transaction per `with`: its repository stages the writes
  of that transaction only, reads see the committed store plus the transaction's own writes,
  and `commit` applies them, so several units of work over the same store behave like several
  connections to one database. Like an `UPDATE ... WHERE version = :expected`, a write
  conflicts with a run another transaction committed after the one this transaction read.

Everything stored or returned is deep-copied, so callers never alias the store.
"""

import copy
from dataclasses import dataclass, field
from types import TracebackType
from typing import Self

from mister.game.application.ports import (
    ConcurrencyError,
    DecisionLogRewrittenError,
    IdempotencyKeyExistsError,
    IdempotencyRecord,
    NoActiveTransactionError,
    RunAlreadyExistsError,
    RunNotFoundError,
    RunRecord,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import RunId


@dataclass
class InMemoryRunStore:
    """Committed state shared by every repository and unit of work built on it."""

    runs: dict[RunId, RunRecord] = field(default_factory=dict)
    replies: dict[tuple[RunId, str], IdempotencyRecord] = field(default_factory=dict)


class InMemoryRunRepository:
    """`RunRepository` over a store; every write is committed immediately."""

    def __init__(self, store: InMemoryRunStore | None = None) -> None:
        self.store = store if store is not None else InMemoryRunStore()

    # --- storage primitives, overridden by the transactional repository

    def _read_run(self, run_id: RunId) -> RunRecord | None:
        return self.store.runs.get(run_id)

    def _write_run(self, record: RunRecord, *, expected_version: int | None) -> None:
        del expected_version
        self.store.runs[record.run_id] = copy.deepcopy(record)

    def _read_reply(self, run_id: RunId, key: str) -> IdempotencyRecord | None:
        return self.store.replies.get((run_id, key))

    def _write_reply(self, record: IdempotencyRecord) -> None:
        self.store.replies[(record.run_id, record.key)] = copy.deepcopy(record)

    # --- the port

    def add(self, record: RunRecord) -> None:
        if self._read_run(record.run_id) is not None:
            raise RunAlreadyExistsError(record.run_id)
        self._write_run(record, expected_version=None)

    def get(self, run_id: RunId) -> RunRecord | None:
        stored = self._read_run(run_id)
        return None if stored is None else copy.deepcopy(stored)

    def save(self, record: RunRecord, expected_version: int) -> None:
        stored = self._read_run(record.run_id)
        if stored is None:
            raise RunNotFoundError(record.run_id)
        if stored.version != expected_version:
            raise ConcurrencyError(record.run_id, expected=expected_version)
        if record.version != expected_version + 1:
            raise InvalidValueError(
                f"saved version must be {expected_version + 1}, got {record.version}"
            )
        for name in ("seed", "run_token_hash", "playable_season_id", "created_at"):
            if getattr(record, name) != getattr(stored, name):
                raise InvalidValueError(f"{name} is immutable")
        if record.decisions[: len(stored.decisions)] != stored.decisions:
            raise DecisionLogRewrittenError(record.run_id)
        self._write_run(record, expected_version=expected_version)

    def get_idempotent(self, run_id: RunId, key: str) -> IdempotencyRecord | None:
        stored = self._read_reply(run_id, key)
        return None if stored is None else copy.deepcopy(stored)

    def put_idempotent(self, record: IdempotencyRecord) -> None:
        if self._read_run(record.run_id) is None:
            raise RunNotFoundError(record.run_id)
        if self._read_reply(record.run_id, record.key) is not None:
            raise IdempotencyKeyExistsError(record.run_id, record.key)
        self._write_reply(record)


class _StagedRunRepository(InMemoryRunRepository):
    """The repository of one transaction: stages writes until `commit_to_store`."""

    def __init__(self, store: InMemoryRunStore) -> None:
        super().__init__(store)
        self._runs: dict[RunId, RunRecord] = {}
        self._base_versions: dict[RunId, int | None] = {}
        self._replies: dict[tuple[RunId, str], IdempotencyRecord] = {}

    def _read_run(self, run_id: RunId) -> RunRecord | None:
        return self._runs.get(run_id) or self.store.runs.get(run_id)

    def _write_run(self, record: RunRecord, *, expected_version: int | None) -> None:
        # Remember the committed version the transaction started from, to detect at commit
        # time a run that another transaction committed in the meantime.
        self._base_versions.setdefault(record.run_id, expected_version)
        self._runs[record.run_id] = copy.deepcopy(record)

    def _read_reply(self, run_id: RunId, key: str) -> IdempotencyRecord | None:
        return self._replies.get((run_id, key)) or self.store.replies.get((run_id, key))

    def _write_reply(self, record: IdempotencyRecord) -> None:
        self._replies[(record.run_id, record.key)] = copy.deepcopy(record)

    def commit_to_store(self) -> None:
        """Apply the staged writes; raise, changing nothing, if another commit got there first."""
        for run_id, base in self._base_versions.items():
            committed = self.store.runs.get(run_id)
            if base is None and committed is not None:
                raise RunAlreadyExistsError(run_id)
            if base is not None and (committed is None or committed.version != base):
                raise ConcurrencyError(run_id, expected=base)
        for slot in self._replies:
            if slot in self.store.replies:
                raise IdempotencyKeyExistsError(*slot)
        self.store.runs.update(self._runs)
        self.store.replies.update(self._replies)
        self.discard()

    def discard(self) -> None:
        self._runs.clear()
        self._base_versions.clear()
        self._replies.clear()


class InMemoryUnitOfWork:
    """One transaction per `with` over an `InMemoryRunStore`; uncommitted changes are dropped."""

    def __init__(self, store: InMemoryRunStore | None = None) -> None:
        self._store = store if store is not None else InMemoryRunStore()
        self._transaction: _StagedRunRepository | None = None

    @property
    def runs(self) -> InMemoryRunRepository:
        if self._transaction is None:
            raise NoActiveTransactionError
        return self._transaction

    def __enter__(self) -> Self:
        self._transaction = _StagedRunRepository(self._store)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._transaction = None  # staged writes die with the transaction

    def commit(self) -> None:
        self._active().commit_to_store()

    def rollback(self) -> None:
        self._active().discard()

    def _active(self) -> _StagedRunRepository:
        if self._transaction is None:
            raise NoActiveTransactionError
        return self._transaction
