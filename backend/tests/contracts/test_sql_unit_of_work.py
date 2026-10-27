"""The PostgreSQL unit of work must satisfy the shared transaction contract."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from testcontainers.community.postgres import PostgresContainer

from mister.game.application.ports import UnitOfWork
from mister.game.infrastructure.sqlalchemy.uow import SqlUnitOfWork
from tests.contracts.suites.unit_of_work import UnitOfWorkContract

pytestmark = pytest.mark.integration
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


@pytest.fixture(scope="module")
def engine() -> Iterator[sa.Engine]:
    with PostgresContainer("postgres:16.15", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(ALEMBIC_INI))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        database = sa.create_engine(url)
        try:
            yield database
        finally:
            database.dispose()


class TestSqlUnitOfWork(UnitOfWorkContract):
    @pytest.fixture
    def make_uows(self, engine: sa.Engine):
        def factory() -> tuple[UnitOfWork, UnitOfWork]:
            return SqlUnitOfWork(engine), SqlUnitOfWork(engine)

        return factory
