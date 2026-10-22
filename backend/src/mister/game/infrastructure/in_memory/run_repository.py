"""In-memory `RunRepository` and `UnitOfWork`.

The repository deep-copies what it stores and returns, so callers can never alias its state
(a real adapter returns fresh objects too). The unit of work gives it transactional behaviour
by restoring a copy of the state taken on `__enter__`.
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
    RunAlreadyExistsError,
    RunNotFoundError,
    RunRecord,
)
from mister.shared_kernel.errors import InvalidValueError
from mister.shared_kernel.ids import RunId


@dataclass
class _State:
    runs: dict[RunId, RunRecord] = field(default_factory=dict)
    replies: dict[tuple[RunId, str], IdempotencyRecord] = field(default_factory=dict)


class InMemoryRunRepository:
    """Dictionary-backed `RunRepository`."""

    def __init__(self) -> None:
        self._state = _State()

    def add(self, record: RunRecord) -> None:
        if record.run_id in self._state.runs:
            raise RunAlreadyExistsError(record.run_id)
        self._state.runs[record.run_id] = copy.deepcopy(record)

    def get(self, run_id: RunId) -> RunRecord | None:
        stored = self._state.runs.get(run_id)
        return None if stored is None else copy.deepcopy(stored)

    def save(self, record: RunRecord, expected_version: int) -> None:
        stored = self._state.runs.get(record.run_id)
        if stored is None:
            raise RunNotFoundError(record.run_id)
        if stored.version != expected_version:
            raise ConcurrencyError(record.run_id, expected=expected_version)
        if record.version != expected_version + 1:
            raise InvalidValueError(
                f"saved version must be {expected_version + 1}, got {record.version}"
            )
        if record.decisions[: len(stored.decisions)] != stored.decisions:
            raise DecisionLogRewrittenError(record.run_id)
        self._state.runs[record.run_id] = copy.deepcopy(record)

    def get_idempotent(self, run_id: RunId, key: str) -> IdempotencyRecord | None:
        stored = self._state.replies.get((run_id, key))
        return None if stored is None else copy.deepcopy(stored)

    def put_idempotent(self, record: IdempotencyRecord) -> None:
        slot = (record.run_id, record.key)
        if slot in self._state.replies:
            raise IdempotencyKeyExistsError(record.run_id, record.key)
        self._state.replies[slot] = copy.deepcopy(record)

    # Used by `InMemoryUnitOfWork`; not part of the port.

    def export_state(self) -> _State:
        return copy.deepcopy(self._state)

    def restore_state(self, state: _State) -> None:
        self._state = copy.deepcopy(state)


class InMemoryUnitOfWork:
    """Transaction over an `InMemoryRunRepository`: uncommitted changes are rolled back."""

    def __init__(self, runs: InMemoryRunRepository | None = None) -> None:
        self._runs = runs if runs is not None else InMemoryRunRepository()
        self._checkpoint = self._runs.export_state()

    @property
    def runs(self) -> InMemoryRunRepository:
        return self._runs

    def __enter__(self) -> Self:
        self._checkpoint = self._runs.export_state()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.rollback()

    def commit(self) -> None:
        self._checkpoint = self._runs.export_state()

    def rollback(self) -> None:
        self._runs.restore_state(self._checkpoint)
