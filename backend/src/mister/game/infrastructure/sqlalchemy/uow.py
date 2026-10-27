"""Transactional unit of work for Game's SQL repositories."""

from sqlalchemy.engine import Connection, Engine, RootTransaction

from mister.game.application.ports import NoActiveTransactionError
from mister.game.infrastructure.sqlalchemy.runs import SqlRunRepository


class SqlUnitOfWork:
    """Own a connection and transaction for one command."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._connection: Connection | None = None
        self._transaction: RootTransaction | None = None
        self._runs: SqlRunRepository | None = None

    @property
    def runs(self) -> SqlRunRepository:
        if self._connection is None or self._runs is None:
            raise NoActiveTransactionError()
        return self._runs

    def __enter__(self) -> "SqlUnitOfWork":
        if self._connection is not None:
            raise RuntimeError("unit of work is already active")
        self._connection = self._engine.connect()
        self._transaction = self._connection.begin()
        self._runs = SqlRunRepository(self._engine, self._connection)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._transaction is not None and self._transaction.is_active:
            self._transaction.rollback()
        if self._connection is not None:
            self._connection.close()
        self._transaction = None
        self._connection = None
        self._runs = None

    def commit(self) -> None:
        transaction = self._require_transaction()
        connection = self._active_connection()
        transaction.commit()
        self._transaction = connection.begin()

    def rollback(self) -> None:
        transaction = self._require_transaction()
        connection = self._active_connection()
        transaction.rollback()
        self._transaction = connection.begin()

    def _active_connection(self) -> Connection:
        if self._connection is None:
            raise NoActiveTransactionError()
        return self._connection

    def _require_transaction(self) -> RootTransaction:
        if self._transaction is None or not self._transaction.is_active:
            raise NoActiveTransactionError()
        return self._transaction
